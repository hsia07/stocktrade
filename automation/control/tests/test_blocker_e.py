"""
BLOCKER_E runtime tests: automated signoff mechanism.
Verifies auto-candidate path requires machine-checkable signoff.
Manual review path and bounded_auto_mode preserved.
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
                      paused=False, automated_signoff=None):
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
    if automated_signoff is not None:
        result["automated_signoff"] = automated_signoff
    return result


def test_auto_candidate_full_signoff():
    """auto_candidate_ready + all signoff conditions pass → auto-candidate path."""
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(
        status="completed",
        formal_status_code="auto_candidate_ready",
        automated_signoff={
            "hash_verified": True,
            "law_compliance_verified": True,
            "evidence_validated": True,
        },
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is True, f"Expected True, got {can_advance}"
    assert gate == "none", f"Expected none, got {gate}"
    assert "auto_candidate_path_clear" in reason
    print("PASS: test_auto_candidate_full_signoff")


def test_auto_candidate_missing_signoff():
    """auto_candidate_ready + missing signoff fields → blocked."""
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(
        status="completed",
        formal_status_code="auto_candidate_ready",
        automated_signoff={
            "hash_verified": True,
        },
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is False, "Missing signoff fields should block"
    assert gate == "signoff_gate", f"Expected signoff_gate, got {gate}"
    assert "signoff_incomplete" in reason
    print("PASS: test_auto_candidate_missing_signoff")


def test_auto_candidate_no_signoff_data():
    """auto_candidate_ready + no automated_signoff dict → blocked."""
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(
        status="completed",
        formal_status_code="auto_candidate_ready",
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is False, "No signoff data should block"
    assert gate == "signoff_gate"
    print("PASS: test_auto_candidate_no_signoff_data")


def test_auto_candidate_partial_signoff():
    """auto_candidate_ready + partial signoff → blocked with all missing listed."""
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(
        status="completed",
        formal_status_code="auto_candidate_ready",
        automated_signoff={
            "hash_verified": False,
            "law_compliance_verified": True,
            "evidence_validated": False,
        },
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is False
    assert gate == "signoff_gate"
    assert "hash_verified" in reason
    assert "evidence_validated" in reason
    print("PASS: test_auto_candidate_partial_signoff")


def test_manual_review_path_preserved():
    """candidate_ready_awaiting_manual_review still blocks via review_gate regardless of signoff."""
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(
        status="completed",
        formal_status_code="candidate_ready_awaiting_manual_review",
        automated_signoff={
            "hash_verified": True,
            "law_compliance_verified": True,
            "evidence_validated": True,
        },
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is False
    assert gate == "review_gate", "manual review path must use review_gate, not signoff_gate"
    print("PASS: test_manual_review_path_preserved")


def test_bounded_auto_mode_merge_gate_blocks():
    """Bounded auto-mode: merge gate still blocks (no signoff bypass for non-auto)."""
    ctrl = AutoAdvanceController(REPO_ROOT)
    result = make_round_result(
        status="completed",
        formal_status_code="completed",
        merge_encountered=True,
        automated_signoff={
            "hash_verified": True,
            "law_compliance_verified": True,
            "evidence_validated": True,
        },
    )
    can_advance, reason, gate = ctrl.can_auto_advance(result)
    assert can_advance is False
    assert gate == "merge_gate", "bounded auto-mode must use merge_gate"
    print("PASS: test_bounded_auto_mode_merge_gate_blocks")


def test_stop_gates_includes_signoff():
    """STOP_GATES must include signoff_gate."""
    ctrl = AutoAdvanceController(REPO_ROOT)
    gates = ctrl.get_stop_gates()
    assert "signoff_gate" in gates
    assert len(gates) == 10  # increased from 9 to 10
    print("PASS: test_stop_gates_includes_signoff")


def test_sigoff_requirements_defined():
    """SIGNOFF_REQUIREMENTS must be defined and non-empty."""
    ctrl = AutoAdvanceController(REPO_ROOT)
    assert hasattr(ctrl, "SIGNOFF_REQUIREMENTS")
    assert len(ctrl.SIGNOFF_REQUIREMENTS) > 0
    for req in ctrl.SIGNOFF_REQUIREMENTS:
        assert isinstance(req, str)
        assert len(req) > 0
    print("PASS: test_sigoff_requirements_defined")


if __name__ == "__main__":
    tests = [
        test_auto_candidate_full_signoff,
        test_auto_candidate_missing_signoff,
        test_auto_candidate_no_signoff_data,
        test_auto_candidate_partial_signoff,
        test_manual_review_path_preserved,
        test_bounded_auto_mode_merge_gate_blocks,
        test_stop_gates_includes_signoff,
        test_sigoff_requirements_defined,
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
