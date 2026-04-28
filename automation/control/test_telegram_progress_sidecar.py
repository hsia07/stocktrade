"""
Tests for TelegramProgressSidecar (mock mode)

Sidecar monitors latest_return_to_chatgpt.txt changes and
converts them to TelegramProgressNotifier mock messages.
"""

import unittest
import tempfile
import os
from pathlib import Path

from automation.control.telegram_progress_sidecar import TelegramProgressSidecar
from automation.control.telegram_progress_notifier import TelegramProgressNotifier


class TestTelegramProgressSidecarInit(unittest.TestCase):
    def test_init_default(self):
        sidecar = TelegramProgressSidecar()
        self.assertTrue(sidecar.enabled)
        self.assertTrue(sidecar.mock_mode)
        self.assertIsNotNone(sidecar.notifier)
        self.assertEqual(sidecar.report_path, Path("automation/control/latest_return_to_chatgpt.txt"))

    def test_init_with_notifier(self):
        notifier = TelegramProgressNotifier(enabled=True, mock_mode=True)
        sidecar = TelegramProgressSidecar(
            report_path="test.txt",
            notifier=notifier,
            enabled=False,
            mock_mode=False
        )
        self.assertFalse(sidecar.enabled)
        self.assertFalse(sidecar.mock_mode)
        self.assertEqual(sidecar.report_path, Path("test.txt"))


class TestFileMonitoring(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.report_path = Path(self.temp_dir) / "latest_return_to_chatgpt.txt"
        self.notifier = TelegramProgressNotifier(enabled=True, mock_mode=True)
        self.sidecar = TelegramProgressSidecar(
            report_path=str(self.report_path),
            notifier=self.notifier,
            enabled=True,
            mock_mode=True
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_file_not_exists(self):
        result = self.sidecar.check_and_notify()
        self.assertTrue(result["checked"])
        self.assertFalse(result["changed"])
        self.assertIn("not found", result["reason"])

    def test_first_check_detects_change(self):
        content = """---
# RETURN_TO_CHATGPT
## REPORT - R025
round_id: R025
status: completed
formal_status_code: candidate_ready_awaiting_manual_review
reply_id: r025-report-001
"""
        self.report_path.write_text(content, encoding="utf-8")
        result = self.sidecar.check_and_notify()
        self.assertTrue(result["changed"])
        self.assertTrue(result["notified"])
        self.assertEqual(result["round_id"], "R025")
        self.assertEqual(result["status"], "completed")

    def test_second_check_no_change(self):
        content = """---
# RETURN_TO_CHATGPT
round_id: R025
status: completed
reply_id: r025-report-001
"""
        self.report_path.write_text(content, encoding="utf-8")
        self.sidecar.check_and_notify()  # First check
        result = self.sidecar.check_and_notify()  # Second check
        self.assertTrue(result["checked"])
        self.assertFalse(result["changed"])
        self.assertIn("no change", result["reason"])


class TestDeduplication(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.report_path = Path(self.temp_dir) / "latest_return_to_chatgpt.txt"
        self.notifier = TelegramProgressNotifier(enabled=True, mock_mode=True)
        self.sidecar = TelegramProgressSidecar(
            report_path=str(self.report_path),
            notifier=self.notifier,
            enabled=True,
            mock_mode=True
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_same_reply_id_notified_once(self):
        content1 = """---
round_id: R025
status: completed
reply_id: r025-same-id
"""
        self.report_path.write_text(content1, encoding="utf-8")
        result1 = self.sidecar.check_and_notify()
        self.assertTrue(result1["notified"])

        # Same reply_id, even with content change
        content2 = """---
round_id: R025
status: completed
reply_id: r025-same-id
extra: field
"""
        self.report_path.write_text(content2, encoding="utf-8")
        result2 = self.sidecar.check_and_notify()
        self.assertTrue(result2["changed"])
        self.assertFalse(result2["notified"])
        self.assertIn("duplicate reply_id", result2["reason"])


class TestStatusMapping(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.report_path = Path(self.temp_dir) / "latest_return_to_chatgpt.txt"
        self.notifier = TelegramProgressNotifier(enabled=True, mock_mode=True)
        self.sidecar = TelegramProgressSidecar(
            report_path=str(self.report_path),
            notifier=self.notifier,
            enabled=True,
            mock_mode=True
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_completed_sends_complete(self):
        content = "round_id: R025\nstatus: completed\nreply_id: r025-001\n"
        self.report_path.write_text(content, encoding="utf-8")
        self.sidecar.check_and_notify()
        log = self.notifier.get_log()
        self.assertTrue(any("COMPLETE" in msg for msg in log))

    def test_failed_sends_error(self):
        content = "round_id: R025\nstatus: failed\nformal_status_code: blocked\nreply_id: r025-002\n"
        self.report_path.write_text(content, encoding="utf-8")
        self.sidecar.check_and_notify()
        log = self.notifier.get_log()
        self.assertTrue(any("ERROR" in msg for msg in log))

    def test_paused_sends_error(self):
        content = "round_id: R025\nstatus: paused\nreply_id: r025-003\n"
        self.report_path.write_text(content, encoding="utf-8")
        self.sidecar.check_and_notify()
        log = self.notifier.get_log()
        self.assertTrue(any("ERROR" in msg for msg in log))


class TestDisabledNoOp(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.report_path = Path(self.temp_dir) / "latest_return_to_chatgpt.txt"
        self.notifier = TelegramProgressNotifier(enabled=True, mock_mode=True)
        self.sidecar = TelegramProgressSidecar(
            report_path=str(self.report_path),
            notifier=self.notifier,
            enabled=False,
            mock_mode=True
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_disabled_returns_noop(self):
        content = "round_id: R025\nstatus: completed\n"
        self.report_path.write_text(content, encoding="utf-8")
        result = self.sidecar.check_and_notify()
        self.assertTrue(result["checked"])
        self.assertFalse(result["notified"])
        self.assertIn("disabled", result["reason"])


class TestParseReport(unittest.TestCase):
    def setUp(self):
        self.sidecar = TelegramProgressSidecar(enabled=False)

    def test_parse_round_id(self):
        content = "round_id: R025\nstatus: completed\n"
        state = self.sidecar._parse_report(content)
        self.assertEqual(state["round_id"], "R025")

    def test_parse_status(self):
        content = "round_id: R025\nstatus: failed\n"
        state = self.sidecar._parse_report(content)
        self.assertEqual(state["status"], "failed")

    def test_parse_formal_status_code(self):
        content = "formal_status_code: blocked\n"
        state = self.sidecar._parse_report(content)
        self.assertEqual(state["formal_status_code"], "blocked")

    def test_parse_reply_id(self):
        content = "reply_id: r025-test-001\n"
        state = self.sidecar._parse_report(content)
        self.assertEqual(state["reply_id"], "r025-test-001")


if __name__ == "__main__":
    unittest.main()
