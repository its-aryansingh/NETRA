"""Tests for S3 Hashed Price Documents (Prompt G)."""

import json
from unittest.mock import MagicMock

import pytest

from netra.models import PriceDoc
from netra.pricing import (
    _LOCAL_PRICE_DOC_STORE,
    _get_raw_doc_from_s3,
    _put_cached_price,
    _upload_raw_doc_to_s3,
    canonicalize_doc,
    get_price,
    hash_raw_doc,
    verify_price_ref,
)


SAMPLE_RAW_DOC = json.dumps({
    "product": {
        "productFamily": "Compute Instance",
        "attributes": {"instanceType": "t3.micro", "location": "Asia Pacific (Mumbai)"},
    },
    "terms": {
        "OnDemand": {
            "offer1": {
                "priceDimensions": {
                    "dim1": {
                        "unit": "Hrs",
                        "pricePerUnit": {"USD": "0.0112"},
                    }
                }
            }
        }
    },
})


def test_upload_raw_doc_to_s3_success():
    mock_s3 = MagicMock()
    sha = hash_raw_doc(SAMPLE_RAW_DOC)
    s3_key = _upload_raw_doc_to_s3(
        raw_doc=SAMPLE_RAW_DOC,
        sha256_hex=sha,
        s3_client=mock_s3,
        bucket_name="test-price-docs-bucket",
    )
    assert s3_key == f"prices/{sha}.json"
    mock_s3.put_object.assert_called_once_with(
        Bucket="test-price-docs-bucket",
        Key=f"prices/{sha}.json",
        Body=SAMPLE_RAW_DOC.encode("utf-8"),
        ContentType="application/json",
    )


def test_upload_raw_doc_to_s3_no_client_returns_none():
    s3_key = _upload_raw_doc_to_s3(
        raw_doc=SAMPLE_RAW_DOC,
        sha256_hex="abcdef",
        s3_client=None,
        bucket_name="test-bucket",
    )
    assert s3_key is None


def test_get_raw_doc_from_s3_success():
    mock_s3 = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = SAMPLE_RAW_DOC.encode("utf-8")
    mock_s3.get_object.return_value = {"Body": mock_body}

    retrieved = _get_raw_doc_from_s3(
        s3_key="prices/sample.json",
        s3_client=mock_s3,
        bucket_name="test-price-docs-bucket",
    )
    assert retrieved == SAMPLE_RAW_DOC
    mock_s3.get_object.assert_called_once_with(
        Bucket="test-price-docs-bucket",
        Key="prices/sample.json",
    )


def test_put_cached_price_stores_s3_key_and_clears_raw_doc_in_dynamo():
    mock_dynamo = MagicMock()
    mock_s3 = MagicMock()
    sha = hash_raw_doc(SAMPLE_RAW_DOC)
    price_ref = f"sha256:{sha}"

    doc = PriceDoc(
        kind="ec2",
        sub_type="t3.micro",
        region="ap-south-1",
        usd_hour=0.0112,
        inr_hour=0.98,
        price_ref=price_ref,
        source="aws_pricing_api",
        fetched_at=1700000000,
        raw_doc=SAMPLE_RAW_DOC,
    )

    _put_cached_price(
        dynamodb_client=mock_dynamo,
        price_doc=doc,
        s3_client=mock_s3,
        bucket_name="my-price-docs-bucket",
    )

    # Check S3 upload was called
    mock_s3.put_object.assert_called_once()
    assert mock_s3.put_object.call_args[1]["Key"] == f"prices/{sha}.json"

    # Check DynamoDB put_item was called with s3_key and raw_doc is NULL
    mock_dynamo.put_item.assert_called_once()
    saved_item = mock_dynamo.put_item.call_args[1]["Item"]
    assert saved_item["s3_key"] == {"S": f"prices/{sha}.json"}
    assert saved_item["raw_doc"] == {"NULL": True}
    assert saved_item["price_ref"] == {"S": price_ref}


def test_verify_price_ref_with_s3_provenance():
    mock_s3 = MagicMock()
    canonical = canonicalize_doc(SAMPLE_RAW_DOC)
    sha = hash_raw_doc(canonical)
    price_ref = f"sha256:{sha}"

    # Clear local cache in case it had it
    _LOCAL_PRICE_DOC_STORE.pop(price_ref, None)

    mock_body = MagicMock()
    mock_body.read.return_value = canonical.encode("utf-8")
    mock_s3.get_object.return_value = {"Body": mock_body}

    # Pass raw_doc=None to force S3 lookup
    valid = verify_price_ref(
        price_ref=price_ref,
        raw_doc=None,
        s3_client=mock_s3,
        bucket_name="my-price-docs-bucket",
    )
    assert valid is True
    mock_s3.get_object.assert_called_once_with(
        Bucket="my-price-docs-bucket",
        Key=f"prices/{sha}.json",
    )


def test_verify_price_ref_tampered_s3_content_fails():
    mock_s3 = MagicMock()
    sha = hash_raw_doc(SAMPLE_RAW_DOC)
    price_ref = f"sha256:{sha}"

    # Clear local cache
    _LOCAL_PRICE_DOC_STORE.pop(price_ref, None)

    # Return tampered doc
    tampered_doc = SAMPLE_RAW_DOC.replace("0.0112", "9.9999")
    mock_body = MagicMock()
    mock_body.read.return_value = tampered_doc.encode("utf-8")
    mock_s3.get_object.return_value = {"Body": mock_body}

    valid = verify_price_ref(
        price_ref=price_ref,
        raw_doc=None,
        s3_client=mock_s3,
        bucket_name="my-price-docs-bucket",
    )
    assert valid is False
