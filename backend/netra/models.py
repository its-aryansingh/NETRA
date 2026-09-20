"""NETRA data models.

Frozen dataclasses strictly conforming to §CONTRACTS:
- PricedResource
- PriceDoc
- Finding
- Narrative

Provides robust conversion to and from DynamoDB attribute maps
with recursive float <-> Decimal transformations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
import time
from typing import Any, Dict, List, Literal, Optional, Union


def _to_decimal(obj: Any) -> Any:
    """Recursively convert float values to Decimal for DynamoDB serialization."""
    if isinstance(obj, float):
        # Convert through str to avoid floating point precision artifacts in Decimal
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_decimal(v) for v in obj]
    return obj


def _from_decimal(obj: Any) -> Any:
    """Recursively convert Decimal values back to float/int for Python usage."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0 and "." not in str(obj):
            return int(obj)
        return float(obj)
    if isinstance(obj, dict):
        return {k: _from_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_from_decimal(v) for v in obj]
    return obj


@dataclass(frozen=True)
class PriceDoc:
    """Represents a priced item document with cryptographic or fallback provenance."""

    kind: str  # "ec2" | "ebs" | "nat"
    sub_type: str  # e.g. "c5.4xlarge", "gp3"
    region: str  # e.g. "ap-south-1"
    usd_hour: float
    inr_hour: float
    price_ref: str  # "sha256:<hex>" | "fallback:<sub_type>"
    source: str  # "aws_pricing_api" | "cache" | "fallback"
    fetched_at: int  # epoch seconds
    raw_doc: Optional[str] = None  # Canonical JSON string of source price item
    s3_key: Optional[str] = None  # S3 object key (prices/<sha256>.json)
    ttl: Optional[int] = None  # Cache expiry epoch seconds
    usd_gb_month: Optional[float] = None  # Per-GB-month unit rate for storage (e.g. EBS gp3)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to plain dictionary."""
        return asdict(self)

    def to_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format with Decimal conversion."""
        item = asdict(self)
        item["pk"] = f"PRICE#{self.region}#{self.kind}#{self.sub_type}"
        if self.ttl is None:
            item["ttl"] = self.fetched_at + 86400  # 24h TTL
        return _to_decimal(item)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PriceDoc:
        """Construct instance from dictionary."""
        clean_data = {
            "kind": str(data["kind"]),
            "sub_type": str(data["sub_type"]),
            "region": str(data["region"]),
            "usd_hour": float(data["usd_hour"]),
            "inr_hour": float(data["inr_hour"]),
            "price_ref": str(data["price_ref"]),
            "source": str(data["source"]),
            "fetched_at": int(data["fetched_at"]),
            "raw_doc": data.get("raw_doc"),
            "s3_key": data.get("s3_key"),
            "ttl": int(data["ttl"]) if data.get("ttl") is not None else None,
            "usd_gb_month": float(data["usd_gb_month"]) if data.get("usd_gb_month") is not None else None,
        }
        return cls(**clean_data)

    @classmethod
    def from_item(cls, item: Dict[str, Any]) -> PriceDoc:
        """Construct instance from DynamoDB item."""
        data = _from_decimal(item)
        return cls.from_dict(data)


@dataclass(frozen=True)
class PricedResource:
    """Represents an active AWS inventory resource priced with provenance."""

    resource_id: str
    kind: str  # "ec2" | "ebs" | "nat"
    sub_type: str  # e.g. "c5.4xlarge"
    region: str  # "ap-south-1"
    launched_at: int  # epoch seconds
    age_seconds: int
    usd_hour: float
    inr_hour: float
    price_ref: str  # "sha256:4a9f..." | "fallback:c5.4xlarge"
    tags: Dict[str, Optional[str]]
    state: str  # "running" | "available" | "active"
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to standard Python dictionary."""
        return asdict(self)

    def to_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB-compatible item with Decimals."""
        return _to_decimal(asdict(self))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PricedResource:
        """Construct instance from standard dictionary."""
        return cls(
            resource_id=str(data["resource_id"]),
            kind=str(data["kind"]),
            sub_type=str(data["sub_type"]),
            region=str(data["region"]),
            launched_at=int(data["launched_at"]),
            age_seconds=int(data["age_seconds"]),
            usd_hour=float(data["usd_hour"]),
            inr_hour=float(data["inr_hour"]),
            price_ref=str(data["price_ref"]),
            tags=dict(data.get("tags") or {}),
            state=str(data["state"]),
            meta=dict(data.get("meta") or {}),
        )

    @classmethod
    def from_item(cls, item: Dict[str, Any]) -> PricedResource:
        """Construct instance from DynamoDB item."""
        return cls.from_dict(_from_decimal(item))


@dataclass(frozen=True)
class Narrative:
    """Represents validated model or fallback narrative explaining a finding."""

    headline: str  # max 70 chars
    narrative: List[str]  # 3 paragraphs: what happened, evidence, costs & next steps
    evidence: List[Dict[str, str]]  # e.g. [{"label": "CPUUtilization max", "value": "2.0%"}]
    recommended_action: str  # "stop"|"terminate"|"delete"|"snapshot_and_terminate"|"snapshot_and_delete"|"downsize"|"none"
    risk: str  # "low" | "medium" | "high"
    steps: List[Dict[str, str]]  # e.g. [{"api": "ec2:CreateSnapshot", "why": "string"}]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to standard Python dictionary."""
        return asdict(self)

    def to_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB-compatible item."""
        return _to_decimal(asdict(self))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Narrative:
        """Construct instance from dictionary."""
        return cls(
            headline=str(data["headline"]),
            narrative=list(data.get("narrative") or []),
            evidence=[dict(e) for e in data.get("evidence") or []],
            recommended_action=str(data["recommended_action"]),
            risk=str(data["risk"]),
            steps=[dict(s) for s in data.get("steps") or []],
        )

    @classmethod
    def from_item(cls, item: Dict[str, Any]) -> Narrative:
        """Construct instance from DynamoDB item."""
        return cls.from_dict(_from_decimal(item))


@dataclass(frozen=True)
class Finding:
    """Represents an anomaly finding computed deterministically before model narration."""

    finding_id: str  # ULID or deterministic hash id
    severity: str  # "critical" | "warning" | "info"
    status: str  # "DETECTED" | "NARRATING" | "AWAITING_APPROVAL" | "EXECUTING" | "RESOLVED" | "DISMISSED" | "SNOOZED" | "FAILED"
    rules_fired: List[Dict[str, str]]  # e.g. [{"rule": "idle_compute", "detail": "cpu_max=2.0 age=41m"}]
    resource: PricedResource
    computed: Dict[str, float]  # inr_hour, inr_month, baseline_inr_hour, multiple, runway_hours, share_of_burn_pct
    detected_at: int  # epoch seconds
    account_id: str = "default"
    narrative: Optional[Narrative] = None
    narrative_source: Optional[str] = None  # "openai" | "bedrock" | "ollama" | "fallback"
    agent_trace: Optional[List[Dict[str, Any]]] = None
    detection_path: str = "sweep"  # "fast" | "sweep"
    detection_latency_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation matching JSON data contract."""
        data: Dict[str, Any] = {
            "finding_id": self.finding_id,
            "severity": self.severity,
            "status": self.status,
            "rules_fired": self.rules_fired,
            "resource": self.resource.to_dict(),
            "computed": self.computed,
            "detected_at": self.detected_at,
            "account_id": self.account_id,
            "detection_path": self.detection_path,
        }
        if self.detection_latency_ms is not None:
            data["detection_latency_ms"] = self.detection_latency_ms
        if self.narrative is not None:
            data["narrative"] = self.narrative.to_dict()
        if self.narrative_source is not None:
            data["narrative_source"] = self.narrative_source
        if self.agent_trace is not None:
            data["agent_trace"] = self.agent_trace
        return data

    def to_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format with primary keys and Decimal conversions."""
        item = self.to_dict()
        item["pk"] = f"ACCOUNT#{self.account_id}"
        item["sk"] = f"FIND#{self.finding_id}"
        return _to_decimal(item)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Finding:
        """Construct instance from dictionary."""
        resource_data = data["resource"]
        resource = (
            resource_data
            if isinstance(resource_data, PricedResource)
            else PricedResource.from_dict(resource_data)
        )

        narrative_data = data.get("narrative")
        narrative = None
        if narrative_data is not None:
            narrative = (
                narrative_data
                if isinstance(narrative_data, Narrative)
                else Narrative.from_dict(narrative_data)
            )

        computed_dict = {
            k: float(v) for k, v in (data.get("computed") or {}).items()
        }

        return cls(
            finding_id=str(data["finding_id"]),
            severity=str(data["severity"]),
            status=str(data.get("status", "DETECTED")),
            rules_fired=[dict(r) for r in data.get("rules_fired") or []],
            resource=resource,
            computed=computed_dict,
            detected_at=int(data["detected_at"]),
            account_id=str(data.get("account_id", "default")),
            narrative=narrative,
            narrative_source=data.get("narrative_source"),
            agent_trace=data.get("agent_trace"),
            detection_path=str(data.get("detection_path", "sweep")),
            detection_latency_ms=int(data["detection_latency_ms"]) if data.get("detection_latency_ms") is not None else None,
        )

    @classmethod
    def from_item(cls, item: Dict[str, Any]) -> Finding:
        """Construct instance from DynamoDB item."""
        return cls.from_dict(_from_decimal(item))
