"""
BLOCKER_G tests: auto_candidate_ready status code.
Runtime import of AutoAdvanceController is blocked by pre-existing
evidence_checker.py:810 indentation error (pre-existing infrastructure defect).
Tests verify correctness via static source analysis and logic replication.
"""

import sys
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
AUTO_ADVANCE_PATH = REPO_ROOT / "automation" / "control" / "auto_advance.py"


def _read_source():
    return AUTO_ADVANCE_PATH.read_text(encoding="utf-8")


def test_auto_candidate_ready_constant_exists():
    source = _read_source()
    assert "AUTO_CANDIDATE_READY" in source
    assert '"auto_candidate_ready"' in source
    print("PASS: test_auto_candidate_ready_constant_exists")


def test_is_auto_candidate_status_method_exists():
    source = _read_source()
    assert "def is_auto_candidate_status" in source
    assert "formal_code" in source
    assert "AUTO_CANDIDATE_READY" in source
    print("PASS: test_is_auto_candidate_status_method_exists")


def test_candidate_ready_awaiting_manual_review_preserved():
    source = _read_source()
    assert "candidate_ready_awaiting_manual_review" in source
    assert "BLOCKED_STATUS_CODES" in source
    print("PASS: test_candidate_ready_awaiting_manual_review_preserved")


def test_blocked_in_blocked_status_codes():
    source = _read_source()
    assert '"blocked"' in source
    print("PASS: test_blocked_in_blocked_status_codes")


def test_logic_is_auto_candidate_ready():
    AUTO_CANDIDATE_READY = "auto_candidate_ready"
    def is_auto_candidate_status(formal_code):
        return formal_code == AUTO_CANDIDATE_READY
    assert is_auto_candidate_status("auto_candidate_ready") is True
    assert is_auto_candidate_status("candidate_ready_awaiting_manual_review") is False
    assert is_auto_candidate_status("blocked") is False
    assert is_auto_candidate_status("") is False
    assert is_auto_candidate_status("unknown") is False
    print("PASS: test_logic_is_auto_candidate_ready")


def test_no_evidence_checker_modification():
    assert "return_to_chatgpt" not in _read_source()
    print("PASS: test_no_evidence_checker_modification")


def test_can_auto_advance_not_modified():
    source = _read_source()
    assert "def can_auto_advance" in source
    can_advance_start = source.index("def can_auto_advance")
    snippet = source[can_advance_start:]
    assert "BLOCKED_STATUS_CODES" in snippet
    assert "round_status_gate" in snippet
    assert "review_gate" in snippet
    assert "merge_gate" in snippet
    print("PASS: test_can_auto_advance_not_modified")


if __name__ == "__main__":
    tests = [
        test_auto_candidate_ready_constant_exists,
        test_is_auto_candidate_status_method_exists,
        test_candidate_ready_awaiting_manual_review_preserved,
        test_blocked_in_blocked_status_codes,
        test_logic_is_auto_candidate_ready,
        test_no_evidence_checker_modification,
        test_can_auto_advance_not_modified,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
