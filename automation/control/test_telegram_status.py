"""
Anti-Regression Tests for Telegram Status Reporting

Tests that validate:
- StatusReporter reads only structured fields
- StatusScheduler builds state from current_round.yaml (not notes)
- /pause stops at correct boundary
- /start rejects when chain frozen/backlog pending/state inconsistent
- Stale round reporting is detected and prevented
"""

import unittest
import json
import tempfile
from pathlib import Path
import yaml

from automation.control.status_reporter import StatusReporter
from automation.control.status_scheduler import StatusScheduler
from automation.control.pause_state import PauseStateManager


class TestAntiRegressionStaleState(unittest.TestCase):
    """Prevent regression to stale round reporting."""

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

    def _write_lock(self, data):
        with self.lock_path.open("w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_scheduler_reads_structured_fields_not_notes(self):
        """
        StatusScheduler.build_state() must read last_completed_round,
        current_round, next_round_to_dispatch from structured fields,
        NOT from notes.
        """
        manifest = {
            "round_id": "STATE-NORMALIZATION",
            "status": "candidate_pass",
            "last_completed_round": "R019",
            "current_round": "NONE",
            "next_round_to_dispatch": "R020",
            "auto_run": False,
            "chain_status": "frozen_pending_backlog_merge",
            "notes": "This is free text that should be IGNORED for state building",
            "backlog": {
                "r018": {"merge_review_status": "merged"},
                "r019": {"merge_review_status": "merged"},
            },
        }
        self._write_manifest(manifest)
        self._write_lock({"chain_control": {"status": "frozen"}})

        scheduler = StatusScheduler(self.tmpdir)
        state = scheduler.build_state()

        self.assertEqual(state["last_completed_round"], "R019")
        self.assertEqual(state["current_round"], "NONE")
        self.assertEqual(state["next_round"], "R020")
        self.assertEqual(state["auto_run"], False)
        self.assertEqual(state["chain_status"], "frozen_pending_backlog_merge")
        # Ensure notes did NOT influence state
        self.assertNotIn("free text", state.get("stop_reason", ""))

    def test_scheduler_detects_stale_last_completed_round(self):
        """
        If last_completed_round is older than actual git history,
        the state is inconsistent. This test documents the gap;
        a full implementation would cross-reference git history.
        """
        manifest = {
            "last_completed_round": "R017",  # stale
            "current_round": "NONE",
            "next_round_to_dispatch": "R018",
            "auto_run": False,
            "chain_status": "frozen_pending_backlog_merge",
            "backlog": {},
        }
        self._write_manifest(manifest)
        self._write_lock({"chain_control": {"status": "frozen"}})

        scheduler = StatusScheduler(self.tmpdir)
        state = scheduler.build_state()

        # Scheduler faithfully reports what it reads; anti-regression
        # requires a validator that compares manifest to git history.
        self.assertEqual(state["last_completed_round"], "R017")

    def test_status_reporter_does_not_read_notes(self):
        """
        StatusReporter.generate_summary() must only read from the
        passed state dict, never directly from files or notes.
        """
        reporter = StatusReporter()
        state = {
            "current_round": "R020",
            "next_round": "R021",
            "auto_advanced": True,
            "stop_reason": "",
            "stop_gate_type": "",
            "evidence_complete": True,
            "candidate_branch": "work/candidate-r020",
            "candidate_commit": "deadbeef",
            "awaiting_review": False,
            "lane_frozen": False,
            "paused": False,
            "backlog_pending": False,
        }
        summary = reporter.generate_summary(state)
        self.assertEqual(summary["current_round"], "R020")
        self.assertEqual(summary["next_round"], "R021")
        self.assertTrue(summary["evidence_complete_true_or_false"])


class TestPauseSemantics(unittest.TestCase):
    """/pause must stop after current round, before next dispatch."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.manifest_path = self.tmpdir / "manifests" / "current_round.yaml"
        self.lock_path = self.tmpdir / "automation" / "control" / "AUTO_MODE_ACTIVATION_LOCK"
        self.manifest_path.parent.mkdir(parents=True)
        self.lock_path.parent.mkdir(parents=True)
        self.pause_manager = PauseStateManager(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_manifest(self, data):
        with self.manifest_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

    def _write_lock(self, data):
        with self.lock_path.open("w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_pause_when_no_round_in_progress(self):
        """When current_round=NONE, pause is immediately safe."""
        manifest = {
            "current_round": "NONE",
            "chain_status": "frozen_pending_backlog_merge",
            "auto_run": False,
        }
        self._write_manifest(manifest)
        scheduler = StatusScheduler(self.tmpdir)
        result = scheduler.check_can_pause()
        self.assertTrue(result["can_pause"])
        self.assertEqual(result["current_round"], "NONE")

    def test_pause_when_round_in_progress(self):
        """When a round is in progress, pause should finish current first."""
        manifest = {
            "current_round": "R020",
            "chain_status": "in_progress",
            "auto_run": True,
        }
        self._write_manifest(manifest)
        scheduler = StatusScheduler(self.tmpdir)
        result = scheduler.check_can_pause()
        self.assertTrue(result["can_pause"])
        self.assertEqual(result["reason"], "pause_after_current_round_completes")

    def test_pause_already_paused(self):
        """Cannot pause if already paused."""
        self.pause_manager.set_pause("test_pause")
        manifest = {"current_round": "NONE"}
        self._write_manifest(manifest)
        scheduler = StatusScheduler(self.tmpdir)
        result = scheduler.check_can_pause()
        self.assertFalse(result["can_pause"])
        self.pause_manager.clear_pause()


class TestStartSemantics(unittest.TestCase):
    """/start must reject when frozen, backlog pending, or state inconsistent."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.manifest_path = self.tmpdir / "manifests" / "current_round.yaml"
        self.lock_path = self.tmpdir / "automation" / "control" / "AUTO_MODE_ACTIVATION_LOCK"
        self.manifest_path.parent.mkdir(parents=True)
        self.lock_path.parent.mkdir(parents=True)
        self.pause_manager = PauseStateManager(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_manifest(self, data):
        with self.manifest_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

    def _write_lock(self, data):
        with self.lock_path.open("w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_start_rejects_when_chain_frozen(self):
        manifest = {
            "last_completed_round": "R019",
            "current_round": "NONE",
            "next_round_to_dispatch": "R020",
            "auto_run": False,
            "chain_status": "frozen_pending_backlog_merge",
            "backlog": {},
        }
        self._write_manifest(manifest)
        self._write_lock({"chain_control": {"status": "frozen"}})
        scheduler = StatusScheduler(self.tmpdir)
        result = scheduler.check_can_start()
        self.assertFalse(result["can_start"])
        self.assertIn("auto_run is false", result["reason"])

    def test_start_rejects_when_backlog_pending(self):
        manifest = {
            "last_completed_round": "R019",
            "current_round": "NONE",
            "next_round_to_dispatch": "R020",
            "auto_run": True,
            "chain_status": "frozen_pending_backlog_merge",
            "backlog": {
                "r019": {"merge_review_status": "pending"},
            },
        }
        self._write_manifest(manifest)
        self._write_lock({"chain_control": {"status": "frozen"}})
        scheduler = StatusScheduler(self.tmpdir)
        result = scheduler.check_can_start()
        self.assertFalse(result["can_start"])
        self.assertIn("backlog merge review pending", result["reason"])

    def test_start_rejects_when_paused(self):
        manifest = {
            "last_completed_round": "R019",
            "current_round": "NONE",
            "next_round_to_dispatch": "R020",
            "auto_run": True,
            "chain_status": "running",
            "backlog": {},
        }
        self._write_manifest(manifest)
        self.pause_manager.set_pause("test")
        scheduler = StatusScheduler(self.tmpdir)
        result = scheduler.check_can_start()
        self.assertFalse(result["can_start"])
        self.assertIn("PAUSE.flag is active", result["reason"])
        self.pause_manager.clear_pause()

    def test_start_rejects_when_state_inconsistent(self):
        manifest = {
            "last_completed_round": "",
            "current_round": "NONE",
            "next_round_to_dispatch": "",
            "auto_run": True,
            "chain_status": "running",
            "backlog": {},
        }
        self._write_manifest(manifest)
        scheduler = StatusScheduler(self.tmpdir)
        result = scheduler.check_can_start()
        self.assertFalse(result["can_start"])
        self.assertIn("structured state incomplete", result["reason"])

    def test_start_accepts_when_all_clear(self):
        manifest = {
            "last_completed_round": "R019",
            "current_round": "NONE",
            "next_round_to_dispatch": "R020",
            "auto_run": True,
            "chain_status": "running",
            "backlog": {
                "r018": {"merge_review_status": "merged"},
                "r019": {"merge_review_status": "merged"},
            },
        }
        self._write_manifest(manifest)
        scheduler = StatusScheduler(self.tmpdir)
        result = scheduler.check_can_start()
        self.assertTrue(result["can_start"])
        self.assertEqual(result["resume_from_round"], "R020")


class TestTelegramSenderMock(unittest.TestCase):
    """Mock tests for Telegram sender (no real API calls)."""

    def test_sender_not_configured_returns_error(self):
        """When no env vars, sender should return not_configured error."""
        import os
        # Ensure no token in env
        old_token = os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        old_chat = os.environ.pop("TELEGRAM_CHAT_ID", None)
        try:
            from automation.telegram.sender import TelegramSender
            sender = TelegramSender()
            self.assertFalse(sender.is_configured())
            result = sender.send_message("test")
            self.assertFalse(result["success"])
            self.assertEqual(result["error"], "not_configured")
        finally:
            if old_token:
                os.environ["TELEGRAM_BOT_TOKEN"] = old_token
            if old_chat:
                os.environ["TELEGRAM_CHAT_ID"] = old_chat

    def test_sender_send_status_requires_formatted_text(self):
        """send_status requires 'formatted_text' key."""
        from automation.telegram.sender import TelegramSender
        sender = TelegramSender()
        result = sender.send_status({})
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "no_formatted_text")


if __name__ == "__main__":
    unittest.main()
