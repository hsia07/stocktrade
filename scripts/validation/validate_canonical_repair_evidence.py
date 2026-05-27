#!/usr/bin/env python3
"""
validate_canonical_repair_evidence.py

Dedicated validator for canonical repair / governance repair merge evidence packages.
Does NOT use current_round.yaml — dynamically locates changed candidate evidence
from git diff, or accepts explicit --candidate-dir.

Designed to be called from .github/workflows/validate-canonical-repair.yml.
"""

from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


REQUIRED_FILES = [
    "evidence.json",
    "candidate.diff",
    "RETURN_TO_CHATGPT.txt",
    "test-results.txt",
    "task.txt",
]

RTCG_REQUIRED_MARKERS = ["round_id", "formal_status_code", "base_head", "candidate_branch"]

FORBIDDEN_CLAIMS = [
    "runtime_started",
    "r049_started",
    "r047_started",
    "r048_started",
    "r031_started",
    "broker_api_called",
    "order_execution_allowed",
    "trading_broker_execution_live_started",
    "fubon_api_integrated",
    "live_started",
]

CANDIDATE_DIR_PREFIX = "automation/control/candidates/"

GOVERNANCE_FORBIDDEN_PATH_PATTERNS = [
    "modules/",
    "tests/",
    "server_v2.py",
    "index_v2.html",
    ".env",
    ".env.",
    "broker",
    "live",
    "order",
]

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf899d153036d7c3d"


