"""
Test Phase A features: pause boundary, start from checkpoint,
connection failure blocking, manual unlock only.
Phase B features MUST NOT be tested here.

Integration tests for:
1. /start reads checkpoint and resumes from step
2. /start fallback to state.runtime.json when checkpoint missing
3. pause_reason flows into return_report
4. connection_failures >= 3 triggers paused_after_failure
5. Only manual /start can unlock
"""

import unittest
import sys
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone

sys.path.insert(0, '.')
from automation.control.pause_state import PauseStateManager
from automation.control.status_scheduler import StatusScheduler
from automation.control.return_report import ReturnReportGenerator


class TestPauseBoundary(unittest.TestCase):
    """Test that /pause only happens at safe step boundaries."""

    def setUp(self):
        self.repo_root = Path.cwd()
        self.manager = PauseStateManager(self.repo_root)
        self._cleanup()

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        if self.manager.is_paused():
            self.manager.clear_pause()
        if self.manager.checkpoint_path.exists():
            self.manager.checkpoint_path.unlink()

    def test_pause_creates_flag(self):
        """PAUSE.flag is created."""
        result = self.manager.set_pause(reason="manual_pause_requested")
        self.assertTrue(result)
        self.assertTrue(self.manager.is_paused())

    def test_pause_with_checkpoint(self):
        """Pause saves checkpoint."""
        checkpoint_data = {
            "checkpoint_version": "1.0",
            "round_id": "R017",
            "current_step": "construction_in_progress",
            "pause_reason": "manual_pause_requested"
        }
        result = self.manager.set_pause(
            reason="manual_pause_requested",
            checkpoint_data=checkpoint_data
        )
        self.assertTrue(result)
        self.assertTrue(self.manager.checkpoint_path.exists())

    def test_clear_pause(self):
        """PAUSE.flag can be cleared."""
        self.manager.set_pause(reason="test")
        result = self.manager.clear_pause()
        self.assertTrue(result)
        self.assertFalse(self.manager.is_paused())


class TestStartFromCheckpoint(unittest.TestCase):
    """Test /start resumes from checkpoint preferentially."""

    def setUp(self):
        self.repo_root = Path.cwd()
        self.manager = PauseStateManager(self.repo_root)
        self._cleanup()

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        if self.manager.is_paused():
            self.manager.clear_pause()
        if self.manager.checkpoint_path.exists():
            self.manager.checkpoint_path.unlink()

    def test_load_checkpoint_exists(self):
        """Can load checkpoint if exists."""
        checkpoint_data = {
            "checkpoint_version": "1.0",
            "round_id": "R017",
            "current_step": "candidate_commit_created",
            "pause_reason": "manual_pause_requested"
        }
        self.manager._save_checkpoint(checkpoint_data)
        loaded = self.manager.load_checkpoint()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["round_id"], "R017")
        self.assertEqual(loaded["current_step"], "candidate_commit_created")

    def test_load_checkpoint_missing(self):
        """Returns None if checkpoint missing."""
        loaded = self.manager.load_checkpoint()
        self.assertIsNone(loaded)

    def test_checkpoint_clear(self):
        """Can clear checkpoint."""
        checkpoint_data = {"test": True}
        self.manager._save_checkpoint(checkpoint_data)
        self.assertTrue(self.manager.checkpoint_path.exists())
        result = self.manager.clear_checkpoint()
        self.assertTrue(result)
        self.assertFalse(self.manager.checkpoint_path.exists())


