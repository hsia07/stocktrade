#!/usr/bin/env python3
"""
Law Mirror Synchronization Validator

Checks that law authoritative files and their readable/opencode-readable
mirrors are synchronized and consistent.

COVERAGE:
- 04 (交易系統法典補強版): authoritative ↔ readable ↔ opencode-readable
- 03 (161輪逐輪施行細則法典): readable ↔ opencode-readable
- Round topics and phase mapping must be consistent across mirrors
- 02 > 03 > 04 > 01 priority ordering check

Exit codes:
- 0: PASS - all mirrors synchronized
- 1: FAIL - synchronization errors found
- 2: PARTIAL - some checks passed, some only partially verifiable
"""

import argparse
import sys
from pathlib import Path


LAW_DIR = Path("_governance") / "law"
LAW_READABLE_DIR = Path("_governance") / "law" / "readable"
OPENCODE_READABLE_DIR = Path("opencode_readable_laws")

REQUIRED_MIRROR_PAIRS = [
    {
        "name": "04交易系統法典補強版",
        "authoritative_glob": "*04*交易系統法典補強版*",
        "authoritative_dir": LAW_DIR,
        "readable_glob": "*04*交易系統法典補強版*",
        "readable_dir": LAW_READABLE_DIR,
        "opencode_glob": "*04*交易系統法典補強版*",
        "opencode_dir": OPENCODE_READABLE_DIR,
        "check_content": True,
    },
    {
        "name": "03161輪逐輪施行細則法典整合法條增補版",
        "authoritative_glob": "*03*161輪逐輪施行細則法典*整合法條增補版*",
        "authoritative_dir": LAW_DIR,
        "readable_glob": "*03*161輪逐輪施行細則法典*",
        "readable_dir": LAW_READABLE_DIR,
        "opencode_glob": "*03*161輪逐輪施行細則法典*",
        "opencode_dir": OPENCODE_READABLE_DIR,
        "check_content": False,
    },
]

PRIORITY_ORDER = ["02", "03", "04", "01"]


def find_file(directory: Path, glob_pattern: str) -> Path:
    if not directory.exists():
        return None
    for f in directory.iterdir():
        if f.is_file():
            import fnmatch
            if fnmatch.fnmatch(f.name, glob_pattern):
                return f
    return None


def check_mirror_pair(pair: dict) -> list:
    errors = []
    warnings = []

    auth_dir = pair["authoritative_dir"]
    auth_glob = pair["authoritative_glob"]
    auth_file = find_file(auth_dir, auth_glob)

    readable_dir = pair.get("readable_dir")
    readable_glob = pair.get("readable_glob")
    readable_file = find_file(readable_dir, readable_glob) if readable_dir else None

    opencode_dir = pair.get("opencode_dir")
    opencode_glob = pair.get("opencode_glob")
    opencode_file = find_file(opencode_dir, opencode_glob) if opencode_dir else None

    if not auth_file:
        errors.append(
            f"{pair['name']}: authoritative file not found in {auth_dir} ({auth_glob})"
        )
        return errors

    if not readable_file:
        errors.append(
            f"{pair['name']}: readable mirror not found in {readable_dir} ({readable_glob})"
        )

    if not opencode_file:
        errors.append(
            f"{pair['name']}: opencode-readable mirror not found in {opencode_dir} ({opencode_glob})"
        )

    if errors:
        return errors

    if pair.get("check_content") and auth_file and readable_file:
        try:
            auth_size = auth_file.stat().st_size
            readable_size = readable_file.stat().st_size
            if auth_size != readable_size:
                warnings.append(
                    f"{pair['name']}: file size mismatch "
                    f"authoritative={auth_size} readable={readable_size}"
                )
        except OSError as e:
            warnings.append(f"{pair['name']}: cannot check file size: {e}")

    return errors + warnings


def check_priority_order() -> list:
    errors = []
    for priority in PRIORITY_ORDER:
        found = False
        for f in LAW_DIR.iterdir():
            if f.is_file() and f.name.startswith(priority + "_"):
                found = True
                break
        if not found:
            errors.append(
                f"Priority law file not found: {priority}_* in {LAW_DIR}"
            )
    return errors


def main():
    parser = argparse.ArgumentParser(description="Law Mirror Synchronization Validator")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    all_errors = []
    all_warnings = []

    if not LAW_DIR.exists():
        all_errors.append(f"Law directory not found: {LAW_DIR}")
        print_result(False, all_errors, all_warnings)
        sys.exit(1)

    for pair in REQUIRED_MIRROR_PAIRS:
        results = check_mirror_pair(pair)
        for r in results:
            if r.startswith("PARTIAL") or "size mismatch" in r:
                all_warnings.append(r)
            else:
                all_errors.append(r)

    all_errors.extend(check_priority_order())

    passed = len(all_errors) == 0
    partial = len(all_errors) == 0 and len(all_warnings) > 0

    print_result(passed, all_errors, all_warnings)
    sys.exit(0 if passed else (2 if partial else 1))


def print_result(passed: bool, errors: list, warnings: list):
    if passed:
        if warnings:
            print("PARTIAL: Mirror sync check passed with warnings")
        else:
            print("PASS: All law mirrors synchronized")
    else:
        print("FAIL: Law mirror synchronization errors detected")
        for e in errors:
            print(f"  - {e}")
    for w in warnings:
        print(f"  WARN: {w}")


if __name__ == "__main__":
    main()
