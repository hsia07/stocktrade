"""
Tests for TelegramProgressNotifier (mock mode)
"""

import unittest
from automation.control.telegram_progress_notifier import TelegramProgressNotifier


class TestTelegramProgressNotifierInit(unittest.TestCase):
    def test_init_default(self):
        notifier = TelegramProgressNotifier()
        self.assertTrue(notifier.enabled)
        self.assertTrue(notifier.mock_mode)
        self.assertIsNone(notifier.sender)

    def test_init_with_sender(self):
        sender = object()
        notifier = TelegramProgressNotifier(sender=sender, enabled=False, mock_mode=False)
        self.assertFalse(notifier.enabled)
        self.assertFalse(notifier.mock_mode)
        self.assertIs(sender, notifier.sender)


class TestMockModeNoSend(unittest.TestCase):
    def setUp(self):
        self.sender = DummySender()
        self.notifier = TelegramProgressNotifier(sender=self.sender, enabled=True, mock_mode=True)

    def test_mock_mode_does_not_call_sender(self):
        result = self.notifier.send_start("R025")
        self.assertTrue(result.get("mock"))
        self.assertEqual(self.sender.send_count, 0)

    def test_mock_mode_appends_to_log(self):
        self.notifier.send_start("R025")
        log = self.notifier.get_log()
        self.assertEqual(len(log), 1)
        self.assertIn("[AUTO-RUN][START] R025", log[0])


class TestMessageFormat(unittest.TestCase):
    def setUp(self):
        self.notifier = TelegramProgressNotifier(enabled=True, mock_mode=True)

    def test_start_format(self):
        self.notifier.send_start("R025")
        self.assertIn("[AUTO-RUN][START] R025", self.notifier.get_log()[0])

    def test_progress_format(self):
        self.notifier.send_progress("R025", step="construction", status="passed")
        log = self.notifier.get_log()[0]
        self.assertIn("[AUTO-RUN][PROGRESS]", log)
        self.assertIn("step=construction", log)
        self.assertIn("status=passed", log)

    def test_error_format(self):
        self.notifier.send_error("R025", error="something broke")
        log = self.notifier.get_log()[0]
        self.assertIn("[AUTO-RUN][ERROR]", log)
        self.assertIn("error=something broke", log)

    def test_complete_format(self):
        self.notifier.send_complete("R025")
        self.assertIn("[AUTO-RUN][COMPLETE] R025", self.notifier.get_log()[0])


class TestProgressSequence(unittest.TestCase):
    def setUp(self):
        self.notifier = TelegramProgressNotifier(enabled=True, mock_mode=True)

    def test_sequence(self):
        self.notifier.send_start("R025")
        self.notifier.send_progress("R025", step="build", status="ok")
        self.notifier.send_progress("R025", step="test", status="passed")
        self.notifier.send_complete("R025")
        log = self.notifier.get_log()
        self.assertEqual(len(log), 4)
        self.assertIn("START", log[0])
        self.assertIn("PROGRESS", log[1])
        self.assertIn("PROGRESS", log[2])
        self.assertIn("COMPLETE", log[3])


class TestDisabledNoOp(unittest.TestCase):
    def setUp(self):
        self.sender = DummySender()
        self.notifier = TelegramProgressNotifier(sender=self.sender, enabled=False, mock_mode=True)

    def test_disabled_send_start_no_op(self):
        result = self.notifier.send_start("R025")
        self.assertTrue(result.get("skipped"))
        self.assertEqual(len(self.notifier.get_log()), 0)

    def test_disabled_send_progress_no_op(self):
        result = self.notifier.send_progress("R025", step="x", status="y")
        self.assertTrue(result.get("skipped"))

    def test_disabled_send_error_no_op(self):
        result = self.notifier.send_error("R025", error="z")
        self.assertTrue(result.get("skipped"))

    def test_disabled_send_complete_no_op(self):
        result = self.notifier.send_complete("R025")
        self.assertTrue(result.get("skipped"))


class DummySender:
    def __init__(self):
        self.send_count = 0

    def send_message(self, text, parse_mode="Markdown"):
        self.send_count += 1
        return {"success": True, "message_id": self.send_count}


if __name__ == "__main__":
    unittest.main()
