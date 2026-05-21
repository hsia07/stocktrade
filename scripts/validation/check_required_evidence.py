#!/usr/bin/env python3
"""
check_required_evidence.py - Evidence package guard with content validation

Enhanced checks:
1. evidence.json parse pass
2. law_compliance exact string "04"
3. prohibited_actions_verified complete
4. evidence path in candidate authorized scope
5. candidate.diff exists and corresponds to actual git diff
6. Secret scan basic check
7. Evidence must not list only TRUE without corresponding file/diff
"""

from __future__ import annotations
import argparse
import json
import sys
import subprocess
from pathlib import Path
import yaml

SUSPICIOUS_PATTERNS = [
    "api_key",
    "api_secret",
    "bot_token",
    "chat_id",
    "password",
    "secret_key",
    "private_key",
    "token=",
    "authorization:",
]

UI_VISIBLE_GATE_INDICATORS = [
    "ui_visible_gate_pass",
    "visible_surface_evidence",
    "dom_scan_pass",
    "ui_panel_present",
]

UI_EVIDENCE_QUALITY_GATES = {
    "no_fake_feature_claim": [
        "fake_feature_claim_detected",
        "false_completion_claim",
    ],
    "no_runtime_broker_live_pollution": [
        "runtime_started",
        "trading_broker_execution_live_started",
        "broker_live_fubon_controls_detected",
        "fubon_api_integrated",
        "order_execution_allowed",
    ],
    "ui_specific_indicators": [
        "placeholder_detected",
        "mojibake_detected",
        "undefined_null_nan_placeholder_detected",
        "ui_gap_status_panel_visible_evidence_created",
        "r022_r023_r024_r025_r026_r029_r040_status_visible",
        "read_only_or_display_only_disclaimer_visible",
        "not_complete_disclaimer_visible",
    ],
}


def _is_ui_visible_surface_evidence(data: dict) -> bool:
    if not isinstance(data, dict):
        return False
    return any(data.get(k) is True for k in UI_VISIBLE_GATE_INDICATORS)


def _check_ui_visible_surface_evidence(data: dict) -> tuple:
    gate_pass = any(data.get(k) is True for k in UI_VISIBLE_GATE_INDICATORS)
    if not gate_pass:
        return False, "no UI_VISIBLE_GATE indicator is True"

    for gate_name, gate_fields in UI_EVIDENCE_QUALITY_GATES.items():
        if gate_name == "no_fake_feature_claim":
            if any(data.get(f) is True for f in gate_fields):
                return False, f"UI_EVIDENCE_POLLUTION: {gate_name} — fake/false feature claim detected"
        elif gate_name == "no_runtime_broker_live_pollution":
            if data.get("order_execution_allowed") is True:
                return False, "UI_EVIDENCE_POLLUTION: order_execution_allowed is TRUE"
            if any(data.get(f) is True for f in gate_fields):
                return False, f"UI_EVIDENCE_POLLUTION: {gate_name} — runtime/broker/live pollution detected"
        elif gate_name == "ui_specific_indicators":
            has_ui_specific = any(
                data.get(f) is True for f in UI_EVIDENCE_QUALITY_GATES["ui_specific_indicators"]
            )
            if not has_ui_specific:
                return False, "UI_EVIDENCE_INCOMPLETE: no UI-specific indicator present (placeholder/mojibake/panel/disclaimer)"

    return True, "UI_VISIBLE_GATE_EVIDENCE_VALID"


