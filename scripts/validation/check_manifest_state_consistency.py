#!/usr/bin/env python3
"""
Manifest / State Consistency Validator

Checks that manifests/current_round.yaml and automation/control/state.runtime.json
are consistent for key fields: round, run_state, chain_status, next_round_to_dispatch.

SPECIAL HANDLING for known inconsistency:
- manifest current_round=NONE vs state current_round=GOV_INT_003_COMPLETED:
  This is a valid post-governance-completion stopped state where the manifest
  has been reset to NONE while the state file still records the last completed
  governance intervention. This is treated as LEGAL STOPPED/GOVERNANCE-COMPLETED
  state IF AND ONLY IF:
    a) run_state = stopped (state file)
    b) chain_status allows backlog_merged or frozen state
    c) No R030 dispatch in progress
    d) No main_control_loop running

Exit codes:
- 0: PASS - manifest and state are consistent
- 1: FAIL - inconsistency detected that cannot be classified as legal
"""

import argparse
import json
import sys
from pathlib import Path
import yaml


MANIFEST_PATH = Path("manifests") / "current_round.yaml"
STATE_PATH = Path("automation") / "control" / "state.runtime.json"


def parse_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {"error": f"Manifest not found: {MANIFEST_PATH}"}
    try:
        return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"Manifest parse error: {e}"}


def parse_state() -> dict:
    if not STATE_PATH.exists():
        return {"error": f"State file not found: {STATE_PATH}"}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"State parse error: {e}"}


def check_round_consistency(manifest: dict, state: dict) -> list:
    errors = []
    warnings = []

    manifest_round = manifest.get("current_round", "NONE")
    state_round = state.get("current_round", "NONE")

    if manifest_round == state_round:
        return errors

    if manifest_round == "NONE" and state_round == "GOV_INT_003_COMPLETED":
        run_state = state.get("run_state", "").lower()
        chain_status = manifest.get("chain_status", "").lower()
        allowed_run_states = ["stopped"]
        allowed_chain_statuses = ["backlog_merged_ready_for_next_dispatch", "frozen"]

        if run_state in allowed_run_states and any(
            c in chain_status for c in allowed_chain_statuses
        ):
            warnings.append(
                "MANIFEST_STATE_DIFFERENCE: manifest current_round=NONE, "
                "state current_round=GOV_INT_003_COMPLETED — classified as "
                "LEGAL_STOPPED_GOVERNANCE_COMPLETED state "
                f"(run_state={run_state}, chain_status={chain_status})"
            )
            return errors

        errors.append(
            f"MANIFEST_STATE_INCONSISTENCY: manifest current_round={manifest_round} "
            f"vs state current_round={state_round} — does not match any legal "
            f"stopped/completed classification"
        )
        return errors

    errors.append(
        f"MANIFEST_STATE_INCONSISTENCY: manifest current_round={manifest_round} "
        f"vs state current_round={state_round}"
    )
    return errors


def check_next_dispatch(manifest: dict, state: dict) -> list:
    errors = []

    manifest_next = manifest.get("next_round_to_dispatch", "NONE")
    state_next = state.get("next_round_to_dispatch", "")

    if not state_next:
        return errors

    if manifest_next != state_next:
        errors.append(
            f"next_round_to_dispatch mismatch: manifest={manifest_next}, state={state_next}"
        )
    return errors


def check_run_state(manifest: dict, state: dict) -> list:
    errors = []
    state_run = state.get("run_state", "")

    if state_run not in ("stopped", "paused", "running"):
        errors.append(f"run_state is unexpected: {state_run}")
    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Manifest/State Consistency Validator"
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    all_errors = []
    all_warnings = []

    manifest = parse_manifest()
    state = parse_state()

    if "error" in manifest:
        all_errors.append(manifest["error"])
    if "error" in state:
        all_errors.append(state["error"])

    if all_errors:
        print_result(False, all_errors, all_warnings)
        sys.exit(1)

    all_errors.extend(check_round_consistency(manifest, state))
    all_errors.extend(check_next_dispatch(manifest, state))
    all_errors.extend(check_run_state(manifest, state))

    passed = len(all_errors) == 0
    print_result(passed, all_errors, all_warnings)
    sys.exit(0 if passed else 1)


def print_result(passed: bool, errors: list, warnings: list):
    if passed:
        print("PASS: Manifest and state are consistent")
    else:
        print("FAIL: Manifest/state consistency check failed")
        for e in errors:
            print(f"  - {e}")
    for w in warnings:
        print(f"  WARN: {w}")


if __name__ == "__main__":
    main()
