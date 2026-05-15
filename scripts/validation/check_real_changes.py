#!/usr/bin/env python3
"""
Real Changes Guard - 實質變更 vs 空殼/噪音變更檢測

Enforces: 04 補正版第十九章第 10-11 條（真實落盤原則）

Checks:
A. evidence.json only with no real code/law/validator change → FAIL
B. candidate.diff exists but content is empty/noise/only evidence → FAIL
C. candidate.diff hash/content matches actual git diff
D. No real change detected → FAIL (fail-closed)
E. Evidence-only commits with no substantive changes → FAIL

Exit codes:
- 0: PASS - real changes detected
- 1: FAIL - no real changes
"""

import argparse
import os
import subprocess
import sys
import hashlib
from pathlib import Path


CORE_EXTENSIONS = [".py", ".ps1", ".psm1", ".bat", ".cmd", ".sh", ".yaml", ".yml", ".json", ".xml", ".sql", ".md"]
NOISE_EXTENSIONS = [".log", ".tmp", ".swp", "~", ".bak", ".cache"]
REPORT_ARTIFACT_PATTERNS = ["report.json", "aider.log", "evidence.json", "candidate.diff", "task.txt"]


def run_cmd(cmd: list) -> tuple:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding='utf-8', errors='replace')
        return result.returncode, result.stdout or "", result.stderr or ""
    except Exception as e:
        return -1, "", str(e)


def get_git_diff_files() -> list:
    code, stdout, _ = run_cmd(["git", "diff", "--name-only", "HEAD"])
    if code != 0:
        return []
    return [f.strip() for f in stdout.split("\n") if f.strip()]


def get_git_status_untracked() -> list:
    code, stdout, _ = run_cmd(["git", "status", "--porcelain"])
    if code != 0:
        return []
    untracked = []
    for line in stdout.split("\n"):
        if line.strip().startswith("??"):
            filepath = line.strip()[2:].strip()
            untracked.append(filepath)
    return untracked


def is_real_change(filepath: str) -> bool:
    ext = os.path.splitext(filepath)[1].lower()
    if ext in CORE_EXTENSIONS and not any(p in filepath.lower() for p in REPORT_ARTIFACT_PATTERNS):
        return True
    core_dirs = ["automation/control/", "scripts/", "manifests/", "_governance/law/", ".githooks/"]
    for d in core_dirs:
        if filepath.startswith(d) and not any(p in filepath.lower() for p in REPORT_ARTIFACT_PATTERNS):
            return True
    return False


def is_comment_only_diff(diff_content: str) -> bool:
    code_lines = 0
    for line in diff_content.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("--"):
            continue
        code_lines += 1
    return code_lines == 0


def check_candidate_diff_vs_actual(candidate_diff_path: Path, round_id: str) -> list:
    errors = []
    if not candidate_diff_path.exists():
        errors.append(f"candidate.diff not found: {candidate_diff_path}")
        return errors

    try:
        candidate_content = candidate_diff_path.read_bytes()
        candidate_hash = hashlib.sha256(candidate_content).hexdigest()[:16]
    except Exception as e:
        errors.append(f"cannot read candidate.diff: {e}")
        return errors

    code, git_diff, _ = run_cmd(["git", "diff", "HEAD"])
    if code != 0:
        errors.append("cannot get git diff HEAD")
        return errors

    if not git_diff.strip():
        errors.append("git diff HEAD is empty — no changes to validate")
        return errors

    git_hash = hashlib.sha256(git_diff.encode("utf-8")).hexdigest()[:16]

    if candidate_hash[:8] != git_hash[:8]:
        errors.append(
            f"candidate.diff hash mismatch: candidate={candidate_hash[:8]}, "
            f"actual git diff={git_hash[:8]}"
        )

    if is_comment_only_diff(git_diff):
        errors.append("diff only contains comments — no substantive code change")

    return errors


def check_evidence_only_fail(authorized_changes: list) -> list:
    errors = []
    real_changes = [f for f in authorized_changes if is_real_change(f)]
    evidence_only = [f for f in authorized_changes if "evidence.json" in f or "candidate.diff" in f or "candidates/" in f]

    if len(real_changes) == 0 and len(evidence_only) > 0:
        errors.append(
            "EVIDENCE_ONLY_CHANGE: only evidence/candidate files changed, "
            "no real code/law/validator change"
        )
    return errors


def main():
    parser = argparse.ArgumentParser(description="Real changes guard")
    parser.add_argument("--round-id", help="Round ID for reporting")
    parser.add_argument("--candidate-dir", help="Candidate directory")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    all_errors = []
    diff_files = get_git_diff_files()
    untracked_files = get_git_status_untracked()
    all_changed = list(set(diff_files + untracked_files))

    if not all_changed:
        all_errors.append("NO_CHANGES_DETECTED: no diff, no untracked changes")
        print_result(False, all_errors)
        sys.exit(1)

    all_errors.extend(check_evidence_only_fail(all_changed))

    if args.candidate_dir:
        candidate_path = Path(args.candidate_dir)
        diff_file = candidate_path / "candidate.diff"
        round_id = args.round_id or candidate_path.name
        all_errors.extend(check_candidate_diff_vs_actual(diff_file, round_id))

    real_count = sum(1 for f in all_changed if is_real_change(f))
    if real_count == 0 and not all_errors:
        all_errors.append("NO_REAL_CHANGES: only noise/artifact files changed")

    passed = len(all_errors) == 0
    print_result(passed, all_errors)

    if args.verbose and passed:
        print(f"INFO: {real_count} real change(s) in {len(all_changed)} total file(s)")

    sys.exit(0 if passed else 1)


def print_result(passed: bool, errors: list):
    if passed:
        print("PASS: real changes detected")
    else:
        print("FAIL: no valid real changes")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    main()
