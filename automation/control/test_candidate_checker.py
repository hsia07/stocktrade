"""
Anti-Regression Tests: Candidate Checker Hardening

Tests that validate:
- Stale evidence directories are NOT counted as valid candidates
- Evidence must contain candidate_commit OR materialized_candidate=true
- Execution log evidence types are rejected
- Stale archives in candidates_stale/ do not interfere with dispatch
"""

import json
import unittest
import tempfile
from pathlib import Path

from automation.control.candidate_checker import CandidateChecker


class TestCandidateCheckerHardening(unittest.TestCase):
    """Prevent stale evidence from being mistaken for materialized candidates."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.candidates_dir = self.tmpdir / "automation" / "control" / "candidates"
        self.candidates_dir.mkdir(parents=True)
        self.stale_dir = self.tmpdir / "automation" / "control" / "candidates_stale"
        self.stale_dir.mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_candidate_dir(self, name: str, evidence: dict, base_dir: Path = None):
        """Create a candidate directory with evidence.json and task.txt."""
        base = base_dir or self.candidates_dir
        d = base / name
        d.mkdir(parents=True, exist_ok=True)
        with (d / "evidence.json").open("w", encoding="utf-8") as f:
            json.dump(evidence, f)
        with (d / "task.txt").open("w", encoding="utf-8") as f:
            f.write("task description\n")
        return d

    def test_stale_evidence_without_materialization_proof_rejected(self):
        """
        Evidence directory matching round ID but without candidate_commit
        or materialized_candidate=true must be rejected.
        """
        self._create_candidate_dir(
            "PHASE2-API-AUTOMODE-R020-DISPATCH-EXECUTION",
            {"evidence_type": "r020_dispatch_execution", "round_id": "R020"},
        )
        checker = CandidateChecker(self.tmpdir)
        result = checker.check_candidate_exists("R020")
        self.assertFalse(result["exists"])
        self.assertIsNone(result["candidate_dir"])

    def test_evidence_with_candidate_commit_accepted(self):
        """
        Evidence containing candidate_commit must be accepted as valid candidate.
        """
        self._create_candidate_dir(
            "PHASE2-API-AUTOMODE-R020-FEATURE-X",
            {
                "evidence_type": "feature_candidate",
                "round_id": "R020",
                "candidate_commit": "abc123def456",
                "candidate_branch": "work/candidate-r020-feature-x",
            },
        )
        checker = CandidateChecker(self.tmpdir)
        result = checker.check_candidate_exists("R020")
        self.assertTrue(result["exists"])
        self.assertIsNotNone(result["candidate_dir"])
        self.assertIsNotNone(result["evidence_json"])
        self.assertIsNotNone(result["task_txt"])

    def test_evidence_with_materialized_flag_accepted(self):
        """
        Evidence with materialized_candidate=true must be accepted.
        """
        self._create_candidate_dir(
            "PHASE2-API-AUTOMODE-R020-FEATURE-Y",
            {
                "evidence_type": "feature_candidate",
                "round_id": "R020",
                "materialized_candidate": True,
            },
        )
        checker = CandidateChecker(self.tmpdir)
        result = checker.check_candidate_exists("R020")
        self.assertTrue(result["exists"])

    def test_execution_log_evidence_rejected(self):
        """
        Evidence types that are execution logs (e.g., r020_dispatch_execution)
        must never count as candidates regardless of other fields.
        """
        self._create_candidate_dir(
            "PHASE2-API-AUTOMODE-R020-BOOTSTRAP",
            {
                "evidence_type": "r020_dispatch_execution",
                "round_id": "R020",
                "candidate_commit": "abc123",  # Even with commit, type rules it out
            },
        )
        checker = CandidateChecker(self.tmpdir)
        result = checker.check_candidate_exists("R020")
        self.assertFalse(result["exists"])

    def test_stale_archives_do_not_interfere_with_dispatch(self):
        """
        Stale candidate directories in candidates_stale/ must not be scanned
        and must not interfere with dispatch.
        """
        # Put stale evidence in candidates_stale/
        self._create_candidate_dir(
            "PHASE2-API-AUTOMODE-R020-OLD-DISPATCH",
            {"evidence_type": "r020_dispatch_execution", "round_id": "R020"},
            base_dir=self.stale_dir,
        )
        # Also put a valid candidate in candidates/
        self._create_candidate_dir(
            "PHASE2-API-AUTOMODE-R020-VALID",
            {
                "evidence_type": "feature_candidate",
                "round_id": "R020",
                "materialized_candidate": True,
            },
        )
        checker = CandidateChecker(self.tmpdir)
        result = checker.check_candidate_exists("R020")
        # Should find the valid one, not the stale one
        self.assertTrue(result["exists"])
        self.assertIn("VALID", result["candidate_dir"])

    def test_no_candidate_when_only_stale_in_active_dir(self):
        """
        If candidates/ contains only stale evidence (no materialization proof),
        check_candidate_exists must return False, allowing construction bootstrap.
        """
        self._create_candidate_dir(
            "PHASE2-API-AUTOMODE-R020-BOOTSTRAP-OLD",
            {"evidence_type": "bootstrap_continuation", "round_id": "R020"},
        )
        checker = CandidateChecker(self.tmpdir)
        result = checker.check_candidate_exists("R020")
        self.assertFalse(result["exists"])

    def test_evidence_without_task_txt_rejected(self):
        """
        A directory with evidence.json but no task.txt must be rejected.
        """
        d = self.candidates_dir / "PHASE2-API-AUTOMODE-R020-INCOMPLETE"
        d.mkdir(parents=True)
        with (d / "evidence.json").open("w", encoding="utf-8") as f:
            json.dump({
                "evidence_type": "feature_candidate",
                "round_id": "R020",
                "materialized_candidate": True,
            }, f)
        # intentionally omit task.txt
        checker = CandidateChecker(self.tmpdir)
        result = checker.check_candidate_exists("R020")
        self.assertFalse(result["exists"])


if __name__ == "__main__":
    unittest.main()
