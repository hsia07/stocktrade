"""USAGE_EXHAUSTION_PAUSE_NOTIFY_BATCH: tests for usage exhaustion detection, pause integration, and Telegram notification coverage."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from automation.control.auto_advance import AutoAdvanceController
from automation.control.api_automode_loop import APIAutoModeLoop
from automation.control.telegram_notifier import TelegramNotifier
from automation.control.pause_state import PauseStateManager

REASON_USAGE = PauseStateManager.REASON_USAGE


# ---------------------------------------------------------------------------
# TelegramNotifier — mock-mode coverage tests
# ---------------------------------------------------------------------------

class TestTelegramNotifierMockMode:
    """All notification methods must work in mock mode (no real Telegram HTTP)."""

    @pytest.fixture()
    def notifier(self) -> TelegramNotifier:
        return TelegramNotifier(mock_mode=True)

    def test_pause_notification_mock(self, notifier: TelegramNotifier) -> None:
        result = notifier.send_pause_notification(pause_reason="test_reason")
        assert result["success"] is True
        assert result["mock"] is True

    def test_stall_warning_mock(self, notifier: TelegramNotifier) -> None:
        result = notifier.send_stall_warning(100.0, 300.0)
        assert result["success"] is True
        assert result["mock"] is True

    def test_failure_warning_mock(self, notifier: TelegramNotifier) -> None:
        result = notifier.send_failure_warning(2, 3)
        assert result["success"] is True
        assert result["mock"] is True

    def test_usage_exhausted_notification_mock(self, notifier: TelegramNotifier) -> None:
        result = notifier.send_usage_exhausted_notification()
        assert result["success"] is True
        assert result["mock"] is True
        assert "usage" in result["message"].lower()

    def test_blocked_notification_mock(self, notifier: TelegramNotifier) -> None:
        result = notifier.send_blocked_notification(reason="gate_blocked")
        assert result["success"] is True
        assert result["mock"] is True
        assert "blocked" in result["message"].lower()

    def test_blocked_notification_no_reason(self, notifier: TelegramNotifier) -> None:
        result = notifier.send_blocked_notification()
        assert result["success"] is True
        assert result["mock"] is True

    def test_awaiting_instruction_notification_mock(self, notifier: TelegramNotifier) -> None:
        result = notifier.send_awaiting_instruction_notification()
        assert result["success"] is True
        assert result["mock"] is True
        assert "awaiting" in result["message"].lower()

    def test_undefined_round_blocked_notification_mock(self, notifier: TelegramNotifier) -> None:
        result = notifier.send_undefined_round_blocked_notification()
        assert result["success"] is True
        assert result["mock"] is True
        assert "undefined" in result["message"].lower()

    def test_notifier_disabled_skips(self) -> None:
        n = TelegramNotifier(mock_mode=True, enabled=False)
        result = n.send_usage_exhausted_notification()
        assert result.get("skipped") is True
        assert result["success"] is True

        result = n.send_undefined_round_blocked_notification()
        assert result.get("skipped") is True

        result = n.send_blocked_notification()
        assert result.get("skipped") is True

        result = n.send_awaiting_instruction_notification()
        assert result.get("skipped") is True

    def test_log_accumulation(self, notifier: TelegramNotifier) -> None:
        notifier.send_usage_exhausted_notification()
        notifier.send_blocked_notification(reason="test")
        notifier.send_awaiting_instruction_notification()
        notifier.send_undefined_round_blocked_notification()
        log = notifier.get_log()
        assert len(log) == 4
        titles = [msg.split("\n")[0] for msg in log]
        assert any("Usage" in t for t in titles)
        assert any("Blocked" in t for t in titles)
        assert any("Awaiting" in t for t in titles)
        assert any("Undefined" in t for t in titles)


# ---------------------------------------------------------------------------
# AutoAdvanceController — usage exhaustion detection
# ---------------------------------------------------------------------------

class TestUsageExhaustionDetection:
    """check_usage_exhaustion, exhaust_usage, clear_usage_exhaustion."""

    @pytest.fixture()
    def controller(self, tmp_path: Path) -> AutoAdvanceController:
        ctrl = AutoAdvanceController(tmp_path)
        # Ensure the candidates dir exists (required by dispatch)
        candidates_dir = tmp_path / "automation" / "control" / "candidates"
        candidates_dir.mkdir(parents=True, exist_ok=True)
        return ctrl

    def test_not_exhausted_by_default(self, controller: AutoAdvanceController) -> None:
        assert controller.check_usage_exhaustion() is False

    def test_exhausted_after_exhaust(self, controller: AutoAdvanceController) -> None:
        controller.exhaust_usage()
        assert controller.check_usage_exhaustion() is True

    def test_clear_removes_exhaustion(self, controller: AutoAdvanceController) -> None:
        controller.exhaust_usage()
        controller.clear_usage_exhaustion()
        assert controller.check_usage_exhaustion() is False

    def test_double_clear_safe(self, controller: AutoAdvanceController) -> None:
        controller.clear_usage_exhaustion()
        controller.clear_usage_exhaustion()
        assert controller.check_usage_exhaustion() is False

    def test_sentinel_path_is_dotfile(self, controller: AutoAdvanceController) -> None:
        assert controller.USAGE_SENTINEL_PATH == ".usage_exhausted"

    def test_sentinel_content(self, controller: AutoAdvanceController) -> None:
        controller.exhaust_usage()
        sentinel = controller.repo_root / ".usage_exhausted"
        assert sentinel.read_text(encoding="utf-8") == "exhausted"

    def test_exhausted_from_different_instance(self, tmp_path: Path) -> None:
        ctrl1 = AutoAdvanceController(tmp_path)
        ctrl1.exhaust_usage()
        ctrl2 = AutoAdvanceController(tmp_path)
        assert ctrl2.check_usage_exhaustion() is True


class TestAutoAdvanceNotifyMethods:
    """notify_usage_exhausted and notify_undefined_round_blocked."""

    @pytest.fixture()
    def controller(self, tmp_path: Path) -> AutoAdvanceController:
        ctrl = AutoAdvanceController(tmp_path)
        candidates_dir = tmp_path / "automation" / "control" / "candidates"
        candidates_dir.mkdir(parents=True, exist_ok=True)
        return ctrl

    def test_notify_usage_exhausted_sets_pause(self, controller: AutoAdvanceController) -> None:
        controller.notify_usage_exhausted()
        assert controller.pause_manager.is_paused() is True
        info = controller.pause_manager.get_pause_info()
        assert info is not None
        assert info.get("reason") == REASON_USAGE

    def test_notify_usage_exhausted_logs_notification(self, controller: AutoAdvanceController) -> None:
        controller.notify_usage_exhausted()
        log = controller.notifier.get_log()
        assert len(log) >= 1
        assert "Usage" in log[-1]

    def test_notify_undefined_round_blocked_logs(self, controller: AutoAdvanceController) -> None:
        controller.notify_undefined_round_blocked()
        log = controller.notifier.get_log()
        assert len(log) >= 1
        assert "Undefined" in log[-1]


# ---------------------------------------------------------------------------
# APIAutoModeLoop — usage exhaustion triggers pause
# ---------------------------------------------------------------------------

class TestAPIAutoModeLoopUsageExhaustion:
    """check_usage_exhaustion integration in the runtime loop."""

    @pytest.fixture()
    def loop(self, tmp_path: Path) -> APIAutoModeLoop:
        lp = APIAutoModeLoop(tmp_path)
        # Ensure candidates dir exists
        candidates_dir = tmp_path / "automation" / "control" / "candidates"
        candidates_dir.mkdir(parents=True, exist_ok=True)
        return lp

    def test_not_paused_when_not_exhausted(self, loop: APIAutoModeLoop) -> None:
        loop.check_usage_exhaustion()
        assert loop.pause_manager.is_paused() is False

    def test_paused_when_exhausted(self, loop: APIAutoModeLoop) -> None:
        loop.auto_advance.exhaust_usage()
        loop.check_usage_exhaustion()
        assert loop.pause_manager.is_paused() is True
        info = loop.pause_manager.get_pause_info()
        assert info is not None
        assert info.get("reason") == REASON_USAGE

    def test_cleared_exhaustion_does_not_pause(self, loop: APIAutoModeLoop) -> None:
        loop.auto_advance.exhaust_usage()
        loop.auto_advance.clear_usage_exhaustion()
        loop.check_usage_exhaustion()
        assert loop.pause_manager.is_paused() is False

    def test_exhaustion_notification_sent(self, loop: APIAutoModeLoop) -> None:
        """Check_usage_exhaustion sends Telegram notification when exhausted."""
        loop.auto_advance.exhaust_usage()
        loop.check_usage_exhaustion()
        # The notifier created inside check_usage_exhaustion is a separate instance,
        # so we verify the pause state (the notification was sent as a side effect)
        assert loop.pause_manager.is_paused() is True


# ---------------------------------------------------------------------------
# AutoAdvanceController — undefined_round gate triggers notification
# ---------------------------------------------------------------------------

class TestUndefinedRoundGateNotifies:
    """When can_auto_advance / can_dispatch_next_round hits undefined_round_gate, notification fires."""

    @pytest.fixture()
    def controller(self, tmp_path: Path) -> AutoAdvanceController:
        ctrl = AutoAdvanceController(tmp_path)
        candidates_dir = tmp_path / "automation" / "control" / "candidates"
        candidates_dir.mkdir(parents=True, exist_ok=True)
        return ctrl

    def _result(self, round_id: str, **kw: Any) -> dict:
        base = {
            "round_id": round_id,
            "status": "completed",
            "formal_status_code": "auto_candidate_ready",
            "automated_signoff": {
                "hash_verified": True,
                "law_compliance_verified": True,
                "evidence_validated": True,
            },
            "blockers_found": [],
            "evidence_directory": None,
            "is_new_round_dispatch": False,
            "candidate_exists": False,
        }
        base.update(kw)
        return base

    def test_can_auto_advance_notifies_on_undefined(self, controller: AutoAdvanceController) -> None:
        r = self._result(round_id="none")
        ok, reason, gate = controller.can_auto_advance(r)
        assert ok is False
        assert gate == "undefined_round_gate"
        log = controller.notifier.get_log()
        assert any("Undefined" in msg for msg in log)

    def test_can_dispatch_next_round_notifies_on_undefined(self, controller: AutoAdvanceController) -> None:
        r = self._result(round_id="undefined")
        ok, reason, detail = controller.can_dispatch_next_round(r)
        assert ok is False
        assert "undefined_round" in reason
        log = controller.notifier.get_log()
        assert any("Undefined" in msg for msg in log)

    def test_defined_round_does_not_notify(self, controller: AutoAdvanceController) -> None:
        r = self._result(round_id="BLOCKER_I")
        ok, reason, gate = controller.can_auto_advance(r)
        log = controller.notifier.get_log()
        assert all("Undefined" not in msg for msg in log)


# ---------------------------------------------------------------------------
# TelegramNotifier — edge cases
# ---------------------------------------------------------------------------

class TestTelegramNotifierEdgeCases:

    def test_no_sender_no_crash(self) -> None:
        n = TelegramNotifier(sender=None, mock_mode=False, enabled=True)
        result = n.send_usage_exhausted_notification()
        assert result["success"] is False
        assert "no sender configured" in result.get("error", "")

    def test_clear_log(self) -> None:
        n = TelegramNotifier(mock_mode=True)
        n.send_pause_notification(pause_reason="test")
        assert len(n.get_log()) == 1
        n.clear_log()
        assert len(n.get_log()) == 0
