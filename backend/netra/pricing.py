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
import time
from typing import Any, Dict, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

from netra.config import (
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


def _put_cached_price(
    dynamodb_client: Any,
    price_doc: PriceDoc,
    table_name: str = TABLE_PRICE_CACHE,
) -> None:
    """Store priced document in DynamoDB cache with 24h TTL."""
    if dynamodb_client is None:
        return

    try:
        item = price_doc.to_item()
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

    if kind == "ebs":
        # Price is per GB-month. Convert to hourly: usd_gb_month * size_gb / 730
        volume_size = size_gb if size_gb is not None and size_gb > 0 else 1
        usd_hour = (usd_unit_price * volume_size) / 730.0
    else:
        usd_hour = usd_unit_price

    sha256_hex = hashlib.sha256(canonical_raw_doc.encode("utf-8")).hexdigest()
    return usd_hour, canonical_raw_doc, sha256_hex


def get_fallback_price(
    kind: str,
    sub_type: str,
    region: str,
    size_gb: Optional[int] = None,
) -> PriceDoc:
    """Generate fallback PriceDoc when API and cache are unavailable."""
    now = int(time.time())

    if kind == "ebs":
        rate_gb_month = FALLBACK_USD_HOUR.get(sub_type, FALLBACK_USD_HOUR["gp3"])
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
    )


def get_price(
    kind: str,
    sub_type: str,
    region: str = REGION,
    size_gb: Optional[int] = None,
    dynamodb_client: Any = None,
    pricing_client: Any = None,
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
        if kind == "ebs" and size_gb is not None and size_gb > 0:
            # Adjust ebs unit price for requested size
            rate_gb_month = cached.usd_hour * 730.0
            adjusted_usd = (rate_gb_month * size_gb) / 730.0
            return PriceDoc(
                kind=cached.kind,
                sub_type=cached.sub_type,
                region=cached.region,
                usd_hour=round(adjusted_usd, 6),
                inr_hour=round(adjusted_usd * USD_INR, 2),
                price_ref=cached.price_ref,
                source=cached.source,
                fetched_at=cached.fetched_at,
                raw_doc=cached.raw_doc,
                ttl=cached.ttl,
            )
        return cached

    # 2. AWS Price List API check
    if pricing_client is not None or _should_attempt_api_call():
        try:
            client = pricing_client or boto3.client("pricing", region_name=PRICING_REGION)
            usd_hour, raw_doc, sha256_hex = _fetch_from_pricing_api(
                pricing_client=client,
                kind=kind,
                sub_type=sub_type,
                region=region,
                size_gb=size_gb,
            )
            price_ref = f"sha256:{sha256_hex}"
            inr_hour = round(usd_hour * USD_INR, 2)

            price_doc = PriceDoc(
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
            )

            # Record in local store for verification
            _LOCAL_PRICE_DOC_STORE[price_ref] = raw_doc

            # Cache in DynamoDB
            _put_cached_price(dynamodb_client, price_doc)
            return price_doc
        except Exception as err:
            logger.warning(
                f"AWS Price List API failed for {kind}:{sub_type}:{region}; invoking fallback: {err}",
                extra={"kind": kind, "sub_type": sub_type, "region": region, "error": str(err)},
            )

    # 3. Static fallback
    return get_fallback_price(kind, sub_type, region, size_gb)


def _should_attempt_api_call() -> bool:
    """Determine whether to attempt an AWS API call based on environment credentials."""
    import os
    return bool(
        os.getenv("AWS_ACCESS_KEY_ID")
        or os.getenv("AWS_PROFILE")
        or os.getenv("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
        or os.getenv("AWS_WEB_IDENTITY_TOKEN_FILE")
    )


def verify_price_ref(
    price_ref: str,
    raw_doc: Optional[str] = None,
    dynamodb_client: Any = None,
    table_name: str = TABLE_PRICE_CACHE,
) -> bool:
    """Verify cryptographic provenance of a price reference.

    Re-hashes raw_doc (provided or retrieved from store/DynamoDB) and ensures
    it matches the SHA-256 hash in price_ref.
    Fallback references always return False as they lack cryptographic proof.
    """
    if not price_ref or not price_ref.startswith("sha256:"):
        return False

    expected_hash = price_ref.split(":", 1)[1]
    doc_to_check = raw_doc

    if doc_to_check is None:
        doc_to_check = _LOCAL_PRICE_DOC_STORE.get(price_ref)

    if doc_to_check is None and dynamodb_client is not None:
        # Search DynamoDB cache by price_ref if not in local store
        try:
            # Query or Scan for matching price_ref
            response = dynamodb_client.scan(
                TableName=table_name,
                FilterExpression="price_ref = :ref",
                ExpressionAttributeValues={":ref": {"S": price_ref}},
                Limit=1,
            )
            items = response.get("Items", [])
            if items:
                raw_val = items[0].get("raw_doc")
                if raw_val and isinstance(raw_val, dict) and "S" in raw_val:
                    doc_to_check = raw_val["S"]
                elif raw_val and isinstance(raw_val, str):
                    doc_to_check = raw_val
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
