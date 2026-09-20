# NETRA — AWS Well-Architected Framework Deep Dive

> **Workload Name**: NETRA (Near-real-time Expenditure Tracking & Remediation Agent)  
> **Lens Applied**: Serverless Application Lens & Financial Operations (FinOps) Lens  
> **Evaluation Target**: WeMakeDevs × AWS · First Commit 2026 Hackathon (Ship It Track)  
> **Prepared For**: AWS Solutions Architects, Technical Account Managers (TAMs), and DevOps Specialists  

---

## Executive Summary

NETRA is an autonomous, event-driven cloud financial incident detector and human-gated remediation agent. It addresses the documented **24 to 33-hour Cost Explorer data latency blind spot** ([aws-solutions/innovation-sandbox-on-aws#92](https://github.com/aws-solutions/innovation-sandbox-on-aws/issues/92)) by intercepting EC2 lifecycle events via Amazon EventBridge in **sub-10 seconds** (measured at 50ms) and pricing resources deterministically against hashed AWS Price List documents.

This document details how NETRA complies with the six pillars of the **AWS Well-Architected Framework**.

---

## 1. Cost Optimization Pillar

> *"The ability to run systems to deliver business value at the lowest price point."*

### Key Architectural Choices & Evidence:
1. **Pre-Aggregation Financial Interception**:
   - Native AWS billing pipelines aggregate charges hours after compute runs. NETRA pulls unit rates directly from the AWS Price List API upon `RunInstances` or `CreateVolume` events, calculating hourly burn rates before billing meters turn over.
2. **Serverless Scale-to-Zero Run Cost**:
   - The entire NETRA system is serverless: AWS Lambda (Python 3.12), Amazon EventBridge, Amazon DynamoDB (On-Demand), Amazon SQS, and Amazon S3.
   - **Measured baseline running cost**: **< ₹10.00/month (< $0.15/month)**. NETRA consumes zero compute cycles and zero dollars when infrastructure is quiet.
3. **Automated Resource Lifecycling**:
   - DynamoDB tables (`NetraBurnSnapshots`) enforce 7-day Time-To-Live (TTL) timestamps, automatically purging ephemeral time-series telemetry without manual cleanup scripts or table scans.
4. **S3 Digest Caching vs API Egress**:
   - Raw price documents are digested with SHA-256 and cached in Amazon S3 (`s3://<bucket>/prices/<sha256>.json`). Subsequent inventory evaluations read from memory/S3, eliminating repeated AWS Price List API calls.

---

## 2. Security Pillar

> *"The ability to protect data, systems, and assets to take advantage of cloud technologies to improve your security."*

### Key Architectural Choices & Evidence:
1. **Zero-Mutating Investigator IAM Role (Least Privilege)**:
   - The Investigator Lambda that interfaces with LLMs (OpenAI / Bedrock Claude) holds strictly **read-only** permissions (`ec2:Describe*`, `dynamodb:GetItem`, `sns:Publish`). It possesses zero mutating capabilities (`ec2:Terminate*`, `ec2:Stop*`, `ec2:Delete*`).
   - Even if prompt injection succeeds in compromising the LLM, the model cannot execute any mutating action.
2. **Cryptographic Human Approval Boundary**:
   - Mutating actions are isolated behind single-use **HMAC-SHA256 tokens** with a 5-minute TTL. Tokens cryptographically bind the action payload, target ARN, and a random execution nonce. Replay and parameter tampering attacks are rejected at the gate.
3. **Formal Policy Invariants via AWS Cedar (`cedarpy`)**:
   - Evaluated in ~1.2ms before Step Functions remediation.
   - `forbid_protected`: Unconditionally forbids stopping or terminating any resource tagged `netra:protected == true`.
   - `forbid_dependents`: Denies termination if active Elastic Network Interfaces (ENIs) or route tables depend on the instance.
   - `forbid_unsnapshotted`: Disallows volume deletion without an EBS snapshot ID.
4. **Conditioned Executor IAM Boundaries**:
   - The Step Functions executor role enforces `Condition: StringEquals: aws:ResourceTag/netra:managed: "true"`, preventing accidental mutation of unmanaged production instances.

---

## 3. Reliability Pillar

> *"The ability of a system to recover from infrastructure or service disruptions, dynamically acquire computing resources to meet demand, and mitigate disruptions."*

### Key Architectural Choices & Evidence:
1. **AWS Step Functions 5-Stage Orchestration (`netra-remediate`)**:
   - Remediations run through a deterministic state machine: `Authorize` &rarr; `PolicyCheck` &rarr; `DryRun` &rarr; `Snapshot` &rarr; `Act`.
   - Any failure in authorization or dry-run cleanly halts the execution without mutating infrastructure.
2. **Automated 7-Day EBS Snapshot Rollback**:
   - Before any compute or storage resource is terminated or deleted, NETRA takes an EBS snapshot tagged `netra:rollback: true`.
   - Operators can revert any approved remediation with a single click, restoring the instance or volume from the audit ledger.
3. **Dead-Letter Queue (DLQ) & Fault Isolation**:
   - Findings from the collector pass through `NetraFindingsQueue` (Amazon SQS) with a redrive policy targeting `NetraFindingsDLQ` (maxReceiveCount: 3). If Bedrock or downstream APIs throttle, messages are preserved for 4 days without data loss.
4. **Deterministic Fallback Narrative Engine**:
   - If LLM APIs (OpenAI or Bedrock) experience an outage, `fallback.py` automatically synthesizes a publication-grade 3-paragraph root cause explanation from structured Python data with zero external API dependencies.

---

## 4. Operational Excellence Pillar

> *"The ability to support development and run workloads effectively, gain insight into their operations, and continuously improve supporting processes."*

### Key Architectural Choices & Evidence:
1. **Immutable DynamoDB Audit Ledger**:
   - Every human approval, execution ARN, recovered rupee amount, and snapshot ID is written to an append-only DynamoDB audit table with cryptographic timestamps.
2. **Byte-Identical Deterministic Rules Engine**:
   - Detection criteria are declared as data in `rules.yaml`. Evaluating the same telemetry multiple times produces byte-identical finding fingerprints, eliminating non-deterministic alerting chatter.
3. **Declarative Infrastructure-as-Code (AWS SAM)**:
   - The entire stack is packaged in `infra/template.yaml` (717 lines), fully linted with `cfn-lint` and testable via SAM local.
4. **Automated Continuous Integration (CI)**:
   - GitHub Actions runs parallel matrices validating SAM CloudFormation syntax, Python 3.12 pytest (131 tests), and Next.js 15 TypeScript typechecking on every commit.

---

## 5. Performance Efficiency Pillar

> *"The ability to use computing resources efficiently to meet system requirements, and to maintain that efficiency as demand changes and technologies evolve."*

### Key Architectural Choices & Evidence:
1. **Sub-10-Second Event-Driven Fast Path**:
   - Rather than polling CloudWatch every few minutes, NETRA intercepts `aws.ec2` state-change events directly via Amazon EventBridge, achieving a measured detection latency of **50 milliseconds**.
2. **CloudWatch Telemetry Batching via `GetMetricData`**:
   - Calling `GetMetricStatistics` per resource sequentially required 8+ seconds and hit API rate limits. Migrating to batched `GetMetricData` with metric math reduced latency across all instances to **< 400ms**.
3. **Multi-Region Concurrency**:
   - Multi-region sweeps utilize Python thread pools to query `ap-south-1`, `us-east-1`, and `eu-west-1` concurrently, maintaining a flat 60-second execution profile regardless of fleet size.

---

## 6. Sustainability Pillar

> *"The ability to continually improve sustainability impacts by reducing energy consumption and increasing efficiency."*

### Key Architectural Choices & Evidence:
1. **Zero Idle Compute Footprint**:
   - Rather than maintaining an always-on EC2 instance, ECS container, or OpenSearch cluster, NETRA uses serverless microservices that scale strictly to zero. Between scheduled 60-second sweeps, zero compute cycles are consumed.
2. **High-Density Telemetry Packing**:
   - Minute-by-minute spend velocity is packed into compressed time-series records with 7-day auto-expiry, avoiding redundant data bloat in cloud storage.
3. **The Core Business Value**:
   - NETRA directly eliminates wasted cloud kilowatt-hours by identifying idle compute (`c5.4xlarge` idling at 1.8% CPU) and unattached storage, turning off unused hardware that would otherwise draw continuous power in AWS data centers.

---

## Verification Matrix

| Claim | Measured / Proven Value | Verification Source |
|:---|:---|:---|
| Fast Path Detection Latency | **50 ms (0.05 seconds)** | `scripts/break.py` event timestamp comparison |
| Verification Harness Duration | **1.23 seconds** | `netra.verify` / `make verify` |
| Automated Backend Unit Tests | **131 / 131 passed** | `python -m pytest backend/tests/ -v` |
| Adversarial Red Team Defense | **0 / 12 breaches** | `scripts/redteam.py` / `docs/redteam-results.md` |
| Monthly Idle Run Cost | **< ₹10.00 / month (< $0.15)** | AWS pricing calculation on Lambda & DynamoDB on-demand |
| Replay & Parameter Tampering | **100% rejected** | `test_token_tampering_refused`, `test_token_replay_refused` |
| Protected Resource Safety | **100% blocked** | Cedar policy `forbid_protected` unit & integration tests |
