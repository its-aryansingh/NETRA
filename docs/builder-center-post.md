# Building NETRA: How a 24-Hour Billing Lag Turned into an Autonomous AWS Cost Agent

*Submitted to the WeMakeDevs × AWS First Commit 2026 Hackathon (Ship It Track)*  
*Author: NETRA Team*

---

## The Panic that Started It All

Every cloud engineer and student developer remembers their first accidental AWS bill. 

It almost always follows the same cruel script: you spin up an EC2 instance or GPU node on Friday evening to benchmark a deep learning model or test a microservice. You close your laptop and head to sleep. On Saturday morning, you log into the AWS Console and check AWS Cost Explorer. It reports that you have spent **$0.00** today. You breathe a sigh of relief.

Then, on Sunday morning, you receive an automated email from AWS: your monthly grant is exhausted, and your personal credit card has been charged **$420.00**.

Why did this happen? Because **AWS Cost Explorer updates on a 24-hour delayed batch cycle.** 

Cost Explorer was designed for finance departments conducting end-of-month reconciliations, not for developers actively deploying code. By the time a billing dashboard alerts you that an instance is burning money, your budget is already gone. 

We built **NETRA** (**N**ear-real-time **E**xpenditure **T**racking & **R**emediation **A**gent) to solve this exact problem. Our premise is simple: **AWS tells you what you spent yesterday. NETRA tells you what you are burning right now in rupees per hour.**

---

## What We Built

NETRA is an autonomous cloud financial observability and remediation cockpit built 100% natively on AWS in the Mumbai region (`ap-south-1`).

Rather than reading delayed billing files, NETRA interrogates active infrastructure (EC2, EBS, and NAT Gateways) every 60 seconds, prices every resource deterministically against authentic AWS Price List API documents, and computes your exact account burn rate (`₹/hr`). 

When spend surges above a rolling median baseline, NETRA dispatches a **Strands Cost Agent** powered by **Claude 3.7 Sonnet on Amazon Bedrock** (running at `temperature=0`) to investigate CloudWatch telemetry and explain the anomaly in plain English. 

Finally, NETRA provides a human-gated remediation flow: through a 5-stage AWS Step Functions workflow, an operator can click a single button to create a safeguarding rollback snapshot and terminate the runaway resource, dropping spend back to baseline within 60 seconds.

---

## Which AWS Service Did What

We deliberately chose a serverless, event-driven architecture to keep NETRA lightweight, cost-effective, and fast:

1. **AWS Lambda (Python 3.12)**:
   - `netra-collector`: Runs every 60 seconds via EventBridge Scheduler to inventory resources, fetch CloudWatch metrics, and calculate spend.
   - `netra-api`: A monolithic single-Lambda router serving all 12 API Gateway HTTP API v2 endpoints without cold-start multiplication.
   - `netra-investigator`: EventBridge-triggered agent handler that gathers evidence and generates natural language explanations.
   - `netra-executor`: Executes the 5-stage Step Functions remediation pipeline.

2. **Amazon DynamoDB**:
   - `netra_burn_snapshots`: Minute-by-minute spend velocity snapshots (7-day TTL).
   - `netra_price_cache`: Authoritative pricing catalog cached for 24 hours with SHA-256 raw document hashes.
   - `netra_findings`: Active and historic anomaly records with a `status-index` Global Secondary Index.
   - `netra_audit_log`: Append-only immutable ledger recording every human approval, remediation action, and rollback snapshot ID.

3. **Amazon Bedrock**:
   - Powers the Strands Agent using Claude 3.7 Sonnet (`apac.anthropic.claude-sonnet-4-5-20250929-v1:0`) in `ap-south-1` at `temperature=0` for deterministic, grounded reasoning.

4. **AWS Step Functions (`netra-remediate`)**:
   - Orchestrates the 5-stage remediation lifecycle (`Authorize` $\rightarrow$ `DryRun` $\rightarrow$ `Snapshot` $\rightarrow$ `Act` $\rightarrow$ `RecordAudit`) with built-in error handling and fallback audit logging.

5. **Amazon EventBridge**:
   - Emits `netra.finding.created` events to decouple the 60-second collection loop from model inference times.

6. **AWS Price List API (in `us-east-1`)**:
   - Provides authoritative, real-time on-demand pricing documents. Every fetch is hashed with SHA-256 so every rupee on the dashboard can be mathematically proven.

7. **AWS Amplify Hosting**:
   - Deploys our Next.js 15 App Router frontend on global CDN edge nodes with sub-100ms response times.

---

## What Broke, What Surprised Us, and What We Learned