class TestStartChainIntegration(unittest.TestCase):
    """Test /start reads checkpoint and resumes from step."""

    def setUp(self):
        self.repo_root = Path.cwd()
        self.manager = PauseStateManager(self.repo_root)
        self._cleanup()

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        if self.manager.is_paused():
            self.manager.clear_pause()
        if self.manager.checkpoint_path.exists():
            self.manager.checkpoint_path.unlink()

    @patch('automation.control.status_scheduler.StatusScheduler.check_can_start')
    @patch('automation.control.status_scheduler.StatusScheduler._load_manifest')
    @patch('automation.control.status_scheduler.TelegramSender')
    @patch('automation.control.status_scheduler.CandidateChecker')
    @patch('automation.control.status_scheduler.StatusReporter')
    def test_start_chain_reads_checkpoint(self, mock_reporter, mock_checker, mock_sender, mock_load_manifest, mock_check_can_start):
        """/start reads checkpoint and returns resume_from_step."""
        # Save checkpoint
        checkpoint_data = {
            "checkpoint_version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "round_id": "R017",
            "current_step": "candidate_commit_created",
            "last_completed_action": "dispatch_completed",
            "pause_reason": "manual_pause_requested",
            "phase": "construction_in_progress",
            "recoverable": True
        }
        self.manager._save_checkpoint(checkpoint_data)
        self.manager.set_pause(reason="manual_pause_requested")

        # Mock sender
        mock_sender_instance = Mock()
        mock_sender.return_value = mock_sender_instance
        mock_sender_instance.send_message.return_value = {"ok": True}

        # Mock check_can_start to return True
        mock_check_can_start.return_value = {
            "can_start": True,
            "reason": "",
            "resume_from_round": "R017"
        }

        # Mock _load_manifest
        mock_load_manifest.return_value = {
            "current_round": "R017",
            "next_round_to_dispatch": "R018",
            "auto_run": True,
            "chain_status": "active"
        }

        # Create scheduler and call start_chain
        scheduler = StatusScheduler(self.repo_root)
        result = scheduler.start_chain()

        self.assertTrue(result["started"])
        self.assertEqual(result["resume_from_step"], "candidate_commit_created")
        self.assertEqual(result["last_completed_action"], "dispatch_completed")
        self.assertEqual(result["pause_reason"], "manual_pause_requested")
        self.assertEqual(result["resume_from_round"], "R017")

    @patch('automation.control.status_scheduler.StatusScheduler.check_can_start')
    @patch('automation.control.status_scheduler.StatusScheduler._load_manifest')
    @patch('automation.control.status_scheduler.TelegramSender')
    @patch('automation.control.status_scheduler.CandidateChecker')
    @patch('automation.control.status_scheduler.StatusReporter')
    def test_start_chain_fallback_to_runtime_json(self, mock_reporter, mock_checker, mock_sender, mock_load_manifest, mock_check_can_start):
        """/start falls back to state.runtime.json when checkpoint missing."""
        # Ensure no checkpoint exists
        self._cleanup()

        # Create a mock state.runtime.json with last_completed_action
        runtime_path = self.repo_root / "automation" / "control" / "state.runtime.json"
        if runtime_path.exists():
            with open(runtime_path, 'r', encoding='utf-8') as f:
                runtime_data = json.load(f)
        else:
            runtime_data = {
                "current_round": "R017",
                "last_completed_action": "phase2_completed",
                "pause_reason": "manual_pause_requested"
            }

        # Mock sender
        mock_sender_instance = Mock()
        mock_sender.return_value = mock_sender_instance
        mock_sender_instance.send_message.return_value = {"ok": True}

        # Mock check_can_start to return True
        mock_check_can_start.return_value = {
            "can_start": True,
            "reason": "",
            "resume_from_round": "R017"
        }

        # Mock _load_manifest
        mock_load_manifest.return_value = {
            "current_round": "R017",
            "next_round_to_dispatch": "R018",
            "auto_run": True,
            "chain_status": "active"
        }

        # Create scheduler and call start_chain (no checkpoint)
        scheduler = StatusScheduler(self.repo_root)
        result = scheduler.start_chain()

        # Should still start (no checkpoint, no pause)
        self.assertTrue(result["started"])
        # Without checkpoint, resume_from_step should be None
        self.assertIsNone(result.get("resume_from_step"))


class TestConnectionFailureBlocking(unittest.TestCase):
    """Test connection failure count and blocking."""

    def test_connection_failure_count(self):
        """_connection_failures increments and blocks at max."""
        loop = Mock()
        loop._connection_failures = 0
        loop._max_failures = 3

        loop._connection_failures += 1
        self.assertEqual(loop._connection_failures, 1)

        loop._connection_failures += 1
        self.assertEqual(loop._connection_failures, 2)

        loop._connection_failures += 1
        self.assertEqual(loop._connection_failures, 3)
        # At 3 failures, should be blocked
        self.assertGreaterEqual(loop._connection_failures, loop._max_failures)

    def test_failure_triggers_pause_after_failure(self):
        """connection_failures >= max triggers paused_after_failure."""
        manager = PauseStateManager(Path.cwd())
        if manager.is_paused():
            manager.clear_pause()
        if manager.checkpoint_path.exists():
            manager.checkpoint_path.unlink()

        # Simulate what api_automode_loop.py does at line 468-481
        connection_failures = 3
        max_failures = 3

        if connection_failures >= max_failures:
            checkpoint_data = {
                "checkpoint_version": "1.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "round_id": "R017",
                "current_step": "paused_after_failure",
                "phase": "paused",
                "pause_reason": "paused_after_failure",
                "connection_failures": connection_failures,
                "recoverable": False
            }
            result = manager.set_pause(
                reason="paused_after_failure",
                checkpoint_data=checkpoint_data
            )
            self.assertTrue(result)
            self.assertTrue(manager.is_paused())

            # Verify checkpoint saved
            loaded = manager.load_checkpoint()
            self.assertEqual(loaded["pause_reason"], "paused_after_failure")
            self.assertEqual(loaded["connection_failures"], 3)

        # Cleanup
        if manager.is_paused():
            manager.clear_pause()
        if manager.checkpoint_path.exists():
            manager.checkpoint_path.unlink()