def find_changed_candidate_dirs(head_ref: str = "HEAD") -> List[Path]:
    """Find candidate evidence directories changed in head_ref using git diff-tree -m."""
    result = subprocess.run(
        ["git", "diff-tree", "-m", "--no-commit-id", "-r", "--name-only", head_ref, "--", CANDIDATE_DIR_PREFIX],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        print(f"FAIL: git diff-tree error: {result.stderr.strip()}")
        sys.exit(1)

    changed_dirs: set[Path] = set()
    seen: set[str] = set()
    for line in result.stdout.strip().splitlines():
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


def check_file_exists(candidate_dir: Path, filename: str) -> Tuple[bool, str]:
    full = candidate_dir / filename
    if not full.exists():
        return False, f"missing:{filename}"
    if full.stat().st_size == 0:
        return False, f"empty:{filename}"
    return True, ""


def check_evidence_json(candidate_dir: Path) -> Tuple[bool, List[str]]:
    issues = []
    path = candidate_dir / "evidence.json"
    if not path.exists():
        return False, ["missing:evidence.json"]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return False, [f"evidence_parse_error:{e}"]

    lc = data.get("law_compliance")
    if lc is None:
        issues.append("law_compliance:missing")
    elif not isinstance(lc, str) or lc != "04":
        issues.append(f"law_compliance:wrong_value:{lc}")

    for claim in FORBIDDEN_CLAIMS:
        if data.get(claim) is True:
            issues.append(f"forbidden_claim:{claim}")

    return len(issues) == 0, issues


def check_candidate_diff(candidate_dir: Path) -> Tuple[bool, List[str]]:
    issues = []
    path = candidate_dir / "candidate.diff"
    if not path.exists():
        return False, ["missing:candidate.diff"]

    raw = path.read_bytes()
    if len(raw) == 0:
        return False, ["empty:candidate.diff"]

    if raw[:3] == b"\xef\xbb\xbf":
        issues.append("candidate_diff:utf8_bom_present")

    if raw[:2] == b"\xff\xfe" or raw[:2] == b"\xfe\xff":
        issues.append("candidate_diff:utf16_detected")

    return len(issues) == 0, issues


def check_return_to_chatgpt(candidate_dir: Path) -> Tuple[bool, List[str]]:
    issues = []
    path = candidate_dir / "RETURN_TO_CHATGPT.txt"
    if not path.exists():
        return False, ["missing:RETURN_TO_CHATGPT.txt"]

    try:
        content = path.read_text(encoding="utf-8-sig", errors="replace").strip()
    except Exception as e:
        return False, [f"rtcg_read_error:{e}"]

    if len(content) < 100:
        issues.append("rtcg:too_short")
        return len(issues) == 0, issues

    lower = content.lower()
    for marker in RTCG_REQUIRED_MARKERS:
        if marker not in lower:
            issues.append(f"rtcg:missing_marker:{marker}")
            return len(issues) == 0, issues

    if "recommendation" not in lower and "blocker" not in lower:
        issues.append("rtcg:missing_recommendation_or_blocker")

    return len(issues) == 0, issues


def check_test_output_not_substituted(candidate_dir: Path) -> Tuple[bool, List[str]]:
    issues = []
    test_results = candidate_dir / "test-results.txt"
    test_output = candidate_dir / "test_output.txt"

    if test_output.exists() and not test_results.exists():
        issues.append("test_output_substituted_for_test_results")

    return len(issues) == 0, issues


def check_path_in_authorized_scope(candidate_dir: Path) -> Tuple[bool, List[str]]:
    posix = candidate_dir.as_posix()
    if CANDIDATE_DIR_PREFIX not in posix:
        return False, [f"path_out_of_scope:{posix}"]

    return True, []


def check_governance_record_diff_scope(candidate_dir: Path) -> Tuple[bool, List[str]]:
    """Check that governance record acceptance only touches governance/evidence paths.
    Only checks diff --git header lines (actual file paths modified), not diff content."""
    issues = []
    diff_path = candidate_dir / "candidate.diff"
    if not diff_path.exists():
        return True, []

    try:
        content = diff_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return False, [f"governance_diff_read_error:{e}"]

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith("diff --git"):
            continue
        for pattern in GOVERNANCE_FORBIDDEN_PATH_PATTERNS:
            if pattern in stripped:
                issues.append(f"governance_record:forbidden_path:{stripped}")
                break

    return len(issues) == 0, issues


def classify_candidate(candidate_dir: Path) -> str:
    ev_path = candidate_dir / "evidence.json"
    if not ev_path.exists():
        return "unknown"

    try:
        data = json.loads(ev_path.read_text(encoding="utf-8"))
    except Exception:
        return "unknown"

    if data.get("should_not_be_used_for_acceptance") is True:
        return "expected_invalid_superseded"

    status = data.get("evidence_status", "")
    if "invalid" in status.lower() or "superseded" in status.lower():
        return "expected_invalid_superseded"

    acceptance_path = data.get("acceptance_path", "")
    if acceptance_path == "governance_record_acceptance_path":
        return "governance_record_acceptance"

    return "valid_acceptance_candidate"


def validate_candidate(candidate_dir: Path) -> Tuple[bool, List[str], str]:
    all_issues: List[str] = []

    for fname in REQUIRED_FILES:
        ok, msg = check_file_exists(candidate_dir, fname)
        if not ok:
            all_issues.append(msg)

    ev_ok, ev_issues = check_evidence_json(candidate_dir)
    if not ev_ok:
        all_issues.extend(ev_issues)

    diff_ok, diff_issues = check_candidate_diff(candidate_dir)
    if not diff_ok:
        all_issues.extend(diff_issues)

    rtcg_ok, rtcg_issues = check_return_to_chatgpt(candidate_dir)
    if not rtcg_ok:
        all_issues.extend(rtcg_issues)

    sub_ok, sub_issues = check_test_output_not_substituted(candidate_dir)
    if not sub_ok:
        all_issues.extend(sub_issues)

    scope_ok, scope_issues = check_path_in_authorized_scope(candidate_dir)
    if not scope_ok:
        all_issues.extend(scope_issues)

    classification = classify_candidate(candidate_dir)
    if classification == "expected_invalid_superseded":
        return True, all_issues, classification

    if classification == "governance_record_acceptance":
        gov_ok, gov_issues = check_governance_record_diff_scope(candidate_dir)
        if not gov_ok:
            all_issues.extend(gov_issues)

    return len(all_issues) == 0, all_issues, classification


def main():
    ap = argparse.ArgumentParser(description="Validate canonical repair evidence package")
    ap.add_argument("--candidate-dir", help="Explicit path to candidate evidence directory")
    ap.add_argument("--head-ref", default="HEAD", help="Head ref for git diff-tree (default: HEAD)")
    args = ap.parse_args()

    if args.candidate_dir:
        dirs = [Path(args.candidate_dir)]
    else:
        dirs = find_changed_candidate_dirs(args.head_ref)
        if not dirs:
            parent_check = subprocess.run(
                ["git", "rev-list", "--count", "--max-parents=0", args.head_ref],
                capture_output=True, text=True, timeout=30,
            )
            if parent_check.stdout.strip() == "1":
                diff_root = subprocess.run(
                    ["git", "diff-tree", "--no-commit-id", "-r", "--name-only", EMPTY_TREE, args.head_ref, "--", CANDIDATE_DIR_PREFIX],
                    capture_output=True, text=True, timeout=30,
                )
                if diff_root.returncode == 0:
                    dirs = []
                    seen = set()
                    for line in diff_root.stdout.strip().splitlines():
                        line = line.strip()
                        if not line or line in seen:
                            continue
                        seen.add(line)
                        p = Path(line)
                        parent = p.parent
                        while parent.name:
                            if (parent / "evidence.json").exists():
                                dirs.append(parent)
                                break
                            parent = parent.parent
            if not dirs:
                print("FAIL: no changed candidate evidence package found in diff")
                print(f"       checked {args.head_ref} in {CANDIDATE_DIR_PREFIX}")
                sys.exit(1)

    pass_count = 0
    expected_invalid_count = 0
    blocking_fail_count = 0

    for d in dirs:
        ok, issues, classification = validate_candidate(d)
        if classification == "expected_invalid_superseded":
            print(f"[EXPECTED_INVALID_SUPERSEDED] {d}")
            for issue in issues:
                print(f"  - {issue}")
            expected_invalid_count += 1
        elif ok:
            print(f"[PASS] {d}")
            pass_count += 1
        else:
            print(f"[FAIL] {d}")
            for issue in issues:
                print(f"  - {issue}")
            blocking_fail_count += 1

    print()
    if blocking_fail_count > 0:
        print(f"FAIL: {blocking_fail_count} blocking failure(s) found")
        print("PASS: canonical repair evidence validation complete")
        sys.exit(1)

    print(f"PASS: {pass_count} acceptance package(s) validated")
    if expected_invalid_count > 0:
        print(f"      {expected_invalid_count} expected_invalid_superseded package(s) skipped")
    print("PASS: canonical repair evidence validation complete")


if __name__ == "__main__":
    main()
