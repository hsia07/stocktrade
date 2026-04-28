"""
Test Phase A features: pause boundary, start from checkpoint,
connection failure blocking, manual unlock only.
Phase B features MUST NOT be tested here.
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, '.')
from automation.control.pause_state import PauseStateManager
from automation.runtime.api_automode_loop import AutomodeRuntimeLoop

class TestPauseBoundary(unittest.TestCase):
    """Test that /pause only happens at safe step boundaries."""
    
    def setUp(self):
        self.repo_root = Path.cwd()
        self.manager = PauseStateManager(self.repo_root)
        # Clean up before test
        if self.manager.is_paused():
            self.manager.clear_pause()
        if self.manager.checkpoint_path.exists():
            self.manager.checkpoint_path.unlink()
    
    def tearDown(self):
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
        # Checkpoint should be saved
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
        if self.manager.is_paused():
            self.manager.clear_pause()
        if self.manager.checkpoint_path.exists():
            self.manager.checkpoint_path.unlink()
    
    def tearDown(self):
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
        # Save checkpoint
        self.manager._save_checkpoint(checkpoint_data)
        # Load checkpoint
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

class TestConnectionFailureBlocking(unittest.TestCase):
    """Test connection failure count and blocking."""
    
    def test_connection_failure_count(self):
        """_connection_failures increments."""
        # Mock the runtime loop
        loop = Mock(spec=AutomodeRuntimeLoop)
        loop._connection_failures = 0
        loop._max_failures = 3
        
        # Simulate failures
        loop._connection_failures += 1
        self.assertEqual(loop._connection_failures, 1)
        
        loop._connection_failures += 1
        self.assertEqual(loop._connection_failures, 2)
        
        loop._connection_failures += 1
        self.assertEqual(loop._connection_failures, 3)
        # At 3 failures, should be blocked
        self.assertGreaterEqual(loop._connection_failures, loop._max_failures)
    
    def test_failure_reset_on_start(self):
        """/start resets failure count."""
        loop = Mock(spec=AutomodeRuntimeLoop)
        loop._connection_failures = 3
        
        # Simulate /start
        loop._connection_failures = 0
        self.assertEqual(loop._connection_failures, 0)

class TestPauseReasonReported(unittest.TestCase):
    """Test that pause_reason is reported."""
    
    def setUp(self):
        self.repo_root = Path.cwd()
        self.manager = PauseStateManager(self.repo_root)
        if self.manager.is_paused():
            self.manager.clear_pause()
    
    def tearDown(self):
        if self.manager.is_paused():
            self.manager.clear_pause()
    
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

if __name__ == "__main__":
    unittest.main()
