#!/usr/bin/env python3
"""
RETURN_TO_CHATGPT field completeness, status consistency, and RTC quality validator.

Enforces: 04 補正版第十九章第 14-15 條

Checks:
1. Required fields: round_id, task_type, status, formal_status_code,
   files_modified, recommended_next_action, final_recommendation
2. law_compliance if present must be string "04", not numeric 04
3. Rejects stale RTC (timestamp > 7 days old)
4. Rejects synthetic RTC (contains synthetic generation markers)
5. Rejects malformed RTC (missing required fields, unparseable)
6. Supports embedded RETURN_TO_CHATGPT format (no === markers required)
7. Formal status code membership check (configurable allowed set)
8. RTC must be full body, not summary-only
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta


ALLOWED_FORMAL_STATUS_CODES = [
    "COMPLETED",
    "PASS",
    "FAIL",
    "BLOCKED",
    "CANDIDATE_READY_AWAITING_MANUAL_REVIEW",
    "MANUAL_REVIEW_PASS",
    "MANUAL_REVIEW_BLOCKED",
    "MANUAL_REVIEW_FAILED",
    "LOCAL_NO_FF_MERGE_COMPLETED",
    "LOCAL_NO_FF_MERGE_BLOCKED",
    "REMOTE_PUSH_COMPLETED",
    "REMOTE_PUSH_BLOCKED",
    "POST_PUSH_RECONCILIATION_PASS",
    "POST_PUSH_RECONCILIATION_BLOCKED",
    "REMOTE_PUSH_NOT_COMPLETED_REQUIRES_REVIEW",
    "CANDIDATE_STALE_NO_LONGER_CURRENT",
    "FRESH_RETURN_TO_CHATGPT_RUNTIME_SNAPSHOT_WRITTEN",
]

STALENESS_DAYS = 7
SYNTHETIC_MARKERS = ["[SYNTHETIC]", "synthetically generated", "auto-generated rtc", "[AUTO-GENERATED]"]

REQUIRED_FIELDS = [
    "round_id",
    "task_type",
    "status",
    "formal_status_code",
    "files_modified",
    "recommended_next_action",
    "final_recommendation",
]

EMBEDDED_PATTERN = re.compile(
    r'(?:^|\n)(round_id:\s*\S+)'
    r'(?:\n[^\n]*)*?'
    r'\nfinal_recommendation:\s*\S+',
    re.DOTALL
)


def find_rtc_content(content: str) -> str:
    start_marker = "=== RETURN_TO_CHATGPT ==="
    end_marker = "=== END_RETURN_TO_CHATGPT ==="
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    if start_idx != -1 and end_idx != -1:
        return content[start_idx + len(start_marker):end_idx].strip()

    embedded_match = EMBEDDED_PATTERN.search(content)
    if embedded_match:
        block_start = content.find("round_id:", embedded_match.start())
        if block_start == -1:
            return content
        block_end = content.find("\nfinal_recommendation:", block_start)
        if block_end == -1:
            return content
        block_end = content.index("\n", block_end + 1)
        if block_end < block_start:
            return content[block_start:]
        next_field = content.find("\n", block_end)
        if next_field != -1:
            block_end = next_field
        return content[block_start:block_end]
    return content


def check_required_fields(raw: str) -> list:
    errors = []
    for field in REQUIRED_FIELDS:
        pattern = rf'^{field}:\s*\S+'
        if not re.search(pattern, raw, re.MULTILINE):
            errors.append(f"Missing required field: {field}")
    return errors


def check_law_compliance(raw: str) -> list:
    errors = []
    match = re.search(r'^law_compliance:\s*(.+)$', raw, re.MULTILINE)
    if match:
        value = match.group(1).strip()
        if value == "04":
            return errors
        if value == "04" or value == "4":
            errors.append(f"law_compliance is '{value}' but must be string '04'")
        else:
            errors.append(f"law_compliance is '{value}' but must be '04' when present")
    return errors


def check_staleness(raw: str) -> list:
    errors = []
    ts_match = re.search(r'^timestamp:\s*([\d\-T:Z+]+)', raw, re.MULTILINE)
    if ts_match:
        try:
            ts = ts_match.group(1)
            if "+" not in ts and not ts.endswith("Z"):
                errors.append(
                    f"RTC timestamp must be timezone-aware: '{ts}' has no timezone "
                    f"(expected suffix +00:00 or Z)"
                )
                return errors
            parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - parsed
            if age > timedelta(days=STALENESS_DAYS):
                errors.append(
                    f"RTC is stale: timestamp={ts}, age={age.days} days "
                    f"(max {STALENESS_DAYS} days)"
                )
        except (ValueError, TypeError):
            errors.append("RTC malformed: cannot parse timestamp")
    return errors


def check_synthetic(raw: str) -> list:
    errors = []
    for marker in SYNTHETIC_MARKERS:
        if marker.lower() in raw.lower():
            errors.append(f"RTC rejected synthetic: contains marker '{marker}'")
            break
    return errors


def check_malformed(raw: str) -> list:
    errors = []
    lines = [l for l in raw.split("\n") if l.strip()]
    if len(lines) < 5:
        errors.append("RTC malformed: too few lines for valid RTC block")
    return errors


def check_status_code_membership(raw: str) -> list:
    errors = []
    status_match = re.search(r'^formal_status_code:\s*(\S+)', raw, re.MULTILINE)
    if status_match:
        code = status_match.group(1)
        if code not in ALLOWED_FORMAL_STATUS_CODES:
            if not code.startswith("CANDIDATE_") and not code.startswith("LOCAL_") and not code.startswith("REMOTE_") and not code.startswith("POST_"):
                errors.append(f"formal_status_code '{code}' is not in allowed set")
    return errors


def check_body_not_summary(raw: str) -> list:
    errors = []
    has_summary = bool(re.search(r'^summary:', raw, re.MULTILINE))
    has_formal = bool(re.search(r'^formal_status_code:', raw, re.MULTILINE))
    content_lines = [l for l in raw.split("\n") if l.strip() and not l.strip().startswith("summary:")]
    if has_summary and len(content_lines) < 4:
        errors.append("RTC appears to be summary-only, not full body")
    if has_formal and not re.search(r'^files_modified:', raw, re.MULTILINE):
        errors.append("RTC has formal_status_code but no files_modified — may be summary-only")
    return errors


def validate_file(filepath: str) -> dict:
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

    raw = find_rtc_content(content)
    if not raw or len(raw.strip()) < 10:
        result["errors"].append("No RETURN_TO_CHATGPT content found (embedded or === marker format)")
        return result

    field_errors = check_required_fields(raw)
    result["errors"].extend(field_errors)
    result["checks"]["required_fields"] = "PASS" if not field_errors else "FAIL"

    lc_errors = check_law_compliance(raw)
    result["errors"].extend(lc_errors)
    result["checks"]["law_compliance"] = "PASS" if not lc_errors else "FAIL"

    stale_errors = check_staleness(raw)
    result["errors"].extend(stale_errors)
    result["checks"]["staleness"] = "PASS" if not stale_errors else "FAIL"

    syn_errors = check_synthetic(raw)
    result["errors"].extend(syn_errors)
    result["checks"]["synthetic"] = "PASS" if not syn_errors else "FAIL"

    mal_errors = check_malformed(raw)
    result["errors"].extend(mal_errors)
    result["checks"]["malformed"] = "PASS" if not mal_errors else "FAIL"

    sc_errors = check_status_code_membership(raw)
    result["errors"].extend(sc_errors)
    result["checks"]["status_code_membership"] = "PASS" if not sc_errors else "FAIL"

    body_errors = check_body_not_summary(raw)
    result["errors"].extend(body_errors)
    result["checks"]["main_body"] = "PASS" if not body_errors else "FAIL"

    result["passed"] = len(result["errors"]) == 0
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Validate RETURN_TO_CHATGPT field completeness, law compliance, and quality"
    )
    parser.add_argument("--file", required=True, help="Path to RTC file")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    result = validate_file(args.file)

    if result["passed"]:
        print(f"PASS: {args.file}")
        if args.verbose:
            for check, status in result["checks"].items():
                print(f"  [{status}] {check}")
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
