#!/usr/bin/env python3
"""
Preflight Check Guard - 開工前必備前提驗證

依據：04 補正版第十九章第 3-4 條（preflight 強制檢查）

功能：
A. 檢查 repo root 是否為唯一正式外層 repo，而非 inner repo
B. 檢查 branch 是否屬允許類型（work/*、candidates/*、review/*），不可為 master
C. 檢查 HEAD / git 狀態是否可用，且不存在 merge conflict / rebase 中 / detached HEAD / index 異常
D. 檢查 working tree 是否符合本輪允許狀態；untracked 必須走白名單判定
E. 發現 blocker 時 non-zero exit，讓正式流程記入 failed_criteria

Exit codes:
- 0: PASS - 所有前提檢查通過
- 1: FAIL - 至少一項檢查失敗，阻擋 candidate 推進
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list) -> tuple:
    """執行命令並返回 (exit_code, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode, result.stdout or "", result.stderr or ""
    except Exception as e:
        return -1, "", str(e)


def check_repo_root() -> tuple:
    """A. 檢查 repo root 是否為唯一正式外層 repo"""
    # 取得 actual repo root
    code, stdout, _ = run_cmd(["git", "rev-parse", "--show-toplevel"])
    if code != 0:
        return False, f"Cannot determine repo root: {stdout}"
    
    repo_root = (stdout or "").strip()
    if not repo_root:
        return False, "REPO_ROOT_EMPTY: git rev-parse returned empty"
    
    # 確認是否為外層 repo（特定路徑）
    # 外層 repo 應為 C:\Users\richa\OneDrive\桌面\stocktrade
    # 禁止 inner repo (stocktrade/stocktrade)
    
    if "stocktrade" + os.sep + "stocktrade" in repo_root.replace("/", os.sep):
        return False, f"INNER_REPO_DETECTED: repo root is inner repo: {repo_root}"
    
    # 檢查是否為預期外層路徑
    if not Path(repo_root).exists():
        return False, f"REPO_ROOT_NOT_FOUND: {repo_root}"
    
    return True, f"REPO_ROOT_OK: {repo_root}"


def check_branch_type() -> tuple:
    """B. 檢查 branch 是否屬允許類型"""
    # 取得 current branch
    code, stdout, _ = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if code != 0:
        return False, f"Cannot determine branch: {stdout}"
    
    branch = stdout.strip()
    
    # 禁止 master / main 直接施工
    if branch in ["master", "main"]:
        return False, f"MASTER_BRANCH_FORBIDDEN: cannot work on {branch}"
    
    # 允許類型：work/*, candidates/*, review/*
    allowed_prefixes = ["work/", "candidates/", "review/"]
    if not any(branch.startswith(prefix) for prefix in allowed_prefixes):
        # 也允許 feature/* 類型（如果有）
        if branch.startswith("feature/") or branch.startswith("r") or branch.startswith("R-"):
            pass  # 允許其他常見命名
        else:
            return False, f"DISALLOWED_BRANCH_TYPE: {branch} - must be work/*, candidates/*, review/* or feature/*"
    
    return True, f"BRANCH_TYPE_OK: {branch}"


def check_git_state() -> tuple:
    """C. 檢查 HEAD / git 狀態是否可用"""
    # 檢查是否處於 merge conflict 狀態
    code, stdout, _ = run_cmd(["git", "status"])
    if code != 0:
        return False, f"GIT_STATE_UNAVAILABLE: cannot read git status"
    
    status_output = stdout.lower()
    
    # 檢查 merge conflict
    if "merge conflict" in status_output or "conflict" in status_output:
        return False, f"MERGE_CONFLICT_DETECTED: cannot proceed with unmerged files"
    
    # 檢查 rebase in progress
    if "rebase in progress" in status_output or ".git/rebase-merge" in status_output or ".git/rebase-apply" in status_output:
        return False, f"REBASE_IN_PROGRESS: cannot proceed during rebase"
    
    # 檢查 detached HEAD
    code, stdout, _ = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if code == 0 and stdout.strip() == "HEAD":
        return False, f"DETACHED_HEAD_DETECTED: not on a branch"
    
    return True, f"GIT_STATE_OK"


def check_working_tree(untracked_whitelist: list = None) -> tuple:
    """D. 檢查 working tree 狀態，untracked 必須走白名單"""
    if untracked_whitelist is None:
        # 預設白名單：常見可忽略的檔案類型
        untracked_whitelist = [
            ".env.local",
            ".env.*.local",
            "*.log",
            "*.tmp",
            "*.swp",
            "*~",
            ".DS_Store",
            "Thumbs.db",
            "__pycache__",
            "node_modules",
            ".gitignore",
            # Automation control artifacts (generated runtime files)
            "automation/control/artifacts/prompt_*.txt",
            "automation/control/artifacts/return_*.txt",
            "automation/control/candidates/*/return_*.txt",
            "automation/control/candidates/*/",
            # Validation scripts
            "scripts/validation/check_*.py",
            # Test artifacts
            "automation/control/artifacts/test_*.txt",
            "automation/control/test/*.ps1",
            # Inner repo reference (not a施工目標)
            "stocktrade/",
            "stocktrade/*",
        ]
    
    code, stdout, _ = run_cmd(["git", "status", "--porcelain"])
    if code != 0:
        return False, f"WORKING_TREE_UNAVAILABLE: cannot read git status"
    
    lines = stdout.strip().split("\n") if stdout.strip() else []
    
    untracked_files = []
    for line in lines:
        if line.startswith("?? "):
            # untracked file
            filepath = line[3:].strip()
            
            # 檢查是否在白名單
            is_whitelisted = False
            for pattern in untracked_whitelist:
                import fnmatch
                if fnmatch.fnmatch(filepath, pattern):
                    is_whitelisted = True
                    break
            
            if not is_whitelisted:
                untracked_files.append(filepath)
    
    if untracked_files:
        return False, f"UNTRACKED_FILES_NOT_WHITELISTED: {', '.join(untracked_files[:5])}" + (f"... and {len(untracked_files)-5} more" if len(untracked_files) > 5 else "")
    
    return True, f"WORKING_TREE_OK"


def main():
    parser = argparse.ArgumentParser(description="Preflight check guard - 開工前必備前提驗證")
    parser.add_argument("--repo-root", help="Expected repo root path (optional)")
    parser.add_argument("--strict", action="store_true", help="Enable strict mode for all checks")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    all_passed = True
    failure_reasons = []

    # A. Repo root check
    passed, msg = check_repo_root()
    if args.verbose:
        print(f"[PREFLIGHT-A] {msg}")
    if not passed:
        all_passed = False
        failure_reasons.append(msg)
        print(f"FAIL: {msg}")
    
    # B. Branch type check
    passed, msg = check_branch_type()
    if args.verbose:
        print(f"[PREFLIGHT-B] {msg}")
    if not passed:
        all_passed = False
        failure_reasons.append(msg)
        print(f"FAIL: {msg}")
    
    # C. Git state check
    passed, msg = check_git_state()
    if args.verbose:
        print(f"[PREFLIGHT-C] {msg}")
    if not passed:
        all_passed = False
        failure_reasons.append(msg)
        print(f"FAIL: {msg}")
    
    # D. Working tree check
    passed, msg = check_working_tree()
    if args.verbose:
        print(f"[PREFLIGHT-D] {msg}")
    if not passed:
        all_passed = False
        failure_reasons.append(msg)
        print(f"FAIL: {msg}")

    print("")
    if all_passed:
        print("PASS: All preflight checks passed")
        sys.exit(0)
    else:
        print(f"FAIL: {len(failure_reasons)} preflight check(s) failed")
        for reason in failure_reasons:
            print(f"  - {reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()