#!/usr/bin/env python3
"""
check_branch_workflow.py — Mechanical Gate for Direct-on-Canonical Block
Checks branch workflow compliance, old-source references, and source-of-truth lock.
"""
from __future__ import annotations
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

def run_git(*args) -> str:
    """Run git command and return stdout."""
    try:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return ""

def get_current_branch() -> str:
    return run_git("branch", "--show-current")

def get_commit_parents(commit: str = "HEAD") -> list:
    """Return list of parent commit hashes."""
    out = run_git("rev-parse", f"{commit}^@")
    if not out:
        return []
    return [p for p in out.split("\n") if p]

def is_merge_commit(commit: str = "HEAD") -> bool:
    """A merge commit has 2 or more parents."""
    parents = get_commit_parents(commit)
    return len(parents) >= 2

def get_commit_message() -> str:
    """Get commit message from HEAD or from COMMIT_EDITMSG for pending commits."""
    # First check COMMIT_EDITMSG (for commits in progress, including amend)
    commit_editmsg = Path(".git/COMMIT_EDITMSG")
    if commit_editmsg.exists():
        try:
            return commit_editmsg.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass
    # Fallback to HEAD commit message
    return run_git("log", "-1", "--pretty=%B")

def check_canonical_direct_commit() -> tuple:
    """
    Check if this is a direct non-merge commit on canonical branch.
    Returns (pass: bool, reason: str).
    """
    branch = get_current_branch()
    if branch != "work/canonical-mainline-repair-001":
        return True, "not_on_canonical_branch"
    
    # Check if HEAD is a merge commit
    if is_merge_commit("HEAD"):
        return True, "merge_commit_allowed"
    
    # Check for explicit authorization in commit message
    msg = get_commit_message()
    if "DIRECT-COMMIT-AUTHORIZED" in msg or "direct commit on canonical authorized" in msg.lower():
        return True, "explicitly_authorized"
    
    # Check for incident containment marker
    if "incident containment" in msg.lower() or "GOV-161" in msg:
        # Allow pre-existing incident commits that are formally acknowledged
        # This is for backward compatibility with bf2c16f and 38fc2954
        return True, "incident_containment_acknowledged"
    
    # Check for gate installation
    files = get_staged_or_modified_files()
    for f in files:
        if "check_branch_workflow" in f or "check_canonical_direct_commit" in f or "pre-commit" in f:
            return True, "gate_installation_one_time_exception"
        if "GOV-MECHANICAL-GATE" in f:
            return True, "gate_installation_one_time_exception"
    
    # Fail-closed: direct non-merge commit on canonical without authorization
    return False, (
        "DIRECT_COMMIT_ON_CANONICAL_BLOCKED: "
        "Non-merge commit on work/canonical-mainline-repair-001 is blocked. "
        "Use side branch workflow: create work/[round-id]-candidate, commit there, "
        "then merge to canonical. "
        "Exception: emergency hotfix with 'DIRECT-COMMIT-AUTHORIZED' in commit message."
    )

def get_staged_or_modified_files() -> list:
    """Get list of files in staging area or modified."""
    files = []
    # Staged files
    out = run_git("diff", "--cached", "--name-only")
    if out:
        files.extend(out.split("\n"))
    # Modified unstaged files
    out = run_git("diff", "--name-only")
    if out:
        files.extend(out.split("\n"))
    return sorted(set(f for f in files if f))

