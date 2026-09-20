"""Unit tests for NETRA pricing engine and cryptographic provenance.

All tests run offline with mock responses to ensure deterministic, zero-latency execution.
"""

from __future__ import annotations

import hashlib
import json
import time
from unittest.mock import MagicMock

import pytest

from netra.config import USD_INR
from netra.models import Finding, Narrative, PriceDoc, PricedResource
from netra.pricing import (
    FALLBACK_USD_HOUR,
    canonicalize_doc,
    get_fallback_price,
    get_price,
    hash_raw_doc,
    verify_price_ref,
)

# Sample AWS Pricing API response fixtures
SAMPLE_EC2_PRODUCT = {
    "product": {
        "productFamily": "Compute Instance",
        "attributes": {
            "instanceType": "c5.4xlarge",
            "location": "Asia Pacific (Mumbai)",
            "operatingSystem": "Linux",
            "tenancy": "Shared",
        },
    },
    "terms": {
        "OnDemand": {
            "TERM123": {
                "priceDimensions": {
                    "DIM456": {
                        "pricePerUnit": {
                            "USD": "0.7520000000"
                        }
                    }
                }
            }
        }
    },
}

SAMPLE_EBS_PRODUCT = {
    "product": {
        "productFamily": "Storage",
        "attributes": {
            "volumeApiName": "gp3",
            "location": "Asia Pacific (Mumbai)",
        },
    },
    "terms": {
        "OnDemand": {
            "TERMEBS": {
                "priceDimensions": {
                    "DIMEBS": {
                        "pricePerUnit": {
                            "USD": "0.0912000000"
                        }
                    }
                }
            }
        }
    },
}

SAMPLE_NAT_PRODUCT = {
    "product": {
        "productFamily": "NAT Gateway",
        "attributes": {
            "location": "Asia Pacific (Mumbai)",
        },
    },
    "terms": {
        "OnDemand": {
            "TERMNAT": {
                "priceDimensions": {
                    "DIMNAT": {
                        "pricePerUnit": {
                            "USD": "0.0560000000"
                        }
                    }
                }
            }
        }
    },
}


def test_hash_stability():
    """Verify that identical documents in different key orders produce identical SHA-256 digests."""
    doc_a = {"b": 2, "a": 1, "nested": {"z": 9, "y": 8}}
    doc_b = {"a": 1, "nested": {"y": 8, "z": 9}, "b": 2}

    hash_a = hash_raw_doc(json.dumps(doc_a))
    hash_b = hash_raw_doc(json.dumps(doc_b))

    assert hash_a == hash_b
    assert len(hash_a) == 64


def test_api_parse_ec2():
    """Test parsing AWS Price List API output for EC2 instance with hashed provenance."""
    raw_json = json.dumps(SAMPLE_EC2_PRODUCT)
    expected_hash = hashlib.sha256(canonicalize_doc(raw_json).encode("utf-8")).hexdigest()

    mock_pricing = MagicMock()
    mock_pricing.get_products.return_value = {
        "PriceList": [raw_json]
    }

    doc = get_price(
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        pricing_client=mock_pricing,
    )

    assert doc.usd_hour == 0.752
    assert doc.inr_hour == round(0.752 * USD_INR, 2)
    assert doc.price_ref == f"sha256:{expected_hash}"
    assert doc.source == "aws_pricing_api"
    assert doc.raw_doc is not None


def test_api_parse_ebs_with_size():
    """Test parsing AWS Price List API for EBS storage converting GB-month to hourly."""
    raw_json = json.dumps(SAMPLE_EBS_PRODUCT)
    mock_pricing = MagicMock()
    mock_pricing.get_products.return_value = {
        "PriceList": [raw_json]
    }

    # 500 GB gp3 volume
    doc = get_price(
        kind="ebs",
        sub_type="gp3",
        region="ap-south-1",
        size_gb=500,
        pricing_client=mock_pricing,
    )

    # 0.0912 * 500 / 730 = 0.0624657...
    expected_usd = round((0.0912 * 500) / 730.0, 6)
    assert doc.usd_hour == expected_usd
    assert doc.inr_hour == round(expected_usd * USD_INR, 2)
    assert doc.price_ref.startswith("sha256:")
    assert doc.source == "aws_pricing_api"


