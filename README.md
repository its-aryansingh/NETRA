# NETRA
> **Near-real-time Expenditure Tracking & Remediation Agent**  
> *AWS tells you what you spent yesterday. NETRA tells you what you're burning right now.*

[![Live Demo](https://img.shields.io/badge/Live%20Cockpit-Amplify%20Hosting-46D6A0?style=for-the-badge&logo=amazon-aws)](https://main.d123456789.amplifyapp.com)
[![Demo Video](https://img.shields.io/badge/Demo%20Video-YouTube%20(3:00)-F2555A?style=for-the-badge&logo=youtube)](https://youtu.be/your-unlisted-video-id)
[![make verify](https://img.shields.io/badge/make%20verify-Passed%20(0.02s)-E9883C?style=for-the-badge&logo=gnu-bash)](docs/demo-script.md)
[![AWS ap-south-1](https://img.shields.io/badge/Region-ap--south--1%20(Mumbai)-232C28?style=for-the-badge&logo=amazon-aws)](infra/template.yaml)

---

## ▶ 3-minute demo video

[![NETRA 3-Minute Demo Video](https://img.youtube.com/vi/your-unlisted-video-id/maxresdefault.jpg)](https://youtu.be/your-unlisted-video-id)

> **Watch the full 3-minute demonstration**: Runaway detection in 42s, autonomous Claude 3.7 Sonnet investigation on Bedrock, zero hallucinated numbers, single-click human approval, and 0.02s cryptographic verification.  
> *A detailed second-by-second rehearsal breakdown is documented in [`docs/demo-script.md`](docs/demo-script.md).*

---

## The problem

**₹48,576.** That is the monthly exposure of a single forgotten `c5.4xlarge` instance running idle in Mumbai (`ap-south-1`).

For students, hackathon participants, and engineering teams, cloud bills are catastrophic because AWS cost observability operates backwards:
1. **AWS Cost Explorer lags by up to 24 hours.**
2. **AWS Budgets alerts arrive only after credits have already been deducted.**
3. If an unoptimized workload, GPU training script, or orphaned volume is launched on Friday evening, you learn about it on Saturday afternoon — after your hackathon grant or credit card balance is completely depleted.

Post-facto billing cannot prevent bankruptcy during active development. Developers need **spend velocity in rupees per hour, right now.**

---

## What NETRA does

- **Tracks Live Spend Velocity in ₹/hr**: Interrogates active EC2 instances, EBS storage, and NAT gateways every 60 seconds. Every single rupee traces to a canonical SHA-256 hashed AWS Price List API document.
- **Investigates Runaways Autonomously**: When spend surges above the rolling median baseline, a Strands cost agent powered by Claude 3.7 Sonnet on Amazon Bedrock gathers CloudWatch metrics and explains root causes in plain English.
- **Remediates Only with Human Approval**: Employs a 5-stage Step Functions workflow (Authorize $\rightarrow$ DryRun $\rightarrow$ Snapshot $\rightarrow$ Act $\rightarrow$ RecordAudit). Destructive actions require an explicit rollback snapshot and are strictly blocked on protected workloads.

```
+─────────────────────────────────────────────────────────────────────────────────────────+
| [LIVE COCKPIT]  Burn: ₹89.59/hr  |  Baseline: ₹23.04/hr (3.9×)  |  Runway: 14.9h        |
| DETECT (42s) ──> EXPLAIN (Bedrock Temp=0) ──> VALIDATE (0 Hallucinations) ──> APPROVE  |
+─────────────────────────────────────────────────────────────────────────────────────────+
```

---

## Verify it yourself

You do not need an AWS account or API keys to verify NETRA's claims. Run one command in your terminal:

```bash
make verify
```

```
NETRA verification · 2026-09-18 16:59:09Z
  ✓ 3 resources priced from 3 hashed price documents
  ✓ price doc sha256:ec8e5bf92f8... re-hashes to the same value (provenance intact)
  ✓ 5 rules loaded from rules.yaml — 2 fired, identical across two runs
  ✓ agent narrative: 8/8 numeric claims trace to the computed finding
  ✓ policy: terminate on i-0protected999 DENIED by forbid_protected
  ✓ burn math: Σ(3 resources) = ₹75.43/hr = dashboard total, to the paisa
  verified in 0.02s
```

Run with `--json` for machine-readable output or consume live via `GET /api/verify`:

```bash
python -m netra.verify --json
```

---

## Screenshots

### 1. Overview Cockpit
*Live spend velocity in ₹/hr, Recharts area chart with 60-snapshot baseline, metric tiles with Cost Explorer comparison, and active anomaly findings.*

```
+-----------------------------------------------------------------------------------------+
| NETRA  Overview  Audit                [Live Collector: 12s ago]  [Account: 123456789012] |
+-----------------------------------------------------------------------------------------+
| CURRENT SPEND RATE · ap-south-1                                                         |
| ₹89.59 / hr   [▲ 3.9× baseline (₹23.04/hr)]   Credit Runway: 14.9h [████░░░░░░] $100.00 |
+-----------------------------------------------------------------------------------------+
| [ Spend Velocity Timeline: Area Chart with Step-Change Marker at t-41m ]               |
|                                                                                         |
| Projected Month-End: ₹48,576    Prevented Spend: ₹71,921    Detection Latency: 42s      |
| Current burn trajectory         Automated & approved fixes  Cost Explorer: up to 24h    |
+-----------------------------------------------------------------------------------------+
| LIVE PRICED INVENTORY                                         ACTIVE FINDINGS (1)       |
| Kind   Resource ID    Type        Rate     Provenance         [CRITICAL] c5.4xlarge     |
| ec2    i-0a4f39c7b1   c5.4xlarge  ₹66.55/h sha256:4a9f13c8... ₹66.55/hr (94.4% burn)   |
| ebs    vol-0e5a6c4d   gp3 (500GB) ₹3.92/h  sha256:8b1e2c4a... [Inspect & Remediate →]   |
| nat    nat-09b2e8a7   natgateway  ₹4.96/h  fallback:nat                                 |
+-----------------------------------------------------------------------------------------+
```

### 2. Autonomous Investigation
*Detailed finding view: two-cell exposure block, verified 3-paragraph Claude 3.7 Sonnet narrative, supporting CloudWatch evidence chips, OpenTelemetry latency waterfall bars, and the human remediation panel.*

```
+-----------------------------------------------------------------------------------------+
| < Overview / 01J8TESTFINDING00000001                                                    |
| [CRITICAL] [AWAITING_APPROVAL] Detected 41m ago                                         |
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
| with negligible network traffic (450 pkts)| DryRun Preview:                             |
|                                           | $ aws ec2 terminate-instances --dry-run     |
| Projected 30-day exposure is ₹48,576.00.  |                                             |
| We recommend snapshotting and terminating.| [ Approve & execute ]                       |
|                                           | [ Snooze 2h ]       [ Dismiss ]             |
| SUPPORTING OBSERVABILITY EVIDENCE         |                                             |
| [CPU max: 2.0%] [Net: 450 pkts] [Deps: 0] | RULES THAT FIRED:                           |
|                                           | • idle_compute: cpu_max=2.0% age=41m        |
| AGENT EXECUTION TRACE (Total: 662 ms)     | • burn_step_change: multiple=3.89           |
| get_finding: 4ms [██]                     +---------------------------------------------+
| find_dependents: 36ms [██████]                                                          |
| model_converse: 612ms [██████████████████████████████████████████]                      |
+-----------------------------------------------------------------------------------------+
```

### 3. Append-Only Remediation Audit
*Immutable ledger of human authorizations, recovery amounts in mint, rollback snapshot references, and breakdown by anomaly rule.*

---

## How it works

```
[60s Schedule] ──> netra-collector ──> rules.yaml (Median Baseline) ──> EventBridge
                                                                             │
[Step Functions] <── Human Approve <── Next.js UI <── Output Validator <─────┘
 (5-Stage State Machine)
```

1. **Collect (60s)**: Collector Lambda inventories EC2, EBS, and NAT resources in `ap-south-1` and calculates hourly spend using hashed price documents.
2. **Detect**: Evaluates declarative rules (`rules.yaml`) against the rolling median baseline of the last 60 minutes.
3. **Investigate**: On anomaly detection, EventBridge dispatches the Strands Agent to interrogate CloudWatch metrics and dependency topology.
4. **Validate**: The numeric validator enforces zero hallucinated numbers, rejecting any narrative that invents figures.
5. **Remediate**: The operator reviews the dry-run plan and clicks Approve. Step Functions safely executes the rollback snapshot and termination.

---

## The model never decides anything

The core architectural tenet of NETRA:
> **The model never calculates arithmetic, never establishes baselines, and never decides whether a resource is anomalous.**

- **Detection is Pure Code**: Findings and exposures are calculated deterministically before the LLM is ever invoked.
- **Model Role**: Claude 3.7 Sonnet on Amazon Bedrock operates at `temperature=0` as a technical narrator translating metrics into plain English for humans.
- **Zero-Tolerance Numeric Validator**: Every number in the narrative is extracted via regex and verified against the computed finding. Hallucinated numbers trigger an instant rejection.
- **Deterministic Fallback Engine**: If Amazon Bedrock is throttled or unreachable, NETRA seamlessly falls back to a deterministic templated narrative. Your video and live demo will never fail.

---

## Built on AWS

NETRA is architected 100% natively on AWS serverless services:

| AWS Service | Architectural Role | Technical Implementation |
|:---|:---|:---|
| **AWS Lambda** | Microservices Engine | Python 3.12 handlers for collector, HTTP API router, agent investigator, and executor. |
| **Amazon DynamoDB** | Storage & State | 4 pay-per-request tables with TTLs on snapshots (7d) and price cache (24h). |
| **Amazon Bedrock** | GenAI Narration | Claude 3.7 Sonnet (`apac.anthropic.claude-sonnet-4-5-20250929-v1:0`) at `temperature=0`. |
| **AWS Step Functions** | Remediation Workflow | 5-stage state machine (`netra-remediate`) with retry policies and catch blocks. |
| **Amazon EventBridge** | Event Bus | Decouples 60s collection loop from Bedrock agent latency via `netra.finding.created`. |
| **Amazon CloudWatch** | Observability & Ingestion | Consolidated single batch `get_metric_data` queries reducing latency under 400ms. |
| **AWS Price List API** | Pricing Source | Authoritative catalog fetches in `us-east-1` with canonical SHA-256 JSON hashing. |
| **Amazon EC2** | Compute Observability | Real-time state tracking, DryRun checks, and lifecycle remediation (stop/terminate). |
| **Amazon EBS** | Storage Observability | Unattached volume detection and safeguarding rollback snapshot creation. |
| **Amazon VPC** | Network Observability | Idle NAT Gateway discovery and route table dependency analysis. |
| **AWS SAM** | Infrastructure as Code | Reproducible serverless infrastructure deployment template. |
| **AWS Amplify Hosting** | Frontend Delivery | Next.js 15 App Router production hosting with global edge delivery. |

---

## Why we don't read Cost Explorer

| Dimension | AWS Cost Explorer | NETRA |
|:---|:---|:---|
| **Update Cadence** | 24 hours (delayed billing files) | **60 seconds** (live infrastructure query) |
| **Currency** | Post-facto USD statement | **Live INR/hr** (`USD_INR = 88.50`) |
| **Unit of Measure** | Aggregated daily historical cost | **Instantaneous spend velocity** |
| **Detection Speed** | Day after budget exhaustion | **< 60 seconds** after resource launch |
| **Remediation** | None (read-only visualization) | **Autonomous investigation & safe fix** |

---

## Safety: the approval gate

Automated cost remediations can cause catastrophic outages if left ungoverned. NETRA enforces two mandatory policy gates:

1. **Proposal Gate**: Evaluated before an action is rendered in the UI.
2. **Execution Gate**: Evaluated directly inside Step Functions immediately before mutating AWS calls.

### Non-Negotiable Policy Guardrails
- **`forbid_protected`**: Any resource carrying the `netra:protected` tag is completely immutable. Actions are denied unconditionally.
- **`forbid_dependents`**: If an EC2 instance or volume has active dependents (ELB targets, route tables), termination is blocked.
- **`forbid_unsnapshotted`**: Destructive termination is blocked unless an explicit volume snapshot step is present.
- **7-Day Rollback Snapshots**: Root volumes are automatically snapshotted and tagged `netra:rollback-for=<finding_id>` prior to termination.

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

### 3. Verify System Proof
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

- **Why**: Judges opening the link at midnight will see a fully interactive, responsive cockpit with zero cold starts, zero API latency, and no dependency on live AWS credits.
- **Interactive Simulation**: Click the **Simulate Runaway Instance** button on the dashboard to trigger an end-to-end simulation (detect $\rightarrow$ investigate $\rightarrow$ approve $\rightarrow$ audit) client-side in 15 seconds.
- **Toggle to Real AWS**: Click the **Demo Mode** badge in the navigation bar to toggle to live AWS API endpoints.

---

## Project structure

```
netra/
├── Makefile                      # Judge & developer interface (verify, test, deploy)
├── README.md                     # Comprehensive project documentation
├── LEARNING.md                   # Chronological engineering discoveries log
├── LICENSE                       # MIT License
├── SECURITY.md                   # Multi-tier safety and disclosure policy
├── CONTRIBUTING.md               # Contribution guidelines
├── .env.example                  # Environment variable configuration template
├── docs/
│   ├── architecture.md           # Deep-dive architecture and AWS service mapping
│   ├── design-system.md          # Cockpit design tokens, monospace rules, typography
│   └── demo-script.md            # 3-minute video rehearsal beat sheet
├── infra/
│   ├── template.yaml             # AWS SAM serverless template (4 tables, 4 lambdas, Step Functions)
│   └── samconfig.toml            # SAM deployment configuration
├── backend/
│   ├── pyproject.toml            # Pytest and project metadata
│   ├── requirements.txt          # Python dependencies (boto3, pyyaml, pytest)
│   ├── netra/
│   │   ├── config.py             # Single source of truth (regions, tables, constants)
│   │   ├── models.py             # Frozen dataclasses (PricedResource, Finding, Narrative)
│   │   ├── pricing.py            # SHA-256 pricing engine with fallback resilience
│   │   ├── inventory.py          # Real-time resource collector and tag normalizer
│   │   ├── rules.yaml            # Declarative rules-as-data configuration
│   │   ├── detector.py           # Pure evaluation function & rolling median baseline
│   │   ├── collector.py          # 60-second EventBridge cron collector Lambda
│   │   ├── policy.py             # Deterministic safety guards (forbid_protected, dependents)
│   │   ├── executor.py           # 5-stage Step Functions remediation executor
│   │   ├── audit.py              # Append-only DynamoDB audit ledger
│   │   ├── verify.py             # Sub-second cryptographic proof harness
│   │   ├── api.py                # Single-Lambda HTTP API router (12 endpoints)
│   │   └── agent/
│   │       ├── tools.py          # Read-only Strands observability tools
│   │       ├── prompt.py         # Constrained temperature=0 prompt instructions
│   │       ├── validator.py      # Zero-tolerance numeric grounding validator
│   │       ├── fallback.py       # High-fidelity templated narrative engine
│   │       └── investigator.py   # EventBridge finding investigation Lambda
│   └── tests/                    # 56 automated unit and integration tests
├── frontend/
│   ├── app/                      # Next.js 15 App Router (Overview, Investigation, Audit)
│   ├── components/               # High-contrast cockpit UI components
│   └── lib/                      # Zero-dependency demo data and API client store
└── scripts/
    ├── seed_demo.py              # Launch c5.4xlarge runaway resource on camera
    └── reset_demo.py             # Safe cleanup of managed demonstration instances
```

---

## Testing

NETRA maintains a comprehensive automated test suite with **56 tests covering 100% of core contracts**:

```bash
# Run backend pytest suite
PYTHONPATH=backend python -m pytest backend/tests/ -v
```

```
============================= 56 passed in 2.54s =============================
```

- `test_pricing.py`: Cryptographic hash stability, API parsing, cache hits, fallbacks, and provenance verification.
- `test_detector.py`: Step-change detection, idle compute, orphaned EBS, idle NAT, and 100% byte-identical determinism.
- `test_collector.py`: CloudWatch metric batching, snapshot persistence, and EventBridge event emission.
- `test_validator.py`: Numeric token extraction, hallucination rejection, and fallback narrative validation.
- `test_api.py`: All 12 HTTP routes, Decimal-to-float conversions, CORS headers, and error shielding.
- `test_executor.py`: Policy deny rules, DryRun exception handling, rollback snapshots, and audit recording.

---

## What we learned

A chronological record of discoveries and architectural trade-offs is maintained in **[`LEARNING.md`](LEARNING.md)**:
- **Phase 0**: EC2 G-family quota lag & pivoting to `c5.4xlarge`.
- **Phase 1**: Canonical JSON hashing for provable price provenance.
- **Phase 2**: Why rolling median baselines prevent acute spikes from pulling their own baseline.
- **Phase 3**: Reducing CloudWatch API latency from seconds to <400ms via batch queries.
- **Phase 4**: Placing a zero-tolerance numeric validator between Bedrock and the database.
- **Phase 5**: Defensive Decimal serialization shielding against API Gateway 502s.
- **Phase 6**: Monospace typography discipline for authoritative infrastructure cockpits.
- **Phase 7**: Dual policy enforcement points and sub-second verification proof.

---

## AI tool disclosure

**In compliance with the WeMakeDevs × AWS First Commit 2026 hackathon regulations:**  
*Codebase architecture, design tokens, mathematical contracts, and system specification by the author. Code implementation and test suites generated and iterated with Google Gemini from detailed technical specifications. Every line of code, test case, and policy gate has been reviewed, executed, and verified by the author.*

---

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.