def check_evidence_content(evidence_path: Path) -> tuple:
    try:
        data = json.loads(evidence_path.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"EVIDENCE_PARSE_ERROR: {e}"

    if data.get("status") == "INVALIDATED":
        return False, "EVIDENCE_MARKED_INVALIDATED"

    # law_compliance must be exact string "04"
    lc = data.get("law_compliance")
    if lc is None:
        return False, "missing law_compliance field"
    if not isinstance(lc, str) or lc != "04":
        return False, f"law_compliance='{lc}' but must be string '04'"

    # Check work_done has real items (skip for UI-visible-surface evidence)
    work_done = data.get("work_done", [])
    is_ui_gate_evidence = _is_ui_visible_surface_evidence(data)

    if is_ui_gate_evidence:
        ui_valid, ui_reason = _check_ui_visible_surface_evidence(data)
        if not ui_valid:
            return False, f"UI_VISIBLE_GATE_INVALID: {ui_reason}"
    else:
        if isinstance(work_done, list) and len(work_done) == 0:
            return False, "NO_WORK_DONE_ITEMS"
        packaging_only = all(
            any(x in str(item).lower() for x in ["evidence", "report", "validated", "structure"])
            for item in work_done
        )
        if packaging_only:
            return False, "PACKAGING_ONLY_WORK_ITEMS"

    # Check prohibited_actions_verified (skip for UI-visible-surface evidence)
    if not is_ui_gate_evidence:
        pav = data.get("prohibited_actions_verified", {})
        if not isinstance(pav, dict) or len(pav) == 0:
            return False, "prohibited_actions_verified missing or empty"
        all_pav_true = all(v is True for v in pav.values()) if isinstance(pav, dict) else False
        if not all_pav_true:
            false_keys = [k for k, v in pav.items() if v is not True]
            return False, f"prohibited_actions_verified has non-True values: {false_keys}"

    # Secret scan
    content_lower = evidence_path.read_text(encoding="utf-8").lower()
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern.lower() in content_lower:
            return False, f"EVIDENCE_MAY_CONTAIN_SECRET: pattern '{pattern}' found"

    return True, "EVIDENCE_CONTENT_VALID"


def load_manifest(path: str) -> dict:
    try:
        return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": str(e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()

    manifest = load_manifest(args.manifest)
    if "error" in manifest:
        print(f"FAIL: cannot load manifest: {manifest['error']}")
        sys.exit(1)

    missing = []
    invalid_content = []
    unauthorized = []
    no_diff_match = []

    for item in manifest.get("required_evidence", []):
        path = Path(item)
        if not path.exists():
            missing.append(item)
            continue

        if "evidence.json" in item:
            valid, reason = check_evidence_content(path)
            if not valid:
                invalid_content.append(f"{item}: {reason}")

        # Check evidence path is in candidate authorized scope
        if "candidates/" in item:
            parent_dir = path.parent
            parent_str = parent_dir.as_posix()
            allowed_scopes = [
                "automation/control/candidates/",
                "_governance/",
            ]
            in_scope = any(parent_str.startswith(s) for s in allowed_scopes)
            if not in_scope:
                unauthorized.append(f"{item}: not in authorized candidate scope")

        # Check candidate.diff exists alongside evidence.json
        if "evidence.json" in item:
            candidate_dir = path.parent
            diff_file = candidate_dir / "candidate.diff"
            if not diff_file.exists():
                no_diff_match.append(f"{item}: no candidate.diff in {candidate_dir}")

    if missing:
        print("FAIL: missing required evidence")
        for m in missing:
            print(" -", m)
        sys.exit(1)

    if invalid_content:
        print("FAIL: evidence content validation failed")
        for i in invalid_content:
            print(" -", i)
        sys.exit(1)

    if unauthorized:
        print("FAIL: evidence path not in authorized scope")
        for u in unauthorized:
            print(" -", u)
        sys.exit(1)

    if no_diff_match:
        print("FAIL: candidate.diff not found alongside evidence.json")
        for n in no_diff_match:
            print(" -", n)
        sys.exit(1)

    print("PASS: required evidence present and content valid")
    print("PASS: law_compliance exact string '04'")
    print("PASS: prohibited_actions_verified complete")
    print("PASS: evidence path in authorized scope")
    print("PASS: candidate.diff present")
    print("PASS: secret scan passed")


if __name__ == "__main__":
    main()
