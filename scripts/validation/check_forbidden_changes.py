#!/usr/bin/env python3
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
import yaml

def git_changed_files():
    # staged + unstaged for local gating
    cmds = [
        ["git", "diff", "--name-only"],
        ["git", "diff", "--cached", "--name-only"],
    ]
    files = set()
    for cmd in cmds:
        try:
            out = subprocess.check_output(cmd, text=True).strip()
            if out:
                files.update([line.strip() for line in out.splitlines() if line.strip()])
        except Exception:
            pass
    return sorted(files)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()

    manifest = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8"))
    forbidden = manifest.get("forbidden_paths", [])
    changed = git_changed_files()

    hits = []
    for f in changed:
        for fp in forbidden:
            if f == fp or f.startswith(fp.rstrip("/") + "/"):
                hits.append(f)

    if hits:
        print("FAIL: forbidden path modified")
        for h in hits:
            print(" -", h)
        sys.exit(1)

    print("PASS: no forbidden path modified")

if __name__ == "__main__":
    main()
