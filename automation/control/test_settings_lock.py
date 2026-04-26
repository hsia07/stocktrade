"""
Tests for R021 Important Settings Lock

Verifies:
- Settings can be locked
- Locked settings cannot be modified without authorization
- Unlock flow requires authorization token
- Audit log records all attempts
"""

import json
import tempfile
import unittest
from pathlib import Path

from automation.control.settings_lock import SettingsLock


class TestSettingsLock(unittest.TestCase):
    """Test R021 important settings lock functionality."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.lock = SettingsLock(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_lock_setting(self):
        """Settings can be locked and unlocked."""
        self.lock.lock_setting("chain_status", locked=True)
        self.assertTrue(self.lock.is_locked("chain_status"))

        self.lock.lock_setting("chain_status", locked=False)
        self.assertFalse(self.lock.is_locked("chain_status"))

    def test_locked_setting_blocks_modification(self):
        """Locked settings are blocked from modification."""
        self.lock.lock_setting("auto_run", locked=True)
        result = self.lock.validate_modification("auto_run", proposed_value=False)
        self.assertFalse(result["allowed"])
        self.assertIn("locked", result["reason"])

    def test_unlocked_setting_allows_modification(self):
        """Unlocked settings can be modified."""
        result = self.lock.validate_modification("some_new_setting", proposed_value="test")
        self.assertTrue(result["allowed"])

    def test_unlock_request_requires_authorization(self):
        """Locked settings require authorization token to unlock."""
        self.lock.lock_setting("phase_state", locked=True)
        result = self.lock.request_unlock("phase_state", "Need to update phase")
        self.assertFalse(result["unlock_allowed"])
        self.assertIn("unlock_token", result)

    def test_unlock_confirm_flow(self):
        """Unlock token can be confirmed to unlock a setting."""
        self.lock.lock_setting("current_round", locked=True)
        req = self.lock.request_unlock("current_round", "Test unlock")
        token = req["unlock_token"]

        confirm = self.lock.confirm_unlock(token)
        self.assertTrue(confirm["confirmed"])
        self.assertFalse(self.lock.is_locked("current_round"))

    def test_audit_log_records_attempts(self):
        """All modification attempts are logged to audit."""
        self.lock.lock_setting("test_setting", locked=True)
        self.lock.validate_modification("test_setting", "attempted_value")

        log = self.lock.get_audit_log(limit=10)
        self.assertTrue(len(log) > 0)
        self.assertEqual(log[-1]["setting"], "test_setting")
        self.assertEqual(log[-1]["action"], "modify_attempt")

    def test_double_unlock_rejected(self):
        """Cannot use the same unlock token twice."""
        self.lock.lock_setting("test_setting2", locked=True)
        req = self.lock.request_unlock("test_setting2", "Test")
        token = req["unlock_token"]

        self.lock.confirm_unlock(token)
        result = self.lock.confirm_unlock(token)

        self.assertFalse(result["confirmed"])
        self.assertIn("Invalid token", result.get("error", ""))


if __name__ == "__main__":
    unittest.main()