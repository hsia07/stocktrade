#!/usr/bin/env python3
from __future__ import annotations
import argparse, subprocess, sys, re
from pathlib import Path
import yaml

def get_last_commit_message() -> str:
    try:
        return subprocess.check_output(["git", "log", "-1", "--pretty=%B"], text=True).strip()
    except Exception:
        return ""

def is_governance_round(manifest_round_id: str) -> bool:
    return manifest_round_id.startswith("GOV-")

def extract_governance_id_from_message(msg: str) -> tuple[str | None, bool]:
    direct_match = re.search(r'^(GOV-[A-Z0-9_-]+):', msg, re.MULTILINE)
    if direct_match:
        return direct_match.group(1), True
    merge_match = re.search(r'^MERGE:\s+(GOV-[A-Z0-9_-]+)', msg, re.MULTILINE)
    if merge_match:
        gov_id = merge_match.group(1)
        if re.fullmatch(r'GOV-[A-Z0-9_-]+', gov_id):
            return gov_id, False
    return None, False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()

    manifest = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8"))
    manifest_round_id = manifest.get("round_id", "")
    msg = get_last_commit_message()

    if not msg:
        print("PASS: no commit message to check")
        return

    if is_governance_round(manifest_round_id):
        governance_id, is_direct = extract_governance_id_from_message(msg)
        if governance_id is None:
            print(f"FAIL: governance commit message must include GOV- identifier")
            sys.exit(1)
        if is_direct:
            if governance_id != manifest_round_id:
                print(f"FAIL: governance commit message GOV-ID '{governance_id}' does not match manifest '{manifest_round_id}'")
                sys.exit(1)
        print(f"PASS: governance round-id check ok ({governance_id})")
        return

    if manifest_round_id and manifest_round_id not in msg:
        print(f"FAIL: last commit message must include round id: {manifest_round_id}")
        sys.exit(1)
    print("PASS: commit message round-id check ok")

if __name__ == "__main__":
    main()
