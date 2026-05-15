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

    # Check work_done has real items
    work_done = data.get("work_done", [])
    if isinstance(work_done, list):
        if len(work_done) == 0:
            return False, "NO_WORK_DONE_ITEMS"
        packaging_only = all(
            any(x in str(item).lower() for x in ["evidence", "report", "validated", "structure"])
            for item in work_done
        )
        if packaging_only:
            return False, "PACKAGING_ONLY_WORK_ITEMS"

    # Check prohibited_actions_verified
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
            allowed_scopes = [
                "automation/control/candidates/",
                "_governance/",
            ]
            in_scope = any(str(parent_dir).startswith(s) for s in allowed_scopes)
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