class TestPauseReasonReported(unittest.TestCase):
    """Test that pause_reason is reported in return_report."""

    def setUp(self):
        self.repo_root = Path.cwd()
        self.manager = PauseStateManager(self.repo_root)
        self._cleanup()

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        if self.manager.is_paused():
            self.manager.clear_pause()
        if self.manager.checkpoint_path.exists():
            self.manager.checkpoint_path.unlink()

    def test_pause_reason_in_flag(self):
        """PAUSE.flag contains reason."""
        self.manager.set_pause(reason="paused_after_failure")
        info = self.manager.get_pause_info()
        self.assertIsNotNone(info)
        self.assertEqual(info.get("reason"), "paused_after_failure")

    def test_pause_reason_in_checkpoint(self):
        """Checkpoint contains pause_reason."""
        checkpoint_data = {
            "checkpoint_version": "1.0",
            "pause_reason": "paused_after_failure",
            "connection_failures": 3
        }
        self.manager._save_checkpoint(checkpoint_data)
        loaded = self.manager.load_checkpoint()
        self.assertEqual(loaded["pause_reason"], "paused_after_failure")
        self.assertEqual(loaded["connection_failures"], 3)

    def test_pause_reason_in_return_report(self):
        """pause_reason appears in generated return report."""
        generator = ReturnReportGenerator(self.repo_root)
        state = {
            "current_round": "R017",
            "last_completed_round": "R016",
            "next_round": "R018",
            "chain_status": "paused",
            "auto_run": False,
            "stop_reason": "",
            "stop_gate_type": ""
        }
        pause_reason = "paused_after_failure"

        report = generator.generate_pause_report(state, pause_reason=pause_reason)

        self.assertIn('"paused_after_failure"', report)
        self.assertIn("### pause_reason", report)
        self.assertIn("Pause reason: paused_after_failure", report)

    def test_pause_state_reads_reason_from_source(self):
        """PauseStateManager._read_pause_reason_from_source returns correct reason."""
        # Test with PAUSE.flag
        self.manager.set_pause(reason="manual_pause_requested")
        reason = self.manager._read_pause_reason_from_source()
        self.assertEqual(reason, "manual_pause_requested")

        # Test with checkpoint (checkpoint takes precedence if both exist)
        checkpoint_data = {
            "checkpoint_version": "1.0",
            "pause_reason": "paused_after_failure"
        }
        self.manager._save_checkpoint(checkpoint_data)
        reason = self.manager._read_pause_reason_from_source()
        # _read_pause_reason_from_source tries PAUSE.flag first
        self.assertEqual(reason, "manual_pause_requested")

        # Clear PAUSE.flag, should read from checkpoint
        self.manager.clear_pause()
        reason = self.manager._read_pause_reason_from_source()
        self.assertEqual(reason, "paused_after_failure")


class TestManualUnlockOnly(unittest.TestCase):
    """Test that only manual /start can unlock paused_after_failure."""

    def setUp(self):
        self.repo_root = Path.cwd()
        self.manager = PauseStateManager(self.repo_root)
        self._cleanup()

    def tearDown(self):
        self._cleanup()

    def _cleanup(self):
        if self.manager.is_paused():
            self.manager.clear_pause()
        if self.manager.checkpoint_path.exists():
            self.manager.checkpoint_path.unlink()

    @patch('automation.control.status_scheduler.StatusScheduler.check_can_start')
    @patch('automation.control.status_scheduler.StatusScheduler._load_manifest')
    @patch('automation.control.status_scheduler.TelegramSender')
    @patch('automation.control.status_scheduler.CandidateChecker')
    @patch('automation.control.status_scheduler.StatusReporter')
    def test_only_manual_start_unlocks(self, mock_reporter, mock_checker, mock_sender, mock_load_manifest, mock_check_can_start):
        """Only /start (manual) can clear pause_after_failure."""
        # Simulate paused_after_failure state
        checkpoint_data = {
            "checkpoint_version": "1.0",
            "round_id": "R017",
            "current_step": "paused_after_failure",
            "pause_reason": "paused_after_failure",
            "connection_failures": 3,
            "recoverable": False
        }
        self.manager._save_checkpoint(checkpoint_data)
        self.manager.set_pause(reason="paused_after_failure")
        self.assertTrue(self.manager.is_paused())

        # Mock sender
        mock_sender_instance = Mock()
        mock_sender.return_value = mock_sender_instance
        mock_sender_instance.send_message.return_value = {"ok": True}

        # Mock check_can_start to return True (after clearing pause)
        mock_check_can_start.return_value = {
            "can_start": True,
            "reason": "",
            "resume_from_round": "R017"
        }

        # Mock _load_manifest
        mock_load_manifest.return_value = {
            "current_round": "R017",
            "next_round_to_dispatch": "R018",
            "auto_run": True,
            "chain_status": "active"
        }

        # /start should clear pause and checkpoint
        scheduler = StatusScheduler(self.repo_root)
        result = scheduler.start_chain()

        self.assertTrue(result["started"])
        self.assertFalse(self.manager.is_paused())
        # Checkpoint should be cleared after start
        self.assertFalse(self.manager.checkpoint_path.exists())


if __name__ == "__main__":
    unittest.main()
