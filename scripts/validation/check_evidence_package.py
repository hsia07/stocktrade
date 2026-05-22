#!/usr/bin/env python3
"""
check_evidence_package.py

Runs EvidenceChecker.check_completeness on a candidate evidence directory.
Called from .github/workflows/validate-canonical-repair.yml.
Usage: python check_evidence_package.py <candidate_dir>
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from automation.control.evidence_checker import EvidenceChecker


def main():
    if len(sys.argv) < 2:
        print("FAIL: usage: check_evidence_package.py <candidate_dir>")
        sys.exit(1)

    d = sys.argv[1]
    checker = EvidenceChecker(repo_root=Path(".").resolve())
    ok, issues = checker.check_completeness(Path(d))
    if not ok:
        print(f"FAIL: {d} evidence_checker issues: {issues}")
        sys.exit(1)
    else:
        print(f"PASS: {d} evidence_checker")


if __name__ == "__main__":
    main()
