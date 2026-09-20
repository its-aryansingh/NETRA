# NETRA — 3-Minute Video Demo Script (Second-by-Second)

> **Optimized for the WeMakeDevs × AWS "Ship It" Track Criteria & Kunal Kushwaha's Submission Guidelines**  
> **Target Duration**: 2m 55s (under 3:00 max hard limit)  
> **Format**: Screen recording with crisp microphone voiceover. Record first, upload to YouTube as Unlisted/Public.

---

### [0:00 – 0:25] The Hook: "Your Bill is a Rear-View Mirror"
- **On-Screen**: Open browser to AWS Cost Explorer showing "Last updated 24 hours ago" or empty budget alerts, then show `https://github.com/aws-solutions/innovation-sandbox-on-aws/issues/92`.
- **Voiceover**:
  > *"Every developer knows the dread of an unexpected AWS bill. AWS gave 16,000 hackathon participants $200 in credits. But here's the dirty secret: AWS Cost Explorer lags by up to 24 to 33 hours. AWS's own solutions engineering team documented this exact blind spot in GitHub Issue #92, calling for CloudTrail and EventBridge monitoring. Nobody built it. We built it. This is NETRA — Near-real-time Expenditure Tracking and Remediation Agent."*

---

### [0:25 – 0:50] The Cockpit at Rest: Live Spend Velocity
- **On-Screen**: Switch to NETRA Cockpit (`localhost:3000` or live Amplify URL). Highlight the carbon-black monospace instrument UI, live burn rate (`₹127.30 / hr`), and the 60-snapshot expenditure velocity chart.
- **Voiceover**:
  > *"This isn't a post-facto billing dashboard. NETRA is a real-time operational instrument. It samples running infrastructure continuously and prices every single compute, storage, and networking resource deterministically against SHA-256 hashed AWS Price List documents. Here, spend velocity is tracking at ₹127.30 per hour — 5.53 times our rolling baseline. Our credit runway shows 15 hours remaining before our $200 allocation runs out."*

---

### [0:50 – 1:20] The Fast-Path Detection (<10 Seconds)
- **On-Screen**: Point to the right rail showing the Critical finding: **Runaway c5.4xlarge (₹66.55/hr)** burning 3.9× baseline, alongside detection latency banner showing **42s** (sub-10s fast path via EventBridge).
- **Voiceover**:
  > *"When an unmonitored c5.4xlarge instance was provisioned, Amazon EventBridge captured the state change on our fast path in under 10 seconds — measured as low as 50 milliseconds. While AWS Cost Anomaly Detection would take 24 hours to wake up, NETRA flagged the runaway instance instantly. In the inventory table below, notice that every single rate has cryptographic provenance with a SHA-256 price digest cached in S3."*

---

### [1:20 – 1:55] Defensive AI & Non-Bypassable Cedar Policies
- **On-Screen**: Click **"Inspect & Remediate"** into an investigation. Show the verified narrative with the badge `gpt-4o-mini · verified`, supporting CloudWatch evidence chips (CPU 1.8%), and then show the protected resource `i-0protected999999` with policy denial.
- **Voiceover**:
  > *"Clicking inspect launches our investigation agent powered by OpenAI gpt-4o-mini and Amazon Bedrock. But NETRA has a non-negotiable defensive invariant: the AI is strictly confined to root-cause narration. Every single financial figure is pre-computed in Python. Our zero-tolerance validator tests every generated token against the database — 12 out of 12 adversarial prompt injection attacks are blocked with 0% ungrounded numbers. Furthermore, for resources tagged `netra:protected`, our AWS Cedar policy engine evaluates in 1.2ms and unconditionally disables remediation."*

---

### [1:55 – 2:25] Cryptographic Human Gate & Step Functions Execution
- **On-Screen**: Navigate to an approved finding. Click **"Approve & Execute"**. Show Step Functions state machine execution, then switch to the **Audit Ledger** (`/audit`).
- **Voiceover**:
  > *"NETRA guarantees zero autonomous destruction. Remediations require an operator click, which mints an HMAC-SHA256 single-use, 5-minute approval token. AWS Step Functions orchestrates the 5-stage pipeline: Authorize, PolicyCheck, DryRun, create an EBS rollback snapshot, and mutate the resource. In the audit ledger, you see ₹65,392.20 in recovered spend across 5 human-authorized actions — with 7-day snapshot IDs ready for instant 1-click rollback."*

---

### [2:25 – 2:55] Architecture, Verification & Closing
- **On-Screen**: Show terminal running `make verify` (all 6 invariant checks green in 1.23s) and `pytest` (131/131 passing). Flash the architecture diagram showing 14 load-bearing AWS services.
- **Voiceover**:
  > *"Any judge can clone our repo and run `make verify` to mathematically prove price provenance, Cedar policy enforcement, and replay defense in 1.2 seconds. 131 automated unit tests pass in CI. 14 AWS services perform real, load-bearing work — from EventBridge and SQS to DynamoDB and Step Functions — with a total idle run cost under ₹10 a month. AWS tells you what you spent yesterday. NETRA saves your budget before it's gone. Thank you."*
