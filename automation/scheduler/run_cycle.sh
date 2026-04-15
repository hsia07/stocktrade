#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-.}"
MANIFEST_PATH="${2:-manifests/current_round.yaml}"

cd "$REPO_ROOT"

echo "[scheduler] fetch latest"
git fetch --all --prune

echo "[scheduler] run validation"
python ./scripts/validation/validate_round.py --manifest "$MANIFEST_PATH"
python ./scripts/validation/check_forbidden_changes.py --manifest "$MANIFEST_PATH"
python ./scripts/validation/check_required_evidence.py --manifest "$MANIFEST_PATH"
python ./scripts/validation/check_commit_message.py --manifest "$MANIFEST_PATH"

echo "[scheduler] done"
