"""BLOCKER_H runtime tests: Telegram/API auto-advance handler."""
from __future__ import annotations

from pathlib import Path

import pytest

from automation.control.auto_advance import AutoAdvanceController
from automation.control.auto_advance_handler import handle_auto_advance_trigger


@pytest.fixture()
def controller(tmp_path: Path) -> AutoAdvanceController:
    ctrl = AutoAdvanceController(tmp_path)
    candidates_dir = tmp_path / "automation" / "control" / "candidates"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    return ctrl


def _round_result(
    round_id: str = "BLOCKER_I",
    status: str = "completed",
    formal_status_code: str = "auto_candidate_ready",
    automated_signoff: dict | None = None,
    **kwargs: object,
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
        "is_new_round_dispatch": False,
        "candidate_exists": False,
    }
    result.update(kwargs)
    return result


class TestHandlerAcceptsTrigger:
    def test_handler_full_pass(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_I")
        resp = handle_auto_advance_trigger(result, controller=controller)
        assert resp["handled"] is True
        assert resp["trigger_accepted"] is True
        assert resp["dispatch_executed"] is True
        assert resp["scaffold_created"] is True
        assert resp["next_round_id"] == "BLOCKER_H"
        assert resp["merge_executed"] is False
        assert resp["push_executed"] is False
        assert resp["promote_executed"] is False
        assert resp["pr_created"] is False

    def test_handler_blocked_by_signoff(self, controller: AutoAdvanceController) -> None:
        result = _round_result(
            "BLOCKER_I",
            automated_signoff={
                "hash_verified": False,
                "law_compliance_verified": False,
                "evidence_validated": False,
            },
        )
        resp = handle_auto_advance_trigger(result, controller=controller)
        assert resp["handled"] is True
        assert resp["trigger_accepted"] is False
        assert resp["dispatch_executed"] is False
        assert resp["merge_executed"] is False
        assert resp["push_executed"] is False

    def test_handler_blocked_by_blockers(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_I", blockers_found=["BLOCKER_X"])
        resp = handle_auto_advance_trigger(result, controller=controller)
        assert resp["handled"] is True
        assert resp["trigger_accepted"] is False

    def test_handler_blocked_by_no_next_round(self, controller: AutoAdvanceController) -> None:
        result = _round_result("AUTO_ADVANCE_OPERATIONAL")
        resp = handle_auto_advance_trigger(result, controller=controller)
        assert resp["handled"] is True
        assert resp["trigger_accepted"] is False

    def test_handler_blocked_by_unknown_round(self, controller: AutoAdvanceController) -> None:
        result = _round_result("NONEXISTENT")
        resp = handle_auto_advance_trigger(result, controller=controller)
        assert resp["handled"] is True
        assert resp["trigger_accepted"] is False

    def test_handler_blocked_by_not_completed(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_I", status="failed")
        resp = handle_auto_advance_trigger(result, controller=controller)
        assert resp["handled"] is True
        assert resp["trigger_accepted"] is False


class TestHandlerPreservesModes:
    def test_handler_bounded_auto_mode(self, controller: AutoAdvanceController) -> None:
        """bounded auto mode: merge gate blocks dispatch even for handler."""
        result = _round_result(
            "BLOCKER_I",
            formal_status_code="completed",
            merge_gate_encountered=True,
        )
        resp = handle_auto_advance_trigger(result, controller=controller)
        assert resp["handled"] is True
        assert resp["trigger_accepted"] is False
        assert "merge" in resp["reason"] or "merge_gate" in resp["detail"]

    def test_handler_manual_review_preserved(self, controller: AutoAdvanceController) -> None:
        """manual review: review gate blocks dispatch."""
        result = _round_result(
            "BLOCKER_I",
            formal_status_code="candidate_ready_awaiting_manual_review",
        )
        resp = handle_auto_advance_trigger(result, controller=controller)
        assert resp["handled"] is True
        assert resp["trigger_accepted"] is False
        assert "review_gate" in resp["detail"] or "review_gate" in resp["reason"]

    def test_handler_bounded_push_gate(self, controller: AutoAdvanceController) -> None:
        """bounded auto mode: push gate still blocks."""
        result = _round_result(
            "BLOCKER_I",
            formal_status_code="completed",
            push_gate_encountered=True,
        )
        resp = handle_auto_advance_trigger(result, controller=controller)
        assert resp["handled"] is True
        assert resp["trigger_accepted"] is False


class TestHandlerScaffold:
    def test_handler_creates_scaffold(self, controller: AutoAdvanceController, tmp_path: Path) -> None:
        result = _round_result("BLOCKER_I")
        resp = handle_auto_advance_trigger(result, controller=controller)
        assert resp["scaffold_created"] is True
        assert resp["scaffold_path"] is not None
        scaffold_path = Path(resp["scaffold_path"])
        assert scaffold_path.exists()
        assert (scaffold_path / "evidence.json").exists()
        assert (scaffold_path / "task.txt").exists()

    def test_handler_scaffold_evidence_law04(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_I")
        resp = handle_auto_advance_trigger(result, controller=controller)
        import json
        ev = json.loads(Path(resp["scaffold_path"]).joinpath("evidence.json").read_text(encoding="utf-8"))
        assert ev["law_compliance"] == "04"
        assert ev["merge_blocked"] is True
        assert ev["push_blocked"] is True
        assert ev["promote_blocked"] is True

    def test_handler_no_scaffold_when_blocked(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_I", blockers_found=["BLOCKER_X"])
        resp = handle_auto_advance_trigger(result, controller=controller)
        assert resp["scaffold_created"] is False
        assert resp["scaffold_path"] is None


class TestHandlerNoAutoExec:
    def test_handler_no_merge(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_I")
        resp = handle_auto_advance_trigger(result, controller=controller)
        assert resp["merge_executed"] is False

    def test_handler_no_push(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_I")
        resp = handle_auto_advance_trigger(result, controller=controller)
        assert resp["push_executed"] is False

    def test_handler_no_promote(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_I")
        resp = handle_auto_advance_trigger(result, controller=controller)
        assert resp["promote_executed"] is False

    def test_handler_no_pr(self, controller: AutoAdvanceController) -> None:
        result = _round_result("BLOCKER_I")
        resp = handle_auto_advance_trigger(result, controller=controller)
        assert resp["pr_created"] is False


class TestHandlerFreshController:
    def test_handler_no_controller_arg(self) -> None:
        """Handler should work without an explicit controller."""
        result = _round_result("BLOCKER_I")
        resp = handle_auto_advance_trigger(result)
        assert resp["handled"] is True
        # The fresh controller uses cwd as repo_root; scaffold may or may not
        # be created depending on cwd, but the call should not crash.
