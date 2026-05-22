#!/usr/bin/env python3
"""
detect_candidate_packages.py

Detects changed candidate evidence packages between two git refs.
Outputs space-separated paths to stdout, or 'NONE' if no changes found.
"""

from __future__ import annotations
import subprocess
import sys
from pathlib import Path

CANDIDATE_DIR_PREFIX = "automation/control/candidates/"


def find_changed_candidate_dirs(base_ref: str = "HEAD~1", head_ref: str = "HEAD") -> list[Path]:
    changed_dirs: set[Path] = set()

    diff_result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}..{head_ref}", "--", CANDIDATE_DIR_PREFIX],
        capture_output=True, text=True, timeout=30,
    )
    if diff_result.returncode == 0:
        for line in diff_result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            p = Path(line)
            parent = p.parent
            while parent.name:
                if (parent / "evidence.json").exists():
                    changed_dirs.add(parent)
                    break
                parent = parent.parent

    merge_adds_result = subprocess.run(
        ["git", "log", "--first-parent", "-m", "--name-only", "--pretty=format:", head_ref, "--", CANDIDATE_DIR_PREFIX],
        capture_output=True, text=True, timeout=30,
    )
    if merge_adds_result.returncode == 0:
        for line in merge_adds_result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            p = Path(line)
            parent = p.parent
            while parent.name:
                if (parent / "evidence.json").exists():
                    changed_dirs.add(parent)
                    break
                parent = parent.parent

    return sorted(changed_dirs)


def main():
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1"
    head_ref = sys.argv[2] if len(sys.argv) > 2 else "HEAD"
    dirs = find_changed_candidate_dirs(base_ref, head_ref)
    if dirs:
        print(" ".join(d.as_posix() for d in dirs))
    else:
        print("NONE")


if __name__ == "__main__":
    main()
