"""
BLOCKER_F runtime tests: STOP_GATES redesign.
Verifies auto-candidate path bypasses manual gates, preserves safety gates.
Bounded auto-mode behavior unchanged.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from automation.control.auto_advance import AutoAdvanceController


def make_round_result(status="completed", formal_status_code="", blockers=None,
                      evidence_dir=None, is_new=False, candidate_exists=False,
                      merge_encountered=False, push_encountered=False,
                      auth_encountered=False, activation_encountered=False,
                      paused=False):
    result = {
        "status": status,
        "formal_status_code": formal_status_code or "unknown",
        "blockers_found": blockers or [],
        "is_new_round_dispatch": is_new,
        "candidate_exists": candidate_exists,
        "merge_gate_encountered": merge_encountered,
        "push_gate_encountered": push_encountered,
        "authorization_gate_encountered": auth_encountered,
        "activation_gate_encountered": activation_encountered,
    }
    if evidence_dir:
        result["evidence_directory"] = str(evidence_dir)
    return result


def test_auto_candidate_all_clear():
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(status="completed", formal_status_code="auto_candidate_ready")
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is True, f"Expected True, got {can_advance}"
    assert gate == "none", f"Expected none, got {gate}"
    assert "auto_candidate_path_clear" in reason
    print("PASS: test_auto_candidate_all_clear")


def test_auto_candidate_bypasses_merge_gate():
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(
        status="completed", formal_status_code="auto_candidate_ready",
        merge_encountered=True,
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is True, "auto_candidate should bypass merge_gate"
    assert gate == "none", f"Should not be blocked by merge_gate, got {gate}"
    print("PASS: test_auto_candidate_bypasses_merge_gate")


def test_auto_candidate_bypasses_push_gate():
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(
        status="completed", formal_status_code="auto_candidate_ready",
        push_encountered=True,
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is True
    assert gate == "none"
    print("PASS: test_auto_candidate_bypasses_push_gate")


def test_auto_candidate_bypasses_authorization_gate():
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(
        status="completed", formal_status_code="auto_candidate_ready",
        auth_encountered=True,
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is True
    assert gate == "none"
    print("PASS: test_auto_candidate_bypasses_authorization_gate")


def test_auto_candidate_bypasses_activation_gate():
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(
        status="completed", formal_status_code="auto_candidate_ready",
        activation_encountered=True,
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is True
    assert gate == "none"
    print("PASS: test_auto_candidate_bypasses_activation_gate")


def test_auto_candidate_still_blocked_by_blockers():
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(
        status="completed", formal_status_code="auto_candidate_ready",
        blockers=["some_blocker"],
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is False
    assert gate == "blocker_gate"
    print("PASS: test_auto_candidate_still_blocked_by_blockers")


def test_auto_candidate_still_blocked_by_evidence():
    ctrl = AutoAdvanceController(REPO_ROOT)
    evidence_path = REPO_ROOT / "automation" / "control" / "candidates" / "BLOCKER-G-AUTO-CANDIDATE-READY"
    assert evidence_path.exists(), "BLOCKER_G evidence dir must exist for this test"
    result = make_round_result(
        status="completed", formal_status_code="auto_candidate_ready",
        evidence_dir=evidence_path,
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is False, "auto_candidate should be blocked by incomplete evidence"
    assert gate == "evidence_gate", f"Expected evidence_gate, got {gate}"
    print("PASS: test_auto_candidate_still_blocked_by_evidence")


def test_auto_candidate_still_blocked_by_pause():
    ctrl = AutoAdvanceController(REPO_ROOT)
    ctrl.pause_manager.set_pause(reason="test pause for BLOCKER_F")
    try:
        result = make_round_result(
            status="completed", formal_status_code="auto_candidate_ready",
        )
        can_advance, reason, gate = ctrl.can_auto_advance(result)
        assert can_advance is False, "auto_candidate should be blocked by pause"
        assert gate == "pause_gate", f"Expected pause_gate, got {gate}"
    finally:
        ctrl.pause_manager.clear_pause()
    print("PASS: test_auto_candidate_still_blocked_by_pause")


def test_candidate_ready_awaiting_manual_review_still_blocked():
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(
        status="completed", formal_status_code="candidate_ready_awaiting_manual_review",
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is False
    assert gate == "review_gate"
    print("PASS: test_candidate_ready_awaiting_manual_review_still_blocked")


def test_blocked_status_still_blocked():
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(status="completed", formal_status_code="blocked")
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is False
    assert gate == "review_gate"
    print("PASS: test_blocked_status_still_blocked")


def test_bounded_auto_mode_merge_gate_blocks():
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(
        status="completed", formal_status_code="completed",
        merge_encountered=True,
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is False
    assert gate == "merge_gate"
    print("PASS: test_bounded_auto_mode_merge_gate_blocks")


def test_bounded_auto_mode_push_gate_blocks():
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(
        status="completed", formal_status_code="completed",
        push_encountered=True,
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is False
    assert gate == "push_gate"
    print("PASS: test_bounded_auto_mode_push_gate_blocks")


def test_bounded_auto_mode_auth_gate_blocks():
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(
        status="completed", formal_status_code="completed",
        auth_encountered=True,
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is False
    assert gate == "authorization_gate"
    print("PASS: test_bounded_auto_mode_auth_gate_blocks")


def test_round_status_gate_still_blocks():
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(status="in_progress", formal_status_code="auto_candidate_ready")
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is False
    assert gate == "round_status_gate"
    print("PASS: test_round_status_gate_still_blocks")


def test_new_round_dispatch_unchanged():
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(is_new=True, candidate_exists=False)
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is True
    assert gate == "construction_bootstrap_gate"
    print("PASS: test_new_round_dispatch_unchanged")


if __name__ == "__main__":
    tests = [
        test_auto_candidate_all_clear,
        test_auto_candidate_bypasses_merge_gate,
        test_auto_candidate_bypasses_push_gate,
        test_auto_candidate_bypasses_authorization_gate,
        test_auto_candidate_bypasses_activation_gate,
        test_auto_candidate_still_blocked_by_blockers,
        test_auto_candidate_still_blocked_by_evidence,
        test_auto_candidate_still_blocked_by_pause,
        test_candidate_ready_awaiting_manual_review_still_blocked,
        test_blocked_status_still_blocked,
        test_bounded_auto_mode_merge_gate_blocks,
        test_bounded_auto_mode_push_gate_blocks,
        test_bounded_auto_mode_auth_gate_blocks,
        test_round_status_gate_still_blocks,
        test_new_round_dispatch_unchanged,
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
