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

## 3. AWS Service Utilization (14 Load-Bearing Cloud Services)

| AWS Service | Component Role | Technical Implementation Details |
|:---|:---|:---|
| **1. AWS Lambda** | Serverless microservices | 5 decoupled Python 3.12 functions (`CollectorFunction`, `InvestigatorFunction`, `ApiFunction`, `ExecutorFunction`, `McpActionsFunction`). |
| **2. Amazon EventBridge & Scheduler** | Event-driven telemetry & cron | Sub-10s fast-path capture for `aws.ec2` state changes (50ms measured) + 60s multi-region scheduler sweeps (`ap-south-1`, `us-east-1`, `eu-west-1`). |
| **3. AWS Step Functions** | Remediation workflow | 5-stage human-approved state machine: `Authorize` ➔ `PolicyCheck (Cedar)` ➔ `DryRun` ➔ `Snapshot` ➔ `Act` ➔ `RecordAudit`. |
| **4. Amazon DynamoDB** | Storage & cache | 4 on-demand tables (`netra_burn_snapshots` with 7-day TTL, `netra_price_cache`, `netra_findings`, `netra_audit_log`). |
| **5. Amazon S3** | Price provenance store | Archives SHA-256 digested AWS Price List JSON documents (`s3://.../prices/<sha256>.json`) for audit-grade accountability. |
| **6. Amazon SQS & DLQ** | Decoupling & buffering | `netra-findings-queue` with 3-retry redrive policy to `netra-findings-dlq`. |
| **7. Amazon SNS** | Real-time alerting | `netra-critical-findings` topic sending instant SMS & email alerts (<160 chars) on >3× baseline burn spikes. |
| **8. Amazon CloudWatch** | Utilization telemetry | Consolidates multi-resource metrics (CPU, Network, Disk) via `GetMetricData` in <400 ms + custom `NETRA/SpendVelocity` metrics. |
| **9. Amazon API Gateway** | REST API routing | Low-latency HTTP API v2 with automated CORS enforcement. |
| **10. AWS Price List API** | Real-time pricing | Authoritative on-demand rates for EC2, EBS gp3, and NAT Gateways with cryptographic hashing. |
| **11. Amazon Bedrock** | Defensive AI narration | Multi-provider foundation model inference (Claude 3.7 Sonnet APAC cross-region profile) under read-only IAM policies. |
| **12. AWS IAM** | Security boundaries | Least-privilege roles enforced with mandatory tag conditions (`aws:ResourceTag/netra:managed: "true"`). |
| **13. Amazon EC2 & EBS** | Monitored infrastructure | Real-time lifecycle interception, `DryRunOperation` safety verification, and automated 7-day rollback snapshots (`CreateSnapshot`). |
| **14. AWS Amplify Hosting** | Frontend delivery | Globally distributes the Next.js 15 monospace dashboard across CloudFront edge locations. |

---

## 4. AWS Open Source Stack Integration

We built NETRA using core open-source tools and libraries from the AWS and cloud ecosystem:

- **AWS SAM CLI (`aws-sam-cli`)**: Used for end-to-end local development, Lambda emulation, dependency containerization, and CloudFormation template packaging ([`infra/template.yaml`](../infra/template.yaml)).
- **AWS Cedar Policy Language (`cedar-policy` / `cedarpy`)**: Integrated AWS's open-source formal authorization engine directly into our remediation pipeline. Cedar policies (`forbid_protected`, `forbid_dependents`, `forbid_unsnapshotted`) evaluate safety invariants in 1.2 milliseconds before any mutation can proceed.
- **Boto3 & Botocore**: Used across all backend microservices for asynchronous event publishing, DynamoDB streaming, batched CloudWatch queries, and Price List fetching.
- **Model Context Protocol (MCP)**: Implemented an MCP action server boundary (`netra-mcp-actions`) that isolates AI reasoning tools from mutating infrastructure execution.
- **CFN-Lint & CloudFormation Guard**: Automated template security linting in GitHub Actions CI to enforce least-privilege IAM and pay-per-request billing configurations.

