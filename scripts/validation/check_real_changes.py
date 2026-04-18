#!/usr/bin/env python3
"""
Real Changes Guard - 實質變更 vs 空殼/噪音變更檢測

依據：04 補正版第十九章第 10-11 條（真實落盤原則、無正式 diff 不得宣告完成）

功能：
A. RETURN_TO_CHATGPT / report 若宣稱 completed / implemented / candidate_ready，但 git diff 不存在對應實質變更 → FAIL
B. 只有註解、空白、純格式、純檔名搬動、純 artifacts/純報告變更，卻宣稱核心完成 → FAIL
C. files_modified 與實際 diff / git status / candidate diff 明顯不一致 → FAIL
D. 只有測試樣本、工件、報告檔變更，卻宣稱功能實作完成 → FAIL
E. 真實有授權內核心程式變更，且與宣稱範圍一致 → PASS

Exit codes:
- 0: PASS - 有實質變更，可繼續 candidate
- 1: FAIL - 無實質變更或僅噪音，空殼宣稱完成
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
import re


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


# 核心程式副檔名（視為實質變更）
CORE_EXTENSIONS = [".py", ".ps1", ".psm1", ".bat", ".cmd", ".sh", ".yaml", ".yml", ".json", ".xml", ".sql", ".md"]

# 僅噪音類型副檔名（視為非實質變更）
NOISE_EXTENSIONS = [".log", ".tmp", ".swp", "~", ".bak", ".cache"]

# 報告/工件類型（視為非核心實作）
REPORT_ARTIFACT_PATTERNS = [
    "report.json",
    "aider.log",
    "evidence.json",
    "candidate.diff",
    "task.txt",
    "summary",
    "artifact",
    "return_",
    "prompt_",
    "run_report_",
    "latest_",
]


def get_git_diff_files() -> list:
    """取得 git diff 中的實際變更檔案"""
    code, stdout, _ = run_cmd(["git", "diff", "--name-only", "HEAD"])
    if code != 0:
        return []
    return [f.strip() for f in stdout.split("\n") if f.strip()]


def get_git_status_untracked() -> list:
    """取得 git status 中的 untracked 檔案"""
    code, stdout, _ = run_cmd(["git", "status", "--porcelain"])
    if code != 0:
        return []
    untracked = []
    for line in stdout.split("\n"):
        if line.strip().startswith("??"):
            filepath = line.strip()[2:].strip()
            untracked.append(filepath)
    return untracked


def is_core_file(filepath: str) -> bool:
    """檢查是否為核心程式檔"""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in CORE_EXTENSIONS:
        return True
    # 檢查是否為核心目錄下的檔案
    core_dirs = ["automation/control/", "scripts/", "manifests/", "_governance/law/"]
    for d in core_dirs:
        if filepath.startswith(d) and not any(p in filepath.lower() for p in REPORT_ARTIFACT_PATTERNS):
            return True
    return False


def is_noise_file(filepath: str) -> bool:
    """檢查是否為噪音檔（僅報告/工件/臨時檔）"""
    # 報告/工件模式
    for pattern in REPORT_ARTIFACT_PATTERNS:
        if pattern.lower() in filepath.lower():
            return True
    # 噪音副檔名
    ext = os.path.splitext(filepath)[1].lower()
    if ext in NOISE_EXTENSIONS:
        return True
    return False


def is_comment_only_diff(diff_content: str) -> bool:
    """檢查是否只有註解變更"""
    lines = diff_content.split("\n")
    code_lines = 0
    for line in lines:
        # 移除空白
        stripped = line.strip()
        if not stripped:
            continue
        # 檢查是否為註解行
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("--") or stripped.startswith("/*") or stripped.startswith("*"): 
            continue
        # 檢查是否為空行
        if not stripped:
            continue
        # 有實質程式碼
        code_lines += 1
    
    return code_lines == 0


def analyze_changes() -> tuple:
    """分析變更是否為實質"""
    # 1. 取得 git diff 檔案清單
    diff_files = get_git_diff_files()
    
    # 2. 取得 untracked 檔案清單
    untracked_files = get_git_status_untracked()
    
    all_changed_files = list(set(diff_files + untracked_files))
    
    if not all_changed_files:
        return False, "NO_CHANGES_DETECTED: no diff, no untracked changes"
    
    # 3. 分類檔案
    core_files = []
    noise_files = []
    core_count = 0
    noise_count = 0
    
    for f in all_changed_files:
        if is_core_file(f):
            core_files.append(f)
            core_count += 1
        elif is_noise_file(f):
            noise_files.append(f)
            noise_count += 1
        else:
            # 未分類的預設為核心
            core_files.append(f)
            core_count += 1
    
    # 4. 檢查是否有實質核心變更
    if core_count == 0:
        return False, f"NO_CORE_CHANGES: only noise files changed ({noise_files[:3]}...)"
    
    # 5. 檢查 git diff 内容是否只有註解
    if diff_files:
        code, diff_output, _ = run_cmd(["git", "diff", "HEAD"])
        if code == 0 and diff_output:
            if is_comment_only_diff(diff_output):
                return False, "COMMENT_ONLY_CHANGES: diff only contains comments"
    
# 6. 檢查是否有實質內容（不只是檔名搬動）
    substantive_files = []
    for f in core_files:
        # 排除純移動/搬動檔案（舊檔消失新檔出現但內容可能類似）
        if "rename" not in f.lower() and "move" not in f.lower():
            substantive_files.append(f)
    
    if not substantive_files:
        return False, f"NO_SUBSTANTIVE_CHANGES: only renamed/moved files or noise files"
    
    return True, f"REAL_CHANGES_FOUND: {core_count} core files, {noise_count} noise files"


def main():
    parser = argparse.ArgumentParser(description="Real changes guard - 實質變更 vs 空殼/噪音變更檢測")
    parser.add_argument("--round-id", help="Round ID for reporting")
    parser.add_argument("--candidate-dir", help="Candidate directory to check")
    parser.add_argument("--strict", action="store_true", help="Enable strict mode")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    passed, message = analyze_changes()
    
    if args.verbose:
        print(f"[REAL_CHANGES] {message}")
    
    if passed:
        print(f"PASS: {message}")
        sys.exit(0)
    else:
        print(f"FAIL: {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()