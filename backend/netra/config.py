"""NETRA configuration module.

Single source of truth for runtime constants, AWS region targets,
DynamoDB table names, and currency conversion parameters.
All settings are overridable via environment variables.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict


# Target AWS deployment and pricing regions
# The pricing client MUST be us-east-1 per AWS API specifications.
REGION: str = os.getenv("AWS_REGION", os.getenv("NETRA_REGION", "ap-south-1"))
PRICING_REGION: str = os.getenv("NETRA_PRICING_REGION", "us-east-1")
SUPPORTED_REGIONS: list[str] = [
    r.strip()
    for r in os.getenv("NETRA_REGIONS", "ap-south-1,us-east-1,eu-west-1").split(",")
    if r.strip()
]

# Fixed conversion rate constant. Never fetched from an external FX API.
USD_INR: float = float(os.getenv("NETRA_USD_INR", "88.50"))

TABLE_BURN_SNAPSHOTS: str = os.getenv("NETRA_TABLE_BURN_SNAPSHOTS", "netra_burn_snapshots")
TABLE_PRICE_CACHE: str = os.getenv("NETRA_TABLE_PRICE_CACHE", "netra_price_cache")
TABLE_FINDINGS: str = os.getenv("NETRA_TABLE_FINDINGS", "netra_findings")
TABLE_AUDIT_LOG: str = os.getenv("NETRA_TABLE_AUDIT_LOG", "netra_audit_log")

# Notification & Plumbing Targets
SNS_TOPIC_ARN: str = os.getenv("NETRA_SNS_TOPIC_ARN", "")
BUCKET_PRICE_DOCS: str = os.getenv("NETRA_PRICE_DOCS_BUCKET", "")

# Initial and remaining hackathon credit allocation in USD ($200 basis)
CREDITS_INITIAL_USD: float = float(os.getenv("NETRA_CREDITS_INITIAL_USD", "200.0"))
CREDITS_REMAINING_USD: float = float(os.getenv("NETRA_CREDITS_REMAINING_USD", "200.0"))

# Aliases and account defaults
AUDIT_TABLE: str = TABLE_AUDIT_LOG
FINDINGS_TABLE: str = TABLE_FINDINGS
DEFAULT_ACCOUNT_ID: str = os.getenv("NETRA_ACCOUNT_ID", "default")

# AWS Region to AWS Price List API Location Name mapping
REGION_LONG_NAMES: Dict[str, str] = {
    "ap-south-1": "Asia Pacific (Mumbai)",
    "us-east-1": "US East (N. Virginia)",
    "us-west-2": "US West (Oregon)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "eu-west-1": "Europe (Ireland)",
}


def get_logger(name: str) -> logging.Logger:
    """Configures and returns a structured logger for NETRA services.
    
    Ensures standard structured log output across Lambda invocations and local CLI runs.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt='{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%SZ"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    log_level = os.getenv("NETRA_LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    return logger