Building a real-time autonomous system in a hackathon environment forced us to confront unexpected edge cases. Here is the honest truth about what broke and how we adapted:

### 1. The G-Family Quota Discovery
We initially planned to demonstrate runaway spend on camera by launching an expensive GPU instance (`g5.xlarge`). When we attempted to launch it in `ap-south-1`, AWS threw a quota error: **default EC2 quotas for G-family instances in student and personal accounts are 0 vCPUs**, and raising them takes days via AWS Support tickets.
- **The Pivot**: We pivoted our on-camera demonstration to `c5.4xlarge` (16 vCPUs, 32 GiB RAM, ~₹66.55/hr). It burns fast enough to noticeably move the dashboard needle within 60 seconds, while remaining well within default service quotas.

### 2. The Bedrock Access Wait & The Deterministic Fallback Engine
When setting up Amazon Bedrock in `ap-south-1`, model access requests for Anthropic Claude models can experience approval delays or regional rate throttling. 
- **The Solution**: We realized that no judge's evaluation or video recording should ever depend on third-party API availability. We built an industrial-grade **Deterministic Fallback Engine** (`fallback.py`) that formats publication-grade 3-paragraph explanations directly from the computed finding metrics. If Bedrock throttles, the system automatically falls back and renders a subtle `"deterministic narrative"` badge on the UI. The recording is never sabotaged.

### 3. The CloudWatch API Throttling Trap
In our first prototype, the collector looped through candidate EC2 instances, making individual `get_metric_statistics` API calls for each resource. In accounts with multiple instances, this immediately inflated Lambda execution times to over 8 seconds and caused CloudWatch API rate limiting.
- **The Fix**: We consolidated all candidate metric requests into a **single batch `get_metric_data` query**. This slashed API latency from 8+ seconds to under 400 milliseconds, ensuring the collector executes cleanly inside its 60-second cron budget.

### 4. Language Models Should Never Do Math
One of our earliest experiments involved asking the LLM to calculate percentage exposure and multiple-over-baseline. The result was predictable: Claude occasionally calculated `3.89×` as `4.2×`, or rounded numbers inconsistently.
- **Our Non-Negotiable Rule**: **The model never computes or decides anything.** All arithmetic, baselines, and findings are 100% computed in deterministic Python code before the model is ever called. The model's sole job is narration. To enforce this, we placed a zero-tolerance token-level numeric validator (`validator.py`) between the model and the database. If the model invents even a single ungrounded number, the narrative is rejected immediately.

### 5. Windows Character Encoding (`UnicodeEncodeError`)
While developing locally on Windows PowerShell, our Python test harness threw `UnicodeEncodeError: 'charmap' codec can't encode character '\u20b9'` when printing the Indian Rupee symbol (`₹`). 
- **The Fix**: We configured all logging to use ASCII-safe outputs, added automatic UTF-8 stream reconfiguration (`sys.stdout.reconfigure(encoding='utf-8')`), and enforced strict structured JSON logging across all backend services.

---

## What We Would Do Differently

If we had another week to expand NETRA:

1. **Cedar Policy Language**: We considered integrating AWS Cedar for policy evaluations. However, at ~30 working hours, implementing Cedar bindings and schema entities would have risked delivery of our core collector and UI. We implemented a clean 40-line Python policy guard (`policy.py`) instead. In v2, we would formalize this with Amazon Verified Permissions and Cedar.
2. **Multi-Region Cross-Account Hub**: Currently, NETRA monitors `ap-south-1`. Expanding to an AWS Organizations multi-account collector with an AWS Transit Gateway topology would allow enterprises to monitor entire organizational units from a single cockpit.
3. **Automated RDS & Aurora Support**: Extending our rules engine to identify idle database instances and unattached read replicas.

---

## The Greatest Lesson: `make verify`

If there is one lesson that defined our build, it is this: **extraordinary claims require immediate, reproducible proof.**

Anyone can claim their AI agent is "grounded", "deterministic", or "safe". But in NETRA, we wanted judges and developers to be able to prove it for themselves in under two seconds.

By running `make verify` in our terminal:
- It re-hashes the raw AWS Price List document with SHA-256 to prove price authenticity.
- It loads `rules.yaml` and executes the detector twice to prove 100% byte-identical determinism.
- It validates that 100% of numeric claims in the agent's explanation trace to computed findings.
- It attempts to terminate a protected resource and proves that the policy gate denies it.
- It sums active resource costs and reconciles with the dashboard total to the paisa.

All in **0.02 seconds**.

AWS tells you what you spent yesterday. NETRA tells you what you're burning right now — and proves it before you spend another rupee.
