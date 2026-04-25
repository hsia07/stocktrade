"""
Anti-Regression Tests: Telegram Phase Notifications

Tests that validate:
- Telegram sends notification on round_entered
- Telegram sends notification on construction_in_progress
- Telegram sends notification on candidate_materializing
- Telegram sends notification on stopped
"""

import unittest
import tempfile
from pathlib import Path
import yaml

from automation.control.phase_state import RoundPhase


class MockTelegramSender:
    """Mock sender that records all sent messages."""

    def __init__(self):
        self.messages = []

    def send_message(self, text: str, parse_mode: str = "Markdown") -> dict:
        self.messages.append(text)
        return {"success": True, "message_id": len(self.messages), "error": None, "http_status": 200}

    def send_status(self, summary: dict) -> dict:
        text = summary.get("formatted_text", "")
        return self.send_message(text)

    def is_configured(self) -> bool:
        return True


class TestTelegramPhaseNotify(unittest.TestCase):
    """Prevent regression: Telegram must notify on key phase transitions."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.manifest_path = self.tmpdir / "manifests" / "current_round.yaml"
        self.lock_path = self.tmpdir / "automation" / "control" / "AUTO_MODE_ACTIVATION_LOCK"
        self.manifest_path.parent.mkdir(parents=True)
        self.lock_path.parent.mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_manifest(self, data):
        with self.manifest_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

    def test_telegram_round_entered_notify(self):
        """notify_phase_transition for ROUND_ENTERED must send a message."""
        from automation.control.status_scheduler import StatusScheduler
        scheduler = StatusScheduler(self.tmpdir)
        mock_sender = MockTelegramSender()
        scheduler.sender = mock_sender

        result = scheduler.notify_phase_transition(RoundPhase.ROUND_ENTERED.value, "R020", "Test enter")
        self.assertTrue(result.get("success"))
        self.assertTrue(any("R020" in m and RoundPhase.ROUND_ENTERED.value in m for m in mock_sender.messages))

    def test_telegram_construction_in_progress_notify(self):
        """notify_phase_transition for CONSTRUCTION_IN_PROGRESS must send a message."""
        from automation.control.status_scheduler import StatusScheduler
        scheduler = StatusScheduler(self.tmpdir)
        mock_sender = MockTelegramSender()
        scheduler.sender = mock_sender

        result = scheduler.notify_phase_transition(RoundPhase.CONSTRUCTION_IN_PROGRESS.value, "R020", "Test construction")
        self.assertTrue(result.get("success"))
        self.assertTrue(any(RoundPhase.CONSTRUCTION_IN_PROGRESS.value in m for m in mock_sender.messages))

    def test_telegram_candidate_materializing_notify(self):
        """notify_phase_transition for CANDIDATE_MATERIALIZING must send a message."""
        from automation.control.status_scheduler import StatusScheduler
        scheduler = StatusScheduler(self.tmpdir)
        mock_sender = MockTelegramSender()
        scheduler.sender = mock_sender

        result = scheduler.notify_phase_transition(RoundPhase.CANDIDATE_MATERIALIZING.value, "R020", "Test materializing")
        self.assertTrue(result.get("success"))
        self.assertTrue(any(RoundPhase.CANDIDATE_MATERIALIZING.value in m for m in mock_sender.messages))

    def test_telegram_stop_notify(self):
        """notify_phase_transition for STOPPED must send a message."""
        from automation.control.status_scheduler import StatusScheduler
        scheduler = StatusScheduler(self.tmpdir)
        mock_sender = MockTelegramSender()
        scheduler.sender = mock_sender

        result = scheduler.notify_phase_transition(RoundPhase.STOPPED.value, "R020", "Test stop")
        self.assertTrue(result.get("success"))
        self.assertTrue(any(RoundPhase.STOPPED.value in m for m in mock_sender.messages))

    def test_telegram_runtime_invoked_on_phase_transition(self):
        """
        Simulate runtime _transition_phase calling notify_phase_transition
        for all key phases and verify Telegram messages are sent.
        """
        from automation.control.status_scheduler import StatusScheduler
        scheduler = StatusScheduler(self.tmpdir)
        mock_sender = MockTelegramSender()
        scheduler.sender = mock_sender

        phases = [
            RoundPhase.ROUND_ENTERED.value,
            RoundPhase.CONSTRUCTION_BOOTSTRAP.value,
            RoundPhase.CONSTRUCTION_IN_PROGRESS.value,
            RoundPhase.STOPPED.value,
        ]

        for phase in phases:
            result = scheduler.notify_phase_transition(phase, "R020", f"Runtime {phase}")
            self.assertTrue(result.get("success"), f"Phase {phase} notify failed")

        # Verify all phase messages were sent
        for phase in phases:
            self.assertTrue(
                any(phase in m for m in mock_sender.messages),
                f"No Telegram message for phase {phase}"
            )


if __name__ == "__main__":
    unittest.main()