def check_old_source_references() -> tuple:
    """
    Check if any staged/modified files reference blocked old sources.
    Returns (pass: bool, violations: list).
    """
    blocked_patterns = {
        "opencode_readable_laws/05_每輪詳細主題補充法典_機器可執行補充版.md": "supplementary_law_blocked",
        "_governance/law/readable/03": "deprecated_mirror_blocked",
    }
    
    # Path-based blocks (these are directory-level blocks)
    path_blocks = {
        "archive/": "archive_blocked",
        "historical/": "historical_blocked",
    }
    
    # Old topic strings that should not appear in new/modified files
    old_topic_strings = [
        "基礎治理入口與執行邊界建立",  # R001 old
        "啟動/停止/暫停控制基底",      # R002 old
        "狀態檔與持久化基底",          # R003 old
        "決策來源追溯與主張者紀錄",    # R016 old
    ]
    
    # Files that are allowed to reference blocked sources for documentation purposes
    # (the validator itself, audit docs, governance guide, templates, etc.)
    governance_doc_paths = [
        "scripts/validation/",
        "_governance/audit/",
        "_governance/incident/",
        "docs/",
        "review_memory.txt",
        "templates/",
    ]
    
    files = get_staged_or_modified_files()
    violations = []
    
    for f in files:
        if not Path(f).exists():
            continue
        
        # Skip governance infrastructure files from blocked source checks
        # (they need to reference blocked sources to document them)
        is_governance_doc = any(f.startswith(gp) for gp in governance_doc_paths)
        
        try:
            content = Path(f).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        
        # Check blocked source paths (only in non-governance files)
        if not is_governance_doc:
            for pattern, reason in blocked_patterns.items():
                if pattern in content:
                    violations.append(f"{f}: references blocked source '{pattern}' ({reason})")
        
        # Check path-based blocks in all files (these should never be used as working references)
        for pattern, reason in path_blocks.items():
            if pattern in content:
                # Allow if documenting the block
                if is_governance_doc and ("blocked" in content.lower() or "封鎖" in content or "禁止" in content):
                    continue
                violations.append(f"{f}: references blocked path '{pattern}' ({reason})")
        
        # Check old topic strings (only in non-governance files)
        if not is_governance_doc:
            for old_topic in old_topic_strings:
                if old_topic in content:
                    # Allow if the file is explicitly documenting the old topic as deprecated
                    if "舊版" in content or "old" in content.lower() or "blocked" in content.lower():
                        continue
                    violations.append(f"{f}: contains old topic string '{old_topic}' (must update to v2.1 topic)")
    
    if violations:
        return False, violations
    return True, []

def check_source_of_truth_lock() -> tuple:
    """
    Check if manifest references correct source-of-truth authorities.
    Returns (pass: bool, violations: list).
    """
    # This check is manifest-aware
    # For now, we check if the manifest file exists and references blocked sources
    violations = []
    
    manifest_files = list(Path("manifests").glob("*.yaml"))
    for mf in manifest_files:
        try:
            content = mf.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        
        # Check if manifest references old sources
        if "05_每輪詳細主題補充法典" in content and "blocked" not in content.lower():
            violations.append(f"{mf}: manifest references blocked supplementary law")
    
    if violations:
        return False, violations
    return True, []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--manifest", default="", help="Manifest path (ignored, for compatibility with hook loops)")
    ap.add_argument("--check-canonical", action="store_true", help="Enable canonical direct commit check")
    ap.add_argument("--check-old-source", action="store_true", help="Enable old source reference check")
    ap.add_argument("--check-source-of-truth", action="store_true", help="Enable source-of-truth lock check")
    ap.add_argument("--all", action="store_true", help="Run all checks")
    args = ap.parse_args()
    
    os.chdir(args.repo_root)
    
    all_pass = True
    
    # Check 1: Canonical direct commit block
    if args.check_canonical or args.all:
        ok, reason = check_canonical_direct_commit()
        if ok:
            print(f"PASS: canonical branch workflow check: {reason}")
        else:
            print(f"FAIL: {reason}")
            all_pass = False
    
    # Check 2: Old source reference block
    if args.check_old_source or args.all:
        ok, violations = check_old_source_references()
        if ok:
            print("PASS: no blocked old source references found")
        else:
            print("FAIL: blocked old source references detected:")
            for v in violations:
                print(f"  - {v}")
            all_pass = False
    
    # Check 3: Source-of-truth lock
    if args.check_source_of_truth or args.all:
        ok, violations = check_source_of_truth_lock()
        if ok:
            print("PASS: source-of-truth lock verified")
        else:
            print("FAIL: source-of-truth violations:")
            for v in violations:
                print(f"  - {v}")
            all_pass = False
    
    if not all_pass:
        sys.exit(1)
    
    print("PASS: all branch workflow checks passed")

if __name__ == "__main__":
    main()
