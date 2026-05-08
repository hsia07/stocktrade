"""BLOCKER_I runtime tests: automated next-round dispatch scaffold."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from automation.control.auto_advance import AutoAdvanceController, ROUND_SEQUENCE


@pytest.fixture()
def controller(tmp_path: Path) -> AutoAdvanceController:
    ctrl = AutoAdvanceController(tmp_path)
    candidates_dir = tmp_path / "automation" / "control" / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    return ctrl


def _round_result(
    round_id: str = "BLOCKER_E",
    status: str = "completed",
    formal_status_code: str = "auto_candidate_ready",
    automated_signoff: dict | None = None,
    is_new: bool = False,
    candidate_exists: bool = False,
    **kwargs: Any,
) -> dict:
    result: dict = {
        "round_id": round_id,
        "status": status,
        "formal_status_code": formal_status_code,
        "automated_signoff": automated_signoff or {
            "hash_verified": True,
            "law_compliance_verified": True,
            "evidence_validated": True,
        },
        "blockers_found": [],
        "evidence_directory": None,
        "is_new_round_dispatch": is_new,
        "candidate_exists": candidate_exists,
    }
    result.update(kwargs)
    return result


class TestDetermineNextRound:
    def test_next_after_blocker_e(self, controller: AutoAdvanceController) -> None:
        assert controller.determine_next_round("BLOCKER_E") == "BLOCKER_I"

    def test_next_after_blocker_i(self, controller: AutoAdvanceController) -> None:
        assert controller.determine_next_round("BLOCKER_I") == "BLOCKER_H"

    def test_next_after_blocker_h(self, controller: AutoAdvanceController) -> None:
        assert controller.determine_next_round("BLOCKER_H") == "BLOCKER_C"

    def test_next_after_blocker_c(self, controller: AutoAdvanceController) -> None:
        assert controller.determine_next_round("BLOCKER_C") == "BLOCKER_D"

    def test_next_after_blocker_d(self, controller: AutoAdvanceController) -> None:
        assert controller.determine_next_round("BLOCKER_D") == "AUTO_ADVANCE_OPERATIONAL"

    def test_next_after_last(self, controller: AutoAdvanceController) -> None:
        assert controller.determine_next_round("AUTO_ADVANCE_OPERATIONAL") is None

    def test_next_unknown_round(self, controller: AutoAdvanceController) -> None:
        assert controller.determine_next_round("NONEXISTENT") is None

    def test_case_insensitive(self, controller: AutoAdvanceController) -> None:
        assert controller.determine_next_round("blocker_e") == "BLOCKER_I"

    def test_sequence_order_preserved(self) -> None:
        assert ROUND_SEQUENCE == [
            "BLOCKER_G",
            "FIX-EVIDENCE-CHECKER-INDENTATION",
            "BLOCKER_F",
            "BLOCKER_E",
            "BLOCKER_I",
            "BLOCKER_H",
            "BLOCKER_C",
            "BLOCKER_D",
            "AUTO_ADVANCE_OPERATIONAL",
        ]


class TestCanDispatchNextRound:
    def test_dispatch_all_signoff_pass(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_E")
        can, reason, detail = controller.can_dispatch_next_round(result)
        assert can is True, f"Expected True, got {can}: {reason}"
        assert detail == "BLOCKER_I"

    def test_dispatch_blocked_by_signoff(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_E", automated_signoff={"hash_verified": False, "law_compliance_verified": False, "evidence_validated": False})
        can, reason, detail = controller.can_dispatch_next_round(result)
        assert can is False
        assert "signoff" in reason or "signoff_gate" in detail

    def test_dispatch_blocked_by_blockers(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_E", blockers_found=["BLOCKER_X"])
        can, reason, detail = controller.can_dispatch_next_round(result)
        assert can is False
        assert "blocker" in reason

    def test_dispatch_blocked_by_no_next_round(self, controller: AutoAdvanceController) -> None:
        result = _round_result("AUTO_ADVANCE_OPERATIONAL")
        can, reason, detail = controller.can_dispatch_next_round(result)
        assert can is False
        assert "no_next_round" in reason

    def test_dispatch_blocked_last_in_sequence(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_D")
        can, reason, detail = controller.can_dispatch_next_round(result)
        assert can is True
        assert detail == "AUTO_ADVANCE_OPERATIONAL"

    def test_dispatch_blocked_unknown_round(self, controller: AutoAdvanceController) -> None:
        result = _round_result("NONEXISTENT")
        can, reason, detail = controller.can_dispatch_next_round(result)
        assert can is False

    def test_dispatch_bounded_auto_mode_preserved(self, controller: AutoAdvanceController) -> None:
        """bounded auto mode: even with full signoff, merge gate still blocks."""
        result = _round_result(
            "BLOCKER_E",
            formal_status_code="completed",
            merge_gate_encountered=True,
        )
        can, reason, detail = controller.can_dispatch_next_round(result)
        assert can is False
        assert "merge_gate" in detail or "merge_gate" in reason

    def test_dispatch_manual_review_preserved(self, controller: AutoAdvanceController) -> None:
        """manual review: even with full signoff, review gate blocks."""
        result = _round_result(
            "BLOCKER_E",
            formal_status_code="candidate_ready_awaiting_manual_review",
        )
        can, reason, detail = controller.can_dispatch_next_round(result)
        assert can is False
        assert "review_gate" in detail or "review_gate" in reason


class TestDispatchNextRound:
    def test_dispatch_creates_scaffold(self, controller: AutoAdvanceController, tmp_path: Path) -> None:
        result = _round_result("BLOCKER_E")
        dispatch = controller.dispatch_next_round(result)
        assert dispatch["dispatch_executed"] is True
        assert dispatch["scaffold_created"] is True
        assert dispatch["next_round_id"] == "BLOCKER_I"
        assert dispatch["merge_executed"] is False
        assert dispatch["push_executed"] is False
        assert dispatch["promote_executed"] is False
        assert dispatch["pr_created"] is False
        scaffold_path = Path(dispatch["scaffold_path"])
        assert scaffold_path.exists()
        assert (scaffold_path / "evidence.json").exists()
        assert (scaffold_path / "task.txt").exists()

    def test_dispatch_evidence_content(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_E")
        dispatch = controller.dispatch_next_round(result)
        evidence_path = Path(dispatch["scaffold_path"]) / "evidence.json"
        ev = json.loads(evidence_path.read_text(encoding="utf-8"))
        assert ev["round_id"] == "BLOCKER_I"
        assert ev["law_compliance"] == "04"
        assert ev["scaffold_only"] is True
        assert ev["merge_blocked"] is True
        assert ev["push_blocked"] is True
        assert ev["promote_blocked"] is True

    def test_dispatch_not_executed_when_blocked(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_E", blockers_found=["BLOCKER_X"])
        dispatch = controller.dispatch_next_round(result)
        assert dispatch["dispatch_executed"] is False
        assert dispatch["scaffold_created"] is False

    def test_dispatch_not_executed_when_no_next_round(self, controller: AutoAdvanceController) -> None:
        result = _round_result("AUTO_ADVANCE_OPERATIONAL")
        dispatch = controller.dispatch_next_round(result)
        assert dispatch["dispatch_executed"] is False

    def test_dispatch_scaffold_path_under_candidates(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_E")
        dispatch = controller.dispatch_next_round(result)
        assert "candidates" in dispatch["scaffold_path"]
        assert "BLOCKER_I" in dispatch["scaffold_path"]

    def test_dispatch_does_not_merge_push_promote(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_E")
        dispatch = controller.dispatch_next_round(result)
        assert dispatch["merge_executed"] is False
        assert dispatch["push_executed"] is False
        assert dispatch["promote_executed"] is False
        assert dispatch["pr_created"] is False
