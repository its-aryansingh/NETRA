# Security Policy

## 1. Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

---

## 2. Reporting a Vulnerability

Security is paramount in financial infrastructure automation. If you discover a potential vulnerability or authorization bypass within NETRA:

1. **Do NOT open a public issue.**
2. Email details directly to `security@netra.internal` or contact the core maintainers.
3. Include detailed reproduction steps, environment details, and relevant code traces.
4. Vulnerability disclosures will be acknowledged within 24 hours with a mitigation timeline.

---

## 3. Autonomous Remediation Safeguards

NETRA incorporates multi-tier architectural security controls to prevent unintended infrastructure mutation:
- **Two-Point Evaluation**: Policy gates evaluate both during UI proposal generation and immediately inside the Step Functions executor.
- **DryRun Verification**: Every EC2 mutation validates authorization via `DryRun=True` prior to execution.
- **Rollback Safeguard**: Root volumes are snapshotted and tagged with `netra:rollback-for=<fid>` prior to any instance termination.
- **Protected Resource Defense**: Any resource carrying the `netra:protected` tag is strictly immune from automated actions.
- **Immutable Audit**: All actions and approvals append to an immutable DynamoDB audit ledger.
