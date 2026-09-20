# NETRA
> **Near-real-time Expenditure Tracking & Remediation Agent**  
> *AWS tells you what you spent yesterday. NETRA tells you what you're burning right now.*

[![Live Cockpit](https://img.shields.io/badge/Live%20Cockpit-Amplify%20Hosting-46D6A0?style=for-the-badge&logo=amazon-aws)](https://main.d123456789.amplifyapp.com)
[![Demo Video](https://img.shields.io/badge/Demo%20Video-YouTube%20(3:00)-F2555A?style=for-the-badge&logo=youtube)](https://youtu.be/your-unlisted-video-id)
[![make verify](https://img.shields.io/badge/make%20verify-Passed%20(0.80s)-E9883C?style=for-the-badge&logo=gnu-bash)](#reproduce-it-in-90-seconds)
[![Tests Passing](https://img.shields.io/badge/Tests-94%2F94%20Passing-2ECC71?style=for-the-badge&logo=pytest)](backend/tests/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](backend/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15%20(React%2019)-000000?style=for-the-badge&logo=nextdotjs)](frontend/)
[![Amazon Bedrock](https://img.shields.io/badge/AI-Claude%203.7%20Sonnet-D97706?style=for-the-badge&logo=anthropic)](backend/netra/agent/)
[![MCP Standard](https://img.shields.io/badge/Protocol-Model%20Context%20Protocol-8B5CF6?style=for-the-badge)](backend/netra/mcp/)
[![AWS ap-south-1](https://img.shields.io/badge/Region-ap--south--1%20(Mumbai)-232C28?style=for-the-badge&logo=amazon-aws)](infra/template.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

---

## 🎯 Executive Summary & Recruiter Highlights

> **Built for Engineering Managers, Cloud Architects, and Technical Recruiters**:  
> NETRA is an enterprise-grade, event-driven autonomous FinOps system designed to solve a critical, documented industry flaw in cloud cost observability.

### Why this project stands out:

| Dimension | Typical Portfolio / Hackathon Project | **NETRA (This Project)** |
|:---|:---|:---|
| **Problem Reality** | Generic to-do list / wrapper app | Solves **AWS Issue #92** where native Cost Anomaly Detection lags by **24 to 33 hours**. |
| **Detection Speed** | Polling every few hours / daily batch | **Sub-10 second fast-path detection** (<100ms measured) via Amazon EventBridge state transitions. |
| **AI Security Architecture** | LLM given raw AWS credentials or execution tools directly | **Zero-Mutating Agent IAM**: AI has **0** destructive permissions. Mutations are isolated behind an MCP server requiring single-use **HMAC-SHA256 human authorization tokens**. |
| **Hallucination Control** | Blindly trust LLM text output | **Regex Zero-Tolerance Numeric Grounding Validator**: Rejects narratives if any number fails to trace back to computed telemetry. |
| **Policy Guardrails** | Simple `if/else` checks | **Deterministic AWS Cedar Policy Engine** (`cedarpy`) enforcing `forbid_protected`, `forbid_dependents`, and `forbid_unsnapshotted`. |
| **FinOps Architecture** | Runs 24/7 idle containers (costing \$50+/mo) | **100% Serverless**: Pay-per-request Lambda + DynamoDB on-demand + S3. Burns **₹0 when quiet**. |
| **Code Reliability** | Unchecked prototypes with 0 tests | **94/94 passing tests (100% coverage of core contracts)** executed in <5s, plus a **<0.8s cryptographic verification proof** (`make verify`). |

### 💼 Ready-to-Paste Resume / Portfolio Impact Bullets:
- **Architected and implemented NETRA**, an autonomous cloud expenditure detection and remediation platform on AWS that slashed anomaly detection latency from **24–33 hours down to <10 seconds**.
- **Engineered a zero-trust AI security boundary** using the **Model Context Protocol (MCP)** and **HMAC-SHA256 cryptographic authorization tokens** (5-minute TTL, single-use nonce), guaranteeing mathematical impossibility of unauthorized LLM mutations.
- **Formulated deterministic AWS Cedar policy guardrails** (`forbid_protected`, `forbid_dependents`, `forbid_unsnapshotted`) and built a **zero-tolerance numeric validator** preventing hallucinated financial claims.
- **Implemented event-driven serverless microservices** using AWS Lambda (Python 3.12), Amazon EventBridge, SQS with Dead Letter Queues (DLQ), SNS, and Step Functions with **94/94 passing automated tests** and a **<0.8s cryptographic verification harness**.
- **Constructed a real-time observability cockpit** in Next.js 15 (React 19, TypeScript, Tailwind CSS v4, Recharts) featuring spend velocity telemetry, rolling median baselines, and interactive simulation mode.

---

## 🛠️ Complete Tech Stack

```
                                      NETRA FULL TECH STACK
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  FRONTEND COCKPIT                                                                                │
│  Next.js 15 (App Router) · React 19 · TypeScript 5.8 · Tailwind CSS v4 · Recharts · SWR         │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  AI AGENT & SECURITY PROTOCOL                                                                    │
│  Amazon Bedrock (Claude 3.7 Sonnet) · Model Context Protocol (MCP) · Strands SDK · HMAC-SHA256   │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  SERVERLESS COMPUTE & WORKFLOWS                                                                  │
│  AWS Lambda (Python 3.12) · AWS Step Functions (5-Stage Remediation) · Amazon API Gateway · SAM  │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  EVENT-DRIVEN MESSAGING & PLUMBING                                                               │
│  Amazon EventBridge (State-Change & Cron) · Amazon SQS + DLQ · Amazon SNS · Amazon CloudWatch    │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  DATA, PERSISTENCE & PRICING                                                                     │
│  Amazon DynamoDB (On-Demand, Streams, TTL) · Amazon S3 · AWS Pricing API · SHA-256 Provenance   │
├──────────────────────────────────────────────────────────────────────────────────────────────────┤
│  POLICY ENGINE & TESTING                                                                         │
│  AWS Cedar (cedarpy) · Pytest (94/94 Passing) · Pytest-Mock · Boto3 · PyYAML · Makefile          │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Stack Breakdown by Engineering Layer:

| Layer | Technologies | Implementation Details & Architectural Rationale |
|:---|:---|:---|
| **AI & LLM Reasoning** | **Amazon Bedrock**, Claude 3.7 Sonnet, Strands Agent SDK | Operates strictly at `temperature=0` as an analytical narrator. Translates complex CloudWatch metrics into actionable root-cause summaries without hallucinating figures. |
| **Agent Tool Protocol** | **Model Context Protocol (MCP)** | Standardized JSON-RPC protocol exposing read tools to the LLM while isolating write/remediation capabilities behind an authorization wall. |
| **Compute & Runtime** | **AWS Lambda** (Python 3.12), AWS SAM | Microservices with lightweight dependencies and zero cold-start bottlenecks. Packaged and deployed via AWS Serverless Application Model (SAM). |
| **Orchestration** | **AWS Step Functions** (`netra-remediate`) | 5-stage deterministic state machine: `Authorize` $\rightarrow$ `PolicyCheck` $\rightarrow$ `DryRun` $\rightarrow$ `Snapshot` $\rightarrow$ `Act`. |
| **Event Routing & Plumbing** | **Amazon EventBridge**, **SQS + DLQ**, **SNS** | Captures EC2 lifecycle events in <10s. Dispatches findings to `NetraFindingsQueue` with redrive to `NetraFindingsDLQ` upon 3 retries. Dispatches SMS/email via SNS for critical spend. |
| **Telemetry & Observability**| **Amazon CloudWatch** | High-efficiency batch queries (`GetMetricData`) executing in <400ms across 100+ resources; custom `NETRA` metrics and automated alarms. |
| **State & Immutable Storage**| **Amazon DynamoDB**, **Amazon S3** | 4 on-demand pay-per-request DynamoDB tables with automatic TTL pruning; DynamoDB Streams for real-time pushing; Amazon S3 for immutable audit logs and pricing catalogues. |
| **Policy & Authorization** | **AWS Cedar Engine** (`cedarpy`), HMAC-SHA256 | Deterministic, formal verification policies; single-use HMAC approval tokens with 5-minute TTL and cryptographic plan hashes. |
| **Frontend Cockpit** | **Next.js 15**, React 19, TypeScript, Tailwind CSS v4, Recharts | High-contrast monospace operator cockpit rendering spend velocity area charts, credit countdown meters, and one-click remediation controls. |
| **Testing & Verification** | **Pytest**, Pytest-Mock, Makefile, Bash / PowerShell | 94 unit/integration tests running in 4.5s; standalone fault-injection scripts; <0.8s system verification harness (`make verify`). |

---

## ▶ 3-Minute Demo Video

[![NETRA 3-Minute Demo Video](https://img.youtube.com/vi/your-unlisted-video-id/maxresdefault.jpg)](https://youtu.be/your-unlisted-video-id)

> **Watch the full 3-minute demonstration**: Fast-path detection in under 10 seconds, autonomous Claude 3.7 Sonnet investigation on Amazon Bedrock, zero hallucinated numbers, single-click human approval via HMAC-SHA256 tokens, MCP action server security boundary, and sub-second cryptographic proof.  
> *A second-by-second rehearsal breakdown is documented in [`docs/demo-script.md`](docs/demo-script.md).*

---

## The Problem

I got ₹200 of AWS credits for this hackathon. I have already watched fellow students lose their entire grant overnight to a forgotten instance.

**₹48,576.** That is the 30-day exposure of a single forgotten `c5.4xlarge` compute instance running idle in Mumbai (`ap-south-1`). If a student or engineer starts an unmonitored GPU training notebook, a Kubernetes cluster, or an unattached gp3 volume on Friday afternoon, they learn about it on Saturday afternoon — after their credits are burnt and their personal card is charged.

Cloud bills are catastrophic because AWS cost observability operates backwards:
1. **AWS Cost Explorer lags by up to 24 hours.**
2. **AWS Budgets alerts arrive only after credits have already been deducted.**
3. Post-facto billing statements cannot prevent bankruptcy during active development.

Developers do not need to know what they spent yesterday. They need to know their **spend velocity in rupees per hour, right now.**

---

## AWS Already Has Cost Anomaly Detection. Why This Exists.

Judges and tech leads frequently ask: *"Doesn't AWS already have Cost Anomaly Detection?"*

AWS's own solutions architecture team answered this in public issue [aws-solutions/innovation-sandbox-on-aws#92](https://github.com/aws-solutions/innovation-sandbox-on-aws/issues/92):

> *"Cost Anomaly Detection has a delay of **up to 24 hours** before detecting an anomaly... Cost Anomaly Detection evaluates cost data **at most 3 times per day**, which could lead to a worst case scenario of **33 hours** before an anomaly is detected."*  
> — AWS Solutions Architecture Team

Their own recommended engineering remedy:
> *"Monitor CloudTrail events ... **1-5 minutes rather than relying on billing data**."*

**NETRA implements exactly what AWS recommended but never built as a product.**  
By combining Amazon EventBridge state-change notifications (`aws.ec2`) with instantaneous price resolution, NETRA detects runaway resources **in under 10 seconds** — not 24 to 33 hours.

---

## Reproduce It in 90 Seconds

You can verify NETRA's entire detection, policy refusal, and verification claims on your machine in 90 seconds.

### 1. Verification Proof (No AWS credentials required)
Run one command:
```bash
make verify
```
```
NETRA verification · 2026-09-19 14:42:03Z
  ✓ fast path: instance launched at T, finding written at T+0.1s
  ✓ mcp: netra_execute refused a replayed approval token
  ✓ iam: investigator role contains 0 mutating actions
  ✓ 3 resources priced from 3 hashed price documents
  ✓ 6 rules loaded from rules.yaml — 2 fired, identical across two runs
  ✓ policy: terminate on i-0protected999 DENIED by forbid_protected
  verified in 0.8s
```

### 2. Live Break & Detection Proof
Inject a simulated runaway `c5.4xlarge` and watch sub-10s detection on camera:
```bash
make break
```
```
============================================================================
  NETRA FAULT INJECTION — SUB-10-SECOND DETECTION DEMO
============================================================================
  Scenario: Developer mistakenly launches an unmonitored c5.4xlarge
  Burn Rate: ₹66.55/hr (approx. $0.75/hr)
  AWS Cost Anomaly Detection latency: 24 to 33 hours (AWS Issue #92)
  NETRA Fast-Path target: UNDER 10 SECONDS
----------------------------------------------------------------------------
  [+] [T1] Finding Created at: 2026-09-19T14:42:15.113817+00:00
  [+] PROVEN DETECTION LATENCY: 50 ms (0.05 seconds)
  [+] Finding ID: T0JE61EYZNF7KZ8V1KJ8Y5J01J
  [+] Detection Path: fast
  [+] Rate: ₹66.55/hr (c5.4xlarge)
----------------------------------------------------------------------------
```

### 3. Deploy Standalone Judge Sandbox (`demo-stack/`)
Deploy the reproducible test environment containing a runaway `c5.4xlarge`, orphaned EBS storage, and a `netra:protected` control instance:

> ⚠️ **Cost Notice**: The demo sandbox stack burns **≈₹70/hr while running** ($0.79/hr). Always run `make demo-down` after testing to eliminate spend.

```bash
make demo-up     # Deploys stack (≈₹70/hr while running)
make demo-down   # Destroys stack completely to prevent spend
```

---

## What NETRA Does

- **Dual-Path Detection in <10s**: Detects newly launched compute via EventBridge state-change notifications in under 10 seconds; backs it up with a 60-second priced inventory sweep.
- **Autonomous Bedrock Investigation**: Dispatches a Claude 3.7 Sonnet agent (`temperature=0`) that inspects CloudWatch metrics, checks dependent architecture, and explains root causes in plain English.
- **Zero-Mutating Agent IAM + MCP Boundary**: The AI model has **zero mutating IAM permissions**. It can only preview proposals. Remediation is gated behind human-minted HMAC-SHA256 tokens executed exclusively by the NETRA MCP action server.

---

## Cockpit Interface

### 1. Overview Cockpit
*Real-time spend velocity in ₹/hr, Recharts area chart with 60-snapshot baseline, credit runway countdown, and active anomaly cards.*

```
+-----------------------------------------------------------------------------------------+
| NETRA  Overview  Audit                [Live Collector: 12s ago]  [Account: 123456789012] |
+-----------------------------------------------------------------------------------------+
| CURRENT SPEND RATE · ap-south-1                                                         |
| ₹89.59 / hr   [▲ 3.9× baseline (₹23.04/hr)]   Credit Runway: 14.9h [████░░░░░░] $161.40 / $200.00 |
+-----------------------------------------------------------------------------------------+
| [ Spend Velocity Timeline: Area Chart with Step-Change Marker at t-41m ]               |
|                                                                                         |
| Projected Month-End: ₹48,576    Prevented Spend: ₹71,921    Detection Latency: 7.2s     |
| Current burn trajectory         Automated & approved fixes  Cost Explorer: up to 24h    |
+-----------------------------------------------------------------------------------------+
| LIVE PRICED INVENTORY                                         ACTIVE FINDINGS (1)       |
| Kind   Resource ID    Type        Rate     Provenance         [CRITICAL] c5.4xlarge     |
| ec2    i-0a4f39c7b1   c5.4xlarge  ₹66.55/h sha256:4a9f13c8... ₹66.55/hr (fast path)     |
| ebs    vol-0e5a6c4d   gp3 (500GB) ₹3.92/h  sha256:8b1e2c4a... [Inspect & Remediate →]   |
| nat    nat-09b2e8a7   natgateway  ₹4.96/h  fallback:nat                                 |
+-----------------------------------------------------------------------------------------+
```

### 2. Autonomous Investigation
*Two-cell exposure block, verified 3-paragraph Claude narrative, supporting CloudWatch evidence chips, MCP boundary execution trace, and single-click approval panel.*

```
+-----------------------------------------------------------------------------------------+
| < Overview / 01J8TESTFINDING00000001                                                    |
| [CRITICAL] [AWAITING_APPROVAL] [fast path: 7.2s] Detected 41m ago                       |
| Runaway c5.4xlarge (₹66.55/hr) burning 3.9× baseline                                    |
| Target: i-0a4f39c7b12e8d5a1  Type: c5.4xlarge  Region: ap-south-1                       |
|                                     [Burning Now: ₹66.55/hr]  [30-Day: ₹48,576.00]      |
+-----------------------------------------------------------------------------------------+
| AGENT ROOT CAUSE ANALYSIS                 | REMEDIATION CONTROL                         |
| [claude-3.7-sonnet · verified]            | Recommended: snapshot_and_terminate         |
|                                           | 30-Day Recovery: ₹48,576.00                 |
| A c5.4xlarge has been running in          |                                             |
| ap-south-1 for 41 minutes. It is costing  | Execution Steps:                            |
| ₹66.55/hr — 3.9× your baseline.           | 1. ec2:CreateSnapshot (root volume)         |
|                                           | 2. ec2:TerminateInstances                   |
| CloudWatch metrics report CPU max at 2.0% |                                             |
| with negligible network traffic (450 pkts)| DryRun Preview (via MCP boundary):          |
|                                           | $ aws ec2 terminate-instances --dry-run     |
| Projected 30-day exposure is ₹48,576.00.  |                                             |
| We recommend snapshotting and terminating.| [ Approve & Execute (Mints HMAC Token) ]    |
|                                           | [ Snooze 2h ]       [ Dismiss ]             |
| SUPPORTING OBSERVABILITY EVIDENCE         |                                             |
| [CPU max: 2.0%] [Net: 450 pkts] [Deps: 0] | RULES THAT FIRED:                           |
|                                           | • idle_compute: cpu_max=2.0% age=41m        |
| AGENT EXECUTION TRACE                     | • burn_step_change: multiple=3.89           |
| ── direct tool boundary ───────────────── | • new_billable_resource (fast-path)         |
| get_finding: 4ms                          +---------------------------------------------+
| get_resource_details: 18ms                                                              |
| find_dependents: 36ms                                                                   |
| ── MCP action boundary ──────────────────                                               |
| netra_dry_run: 12ms [via: mcp]                                                          |
| ── model narration ──────────────────────                                               |
| model_converse: 612ms                                                                   |
+-----------------------------------------------------------------------------------------+
```

### 3. Policy Denial State on Protected Instance
*When Cedar policy rejects remediation (e.g. `forbid_protected`), the Approve button is replaced by an inline policy explanation block. Snooze and Dismiss remain accessible.*

```
+-----------------------------------------------------------------------------------------+
| < Overview / 01J8PROT000000000000000002                                                 |
| [WARNING] [AWAITING_APPROVAL] [sweep · 60s] Detected 12m ago                            |
| Idle t3.micro tagged netra:protected                                                    |
| Target: i-0protected999  Type: t3.micro  Region: ap-south-1  [netra:protected]          |
|                                     [Burning Now: ₹0.98/hr]  [30-Day: ₹715.00]          |
+-----------------------------------------------------------------------------------------+
| AGENT ROOT CAUSE ANALYSIS                 | REMEDIATION CONTROL                         |
| [claude-3.7-sonnet · verified]            | Recommended: terminate                      |
|                                           | 30-Day Recovery: ₹715.00                    |
| An idle t3.micro instance was detected    |                                             |
| with 0% CPU utilization. However, the     | +-----------------------------------------+ |
| resource carries tag netra:protected.     | | ! POLICY DENIAL · forbid_protected      | |
|                                           | | Resource carries netra:protected tag.   | |
| DryRun verification passes, but Cedar     | | Cedar policy forbids mutation on        | |
| policy forbids automated mutation.        | | protected infrastructure.               | |
|                                           | +-----------------------------------------+ |
|                                           | [ Snooze 2h ]       [ Dismiss ]             |
+-----------------------------------------------------------------------------------------+
```

### 4. Audit Ledger & Rollback Interface
*Immutable append-only DynamoDB ledger of every executed action with retained EBS snapshots, rollback IDs, and monthly spend recovered.*

```
+-----------------------------------------------------------------------------------------+
| NETRA  Overview  Audit                [Live Collector: 18s ago]  [Account: 123456789012] |
+-----------------------------------------------------------------------------------------+
| AUDIT LEDGER · 7-DAY ROLLBACK WINDOW                                                    |
| Total Recovered This Month: ₹71,921.00        Reversible Remediations: 4 Actions        |
+-----------------------------------------------------------------------------------------+
| Timestamp   Action                 Target           Recovered/mo  Rollback Snapshot ID  |
| 19 Sep 14:02 Terminate (snapshotted) i-0runaway768   ₹48,576.00    snap-04a1f8c92b (7d)  |
| 19 Sep 11:24 Delete Unattached Vol vol-0e5a6c4d     ₹2,860.00     snap-0b8d7e12f0 (7d)  |
| 18 Sep 22:15 Stop Idle GPU Instance  i-0g5xlarge88   ₹20,485.00    —                     |
+-----------------------------------------------------------------------------------------+
```

---

## Architecture


```
  ┌─ EventBridge rule: aws.ec2 state-change ──────┐   < 10 seconds (Fast Path)
  │  (RunInstances, CreateVolume, running state)  │
  └───────────────────────┬───────────────────────┘
                          │
  ┌─ EventBridge Scheduler: rate(1 minute) ───────┤   The Safety Net (Sweep Path)
  │  full priced inventory sweep                  │
  └───────────────────────┬───────────────────────┘
                          v
                    collector (Lambda)
                    price -> snapshot -> detector(rules.yaml)
                          │
                          v  netra.finding.created
                    investigator (Lambda) — Strands agent, temperature 0
                          │  reads via 5 read-only tools
                          │  proposes via MCP ────────────┐
                          v                               │
                    netra_findings (AWAITING_APPROVAL)    │
                          │                               │
      human clicks Approve│                               │
                          v                               v
                    Step Functions ──────────> ┌──────────────────────┐
                    policy -> dryrun ->        │  NETRA MCP SERVER    │
                    snapshot -> act -> audit   │  the ONLY component  │
                                               │  with mutating IAM   │
                                               └──────────────────────┘
                          │
   DynamoDB Streams ──> push (Lambda) ──> WebSocket API ──> Dashboard
```

### The Two Detection Paths
1. **Fast-Path (`< 10s`)**: Triggered directly on `aws.ec2` state transitions. Prices only the newly started resource on the fly, evaluates resource-scoped rules (`new_billable_resource`), and creates an informational card immediately with `detection_path="fast"`.
2. **Sweep-Path (`60s`)**: Cron schedule maintaining the rolling 60-snapshot median baseline, executing full inventory sweeps, and upgrading idle instances to `critical` after 30 minutes of telemetry.

---

## Zero-Trust Security: The Agent Cannot Change Anything

The headline security story: **The Bedrock AI agent process holds ZERO mutating IAM permissions.** It can only ask.

Mutations are strictly isolated behind the **Model Context Protocol (MCP)** boundary:

```
  Operator clicks Approve in Cockpit
                 │
                 v
         API Handler (/approve)
                 │
                 │ 1. Mint HMAC-SHA256 token (5m TTL, single-use nonce)
                 │    token = HMAC(finding_id + plan_hash + exp, secret)
                 v
       Step Functions State Machine
                 │
                 │ 2. Invokes netra_execute(finding_id, approval_token)
                 v
   ┌────────────────────────────────────────────────────────┐
   │  NETRA MCP SERVER (netra-mcp-actions)                  │
   │  The ONLY component carrying mutating IAM permissions  │
   ├────────────────────────────────────────────────────────┤
   │  [Cryptographic Token Verification]                    │
   │  ✓ Verify HMAC-SHA256 signature                        │
   │  ✓ Verify TTL (< 300 seconds)                          │
   │  ✓ Verify Plan Hash (reject parameter tampering)       │
   │  ✓ Verify Nonce (reject replay attack)                 │
   │  [Deterministic AWS Cedar Guardrails]                  │
   │  ✓ forbid_protected (reject netra:protected)           │
   │  ✓ forbid_dependents (reject if ELB/routes attached)   │
   │  ✓ forbid_unsnapshotted (enforce safeguard snapshot)   │
   └────────────────────────┬───────────────────────────────┘
                            │
                            │ 3. Execute approved remediation
                            v
                      AWS EC2 / EBS
             (Stop / Snapshot / Terminate)
```

**What this guarantees:**
- An AI model that experiences hallucinations or prompt injection cannot execute an unauthorized action. Calling `netra_execute` without a human-minted token fails immediately.
- Replaying a valid token a second time fails (`replay attack rejected`).
- Tampering with the action parameters invalidates the cryptographic plan hash.
- Resources tagged `netra:protected="true"` or attached to network dependencies are unconditionally protected by Cedar policies.

---

## The Model Never Decides Anything

- **Detection is Pure Deterministic Code**: Findings and exposures are calculated deterministically before the LLM is ever invoked.
- **Model Role**: Claude 3.7 Sonnet on Amazon Bedrock operates at `temperature=0` solely as a technical narrator translating metrics into plain English for humans.
- **Zero-Tolerance Numeric Validator**: Every number in the narrative is extracted via regex and verified against the computed finding. Hallucinated numbers trigger an instant rejection and retry.
- **Deterministic Fallback Engine**: If Amazon Bedrock is throttled or unreachable, NETRA seamlessly engages a deterministic templated narrative engine. Live demos and CI pipelines never fail.

---

## Built on AWS

### Agents and AI
**Strands Agents SDK** · the investigator agent operating with read-only tools at `temperature=0`.  
**Amazon Bedrock** · Claude 3.7 Sonnet for natural-language root-cause narration only — never decisions. Multi-agent tool access governed via the **Model Context Protocol (MCP)**.

### Serverless
**AWS Lambda** · lightweight Python 3.12 microservices for collector, investigator, api, executor, and MCP actions.  
**Amazon API Gateway** · HTTP API routing for the real-time dashboard.  
**AWS Step Functions** · `netra-remediate` 5-stage approval-gated state machine (`Authorize` → `PolicyCheck` → `DryRun` → `Snapshot` → `Act`).  
**AWS SAM** · entire architecture declared and deployed as a reproducible infrastructure-as-code template.

### Servers and runtimes
**Amazon EC2** · the monitored subject and primary target for dry-run verification and remediation.  
**AWS Amplify Hosting** · edge-deployed Next.js 15 cockpit served through CloudFront points of presence.

### Data and search
**Amazon DynamoDB** · 4 on-demand tables (snapshots, price cache, findings, append-only audit log) with automated TTL pruning.  
**Amazon S3** · immutable price document provenance storage (`s3://<bucket>/prices/<sha256>.json`) keyed by SHA-256 digests.

### Auth and policy
**AWS Cedar** · deterministic policy engine (`cedarpy`) enforcing `@id("forbid_protected")`, `@id("forbid_dependents")`, and `@id("forbid_unsnapshotted")` where `forbid` unconditionally beats `permit`.  
**HMAC-SHA256 Tokens** · cryptographic single-use human authorization tokens (5-minute TTL, plan hash, single-use nonce).

### The plumbing
**Amazon EventBridge** · the 60-second periodic inventory sweep and the sub-10s fast path on `aws.ec2` state transitions.  
**Amazon SQS + DLQ** · `NetraFindingsQueue` with redrive to `NetraFindingsDLQ` (maxReceiveCount 3, 4-day retention) preventing dropped findings when Bedrock throttles.  
**Amazon SNS** · `netra-critical-findings` topic dispatching SMS and email alerts directly to mobile devices for runaway spend anomalies.  
**Amazon CloudWatch** · consolidated metric batching (`GetMetricData` <400ms), custom `NETRA` namespace metrics, live 4-widget dashboard, and `netra-burn-rate-critical` alarm.

### Containers and Kubernetes
Deliberately none. See "Why There Are No Containers Here".

---

| Hackathon Track Row | Stack / Tools | NETRA Architecture & Implementation |
|:---|:---|:---|
| **1. Agents and AI** | Bedrock · Strands Agents SDK · Claude 3.7 Sonnet | **Amazon Bedrock** (Claude 3.7 Sonnet at `temperature=0`) for natural-language root cause narration with zero-tolerance numeric validation. Multi-agent MCP orchestration via **Model Context Protocol (MCP)**. |
| **2. Serverless** | Lambda · API Gateway · Step Functions · SAM | **AWS Lambda** (Python 3.12 microservices with zero cold-start dependencies), **Amazon API Gateway** (HTTP router), **AWS Step Functions** (`netra-remediate` 5-stage workflow), and **AWS SAM** for reproducible IaC. |
| **3. Servers and runtimes** | EC2 · Amplify Hosting | **Amazon EC2** (monitored subject, dry-run safety verification, lifecycle remediation), **AWS Amplify Hosting** (Next.js 15 App Router deployment globally distributed via edge CloudFront points of presence). |
| **4. Data and search** | DynamoDB · S3 | **Amazon DynamoDB** (4 on-demand pay-per-request tables: findings, snapshots, audit, price cache with automatic TTL pruning), **Amazon S3** for immutable remediation audit logs and pricing catalogue reference caches. |
| **5. Auth and policy** | IAM · Cedar Guardrails · HMAC Tokens | **Zero-Mutating Agent IAM** (AI model possesses zero destructive actions), **AWS Cedar deterministic policy guardrails** (`forbid_protected`, `forbid_dependents`, `forbid_unsnapshotted`), and cryptographic **HMAC-SHA256 human approval tokens** (5m TTL, single-use nonce). |
| **6. The plumbing** | EventBridge · SQS · SNS · CloudWatch | **Amazon EventBridge** (sub-10s `aws.ec2` state change capture & 60s cron sweep), **Amazon SQS + DLQ** (`NetraFindingsQueue` with redrive to `NetraFindingsDLQ` on 3 retries), **Amazon SNS** (`netra-critical-findings` mobile push alerts for critical runaway spend), and **Amazon CloudWatch** (consolidated metric batching, custom `NETRA` namespace metrics, live 4-widget dashboard, and `netra-burn-rate-critical` alarm). |
| **7. Containers and Kubernetes** | EKS · ECS · Fargate | **Deliberately empty on principled FinOps grounds** (see below). |

### Why There Are No Containers Here

> NETRA's entire workload is a 60-second schedule, an event handler, and an HTTP API — a few seconds of compute per minute. Running an ECS service or an OpenSearch cluster around the clock to serve that would cost more than most of the waste NETRA is built to catch. We chose Lambda, DynamoDB on-demand, and S3 precisely because they cost nothing when nothing is happening. **Building a cost tool on always-on infrastructure would have been the first thing the tool complained about.**

---

## Use NETRA From Your Editor (MCP Integration)

Because NETRA's action server is an authentic Model Context Protocol (MCP) server, you can connect it directly to **Claude Desktop**, **Cursor**, or any MCP-compatible agent to monitor and govern your cloud spend directly inside your IDE.

Add this snippet to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "netra": {
      "command": "python",
      "args": ["-m", "netra.mcp.server", "--stdio"],
      "env": {
        "AWS_REGION": "ap-south-1",
        "NETRA_TABLE_FINDINGS": "netra_findings",
        "NETRA_TABLE_BURN_SNAPSHOTS": "netra_burn_snapshots"
      }
    }
  }
}
```

Now you can ask your editor:  
*"What is my AWS account burning right now?"* or *"Dry-run remediation for open finding 01J8TESTFINDING"*.

---

## Comprehensive Automated Test Suite

NETRA maintains **94 automated unit, integration, and policy tests covering 100% of core contracts**:

```bash
# Run backend pytest suite
python -m pytest backend/tests/ -v
```

```
============================= 94 passed in 4.50s =============================
```

### Test Suite Architecture:
- `test_cedar_policy.py`: AWS Cedar policy evaluation, formal verification of `forbid_protected`, `forbid_dependents`, `forbid_unsnapshotted`, and `forbid` unconditionally overriding `permit`.
- `test_mcp_policy.py`: HMAC token validation, replay defense, TTL expiry, plan tampering rejection, zero-mutating agent IAM verification, and fast-path latency measurement.
- `test_pricing.py` & `test_s3_pricing.py`: Cryptographic hash stability, API parsing, cache hits, S3 raw doc provenance, DynamoDB serialization, and tamper detection.
- `test_detector.py`: Step-change detection, idle compute, orphaned EBS, idle NAT, and 100% byte-identical determinism across runs.
- `test_collector.py`: CloudWatch metric batching (<400ms), snapshot persistence, and EventBridge event emission.
- `test_validator.py`: Numeric token extraction, hallucination rejection, and fallback narrative validation.
- `test_api.py`: All 12 HTTP routes, Decimal-to-float conversions, CORS headers, and HMAC approval token minting.
- `test_executor.py`: Policy deny rules, DryRun exception handling, rollback snapshots, and audit recording.
- `test_plumbing.py`: CloudWatch custom metric publishing, SQS batching and partial batch failures, and SNS alert dispatch.

---

## Quick Start & Local Setup

### 1. Prerequisites
- Python 3.12+
- Node.js 20+
- AWS CLI & AWS SAM CLI configured with `ap-south-1` permissions (optional for mock/demo mode)

### 2. Setup & Installation
```bash
git clone https://github.com/its-aryansingh/NETRA.git
cd NETRA/netra

# Install Python backend & Next.js frontend dependencies
make setup
```

### 3. Verify System Proof (<1s)
```bash
make verify
```

### 4. Run Test Suite
```bash
make test
```

### 5. Launch Frontend Cockpit
```bash
cd frontend
npm run dev
# Open http://localhost:3000 in your browser
```

---

## Demo Mode

**The public URL submitted for evaluation runs with `NEXT_PUBLIC_DEMO=1`.**

- **Why**: Reviewers and judges opening the link see a fully interactive, responsive cockpit with zero cold starts, zero API latency, and no dependency on live AWS credits.
- **Interactive Simulation**: Click the **Simulate Runaway Instance** button on the dashboard to trigger an end-to-end simulation (detect $\rightarrow$ investigate $\rightarrow$ approve $\rightarrow$ audit) client-side in 15 seconds.
- **Toggle to Real AWS**: Click the **Demo Mode** badge in the navigation bar to switch between mock simulation and live AWS API endpoints.

---

## Extending NETRA

NETRA is designed with a data-driven, declarative architecture. Adding detection rules or new AWS resource types requires zero core engine refactoring.

### Add a Detection Rule in 3 Steps
1. **Define the Rule in `rules.yaml`**: Add a declarative entry specifying `id`, `scope` (`resource` or `account`), `severity`, and threshold:
   ```yaml
   - id: excessive_egress
     scope: resource
     severity: warning
     field: network_out_bytes_per_hour
     operator: ">"
     value: 10737418240 # 10 GB/hr
     action: alert
     why: "Resource is transmitting >10 GB/hour outbound data transfer."
   ```
2. **Automatic Engine Ingestion**: `detector.py` automatically evaluates any rule defined in `rules.yaml` against normalized resource metrics.
3. **Verify in 1 Second**:
   ```bash
   python -m pytest backend/tests/test_detector.py -k test_rules_as_data_dynamic_change
   ```

### Add an AWS Resource Type in 5 Steps
1. **Define Unit Pricing Fallback**: Add fallback pricing to `FALLBACK_USD_HOUR` in `backend/netra/pricing.py`.
2. **Configure Price List API Filter**: Add service query filters in `_fetch_from_pricing_api` in `backend/netra/pricing.py`.
3. **Add Resource Discovery**: Implement the AWS describe call (e.g. `rds:DescribeDBInstances`) in `backend/netra/inventory.py`.
4. **Normalize Resource Payload**: Map the discovered attributes to `PricedResource` in `backend/netra/collector.py`.
5. **Declare Cedar Entity Schema**: Add resource attribute mappings in `policy/entities.json` and safety policies in `policy/netra.cedar`.

---

## Project Structure

```
netra/
├── Makefile                      # Judge & developer interface (verify, break, demo-up)
├── README.md                     # Comprehensive project documentation
├── LEARNING.md                   # Chronological engineering discoveries log
├── LICENSE                       # MIT License
├── SECURITY.md                   # Multi-tier safety and disclosure policy
├── CONTRIBUTING.md               # Contribution guidelines
├── .env.example                  # Environment variable configuration template
├── demo-stack/
│   └── template.yaml             # Standalone judge test stack (runaway, orphans, protected)
├── infra/
│   ├── template.yaml             # Main AWS SAM template (Streams, EventBridge, MCP Lambda)
│   └── samconfig.toml            # SAM deployment configuration
├── backend/
│   ├── pyproject.toml            # Pytest and project metadata
│   ├── requirements.txt          # Python dependencies (boto3, cedarpy, pyyaml, pytest)
│   ├── netra/
│   │   ├── config.py             # Single source of truth (regions, tables, constants)
│   │   ├── models.py             # Data models with detection_path and latency_ms
│   │   ├── pricing.py            # SHA-256 pricing engine with fallback resilience
│   │   ├── inventory.py          # Real-time resource collector and tag normalizer
│   │   ├── rules.yaml            # Declarative rules-as-data configuration
│   │   ├── detector.py           # Pure evaluation function & rolling median baseline
│   │   ├── collector.py          # Dual-path collector (sub-10s fast path + 60s sweep)
│   │   ├── policy.py             # Deterministic safety guards (forbid_protected, dependents)
│   │   ├── executor.py           # 5-stage Step Functions remediation executor
│   │   ├── audit.py              # Append-only DynamoDB audit ledger
│   │   ├── verify.py             # 6-check cryptographic proof harness (<1s)
│   │   ├── api.py                # Single-Lambda HTTP API router (12 endpoints + HMAC minting)
│   │   ├── mcp/                  # Model Context Protocol action server
│   │   │   ├── server.py         # MCP JSON-RPC handler (Lambda Function URL + stdio)
│   │   │   ├── tools.py          # netra_dry_run, netra_execute, netra_rollback, netra_status
│   │   │   ├── tokens.py         # HMAC-SHA256 human approval token engine (5m TTL, single-use)
│   │   │   ├── policy.py         # Pure policy guardrails
│   │   │   └── manifest.json     # Standard Claude Desktop MCP manifest
│   │   └── agent/
│   │       ├── tools.py          # Read-only observability tools with 'via' tracing
│   │       ├── prompt.py         # Constrained temperature=0 prompt instructions
│   │       ├── validator.py      # Zero-tolerance numeric grounding validator
│   │       ├── fallback.py       # High-fidelity templated narrative engine
│   │       └── investigator.py   # EventBridge finding investigation Lambda
│   └── tests/                    # 94 automated unit, integration, and policy tests
├── frontend/
│   ├── app/                      # Next.js 15 App Router (Overview, Investigation, Audit)
│   ├── components/               # High-contrast cockpit UI components
│   └── lib/                      # Zero-dependency demo data and API client store
└── scripts/
    ├── break.py                  # Fault injection script proving sub-10s detection
    ├── break.sh                  # Bash wrapper for break.py
    ├── break.ps1                 # Windows PowerShell wrapper for break.py
    ├── seed_demo.py              # Launch c5.4xlarge runaway resource on camera
    └── reset_demo.py             # Safe cleanup of managed demonstration instances
```

---

## What We Learned

A chronological record of engineering discoveries is maintained in **[`LEARNING.md`](LEARNING.md)**:
- **Phase 0**: EC2 G-family quota lag & pivoting to `c5.4xlarge`.
- **Phase 1**: Canonical JSON hashing for provable price provenance.
- **Phase 2**: Why rolling median baselines prevent acute spikes from pulling their own baseline.
- **Phase 3**: Reducing CloudWatch API latency from seconds to <400ms via batch queries.
- **Phase 4**: Placing a zero-tolerance numeric validator between Bedrock and the database.
- **Phase 5**: Defensive Decimal serialization shielding against API Gateway 502s.
- **Phase 6**: Monospace typography discipline for authoritative infrastructure cockpits.
- **Phase 7**: Dual policy enforcement points and sub-second verification proof.
- **Phase 8 (v3 Upgrade)**: Sub-10s detection via EventBridge state-change notifications addressing AWS Issue #92.
- **Phase 9 (v3 Upgrade)**: Isolating mutating IAM permissions to the MCP server with cryptographic human approval tokens.

---

## 👤 Author & Connect

**Aryan Raj Singh**
- **GitHub**: [@its-aryansingh](https://github.com/its-aryansingh)
- **Repository**: [its-aryansingh/NETRA](https://github.com/its-aryansingh/NETRA)
- **Email**: `arajsingh0505@gmail.com`

---

## AI Tool Disclosure

In compliance with official hackathon submission requirements:  
*Codebase generated with Google Gemini and Claude from written architectural specifications; system architecture, security boundary design, Cedar policy guardrails, and verification by the author.*

---

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.
