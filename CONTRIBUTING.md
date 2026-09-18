# Contributing to NETRA

Thank you for contributing to NETRA! This project is submitted to the WeMakeDevs × AWS First Commit 2026 Hackathon (Ship It Track).

---

## Code of Conduct

All contributors and community members are expected to uphold respectful, inclusive, and professional communication at all times.

---

## Development Principles

1. **The Model Never Decides Anything**:
   - Arithmetic, baselines, and findings must ALWAYS remain 100% deterministic.
   - LLMs only narrate and explain findings in plain English; they never decide severity, exposure, or whether a resource is idle.
2. **Cryptographic Provenance**:
   - Every price must trace back to a canonical JSON SHA-256 hash from the AWS Price List API.
3. **Monospace Typography**:
   - All numbers, currency figures, resource IDs, and timestamps must use `IBM Plex Mono`.
4. **Reproducibility First**:
   - `make verify` must execute in under 2 seconds and pass all checks before submitting any pull request.

---

## Local Setup & Testing

```bash
# 1. Clone the repository
git clone https://github.com/your-username/netra.git
cd netra

# 2. Setup backend & frontend dependencies
make setup

# 3. Run complete test suite (56 tests)
make test

# 4. Run instant judge-facing verification
make verify
```
