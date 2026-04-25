"""
Anti-Regression Tests: Pause Return Report Generation

Tests that validate:
- /pause generates full RETURN_TO_CHATGPT formal body
- Pause report is written to output channel file
- Pause report contains all required structured fields
"""

import unittest
import tempfile
from pathlib import Path
import yaml

from automation.control.return_report import ReturnReportGenerator
from automation.control.pause_state import PauseStateManager


class TestPauseReturnReport(unittest.TestCase):
    """Prevent regression: pause must generate full formal RETURN_TO_CHATGPT."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.manifest_path = self.tmpdir / "manifests" / "current_round.yaml"
        self.manifest_path.parent.mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_manifest(self, data):
        with self.manifest_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

    def test_pause_generates_full_return_to_chatgpt(self):
        """
        generate_pause_report must produce a full RETURN_TO_CHATGPT body
        with round_id, status, formal_status_code, current_round, etc.
        """
        state = {
            "current_round": "R020",
            "last_completed_round": "R019",
            "next_round": "R020",
            "auto_run": True,
            "chain_status": "running",
            "stop_reason": "pause_flag_active",
            "stop_gate_type": "pause_gate",
        }
        generator = ReturnReportGenerator(self.tmpdir)
        report = generator.generate_pause_report(state, pause_reason="test_pause")

        self.assertIn("# RETURN_TO_CHATGPT", report)
        self.assertIn("### round_id", report)
        self.assertIn('"R020"', report)
        self.assertIn("### status", report)
        self.assertIn("paused", report)
        self.assertIn("### formal_status_code", report)
        self.assertIn("### pause_timestamp", report)
        self.assertIn("### current_round", report)
        self.assertIn("### next_round_to_dispatch", report)

    def test_pause_writes_full_formal_body_to_opencode_output_channel(self):
        """
        write_report must write the report to LATEST_PAUSE_RETURN_TO_CHATGPT.txt
        so OpenCode can read it from the output channel.
        """
        state = {
            "current_round": "R020",
            "last_completed_round": "R019",
            "next_round": "R020",
            "auto_run": True,
            "chain_status": "running",
            "stop_reason": "pause_flag_active",
            "stop_gate_type": "pause_gate",
        }
        generator = ReturnReportGenerator(self.tmpdir)
        report = generator.generate_pause_report(state)
        out_path = generator.write_report(report, filename="LATEST_PAUSE_RETURN_TO_CHATGPT.txt")

        self.assertTrue(out_path.exists())
        content = out_path.read_text(encoding="utf-8")
        self.assertIn("# RETURN_TO_CHATGPT", content)
        self.assertIn("R020", content)

    def test_pause_state_manager_generates_and_writes_report(self):
        """
        PauseStateManager.generate_pause_report must use ReturnReportGenerator
        and write to the canonical output file.
        """
        manifest = {
            "current_round": "R020",
            "last_completed_round": "R019",
            "next_round_to_dispatch": "R020",
            "auto_run": True,
            "chain_status": "running",
        }
        self._write_manifest(manifest)

        pause_mgr = PauseStateManager(self.tmpdir)
        report = pause_mgr.generate_pause_report()

        self.assertIn("# RETURN_TO_CHATGPT", report)
        out_path = self.tmpdir / "automation" / "control" / "LATEST_PAUSE_RETURN_TO_CHATGPT.txt"
        self.assertTrue(out_path.exists())


if __name__ == "__main__":
    unittest.main()
