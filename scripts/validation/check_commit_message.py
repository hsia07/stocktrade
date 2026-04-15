#!/usr/bin/env python3
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
import yaml

def get_last_commit_message() -> str:
    try:
        return subprocess.check_output(["git", "log", "-1", "--pretty=%B"], text=True).strip()
    except Exception:
        return ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()

    manifest = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8"))
    round_id = manifest.get("round_id", "")
    msg = get_last_commit_message()
    if msg and round_id and round_id not in msg:
        print(f"FAIL: last commit message must include round id: {round_id}")
        sys.exit(1)
    print("PASS: commit message round-id check ok")

if __name__ == "__main__":
    main()
