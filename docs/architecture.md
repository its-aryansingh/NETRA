# NETRA Architecture Specification

## 1. System Overview

NETRA (**N**ear-real-time **E**xpenditure **T**racking & **R**emediation **A**gent) is a cloud-native financial observability and autonomous remediation platform built natively on Amazon Web Services.

Unlike standard AWS cost tools (Cost Explorer, AWS Budgets) that operate on 24-hour delayed billing reports, NETRA operates continuously at a 60-second cadence, calculating live spend velocity directly from active infrastructure states and AWS Price List API documents.

```
+-----------------------------------------------------------------------------------------+
|                                  NETRA ARCHITECTURE                                     |
+-----------------------------------------------------------------------------------------+

   [AWS CloudWatch]           [AWS Price List API]
 (Single Batch Query)       (Canonical JSON SHA-256)
          │                            │
          ▼                            ▼
+──────────────────────────────────────────────────+
|  netra-collector (AWS Lambda, 60s Cron)          |
|  - Queries EC2, EBS, NAT inventory               |
|  - Computes exact INR/hr (USD_INR = 88.50)       |
|  - Writes 7-day TTL spend snapshot               |
+──────────────────────────────────────────────────+
          │
          ▼
+──────────────────────────────────────────────────+      +───────────────────────────────+
|  Deterministic Rules Engine (rules.yaml)         | ───> | DynamoDB (netra_burn_snapshots|
|  - 60-snapshot rolling median baseline           |      | DynamoDB (netra_price_cache)  |
|  - Pure function, byte-identical evaluation      |      +───────────────────────────────+
+──────────────────────────────────────────────────+
          │
          │ Emits 'netra.finding.created' via EventBridge
          ▼
+──────────────────────────────────────────────────+
|  netra-investigator (Strands Agents SDK)         |
|  - Read-only tools (utilization, dependents)     |
|  - Claude 3.7 Sonnet on Amazon Bedrock (temp=0)  |
|  - Strict Numeric Validator (Zero Hallucinations)|
|  - High-Fidelity Templated Fallback Engine       |
+──────────────────────────────────────────────────+
          │
          ▼
+──────────────────────────────────────────────────+      +───────────────────────────────+
|  Operator Review (Next.js 15 Cockpit)            | <─── | DynamoDB (netra_findings)     |
|  - Monospace telemetry instrument (IBM Plex)     |      | API Gateway HTTP API v2       |
|  - Dry-run verification & 30-day exposure        |      +───────────────────────────────+
+──────────────────────────────────────────────────+
          │
          │ Human Approval (POST /api/findings/{id}/approve)
          ▼
+──────────────────────────────────────────────────+
|  netra-remediate (AWS Step Functions Workflow)   |
|  1. Authorize: Re-evaluates policy safety gates  |
|  2. DryRun: Tests AWS API permissions safely     |
|  3. Snapshot: Creates EBS rollback snapshot      |
|  4. Act: Executes Stop, Terminate, or Delete     |
|  5. RecordAudit: Appends immutable ledger row    |
+──────────────────────────────────────────────────+
          │
          ▼
+──────────────────────────────────────────────────+
|  DynamoDB (netra_audit_log, Append-Only)         |
+──────────────────────────────────────────────────+
```

---

## 2. Core Architectural Pillars

### Pillar I: The Model Never Decides Anything
The foundational design principle of NETRA is that machine learning models and LLMs are strictly forbidden from performing arithmetic, calculating baselines, or deciding whether a resource is anomalous.
- **Detector**: 100% deterministic rules evaluator (`detector.py`) executing against declarative YAML rules (`rules.yaml`).
- **Baselines**: Computed from the rolling median of the last 60 minute snapshots to eliminate self-dragging baseline distortion.
- **LLM Role**: Bedrock Claude 3.7 Sonnet (at `temperature=0`) acts solely as a narrating investigator, synthesizing CloudWatch metrics into plain English for human operators.
- **Output Validator**: A token-level numeric validator intercepts model responses, rejecting any narrative that contains ungrounded numbers.
- **Fallback Guarantee**: If Bedrock is throttled or offline, the publication-grade deterministic fallback engine ships instantly.

### Pillar II: Cryptographic Price Provenance
Every price shown on the dashboard links to an authentic AWS Price List API document.
- API responses are normalized and hashed with SHA-256 (`price_ref="sha256:<hex>"`).
- Fallbacks are explicitly marked (`price_ref="fallback:<sub_type>"`).
- The `verify_price_ref()` function re-hashes the raw document on demand.

### Pillar III: Two-Point Policy Safety Gates
Remediation safety is verified twice:
1. **Proposal Gate**: Evaluated before displaying remediation actions to the user.
2. **Execution Gate**: Evaluated directly inside Step Functions immediately before executing mutating AWS API calls.
Deny rules always win:
- `forbid_protected`: Blocks any action on resources tagged `netra:protected`.
- `forbid_dependents`: Blocks termination when dependent count > 0.
- `forbid_unsnapshotted`: Blocks destructive actions lacking an EBS rollback snapshot.

---

## 3. AWS Service Utilization

| AWS Service | Component Role | Why Chosen |
|:---|:---|:---|
| **AWS Lambda** | Microservices compute | Stateless execution for collector, API router, investigator, and executor. |
| **Amazon DynamoDB** | Database & cache | Single-digit millisecond latency, pay-per-request pricing, and native TTL expiration. |
| **Amazon Bedrock** | GenAI narration | Low-latency inference for Claude 3.7 Sonnet within `ap-south-1`. |
| **AWS Step Functions** | Remediation state machine | Fault-tolerant 5-stage orchestration with retry and catch blocks. |
| **Amazon EventBridge** | Asynchronous event bus | Decouples the 60s collector loop from Bedrock agent latency. |
| **Amazon CloudWatch** | Metric ingestion | Single-batch `get_metric_data` queries reducing API overhead. |
| **AWS Price List API** | Pricing source | Authoritative on-demand catalog with canonical SHA-256 hashing. |
| **Amazon EC2** | Compute tracking | Real-time monitoring and lifecycle management (stop/terminate). |
| **Amazon EBS** | Block storage tracking | Orphaned volume discovery and safety rollback snapshotting. |
| **Amazon VPC** | Networking tracking | Idle NAT Gateway detection and routing topology analysis. |
| **AWS SAM** | Infrastructure as Code | Reproducible serverless template deployment. |
| **AWS Amplify Hosting** | Frontend hosting | Global CDN edge delivery for Next.js 15 dashboard. |
