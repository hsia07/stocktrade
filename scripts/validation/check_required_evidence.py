#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from pathlib import Path
import yaml

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()

    manifest = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8"))
    missing = []
    for item in manifest.get("required_evidence", []):
        if not Path(item).exists():
            missing.append(item)

    if missing:
        print("FAIL: missing required evidence")
        for m in missing:
            print(" -", m)
        sys.exit(1)

    print("PASS: required evidence present")

if __name__ == "__main__":
    main()
