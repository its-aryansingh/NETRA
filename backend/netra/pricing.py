"""NETRA deterministic pricing core with cryptographic provenance.

Retrieves and caches AWS resource pricing in USD/hour and computes INR/hour.
Resolution order:
1. DynamoDB cache (`netra_price_cache` with 24h TTL)
2. AWS Price List API (`boto3.client('pricing', region_name='us-east-1')`)
3. Module-level static fallback dictionary (`FALLBACK_USD_HOUR`)

Every API fetch is hashed with SHA-256 for provable provenance (`price_ref="sha256:<hex>"`).
Fallback fetches are explicitly marked (`price_ref="fallback:<sub_type>"`).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

from netra.config import (
    BUCKET_PRICE_DOCS,
    PRICING_REGION,
    REGION,
    REGION_LONG_NAMES,
    TABLE_PRICE_CACHE,
    USD_INR,
    get_logger,
)
from netra.models import PriceDoc

logger = get_logger("netra.pricing")

# Fallback hourly rates in USD. Covers critical EC2, EBS, and NAT resources.
# If AWS Price List API throttles or fails, this prevents downtime.
FALLBACK_USD_HOUR: Dict[str, float] = {
    # EC2 instances (Linux, on-demand, ap-south-1)
    "t3.micro": 0.0112,
    "t3.small": 0.0224,
    "t3.medium": 0.0448,
    "m5.large": 0.106,
    "m5.xlarge": 0.212,
    "m5.4xlarge": 0.848,
    "c5.2xlarge": 0.376,
    "c5.4xlarge": 0.752,
    "g5.xlarge": 1.006,
    # EBS Storage (gp3 per GB-month)
    "gp3": 0.0912,
    # NAT Gateway (per hour)
    "nat": 0.056,
    "natgateway": 0.056,
}

# Module-level memory cache for verify_price_ref lookups during runs
_LOCAL_PRICE_DOC_STORE: Dict[str, str] = {}


def canonicalize_doc(doc: Any) -> str:
    """Canonicalize a pricing JSON document with sorted keys and compact separators."""
    if isinstance(doc, str):
        parsed = json.loads(doc)
    else:
        parsed = doc
    return json.dumps(parsed, sort_keys=True, separators=(",", ":"))


def hash_raw_doc(raw_doc: str) -> str:
    """Compute SHA-256 hex digest of a canonical raw document."""
    canonical = canonicalize_doc(raw_doc)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _extract_ondemand_usd(terms_dict: Dict[str, Any]) -> float:
    """Extract OnDemand USD price per unit from an AWS Price List product terms block."""
    ondemand = terms_dict.get("OnDemand", {})
    if not ondemand:
        raise ValueError("No OnDemand terms found in price document")

    for term_offer in ondemand.values():
        dimensions = term_offer.get("priceDimensions", {})
        for dimension in dimensions.values():
            price_per_unit = dimension.get("pricePerUnit", {})
            if "USD" in price_per_unit:
                return float(price_per_unit["USD"])

    raise ValueError("No USD pricePerUnit discovered in terms")


def _get_cached_price(
    dynamodb_client: Any,
    pk: str,
    table_name: str = TABLE_PRICE_CACHE,
) -> Optional[PriceDoc]:
    """Attempt to retrieve an unexpired price item from DynamoDB cache."""
    if dynamodb_client is None:
        return None

    try:
        response = dynamodb_client.get_item(
            TableName=table_name,
            Key={"pk": {"S": pk}} if hasattr(dynamodb_client, "get_item") else {"pk": pk},
        )
        item = response.get("Item")
        if not item:
            return None

        # Format item attributes if returned in low-level DynamoDB wire format
        if "pk" in item and isinstance(item["pk"], dict) and "S" in item["pk"]:
            # Wire format conversion
            raw_item: Dict[str, Any] = {}
            for k, v in item.items():
                if "S" in v:
                    raw_item[k] = v["S"]
                elif "N" in v:
                    raw_item[k] = float(v["N"]) if "." in v["N"] else int(v["N"])
                elif "NULL" in v:
                    raw_item[k] = None
                else:
                    raw_item[k] = v
            item = raw_item

        now = int(time.time())
        ttl = item.get("ttl")
        if ttl is not None and int(ttl) < now:
            logger.info(
                f"Cache item for {pk} expired at {ttl} (current {now})",
                extra={"pk": pk, "ttl": ttl},
            )
            return None

        doc = PriceDoc.from_dict(item)
        if doc.raw_doc and doc.price_ref.startswith("sha256:"):
            _LOCAL_PRICE_DOC_STORE[doc.price_ref] = doc.raw_doc
        return doc
    except Exception as err:
        logger.warning(
            f"Failed checking DynamoDB price cache: {err}",
            extra={"pk": pk, "error": str(err)},
        )
        return None


def _upload_raw_doc_to_s3(
    raw_doc: str,
    sha256_hex: str,
    s3_client: Any = None,
    bucket_name: Optional[str] = None,
) -> Optional[str]:
    """Upload raw price document to S3 at prices/<sha256>.json. Returns s3_key if uploaded."""
    bucket = bucket_name or BUCKET_PRICE_DOCS or os.getenv("NETRA_PRICE_DOCS_BUCKET", "")
    if not bucket or s3_client is None:
        return None
    s3_key = f"prices/{sha256_hex}.json"
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=raw_doc.encode("utf-8"),
            ContentType="application/json",
        )
        logger.debug(f"Stored price document provenance in s3://{bucket}/{s3_key}")
        return s3_key
    except Exception as exc:
        logger.debug(f"S3 price upload skipped ({exc})")
        return None


def _get_raw_doc_from_s3(
    s3_key: str,
    s3_client: Any = None,
    bucket_name: Optional[str] = None,
) -> Optional[str]:
    """Retrieve raw price document from S3 provenance bucket."""
    bucket = bucket_name or BUCKET_PRICE_DOCS or os.getenv("NETRA_PRICE_DOCS_BUCKET", "")
    if not bucket or s3_client is None:
        return None
    try:
        resp = s3_client.get_object(Bucket=bucket, Key=s3_key)
        body = resp["Body"].read()
        if isinstance(body, bytes):
            return body.decode("utf-8")
        return str(body)
    except Exception as exc:
        logger.debug(f"S3 price retrieval skipped for s3://{bucket}/{s3_key}: {exc}")
        return None


def _put_cached_price(
    dynamodb_client: Any,
    price_doc: PriceDoc,
    table_name: str = TABLE_PRICE_CACHE,
    s3_client: Any = None,
    bucket_name: Optional[str] = None,
) -> None:
    """Store priced document in DynamoDB cache with 24h TTL, offloading raw_doc to S3."""
    if dynamodb_client is None:
        return

    # Prompt G: Offload raw price document to S3 if s3_client and bucket are configured
    s3_key = price_doc.s3_key
    if not s3_key and price_doc.raw_doc and price_doc.price_ref.startswith("sha256:"):
        sha256_hex = price_doc.price_ref.split(":", 1)[1]
        uploaded_key = _upload_raw_doc_to_s3(price_doc.raw_doc, sha256_hex, s3_client, bucket_name)
        if uploaded_key:
            s3_key = uploaded_key

    doc_to_save = PriceDoc(
        kind=price_doc.kind,
        sub_type=price_doc.sub_type,
        region=price_doc.region,
        usd_hour=price_doc.usd_hour,
        inr_hour=price_doc.inr_hour,
        price_ref=price_doc.price_ref,
        source=price_doc.source,
        fetched_at=price_doc.fetched_at,
        raw_doc=None if s3_key else price_doc.raw_doc,
        s3_key=s3_key,
        ttl=price_doc.ttl,
        usd_gb_month=price_doc.usd_gb_month,
    )

    try:
        item = doc_to_save.to_item()
        # If low-level client is used, convert to attribute map
        if hasattr(dynamodb_client, "put_item"):
            wire_item: Dict[str, Any] = {}
            for k, v in item.items():
                if isinstance(v, str):
                    wire_item[k] = {"S": v}
                elif isinstance(v, (int, float)):
                    wire_item[k] = {"N": str(v)}
                elif hasattr(v, "as_tuple"):  # Decimal
                    wire_item[k] = {"N": str(v)}
                elif v is None:
                    wire_item[k] = {"NULL": True}
                else:
                    wire_item[k] = {"S": str(v)}
            dynamodb_client.put_item(TableName=table_name, Item=wire_item)
        else:
            dynamodb_client.Table(table_name).put_item(Item=item)
    except Exception as err:
        logger.warning(
            f"Failed writing price to DynamoDB cache: {err}",
            extra={"pk": price_doc.to_item().get("pk"), "error": str(err)},
        )


def _fetch_from_pricing_api(
    pricing_client: Any,
    kind: str,
    sub_type: str,
    region: str,
    size_gb: Optional[int] = None,
) -> Tuple[float, str, str]:
    """Query AWS Price List API in us-east-1 and extract hourly USD, raw doc, and sha256."""
    location = REGION_LONG_NAMES.get(region, region)
    filters = []

    if kind == "ec2":
        service_code = "AmazonEC2"
        filters = [
            {"Type": "TERM_MATCH", "Field": "instanceType", "Value": sub_type},
            {"Type": "TERM_MATCH", "Field": "location", "Value": location},
            {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
            {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
            {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
            {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
        ]
    elif kind == "ebs":
        service_code = "AmazonEC2"
        filters = [
            {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Storage"},
            {"Type": "TERM_MATCH", "Field": "volumeApiName", "Value": sub_type},
            {"Type": "TERM_MATCH", "Field": "location", "Value": location},
        ]
    elif kind == "nat":
        service_code = "AmazonVPC"
        filters = [
            {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "NAT Gateway"},
            {"Type": "TERM_MATCH", "Field": "location", "Value": location},
        ]
    else:
        raise ValueError(f"Unsupported resource kind: {kind}")

    response = pricing_client.get_products(
        ServiceCode=service_code,
        Filters=filters,
        FormatVersion="aws_v1",
        MaxResults=1,
    )

    price_list = response.get("PriceList", [])
    if not price_list:
        raise ValueError(
            f"No matching AWS Price List product found for kind={kind}, sub_type={sub_type}, region={region}"
        )

    raw_entry = price_list[0]
    canonical_raw_doc = canonicalize_doc(raw_entry)
    parsed_doc = json.loads(canonical_raw_doc)

    terms = parsed_doc.get("terms", {})
    usd_unit_price = _extract_ondemand_usd(terms)

    usd_gb_month: Optional[float] = None
    if kind == "ebs":
        # Price is per GB-month. Convert to hourly: usd_gb_month * size_gb / 730
        usd_gb_month = usd_unit_price
        volume_size = size_gb if size_gb is not None and size_gb > 0 else 1
        usd_hour = (usd_unit_price * volume_size) / 730.0
    else:
        usd_hour = usd_unit_price

    sha256_hex = hashlib.sha256(canonical_raw_doc.encode("utf-8")).hexdigest()
    return usd_hour, canonical_raw_doc, sha256_hex, usd_gb_month


def get_fallback_price(
    kind: str,
    sub_type: str,
    region: str,
    size_gb: Optional[int] = None,
) -> PriceDoc:
    """Generate fallback PriceDoc when API and cache are unavailable."""
    now = int(time.time())

    usd_gb_month: Optional[float] = None
    if kind == "ebs":
        rate_gb_month = FALLBACK_USD_HOUR.get(sub_type, FALLBACK_USD_HOUR["gp3"])
        usd_gb_month = rate_gb_month
        volume_size = size_gb if size_gb is not None and size_gb > 0 else 1
        usd_hour = (rate_gb_month * volume_size) / 730.0
    elif kind == "nat":
        usd_hour = FALLBACK_USD_HOUR.get("nat", 0.056)
    elif kind == "ec2":
        usd_hour = FALLBACK_USD_HOUR.get(sub_type, 0.0)
    else:
        usd_hour = 0.0

    inr_hour = round(usd_hour * USD_INR, 2)
    return PriceDoc(
        kind=kind,
        sub_type=sub_type,
        region=region,
        usd_hour=round(usd_hour, 6),
        inr_hour=inr_hour,
        price_ref=f"fallback:{sub_type}",
        source="fallback",
        fetched_at=now,
        raw_doc=None,
        ttl=None,
        usd_gb_month=usd_gb_month,
    )


def get_price(
    kind: str,
    sub_type: str,
    region: str = REGION,
    size_gb: Optional[int] = None,
    dynamodb_client: Any = None,
    pricing_client: Any = None,
    s3_client: Any = None,
    bucket_name: Optional[str] = None,
) -> PriceDoc:
    """Resolve price for a resource with hashed provenance.

    Resolution Order:
    1. DynamoDB cache (netra_price_cache, 24h TTL)
    2. AWS Price List API (us-east-1)
    3. FALLBACK_USD_HOUR
    """
    pk = f"PRICE#{region}#{kind}#{sub_type}"
    now = int(time.time())

    # 1. DynamoDB Cache check
    cached = _get_cached_price(dynamodb_client, pk)
    if cached is not None:
        if kind == "ebs":
            volume_size = size_gb if size_gb is not None and size_gb > 0 else 1
            rate_gb_month = (
                cached.usd_gb_month
                if cached.usd_gb_month is not None
                else FALLBACK_USD_HOUR.get(sub_type, FALLBACK_USD_HOUR["gp3"])
            )
            usd_hour = (rate_gb_month * volume_size) / 730.0
            inr_hour = round(usd_hour * USD_INR, 2)
            return PriceDoc(
                kind=cached.kind,
                sub_type=cached.sub_type,
                region=cached.region,
                usd_hour=round(usd_hour, 6),
                inr_hour=inr_hour,
                price_ref=cached.price_ref,
                source=cached.source,
                fetched_at=cached.fetched_at,
                raw_doc=cached.raw_doc,
                s3_key=cached.s3_key,
                ttl=cached.ttl,
                usd_gb_month=rate_gb_month,
            )
        return cached

    # 2. AWS Price List API check - always attempt API call and fall back on exception
    try:
        client = pricing_client or boto3.client("pricing", region_name=PRICING_REGION)
        usd_hour, raw_doc, sha256_hex, usd_gb_month = _fetch_from_pricing_api(
            pricing_client=client,
            kind=kind,
            sub_type=sub_type,
            region=region,
            size_gb=size_gb,
        )
        price_ref = f"sha256:{sha256_hex}"
        inr_hour = round(usd_hour * USD_INR, 2)

        # Cache per-GB-month unit rate for EBS, never a size-adjusted hourly rate
        doc_to_cache = PriceDoc(
            kind=kind,
            sub_type=sub_type,
            region=region,
            usd_hour=round(usd_gb_month / 730.0, 6) if kind == "ebs" and usd_gb_month is not None else round(usd_hour, 6),
            inr_hour=round((usd_gb_month / 730.0) * USD_INR, 2) if kind == "ebs" and usd_gb_month is not None else inr_hour,
            price_ref=price_ref,
            source="aws_pricing_api",
            fetched_at=now,
            raw_doc=raw_doc,
            ttl=now + 86400,
            usd_gb_month=usd_gb_month,
        )

        # Record in local store for verification
        _LOCAL_PRICE_DOC_STORE[price_ref] = raw_doc

        # Cache in DynamoDB (and upload raw document to S3 provenance bucket)
        _put_cached_price(dynamodb_client, doc_to_cache, s3_client=s3_client, bucket_name=bucket_name)

        return PriceDoc(
            kind=kind,
            sub_type=sub_type,
            region=region,
            usd_hour=round(usd_hour, 6),
            inr_hour=inr_hour,
            price_ref=price_ref,
            source="aws_pricing_api",
            fetched_at=now,
            raw_doc=raw_doc,
            ttl=now + 86400,
            usd_gb_month=usd_gb_month,
        )
    except Exception as err:
        logger.warning(
            f"AWS Price List API failed for {kind}:{sub_type}:{region}; invoking fallback: {err}",
            extra={"kind": kind, "sub_type": sub_type, "region": region, "error": str(err)},
        )

    # 3. Static fallback
    return get_fallback_price(kind, sub_type, region, size_gb)


def verify_price_ref(
    price_ref: str,
    raw_doc: Optional[str] = None,
    dynamodb_client: Any = None,
    s3_client: Any = None,
    table_name: str = TABLE_PRICE_CACHE,
    bucket_name: Optional[str] = None,
) -> bool:
    """Verify cryptographic provenance of a price reference.

    Re-hashes raw_doc (provided or retrieved from store/DynamoDB/S3) and ensures
    it matches the SHA-256 hash in price_ref.
    Fallback references always return False as they lack cryptographic proof.
    """
    if not price_ref or not price_ref.startswith("sha256:"):
        return False

    expected_hash = price_ref.split(":", 1)[1]
    doc_to_check = raw_doc

    if doc_to_check is None:
        doc_to_check = _LOCAL_PRICE_DOC_STORE.get(price_ref)

    # If S3 client is available, try fetching object by sha256 key
    if doc_to_check is None and s3_client is not None:
        doc_to_check = _get_raw_doc_from_s3(f"prices/{expected_hash}.json", s3_client=s3_client, bucket_name=bucket_name)

    if doc_to_check is None and dynamodb_client is not None:
        # Search DynamoDB cache by price_ref if not in local store
        try:
            response = dynamodb_client.scan(
                TableName=table_name,
                FilterExpression="price_ref = :ref",
                ExpressionAttributeValues={":ref": {"S": price_ref}},
                Limit=1,
            )
            items = response.get("Items", [])
            if items:
                # Check for direct raw_doc
                raw_val = items[0].get("raw_doc")
                if raw_val and isinstance(raw_val, dict) and "S" in raw_val:
                    doc_to_check = raw_val["S"]
                elif raw_val and isinstance(raw_val, str):
                    doc_to_check = raw_val
                # If offloaded to S3, fetch via s3_key
                elif s3_client is not None:
                    s3_key_val = items[0].get("s3_key")
                    s3_k = s3_key_val.get("S") if isinstance(s3_key_val, dict) else s3_key_val
                    if s3_k:
                        doc_to_check = _get_raw_doc_from_s3(s3_k, s3_client=s3_client, bucket_name=bucket_name)
        except Exception as err:
            logger.warning(f"DynamoDB lookup failed during verify_price_ref: {err}")

    if doc_to_check is None:
        return False

    try:
        calculated_hash = hash_raw_doc(doc_to_check)
        return calculated_hash == expected_hash
    except Exception as err:
        logger.warning(f"Verification hashing failed: {err}")
        return False
