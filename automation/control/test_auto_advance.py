"""Auto-Advance Control Tests"""

import os
import unittest
import tempfile
import json
from pathlib import Path

from automation.control.auto_advance import AutoAdvanceController
from automation.control.pause_state import PauseStateManager
from automation.control.evidence_checker import EvidenceChecker
from automation.control.status_reporter import StatusReporter


class TestAutoAdvanceController(unittest.TestCase):
    def setUp(self):
        self.controller = AutoAdvanceController()
        self.controller.pause_manager.clear_pause()

    def tearDown(self):
        self.controller.pause_manager.clear_pause()

    def _make_round_result(self, **overrides):
        defaults = {
            "status": "completed",
            "formal_status_code": "manual_review_completed",
            "blockers_found": [],
            "evidence_directory": None,
            "merge_gate_encountered": False,
            "push_gate_encountered": False,
            "activation_gate_encountered": False,
            "authorization_gate_encountered": False,
        }
        defaults.update(overrides)
        return defaults

    def test_candidate_pass_auto_advance(self):
        """A: candidate pass + evidence complete + no blocker/gate -> advance"""
        result = self._make_round_result()
        can, reason, gate = self.controller.can_auto_advance(result)
        self.assertTrue(can)
        self.assertEqual(gate, "none")

    def test_evidence_incomplete_stops(self):
        """B: evidence incomplete -> stop"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create incomplete evidence (missing report.json)
            ev_dir = Path(tmpdir)
            (ev_dir / "task.txt").write_text("task")
            (ev_dir / "evidence.json").write_text("{}")
            result = self._make_round_result(evidence_directory=str(ev_dir))
            can, reason, gate = self.controller.can_auto_advance(result)
            self.assertFalse(can)
            self.assertEqual(gate, "evidence_gate")

    def test_blockers_found_stops(self):
        """C: blockers_found non-empty -> stop"""
        result = self._make_round_result(blockers_found=["env001_present"])
        can, reason, gate = self.controller.can_auto_advance(result)
        self.assertFalse(can)
        self.assertEqual(gate, "blocker_gate")

    def test_pause_stops(self):
        """D: /pause received before next dispatch -> stop"""
        self.controller.pause_manager.set_pause("telegram_pause")
        result = self._make_round_result()
        can, reason, gate = self.controller.can_auto_advance(result)
        self.assertFalse(can)
        self.assertEqual(gate, "pause_gate")
        self.controller.pause_manager.clear_pause()

    def test_merge_gate_stops(self):
        """E: merge gate encountered -> stop"""
        result = self._make_round_result(merge_gate_encountered=True)
        can, reason, gate = self.controller.can_auto_advance(result)
        self.assertFalse(can)
        self.assertEqual(gate, "merge_gate")

    def test_push_gate_stops(self):
        result = self._make_round_result(push_gate_encountered=True)
        can, reason, gate = self.controller.can_auto_advance(result)
        self.assertFalse(can)
        self.assertEqual(gate, "push_gate")

    def test_activation_gate_stops(self):
        result = self._make_round_result(activation_gate_encountered=True)
        can, reason, gate = self.controller.can_auto_advance(result)
        self.assertFalse(can)
        self.assertEqual(gate, "activation_gate")

    def test_authorization_gate_stops(self):
        result = self._make_round_result(authorization_gate_encountered=True)
        can, reason, gate = self.controller.can_auto_advance(result)
        self.assertFalse(can)
        self.assertEqual(gate, "authorization_gate")

    def test_status_not_completed_stops(self):
        result = self._make_round_result(status="failed")
        can, reason, gate = self.controller.can_auto_advance(result)
        self.assertFalse(can)
        self.assertEqual(gate, "round_status_gate")

    def test_blocked_formal_status_stops(self):
        result = self._make_round_result(formal_status_code="blocked")
        can, reason, gate = self.controller.can_auto_advance(result)
        self.assertFalse(can)
        self.assertEqual(gate, "review_gate")

    def test_candidate_ready_awaiting_manual_review_stops(self):
        result = self._make_round_result(formal_status_code="candidate_ready_awaiting_manual_review")
        can, reason, gate = self.controller.can_auto_advance(result)
        self.assertFalse(can)
        self.assertEqual(gate, "review_gate")

    def test_complete_evidence_allows_advance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ev_dir = Path(tmpdir)
            (ev_dir / "task.txt").write_text("task")
            report = {"status": "completed", "formal_status_code": "manual_review_completed"}
            (ev_dir / "report.json").write_text(json.dumps(report))
            evidence = {"test_results": {"total_tests": 5, "passed": 5, "failed": 0}}
            (ev_dir / "evidence.json").write_text(json.dumps(evidence))
            result = self._make_round_result(evidence_directory=str(ev_dir))
            can, reason, gate = self.controller.can_auto_advance(result)
            self.assertTrue(can)
            self.assertEqual(gate, "none")


class TestPauseStateManager(unittest.TestCase):
    def setUp(self):
        self.manager = PauseStateManager()
        self.manager.clear_pause()

    def tearDown(self):
        self.manager.clear_pause()

    def test_is_paused_false(self):
        self.assertFalse(self.manager.is_paused())

    def test_set_and_clear_pause(self):
        self.manager.set_pause("test_pause")
        self.assertTrue(self.manager.is_paused())
        info = self.manager.get_pause_info()
        self.assertIsNotNone(info)
        self.assertEqual(info.get("reason"), "test_pause")
        self.manager.clear_pause()
        self.assertFalse(self.manager.is_paused())


class TestEvidenceChecker(unittest.TestCase):
    def setUp(self):
        self.checker = EvidenceChecker()

    def test_missing_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            complete, missing = self.checker.check_completeness(Path(tmpdir))
            self.assertFalse(complete)
            self.assertTrue(any("missing:task.txt" in m for m in missing))

    def test_complete_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ev_dir = Path(tmpdir)
            (ev_dir / "task.txt").write_text("task")
            report = {"status": "completed", "formal_status_code": "manual_review_completed"}
            (ev_dir / "report.json").write_text(json.dumps(report))
            evidence = {"test_results": {"total_tests": 3, "passed": 3, "failed": 0}}
            (ev_dir / "evidence.json").write_text(json.dumps(evidence))
            complete, missing = self.checker.check_completeness(ev_dir)
            self.assertTrue(complete)
            self.assertEqual(len(missing), 0)


class TestStatusReporter(unittest.TestCase):
    def setUp(self):
        self.reporter = StatusReporter()

    def test_generate_summary(self):
        state = {
            "current_round": "R017",
            "next_round": "R018",
            "auto_advanced": False,
            "stop_reason": "env001_present",
            "stop_gate_type": "blocker_gate",
            "evidence_complete": True,
            "candidate_branch": "work/r017-candidate",
            "candidate_commit": "abc123",
            "awaiting_review": False,
            "lane_frozen": False,
        }
        summary = self.reporter.generate_summary(state)
        self.assertEqual(summary["current_round"], "R017")
        self.assertEqual(summary["next_round"], "R018")
        self.assertFalse(summary["auto_advanced_true_or_false"])
        self.assertEqual(summary["stop_reason"], "env001_present")
        self.assertEqual(summary["stop_gate_type"], "blocker_gate")
        self.assertTrue(summary["evidence_complete_true_or_false"])
        self.assertEqual(summary["candidate_branch"], "work/r017-candidate")
        self.assertEqual(summary["candidate_commit"], "abc123")
        self.assertFalse(summary["awaiting_review_true_or_false"])

    def test_format_for_telegram(self):
        state = {
            "current_round": "R017",
            "next_round": "R018",
            "auto_advanced": False,
            "stop_reason": "env001_present",
            "stop_gate_type": "blocker_gate",
            "evidence_complete": True,
            "candidate_branch": "work/r017-candidate",
            "candidate_commit": "abc123",
            "awaiting_review": False,
            "lane_frozen": False,
        }
        summary = self.reporter.generate_summary(state)
        text = self.reporter.format_for_telegram(summary)
        self.assertIn("R017", text)
        self.assertIn("env001_present", text)
        self.assertIn("blocker_gate", text)


if __name__ == "__main__":
    unittest.main()
