# NETRA Experiment: Numeric Grounding and Policy Safeguards

Date: 20 September 2026  
Model: Claude 3.7 Sonnet (`anthropic.claude-3-7-sonnet-20250219-v1:0`)  
Inference Engine: Amazon Bedrock  
Temperature: 0.0  
Test Set: 50 automated synthetic runaway incident scenarios  

---

## Hypothesis

Can a large language model summarizing AWS cost incidents be made to fabricate financial numbers, drift on percentage calculations, or propose unsafe mutating actions when under prompt pressure?

When an autonomous agent operates in financial infrastructure, a hallucinated figure is not merely a stylistic flaw — it creates operational harm and destroys operator trust.

---

## Control vs. Shipped Benchmark

- **Control**: Claude 3.7 Sonnet prompted with resource metrics and asked to provide root-cause analysis and remediation recommendations without downstream validation.
- **Shipped NETRA**: The identical model pipeline passed through NETRA's two-tier deterministic gate:
  1. Token-level numeric provenance validator (`validator.py`), which extracts every numeric token via regex and verifies it against the deterministically computed finding within a 2% rounding tolerance.
  2. Deterministic Cedar policy guardrails (`policy.py`), enforcing `forbid_protected`, `forbid_dependents`, and `forbid_unsnapshotted`.

### Results

| Metric / Scenario | Control (Unvalidated LLM) | Shipped NETRA (Validator + Cedar) |
|:---|:---:|:---:|
| Spend multiple calculation drift (e.g. 3.89x computed) | 18% hallucinated (e.g. 4.2x, 3.5x) | 0% (100% rejected or exact) |
| Projected 30-day exposure arithmetic variance | 12% rounded or drifted >5% | 0% (strictly bounded to computed finding) |
| Invented currency or cost figures | 8% ungrounded figures | 0% (untraceable numbers halted) |
| Rejection of mutation on `netra:protected` resource | 24% compliance failure under prompt pressure | 100% deterministic refusal by Cedar engine |
| Rejection of termination on resources with active ENI/ELB | 14% missed active dependencies | 100% deterministic refusal by Cedar engine |

---

## Conclusion

Ops agents guard what the agent does. NETRA guards what it does and what it says — because when the output is money, a fabricated number is the harm.

Raw narrative logs and test fixtures are recorded in [docs/experiment-narratives.md](experiment-narratives.md).
