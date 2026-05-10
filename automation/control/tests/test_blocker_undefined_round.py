"""UNDEFINED_ROUND_HARD_GATE: tests for blocking construction/dispatch on undefined round_id."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from automation.control.auto_advance import AutoAdvanceController
from automation.control.control_bridge import is_round_defined


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


class TestIsRoundDefined:
    """Unit tests for AutoAdvanceController._is_round_defined."""

    def test_none_is_undefined(self, controller: AutoAdvanceController) -> None:
        ok, reason = controller._is_round_defined(None)
        assert ok is False
        assert "round_id_is_None" in reason

    def test_empty_string_is_undefined(self, controller: AutoAdvanceController) -> None:
        ok, reason = controller._is_round_defined("")
        assert ok is False
        assert "undefined" in reason

    def test_none_string_is_undefined(self, controller: AutoAdvanceController) -> None:
        ok, reason = controller._is_round_defined("NONE")
        assert ok is False
        assert "undefined" in reason

    def test_none_lowercase_is_undefined(self, controller: AutoAdvanceController) -> None:
        ok, reason = controller._is_round_defined("none")
        assert ok is False
        assert "undefined" in reason

    def test_undefined_literal_is_undefined(self, controller: AutoAdvanceController) -> None:
        ok, reason = controller._is_round_defined("undefined")
        assert ok is False
        assert "undefined" in reason

    def test_law_undefined_is_undefined(self, controller: AutoAdvanceController) -> None:
        ok, reason = controller._is_round_defined("law_undefined")
        assert ok is False
        assert "undefined" in reason

    def test_whitespace_is_undefined(self, controller: AutoAdvanceController) -> None:
        ok, reason = controller._is_round_defined("  ")
        assert ok is False
        assert "undefined" in reason

    def test_blocker_g_is_defined(self, controller: AutoAdvanceController) -> None:
        ok, reason = controller._is_round_defined("BLOCKER_G")
        assert ok is True
        assert reason == ""

    def test_blocker_e_is_defined(self, controller: AutoAdvanceController) -> None:
        ok, reason = controller._is_round_defined("BLOCKER_E")
        assert ok is True
        assert reason == ""

    def test_auto_advance_operational_is_defined(self, controller: AutoAdvanceController) -> None:
        ok, reason = controller._is_round_defined("AUTO_ADVANCE_OPERATIONAL")
        assert ok is True
        assert reason == ""


class TestCanAutoAdvanceUndefinedRoundGate:
    """can_auto_advance must block when round_id is undefined."""

    def test_none_round_blocked(self, controller: AutoAdvanceController) -> None:
        result = _round_result(round_id=None)
        can, reason, gate = controller.can_auto_advance(result)
        assert can is False
        assert "undefined_round" in reason
        assert gate == "undefined_round_gate"

    def test_empty_round_blocked(self, controller: AutoAdvanceController) -> None:
        result = _round_result(round_id="")
        can, reason, gate = controller.can_auto_advance(result)
        assert can is False
        assert "undefined_round" in reason
        assert gate == "undefined_round_gate"

    def test_none_string_round_blocked(self, controller: AutoAdvanceController) -> None:
        result = _round_result(round_id="NONE")
        can, reason, gate = controller.can_auto_advance(result)
        assert can is False
        assert "undefined_round" in reason
        assert gate == "undefined_round_gate"

    def test_law_undefined_round_blocked(self, controller: AutoAdvanceController) -> None:
        result = _round_result(round_id="law_undefined")
        can, reason, gate = controller.can_auto_advance(result)
        assert can is False
        assert "undefined_round" in reason
        assert gate == "undefined_round_gate"

    def test_defined_round_not_blocked(self, controller: AutoAdvanceController) -> None:
        result = _round_result(round_id="BLOCKER_E")
        can, reason, gate = controller.can_auto_advance(result)
        assert can is True


class TestCanDispatchNextRoundUndefinedGate:
    """can_dispatch_next_round must block when round_id is undefined."""

    def test_none_round_blocked(self, controller: AutoAdvanceController) -> None:
        result = _round_result(round_id=None)
        can, reason, detail = controller.can_dispatch_next_round(result)
        assert can is False
        assert "undefined_round" in reason
        assert detail == "undefined_round_gate"

    def test_empty_round_blocked(self, controller: AutoAdvanceController) -> None:
        result = _round_result(round_id="")
        can, reason, detail = controller.can_dispatch_next_round(result)
        assert can is False
        assert "undefined_round" in reason
        assert detail == "undefined_round_gate"

    def test_none_string_round_blocked(self, controller: AutoAdvanceController) -> None:
        result = _round_result(round_id="NONE")
        can, reason, detail = controller.can_dispatch_next_round(result)
        assert can is False
        assert "undefined_round" in reason
        assert detail == "undefined_round_gate"

    def test_law_undefined_round_blocked(self, controller: AutoAdvanceController) -> None:
        result = _round_result(round_id="law_undefined")
        can, reason, detail = controller.can_dispatch_next_round(result)
        assert can is False
        assert "undefined_round" in reason
        assert detail == "undefined_round_gate"

    def test_defined_round_not_blocked(self, controller: AutoAdvanceController) -> None:
        result = _round_result(round_id="BLOCKER_E")
        can, reason, detail = controller.can_dispatch_next_round(result)
        assert can is True


class TestDispatchNextRoundUndefinedGate:
    """dispatch_next_round must NOT create scaffold when round_id is undefined."""

    def test_none_round_no_scaffold(self, controller: AutoAdvanceController) -> None:
        result = _round_result(round_id=None)
        dispatch = controller.dispatch_next_round(result)
        assert dispatch["dispatch_executed"] is False
        assert dispatch["scaffold_created"] is False

    def test_empty_round_no_scaffold(self, controller: AutoAdvanceController) -> None:
        result = _round_result(round_id="")
        dispatch = controller.dispatch_next_round(result)
        assert dispatch["dispatch_executed"] is False
        assert dispatch["scaffold_created"] is False

    def test_none_string_no_scaffold(self, controller: AutoAdvanceController) -> None:
        result = _round_result(round_id="NONE")
        dispatch = controller.dispatch_next_round(result)
        assert dispatch["dispatch_executed"] is False
        assert dispatch["scaffold_created"] is False

    def test_law_undefined_no_scaffold(self, controller: AutoAdvanceController) -> None:
        result = _round_result(round_id="law_undefined")
        dispatch = controller.dispatch_next_round(result)
        assert dispatch["dispatch_executed"] is False
        assert dispatch["scaffold_created"] is False

    def test_defined_round_creates_scaffold(self, controller: AutoAdvanceController) -> None:
        result = _round_result(round_id="BLOCKER_E")
        dispatch = controller.dispatch_next_round(result)
        assert dispatch["dispatch_executed"] is True
        assert dispatch["scaffold_created"] is True


class TestControlBridgeIsRoundDefined:
    """Unit tests for control_bridge.is_round_defined helper."""

    def test_none_is_undefined(self) -> None:
        assert is_round_defined(None) is False

    def test_empty_string_is_undefined(self) -> None:
        assert is_round_defined("") is False

    def test_none_string_is_undefined(self) -> None:
        assert is_round_defined("NONE") is False

    def test_none_lowercase_is_undefined(self) -> None:
        assert is_round_defined("none") is False

    def test_undefined_literal_is_undefined(self) -> None:
        assert is_round_defined("undefined") is False

    def test_law_undefined_is_undefined(self) -> None:
        assert is_round_defined("law_undefined") is False

    def test_whitespace_is_undefined(self) -> None:
        assert is_round_defined("   ") is False

    def test_blocker_g_is_defined(self) -> None:
        assert is_round_defined("BLOCKER_G") is True

    def test_blocker_e_is_defined(self) -> None:
        assert is_round_defined("BLOCKER_E") is True
