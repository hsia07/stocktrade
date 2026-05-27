#!/usr/bin/env python3
"""
detect_candidate_packages.py

Detects changed candidate evidence packages between two git refs.
Uses git diff-tree -m for robust merge commit support.
Outputs space-separated paths to stdout, or 'NONE' if no changes found.
"""

from __future__ import annotations
import subprocess
import sys
from pathlib import Path

CANDIDATE_DIR_PREFIX = "automation/control/candidates/"

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf899d153036d7c3d"


def find_changed_candidate_dirs(head_ref: str = "HEAD") -> list[Path]:
    changed_dirs: set[Path] = set()

    diff_result = subprocess.run(
        ["git", "diff-tree", "-m", "--no-commit-id", "-r", "--name-only", head_ref, "--", CANDIDATE_DIR_PREFIX],
        capture_output=True, text=True, timeout=30,
    )
    if diff_result.returncode != 0:
        print(f"FAIL: git diff-tree error: {diff_result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    seen = set()
    for line in diff_result.stdout.strip().splitlines():
        line = line.strip()
        if not line or line in seen:
            continue
        seen.add(line)
        p = Path(line)
        parent = p.parent
        while parent.name:
            if (parent / "evidence.json").exists():
                changed_dirs.add(parent)
                break
            parent = parent.parent

    return sorted(changed_dirs)


def find_changed_candidate_dirs_root(head_ref: str = "HEAD") -> list[Path]:
    changed_dirs: set[Path] = set()
    diff_result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "-r", "--name-only", EMPTY_TREE, head_ref, "--", CANDIDATE_DIR_PREFIX],
        capture_output=True, text=True, timeout=30,
    )
    if diff_result.returncode != 0:
        print(f"FAIL: git diff-tree (root) error: {diff_result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

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

    return sorted(changed_dirs)


def main():
    head_ref = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    dirs = find_changed_candidate_dirs(head_ref)
    if not dirs:
        parent_check = subprocess.run(
            ["git", "rev-list", "--count", "--max-parents=0", head_ref],
            capture_output=True, text=True, timeout=30,
        )
        if parent_check.stdout.strip() == "1":
            dirs = find_changed_candidate_dirs_root(head_ref)
    if dirs:
        print(" ".join(d.as_posix() for d in dirs))
    else:
        print("NONE")


if __name__ == "__main__":
    main()
