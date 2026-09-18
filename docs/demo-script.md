# NETRA — 3-Minute Video Demo Beat Sheet

A second-by-second rehearsal and recording guide for the 3-minute hackathon video submission.

---

### [0:00 – 0:20] The Problem: Post-Facto Billing is Broken
- **Visual**: AWS Billing / Cost Explorer screen showing "Last updated 24 hours ago", alongside an empty AWS account budget alert.
- **Voiceover**:
  > *"Every developer has experienced the panic of an unexpected AWS bill. The fundamental problem is that AWS Cost Explorer lags by up to 24 hours. If an unoptimized PyTorch script or runaway instance is left running on Friday night, AWS will only tell you on Saturday afternoon — after your hackathon credits or monthly budget are completely wiped out."*

---

### [0:20 – 0:40] NETRA Dashboard at Rest: Live Spend Velocity
- **Visual**: Switch to NETRA Overview cockpit (`http://localhost:3000`). Point out the live burn hero (`₹23.04/hr`), the monospace font discipline, and the pulsing collector status.
- **Voiceover**:
  > *"This is NETRA — Near-real-time Expenditure Tracking & Remediation Agent. NETRA does not wait for yesterday's bill. It interrogates active infrastructure every 60 seconds and prices every single compute, storage, and networking resource deterministically against hashed AWS Price List documents. This needle shows what we are burning right now in rupees per hour."*

---

### [0:40 – 1:10] The Runaway: Launching `c5.4xlarge` on Camera
- **Visual**: Split screen or quick cut to AWS Console (ap-south-1). Launch a `c5.4xlarge` (16 vCPU, 32 GiB RAM, ₹66.55/hr) or run `make demo-seed`.
- **Voiceover**:
  > *"Watch what happens during an actual runaway incident. We launch a heavy c5.4xlarge compute node in Mumbai (ap-south-1) for a model test. Notice the time: 10:41 AM."*

---

### [1:10 – 1:40] The Needle Moves & Autonomous Investigation
- **Visual**: NETRA dashboard counts up from ₹23.04/hr to ₹89.59/hr. The multiple badge lights up `3.9× baseline`. A critical Finding Card fades into the right rail. Click "Inspect & Remediate".
- **Voiceover**:
  > *"Within 42 seconds, NETRA's collector catches the step change. The spend velocity jumps 3.9× above the rolling median baseline. The Strands Agent investigator is immediately dispatched. But here is NETRA's core principle: the model never decides or calculates anything. The arithmetic is 100% deterministic. The agent simply gathers CloudWatch telemetry and narrates what was already proven."*

---

### [1:40 – 2:05] The Safety Gate & Single-Click Remediation
- **Visual**: Investigation page showing 3-paragraph verified narrative, CloudWatch evidence chips (CPU 1.8%), execution trace mint bars, and the dry-run command. Click **Approve & execute**.
- **Voiceover**:
  > *"Before anything touches infrastructure, NETRA presents an exact dry-run plan. No hallucinated figures — our zero-tolerance validator verified every single number against the database. We click 'Approve & execute'. Step Functions executes the 5-stage pipeline: Authorize, DryRun, create a rollback snapshot, terminate the instance, and record an immutable audit entry."*
- **Visual**: Finding resolves, dashboard spend drops back down to baseline, and Prevented Spend counter ticks up by ₹48,576.

---

### [2:05 – 2:25] Provable Execution: `make verify` in Terminal
- **Visual**: Switch to terminal. Run `make verify`. 6 green checkmarks print in under 2 seconds.
- **Voiceover**:
  > *"Don't just take our word for it. In our repository, any judge can run one command: `make verify`. In less than two seconds, it mathematically proves SHA-256 price provenance, 100% byte-identical rules determinism, zero hallucinated numbers, and policy enforcement."*

---

### [2:25 – 2:45] Architecture & Native AWS Stack
- **Visual**: Full-screen architecture diagram showing EventBridge, SAM Lambdas, DynamoDB, Strands SDK, Bedrock Claude 3.7 Sonnet, and Step Functions.
- **Voiceover**:
  > *"NETRA is built entirely native to AWS: serverless Python Lambdas deployed via AWS SAM in ap-south-1, four DynamoDB tables with on-demand capacity and TTLs, Amazon EventBridge for event routing, AWS Step Functions for fault-tolerant remediation, and Claude 3.7 Sonnet on Amazon Bedrock running with temperature zero."*

---

### [2:45 – 3:00] Policy Denials & Closing Statement
- **Visual**: Navigate to Audit Ledger (`/audit`). Show append-only log with recovery snapshot IDs and a policy denial on a `netra:protected` database instance.
- **Voiceover**:
  > *"Every action is preserved in an append-only audit ledger with 7-day rollback snapshot tags. If an instance carries `netra:protected`, our policy gate denies execution unconditionally. AWS tells you what you spent yesterday. NETRA tells you what you are burning right now — and saves your budget before it is gone. Thank you."*
