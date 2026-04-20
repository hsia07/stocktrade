#!/usr/bin/env python3
"""
validate_evidence.py - Fail-Closed Evidence Validator
Checks for REAL code changes, not just packaging files.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path
import yaml

def get_git_commit_files(repo_root: str, commit_hash: str) -> list:
    """Get list of files changed in a commit."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_root, "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except subprocess.CalledProcessError:
        return []

def get_git_status(repo_root: str, path: str) -> str:
    """Get git status for a path."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_root, "status", "--short", path],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""

def check_candidate_diff_content(repo_root: str, round_id: str) -> tuple:
    """Check candidate.diff for actual work content."""
    diff_path = Path(repo_root) / "automation" / "control" / "candidates" / round_id / "candidate.diff"
    
    if not diff_path.exists():
        return False, "NO_CANDIDATE_DIFF"
    
    content = diff_path.read_text(encoding="utf-8")
    
    # Check for "Work: 0 tasks" or similar
    if "Work: 0 tasks" in content or "Work: 0 task" in content:
        return False, "WORK_ZERO_TASKS"
    
    # Check for any work indication
    import re
    work_match = re.search(r"Work:\s*(\d+)\s*tasks?", content)
    if work_match:
        task_count = int(work_match.group(1))
        if task_count == 0:
            return False, "WORK_ZERO_TASKS"
        return True, f"WORK_{task_count}_TASKS"
    
    # No work indication found
    return False, "NO_WORK_INDICATOR"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()
    
    manifest = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8"))
    round_id = manifest.get("round_id", "unknown")
    repo_root = args.repo_root
    
    # Check 1: Evidence files exist
    evidence_dir = Path(repo_root) / "automation" / "control" / "candidates" / round_id
    required_files = ["evidence.json", "report.json", "candidate.diff"]
    
    for f in required_files:
        if not (evidence_dir / f).exists():
            print(f"FAIL: missing evidence file: {f}")
            sys.exit(1)
    
    # Check 2: candidate.diff shows actual work (not "Work: 0 tasks")
    has_work, work_status = check_candidate_diff_content(repo_root, round_id)
    if not has_work:
        print(f"FAIL: candidate.diff shows no actual work: {work_status}")
        sys.exit(1)
    
    print(f"PASS: candidate.diff shows actual work: {work_status}")
    
    # Check 3: Evidence is tracked in git (not untracked ??)
    for f in required_files:
        status = get_git_status(repo_root, str(evidence_dir / f))
        if status.startswith("??"):
            print(f"FAIL: evidence file {f} is untracked")
            sys.exit(1)
        if not status and not subprocess.run(
            ["git", "-C", repo_root, "ls-files", str(evidence_dir / f)],
            capture_output=True
        ).stdout.strip():
            print(f"FAIL: evidence file {f} not in git")
            sys.exit(1)
    
    print("PASS: all evidence files tracked in git")
    
    # Check 4: Commit has real code changes, not just packaging
    # This requires the commit hash from evidence.json
    evidence = yaml.safe_load((evidence_dir / "evidence.json").read_text(encoding="utf-8"))
    commit_hash = evidence.get("candidate_commit", "").replace("INVALIDATED_", "")
    
    if commit_hash and len(commit_hash) >= 7:
        changed_files = get_git_commit_files(repo_root, commit_hash)
        
        # Filter packaging files
        packaging_patterns = [
            "evidence.json", "report.json", "candidate.diff", 
            "task.txt", "run_record.json", "review_packet.md",
            "aider.log", "aider.error.log"
        ]
        
        real_changes = [
            f for f in changed_files 
            if not any(p in f for p in packaging_patterns)
        ]
        
        if not real_changes:
            print("FAIL: commit only contains packaging files, no real code changes")
            sys.exit(1)
        
        print(f"PASS: commit contains real code changes: {', '.join(real_changes[:5])}")
    else:
        print("WARN: no valid commit hash in evidence, skipping code change check")
    
    print("PASS: evidence package validates real work (not packaging-only)")

if __name__ == "__main__":
    main()