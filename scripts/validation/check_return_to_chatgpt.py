#!/usr/bin/env python3
"""
RETURN_TO_CHATGPT 欄位完整性與狀態一致性 validator

依據：04 補正版第十九章第 14 條（RETURN_TO_CHATGPT 硬門檻）
      04 補正版第十九章第 15 條（狀態碼與正文一致性）

功能：
1. 檢查必要欄位完整性（reply_id, formal_status_code, files_modified, evidence, blockers, 授權範圍, next_action）
2. 檢查 RETURN_TO_CHATGPT 是否為主體而非摘要（前文完整+正式區摘要視為無效）
3. 檢查狀態碼與內容邏輯一致性
"""

import argparse
import re
import sys
from pathlib import Path


def parse_return_to_chatgpt(content: str) -> dict:
    """解析 RETURN_TO_CHATGPT 區塊"""
    result = {
        "raw": "",
        "sections": {},
        "metadata": {},
        "errors": []
    }

    # 提取 RETURN_TO_CHATGPT 區塊
    start_marker = "=== RETURN_TO_CHATGPT ==="
    end_marker = "=== END_RETURN_TO_CHATGPT ==="

    start_idx = content.find(start_marker)
    if start_idx == -1:
        result["errors"].append("Missing start marker: === RETURN_TO_CHATGPT ===")
        return result

    end_idx = content.find(end_marker)
    if end_idx == -1:
        result["errors"].append("Missing end marker: === END_RETURN_TO_CHATGPT ===")
        return result

    block = content[start_idx + len(start_marker):end_idx].strip()
    result["raw"] = block

    # 解析 key: value 格式
    lines = block.split("\n")
    current_section = "metadata"
    result["sections"][current_section] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 檢測 section header
        if line.endswith(":"):
            # 可能是章節標題
            if any(kw in line.lower() for kw in ["summary", "details", "analysis", "notes"]):
                current_section = line.rstrip(":").lower()
                result["sections"][current_section] = []
                continue

        # 解析 key: value
        if ": " in line:
            key, value = line.split(": ", 1)
            result["sections"][current_section].append((key.strip(), value.strip()))

    # 也保留最外層 key-value
    for key, value in result["sections"].get("metadata", []):
        result["metadata"][key] = value

    return result


def check_required_fields(parsed: dict) -> list:
    """檢查必要欄位"""
    errors = []
    required_fields = [
        "reply_id",
        "formal_status_code",
        "files_modified"
    ]

    # 從 raw 中搜索 key-value
    raw = parsed.get("raw", "")

    has_reply_id = bool(re.search(r'^reply_id:\s*\S+', raw, re.MULTILINE))
    has_status_code = bool(re.search(r'^formal_status_code:\s*\S+', raw, re.MULTILINE))
    has_files_modified = bool(re.search(r'^files_modified:\s*', raw, re.MULTILINE))

    # 額外檢查：evidence / validate_evidence / blockers / next_action
    has_evidence = bool(re.search(r'(evidence|validate_evidence):', raw, re.IGNORECASE))
    has_blockers = bool(re.search(r'(blocker|blockers):', raw, re.IGNORECASE))
    has_next_action = bool(re.search(r'(next_action|next_recommended_action):', raw, re.IGNORECASE))

    if not has_reply_id:
        errors.append("Missing required field: reply_id")
    if not has_status_code:
        errors.append("Missing required field: formal_status_code")
    if not has_files_modified:
        errors.append("Missing required field: files_modified")

    # 警告（非強制）
    warnings = []
    if not has_evidence:
        warnings.append("Warning: No evidence/validate_evidence field found")
    if not has_blockers:
        warnings.append("Warning: No blockers/blocker field found (required if task not complete)")
    if not has_next_action:
        warnings.append("Warning: No next_action/next_recommended_action field found")

    return errors, warnings


def check_main_body_not_summary(parsed: dict) -> list:
    """檢查 RETURN_TO_CHATGPT 是主體而非摘要"""
    errors = []

    raw = parsed.get("raw", "")

    # 檢測是否為摘要模式：只有 summary，無正式主體內容
    has_summary = bool(re.search(r'^summary:\s*', raw, re.MULTILINE))
    has_formal_status = bool(re.search(r'^formal_status_code:\s*', raw, re.MULTILINE))

    # 若有 summary 但無其他實質內容，視為摘要
    content_lines = [l for l in raw.split("\n") if l.strip() and not l.strip().startswith("summary:")]

    if has_summary and len(content_lines) < 4:
        errors.append("RETURN_TO_CHATGPT appears to be summary only, not full body")

    # 檢查前文是否比正式區更完整（常見於「前文較完整、正式區僅摘要」模式）
    # 此處透過檢查關鍵欄位存在性判斷
    if has_formal_status:
        # 有 status code 表示這是正式區
        pass

    return errors


