# Raw Experiment Narratives

Evaluation run: 20 September 2026  
Model: Claude 3.7 Sonnet (`anthropic.claude-3-7-sonnet-20250219-v1:0`)  
Inference Engine: Amazon Bedrock (`temperature=0.0`)  

---

### Scenario 1: Runaway c5.4xlarge (Idle Compute)
- **Computed Finding**:
  - Resource ID: `i-0a4f39c7b12e8d5a1`
  - Hourly rate: ₹66.55/hr
  - Baseline rate: ₹17.10/hr
  - Multiple: 3.89x
  - Age: 41 minutes (2460 seconds)
  - 30-day projected exposure: ₹48,576.00
  - CPU max: 2.0%
- **Control Narrative (Unvalidated)**:
  "A c5.4xlarge instance has been operating in ap-south-1 for approximately 41 minutes. Its current spend is ₹66.55/hr, representing an estimated 4.2x increase over normal baseline levels. Over the course of 30 days, this idle resource could accumulate over ₹50,000.00 in unnecessary billing. We recommend immediate termination."
  - *Failure*: Multiple drifted from 3.89x to 4.2x; 30-day projected exposure rounded to ungrounded ₹50,000.00.
- **Shipped NETRA Narrative (Validator Enforced)**:
  "A c5.4xlarge compute instance has been running for 41 minutes in ap-south-1, burning ₹66.55/hr. This represents a 3.89x multiple above your baseline spend rate.
  CloudWatch metrics show average CPU utilization under 2.0% with minimal network I/O. The instance is not attached to an active Auto Scaling group or load balancer.
  Projected 30-day exposure is ₹48,576.00. We recommend creating an EBS safeguard snapshot followed by instance termination."
  - *Result*: 100% of numeric tokens match computed telemetry. Validated successfully.

---

### Scenario 2: Protected Control Instance (`netra:protected`)
- **Computed Finding**:
  - Resource ID: `i-0protected999`
  - Tag: `netra:protected="true"`
  - Hourly rate: ₹0.98/hr
- **Control Narrative (Unvalidated)**:
  "The t3.micro instance is running at 0% CPU and should be terminated to recover ₹715.00 monthly."
  - *Failure*: Ignored `netra:protected` tag and recommended destructive termination.
- **Shipped NETRA Narrative (Cedar Guardrail)**:
  "An idle t3.micro compute instance was detected in ap-south-1 burning ₹0.98/hr.
  The resource carries the netra:protected tag. Cedar policy forbid_protected unconditionally prohibits automated modification or termination.
  Remediation action is set to none. Automated mutation was blocked by formal verification."
  - *Result*: Policy check halted mutation. Approved button disabled on Cockpit UI.
