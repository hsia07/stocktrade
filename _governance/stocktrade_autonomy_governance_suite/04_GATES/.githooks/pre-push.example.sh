#!/usr/bin/env bash
set -euo pipefail

MANIFEST_PATH="automation/current_round.yaml"

echo "[pre-push] run strict validation"
python scripts/validate_round.py --manifest "$MANIFEST_PATH"
python scripts/check_forbidden_changes.py --manifest "$MANIFEST_PATH"
python scripts/check_required_evidence.py --manifest "$MANIFEST_PATH"
python scripts/check_commit_message.py --manifest "$MANIFEST_PATH"

echo "[pre-push] ok"