def test_api_parse_nat():
    """Test parsing AWS Price List API for NAT Gateway."""
    raw_json = json.dumps(SAMPLE_NAT_PRODUCT)
    mock_pricing = MagicMock()
    mock_pricing.get_products.return_value = {
        "PriceList": [raw_json]
    }

    doc = get_price(
        kind="nat",
        sub_type="nat",
        region="ap-south-1",
        pricing_client=mock_pricing,
    )

    assert doc.usd_hour == 0.056
    assert doc.inr_hour == round(0.056 * USD_INR, 2)
    assert doc.price_ref.startswith("sha256:")


def test_cache_hit():
    """Test that valid unexpired cache entry is returned without calling API."""
    now = int(time.time())
    cached_doc = PriceDoc(
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        usd_hour=0.752,
        inr_hour=round(0.752 * USD_INR, 2),
        price_ref="sha256:abcd1234efgh5678",
        source="aws_pricing_api",
        fetched_at=now - 60,
        raw_doc='{"cached":true}',
        ttl=now + 86400,
    )

    mock_dynamo = MagicMock()
    mock_dynamo.get_item.return_value = {
        "Item": cached_doc.to_item()
    }
    mock_pricing = MagicMock()

    doc = get_price(
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        dynamodb_client=mock_dynamo,
        pricing_client=mock_pricing,
    )

    assert doc.usd_hour == 0.752
    assert doc.price_ref == "sha256:abcd1234efgh5678"
    mock_pricing.get_products.assert_not_called()


def test_fallback_path():
    """Test that failed API call safely resolves to static fallback dictionary."""
    mock_pricing = MagicMock()
    mock_pricing.get_products.side_effect = Exception("ThrottlingException: Rate exceeded")

    doc = get_price(
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        pricing_client=mock_pricing,
    )

    assert doc.usd_hour == FALLBACK_USD_HOUR["c5.4xlarge"]
    assert doc.inr_hour == round(FALLBACK_USD_HOUR["c5.4xlarge"] * USD_INR, 2)
    assert doc.price_ref == "fallback:c5.4xlarge"
    assert doc.source == "fallback"
    assert doc.raw_doc is None


def test_verify_price_ref():
    """Test cryptographic verification of price references."""
    raw_doc = json.dumps(SAMPLE_EC2_PRODUCT)
    valid_hash = hash_raw_doc(raw_doc)
    valid_ref = f"sha256:{valid_hash}"
    tampered_ref = f"sha256:{'0' * 64}"

    # Valid doc matches valid ref
    assert verify_price_ref(valid_ref, raw_doc=raw_doc) is True

    # Tampered doc fails
    tampered_doc = json.dumps({"tampered": True})
    assert verify_price_ref(valid_ref, raw_doc=tampered_doc) is False

    # Tampered ref fails
    assert verify_price_ref(tampered_ref, raw_doc=raw_doc) is False

    # Fallback ref cannot be verified
    assert verify_price_ref("fallback:c5.4xlarge", raw_doc=raw_doc) is False
    assert verify_price_ref("invalid_format", raw_doc=raw_doc) is False


