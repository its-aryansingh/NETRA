#!/usr/bin/env bash
# NETRA Break Script — Launches runaway compute to prove sub-10-second detection
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHONPATH="${SCRIPT_DIR}/../backend" python3 "${SCRIPT_DIR}/break.py" "$@"
