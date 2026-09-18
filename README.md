# NETRA
> **Near-real-time Expenditure Tracking & Remediation Agent**  
> *AWS tells you what you spent yesterday. NETRA tells you what you're burning right now.*

[![Live Cockpit](https://img.shields.io/badge/Live%20Cockpit-Amplify%20Hosting-46D6A0?style=for-the-badge&logo=amazon-aws)](https://main.d123456789.amplifyapp.com)
[![Demo Video](https://img.shields.io/badge/Demo%20Video-YouTube%20(3:00)-F2555A?style=for-the-badge&logo=youtube)](https://youtu.be/your-unlisted-video-id)
[![make verify](https://img.shields.io/badge/make%20verify-Passed%20(0.69s)-E9883C?style=for-the-badge&logo=gnu-bash)](#reproduce-it-in-90-seconds)
[![Tests Passing](https://img.shields.io/badge/Tests-69%2F69%20Passing-2ECC71?style=for-the-badge&logo=pytest)](backend/tests/)
[![AWS ap-south-1](https://img.shields.io/badge/Region-ap--south--1%20(Mumbai)-232C28?style=for-the-badge&logo=amazon-aws)](infra/template.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

---

## ▶ 3-minute demo video

[![NETRA 3-Minute Demo Video](https://img.youtube.com/vi/your-unlisted-video-id/maxresdefault.jpg)](https://youtu.be/your-unlisted-video-id)

> **Watch the full 3-minute demonstration**: Fast-path detection in under 10 seconds, autonomous Claude 3.7 Sonnet investigation on Amazon Bedrock, zero hallucinated numbers, single-click human approval via HMAC-SHA256 tokens, MCP action server security boundary, and sub-second cryptographic proof.  
> *A second-by-second rehearsal breakdown is documented in [`docs/demo-script.md`](docs/demo-script.md).*

---

## The problem

I got ₹200 of AWS credits for this hackathon. I have already watched fellow students lose their entire grant overnight to a forgotten instance.

**₹48,576.** That is the 30-day exposure of a single forgotten `c5.4xlarge` compute instance running idle in Mumbai (`ap-south-1`). If a student or engineer starts an unmonitored GPU training notebook, a Kubernetes cluster, or an unattached gp3 volume on Friday afternoon, they learn about it on Saturday afternoon — after their credits are burnt and their personal card is charged.

Cloud bills are catastrophic because AWS cost observability operates backwards:
1. **AWS Cost Explorer lags by up to 24 hours.**
2. **AWS Budgets alerts arrive only after credits have already been deducted.**
3. Post-facto billing statements cannot prevent bankruptcy during active development.

Developers do not need to know what they spent yesterday. They need to know their **spend velocity in rupees per hour, right now.**

---

## AWS already has Cost Anomaly Detection. Why this exists.

Judges often ask: *"Doesn't AWS already have Cost Anomaly Detection?"*

AWS's own engineering team answered this in public issue [aws-solutions/innovation-sandbox-on-aws#92](https://github.com/aws-solutions/innovation-sandbox-on-aws/issues/92):

> *"Cost Anomaly Detection has a delay of **up to 24 hours** before detecting an anomaly... Cost Anomaly Detection evaluates cost data **at most 3 times per day**, which could lead to a worst case scenario of **33 hours** before an anomaly is detected."*  
> — AWS Solutions Architecture Team

Their own recommended fix:
> *"Monitor CloudTrail events ... **1-5 minutes rather than relying on billing data**."*

**NETRA implements exactly what AWS recommended but never built as a product.**  
By combining Amazon EventBridge state-change notifications (`aws.ec2`) with instantaneous price resolution, NETRA detects runaway resources **in under 10 seconds** — not 24 to 33 hours.

---

## Reproduce it in 90 seconds

You can reproduce NETRA's entire detection, policy refusal, and verification claims on your own machine in 90 seconds.

### 1. Verification Proof (No AWS account required)
Run one command:
```bash
make verify
```
```
NETRA verification · 2026-09-18 20:23:52Z
  ✓ fast path: instance launched at T, finding written at T+0.1s
  ✓ mcp: netra_execute refused a replayed approval token
  ✓ iam: investigator role contains 0 mutating actions
  ✓ 3 resources priced from 3 hashed price documents
  ✓ 6 rules loaded from rules.yaml — 2 fired, identical across two runs
  ✓ policy: terminate on i-0protected999 DENIED by forbid_protected
  verified in 0.69s
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
  [+] [T1] Finding Created at: 2026-09-18T20:22:40.113817+00:00
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

## What NETRA does

- **Dual-Path Detection in <10s**: Detects newly launched compute via EventBridge state-change notifications in under 10 seconds; backs it up with a 60-second priced inventory sweep.
- **Autonomous Bedrock Investigation**: Dispatches a Claude 3.7 Sonnet agent (`temperature=0`) that inspects CloudWatch metrics, checks dependent architecture, and explains root causes in plain English.
- **Zero-Mutating Agent IAM + MCP Boundary**: The AI model has **zero mutating IAM permissions**. It can only preview proposals. Remediation is gated behind human-minted HMAC-SHA256 tokens executed exclusively by the NETRA MCP action server.

---

## Screenshots

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

### 3. Append-Only Remediation Audit
*Immutable ledger of human authorizations, cryptographic token IDs, rollback snapshot links, and spend prevented.*

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

## The agent cannot change anything

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
   │  [Deterministic Policy Guardrails]                     │
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
- An AI model that hallucinations or gets prompt-injected cannot execute an unauthorized action. Calling `netra_execute` without a human-minted token fails immediately.
- Replaying a valid token a second time fails (`replay attack rejected`).
- Tampering with the action parameters invalidates the cryptographic plan hash.

---

## The model never decides anything

- **Detection is Pure Code**: Findings and exposures are calculated deterministically before the LLM is ever invoked.
- **Model Role**: Claude 3.7 Sonnet on Amazon Bedrock operates at `temperature=0` solely as a technical narrator translating metrics into plain English for humans.
- **Zero-Tolerance Numeric Validator**: Every number in the narrative is extracted via regex and verified against the computed finding. Hallucinated numbers trigger an instant rejection and retry.
- **Deterministic Fallback Engine**: If Amazon Bedrock is throttled or unreachable, NETRA seamlessly engages a deterministic templated narrative engine. Live demos and videos never fail.

---

## Built on AWS

NETRA is architected natively across 6 of the 7 official WeMakeDevs × AWS hackathon track rows, with the 7th row (Containers) rejected on principled FinOps grounds:

| Hackathon Track Row | Stack / Tools | NETRA Architecture & Implementation |
|:---|:---|:---|
| **1. Agents and AI** | Bedrock · Strands Agents SDK | **Amazon Bedrock** (Claude 3.7 Sonnet at `temperature=0`) for natural-language root cause narration with zero-tolerance numeric validation. Multi-agent MCP orchestration via **Model Context Protocol (MCP)**. |
| **2. Serverless** | Lambda · API Gateway · Step Functions · SAM | **AWS Lambda** (Python 3.12 microservices with zero cold-start dependencies), **Amazon API Gateway** (HTTP router), **AWS Step Functions** (`netra-remediate` 5-stage workflow), and **AWS SAM** for reproducible IaC. |
| **3. Servers and runtimes** | EC2 · Amplify Hosting | **Amazon EC2** (monitored subject, dry-run safety verification, lifecycle remediation), **AWS Amplify Hosting** (Next.js 15 App Router deployment globally distributed via edge CloudFront points of presence). |
| **4. Data and search** | DynamoDB · S3 | **Amazon DynamoDB** (4 on-demand pay-per-request tables: findings, snapshots, audit, price cache with automatic TTL pruning), **Amazon S3** for immutable remediation audit logs and pricing catalogue reference caches. |
| **5. Auth and policy** | IAM · Cedar Guardrails · HMAC Tokens | **Zero-Mutating Agent IAM** (AI model possesses zero destructive actions), **Cedar-style deterministic policy guardrails** (`forbid_protected`, `forbid_dependents`, `forbid_unsnapshotted`), and cryptographic **HMAC-SHA256 human approval tokens** (5m TTL, single-use nonce). |
| **6. The plumbing** | EventBridge · SQS · SNS · CloudWatch | **Amazon EventBridge** (sub-10s `aws.ec2` state change capture & 60s cron sweep), **Amazon SQS + DLQ** (`NetraFindingsQueue` with redrive to `NetraFindingsDLQ` on 3 retries), **Amazon SNS** (`netra-critical-findings` mobile push alerts for critical runaway spend), and **Amazon CloudWatch** (consolidated metric batching, custom `NETRA` namespace metrics, live 4-widget dashboard, and `netra-burn-rate-critical` alarm). |
| **7. Containers and Kubernetes** | EKS · ECS · Fargate | **Deliberately empty on principled FinOps grounds** (see below). |

### Why there are no containers here

> NETRA's entire workload is a 60-second schedule, an event handler, and an HTTP API — a few seconds of compute per minute. Running an ECS service or an OpenSearch cluster around the clock to serve that would cost more than most of the waste NETRA is built to catch. We chose Lambda, DynamoDB on-demand, and S3 precisely because they cost nothing when nothing is happening. **Building a cost tool on always-on infrastructure would have been the first thing the tool complained about.**

---

## Use NETRA from your editor

Because NETRA's action server is an authentic Model Context Protocol (MCP) server, you can connect it directly to **Claude Desktop**, **Cursor**, or any MCP-compatible agent to monitor your cloud spend from your IDE.

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

## Quick start

### 1. Prerequisites
- Python 3.12+
- Node.js 20+
- AWS CLI & AWS SAM CLI configured with `ap-south-1` permissions

### 2. Setup & Installation
```bash
git clone https://github.com/its-aryansingh/netra.git
cd netra

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

## Demo mode

**The public URL submitted for evaluation runs with `NEXT_PUBLIC_DEMO=1`.**

- **Why**: Judges opening the link will see a fully interactive, responsive cockpit with zero cold starts, zero API latency, and no dependency on live AWS credits.
- **Interactive Simulation**: Click the **Simulate Runaway Instance** button on the dashboard to trigger an end-to-end simulation (detect $\rightarrow$ investigate $\rightarrow$ approve $\rightarrow$ audit) client-side in 15 seconds.
- **Toggle to Real AWS**: Click the **Demo Mode** badge in the navigation bar to toggle to live AWS API endpoints.

---

## Extending NETRA

### Adding a Rule in 3 Steps
1. Open `backend/netra/rules.yaml`.
2. Add your rule condition:
   ```yaml
   - id: high_iops_volume
     severity: warning
     scope: resource
     condition:
       kind: ebs
       iops: "> 3000"
       age_seconds: "> 3600"
   ```
3. Run `make test` — NETRA's rules engine automatically loads and evaluates the rule deterministically.

### Adding a Resource Type in 5 Steps
1. Add resource parser in `backend/netra/inventory.py`.
2. Add price query filter in `backend/netra/pricing.py`.
3. Add CloudWatch metric mapping in `backend/netra/collector.py`.
4. Add policy guardrail in `backend/netra/policy.py`.
5. Add dry-run/execute action in `backend/netra/mcp/tools.py`.

---

## Project structure

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
│   ├── requirements.txt          # Python dependencies
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
│   └── tests/                    # 69 automated unit, integration, and policy tests
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

## Testing

NETRA maintains a comprehensive automated test suite with **69 tests covering 100% of core contracts**:

```bash
# Run backend pytest suite
PYTHONPATH=backend python -m pytest backend/tests/ -v
```

```
============================= 69 passed in 2.56s =============================
```

- `test_mcp_policy.py`: HMAC token validation, replay defense, TTL expiry, plan tampering rejection, zero-mutating agent IAM verification, and fast-path latency measurement.
- `test_pricing.py`: Cryptographic hash stability, API parsing, cache hits, fallbacks, and provenance verification.
- `test_detector.py`: Step-change detection, idle compute, orphaned EBS, idle NAT, and 100% byte-identical determinism.
- `test_collector.py`: CloudWatch metric batching, snapshot persistence, and EventBridge event emission.
- `test_validator.py`: Numeric token extraction, hallucination rejection, and fallback narrative validation.
- `test_api.py`: All 12 HTTP routes, Decimal-to-float conversions, CORS headers, and HMAC approval token minting.
- `test_executor.py`: Policy deny rules, DryRun exception handling, rollback snapshots, and audit recording.

---

## What we learned

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

## AI tool disclosure

**In compliance with the WeMakeDevs × AWS First Commit 2026 hackathon regulations:**  
*Codebase architecture, design tokens, mathematical contracts, and system specification by the author. Code implementation and test suites generated and iterated with Google Gemini from detailed technical specifications. Every line of code, test case, and policy gate has been reviewed, executed, and verified by the author.*

---

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.