def test_models_dynamo_roundtrip():
    """Verify serialization/deserialization to and from DynamoDB for all data contracts."""
    priced = PricedResource(
        resource_id="i-0a4f39c7b12e8d5a1",
        kind="ec2",
        sub_type="c5.4xlarge",
        region="ap-south-1",
        launched_at=1789740877,
        age_seconds=2460,
        usd_hour=0.752,
        inr_hour=66.55,
        price_ref="sha256:4a9f13c8",
        tags={"Owner": None, "netra:protected": None},
        state="running",
        meta={"vpc_id": "vpc-12345", "size_gb": 500},
    )

    narrative = Narrative(
        headline="Runaway c5.4xlarge instance detected in ap-south-1",
        narrative=["Paragraph 1", "Paragraph 2", "Paragraph 3"],
        evidence=[{"label": "CPUUtilization max", "value": "2.0%"}],
        recommended_action="snapshot_and_terminate",
        risk="low",
        steps=[{"api": "ec2:CreateSnapshot", "why": "Safeguard root volume before termination"}],
    )

    finding = Finding(
        finding_id="01J8ABCDEF1234567890",
        severity="critical",
        status="DETECTED",
        rules_fired=[{"rule": "idle_compute", "detail": "cpu_max=2.0 age=41m"}],
        resource=priced,
        computed={
            "inr_hour": 66.55,
            "inr_month": 48576.0,
            "baseline_inr_hour": 23.04,
            "multiple": 3.89,
            "runway_hours": 14.9,
            "share_of_burn_pct": 94.4,
        },
        detected_at=1789740918,
        narrative=narrative,
        narrative_source="bedrock",
    )

    # Roundtrip PricedResource
    pr_item = priced.to_item()
    reconstructed_pr = PricedResource.from_item(pr_item)
    assert reconstructed_pr.resource_id == priced.resource_id
    assert reconstructed_pr.usd_hour == priced.usd_hour
    assert reconstructed_pr.meta["size_gb"] == 500

    # Roundtrip Narrative
    narr_item = narrative.to_item()
    reconstructed_narr = Narrative.from_item(narr_item)
    assert reconstructed_narr.headline == narrative.headline
    assert len(reconstructed_narr.narrative) == 3

    # Roundtrip Finding
    finding_item = finding.to_item()
    assert finding_item["pk"] == "ACCOUNT#default"
    assert finding_item["sk"] == "FIND#01J8ABCDEF1234567890"

    reconstructed_finding = Finding.from_item(finding_item)
    assert reconstructed_finding.finding_id == finding.finding_id
    assert reconstructed_finding.computed["inr_hour"] == 66.55
    assert reconstructed_finding.resource.sub_type == "c5.4xlarge"
    assert reconstructed_finding.narrative.recommended_action == "snapshot_and_terminate"


def test_ebs_cache_hit_regression_unit_rate():
    """Verify a cache entry populated by a 100 GB volume returns usd_hour == 0.062466 for 500 GB gp3."""
    raw_json = json.dumps(SAMPLE_EBS_PRODUCT)
    mock_pricing = MagicMock()
    mock_pricing.get_products.return_value = {"PriceList": [raw_json]}

    saved_items = {}
    mock_dynamo = MagicMock()

    def fake_put_item(TableName, Item):
        saved_items[Item["pk"]["S"]] = Item

    def fake_get_item(TableName, Key):
        pk = Key["pk"]["S"]
        if pk in saved_items:
            return {"Item": saved_items[pk]}
        return {}

    mock_dynamo.put_item.side_effect = fake_put_item
    mock_dynamo.get_item.side_effect = fake_get_item

    # 1. 100 GB volume populates cache (0.0912 USD/GB-month)
    doc_100 = get_price(
        kind="ebs",
        sub_type="gp3",
        region="ap-south-1",
        size_gb=100,
        dynamodb_client=mock_dynamo,
        pricing_client=mock_pricing,
    )
    assert doc_100.usd_hour == round((0.0912 * 100) / 730.0, 6)
    assert doc_100.usd_gb_month == 0.0912

    # 2. 500 GB volume hits cache: must return 0.062466 (rounded to 6dp) for 500 GB gp3 at 0.0912, NOT 6.2465
    doc_500 = get_price(
        kind="ebs",
        sub_type="gp3",
        region="ap-south-1",
        size_gb=500,
        dynamodb_client=mock_dynamo,
        pricing_client=mock_pricing,
    )

    assert doc_500.usd_hour == 0.062466
    assert doc_500.usd_hour != 6.2465
    assert doc_500.usd_gb_month == 0.0912
    # Ensure pricing API was called only once (cache hit on second call)
    mock_pricing.get_products.assert_called_once()