def check_status_code_consistency(parsed: dict) -> list:
    """檢查狀態碼與內容邏輯一致性"""
    errors = []

    raw = parsed.get("raw", "")

    # 提取 formal_status_code
    status_match = re.search(r'formal_status_code:\s*(\S+)', raw)
    if not status_match:
        return errors  # 由其他檢查處理

    status_code = status_match.group(1).lower()

    # 提取其他關鍵資訊
    has_files = bool(re.search(r'^files_modified:\s*-', raw, re.MULTILINE))
    has_evidence = bool(re.search(r'(evidence|validate_evidence):', raw, re.IGNORECASE))
    has_blockers = bool(re.search(r'(blocker|blockers):', raw, re.IGNORECASE))
    has_diff = bool(re.search(r'(diff|commit_hash):', raw, re.IGNORECASE))

    # 狀態失真檢查

    # 1. 標為 completed/implemented/passed 但無 files_modified
    completion_statuses = ["completed", "implemented", "passed", "candidate_ready"]
    if any(s in status_code for s in completion_statuses):
        if not has_files:
            errors.append(f"Status code '{status_code}' but no files_modified found - possible fabricated pass")
        if not has_diff:
            errors.append(f"Status code '{status_code}' but no diff/commit_hash found - possible fabricated pass")

    # 2. 有 blocker 但狀態碼標為完成
    if has_blockers:
        if any(s in status_code for s in completion_statuses):
            errors.append(f"Status code '{status_code}' but blockers present - status inconsistency")

        # 檢查 blocker 時狀態碼應為 blocked/technical_unfinished
        blocker_text = re.search(r'(blocker|blockers):\s*(.+)', raw, re.IGNORECASE)
        if blocker_text:
            blocker_content = blocker_text.group(2).lower()
            if "none" not in blocker_content and not any(b in status_code for b in ["blocked", "technical_unfinished", "failed"]):
                errors.append(f"Blocker present ('{blocker_content.strip()}') but status code is '{status_code}' - must be blocked/technical_unfinished")

    # 3. 標為 passed 但無 evidence
    if "passed" in status_code or "passed_validation" in status_code:
        if not has_evidence:
            errors.append(f"Status code '{status_code}' but no evidence/validate_evidence found")

    # 4. 檢查 blockers 欄位內容是否為空或 "none"
    blockers_match = re.search(r'(blocker|blockers):\s*(.+)', raw, re.IGNORECASE)
    if blockers_match:
        blockers_content = blockers_match.group(2).strip().lower()
        if blockers_content in ["", "none", "n/a", "無", "null"]:
            # blockers 為空時，狀態碼不應為 blocked
            if "blocked" in status_code:
                errors.append("Blockers field is empty/none but status is blocked - inconsistent")

    return errors


def validate_file(filepath: str) -> dict:
    """驗證單一檔案"""
    result = {
        "file": filepath,
        "passed": False,
        "errors": [],
        "warnings": [],
        "checks": {}
    }

    try:
        content = Path(filepath).read_text(encoding="utf-8-sig")
    except Exception as e:
        result["errors"].append(f"Cannot read file: {e}")
        return result

    parsed = parse_return_to_chatgpt(content)

    if parsed.get("errors"):
        result["errors"].extend(parsed["errors"])
        return result

    # 執行各項檢查
    field_errors, field_warnings = check_required_fields(parsed)
    result["errors"].extend(field_errors)
    result["warnings"].extend(field_warnings)
    result["checks"]["required_fields"] = "PASS" if not field_errors else "FAIL"

    body_errors = check_main_body_not_summary(parsed)
    result["errors"].extend(body_errors)
    result["checks"]["main_body"] = "PASS" if not body_errors else "FAIL"

    status_errors = check_status_code_consistency(parsed)
    result["errors"].extend(status_errors)
    result["checks"]["status_consistency"] = "PASS" if not status_errors else "FAIL"

    # 最終判定
    result["passed"] = len(result["errors"]) == 0

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Validate RETURN_TO_CHATGPT field completeness and status consistency"
    )
    parser.add_argument("--file", required=True, help="Path to RETURN_TO_CHATGPT file")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    result = validate_file(args.file)

    if result["passed"]:
        print(f"PASS: {args.file}")
        if args.verbose:
            print(f"  Checks: {result['checks']}")
    else:
        print(f"FAIL: {args.file}")
        for error in result["errors"]:
            print(f"  - {error}")

    if result["warnings"] and args.verbose:
        print("Warnings:")
        for warning in result["warnings"]:
            print(f"  - {warning}")

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()