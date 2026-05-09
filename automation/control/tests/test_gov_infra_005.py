"""
GOV-INFRA-005 runtime tests: evidence cross-file integrity validation.

Verifies:
- All 6 rules with valid consistent data → PASS
- Each rule with inconsistent data → FAIL with integrity: error code
- All existing canonical packages (FIX-BLOCKER-F-TESTS, GOV-INFRA-001/002/003/004) still pass
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from automation.control.evidence_checker import EvidenceChecker

REPO_ROOT = Path(__file__).parent.parent.parent.parent
CANDIDATES_ROOT = REPO_ROOT / "automation" / "control" / "candidates"


def _make_consistent_package(tmp_path: Path, round_id: str) -> Path:
    """Create a candidate package with all 6 files having cross-file consistent content."""
    cand_dir = tmp_path / "candidates" / round_id
    cand_dir.mkdir(parents=True, exist_ok=True)

    task_content = (
        f"=== TASK DESCRIPTION ===\n"
        f"task_id: {round_id}\n"
        f"task_type: governance_test_round\n"
        f"phase: governance\n"
        f"law_compliance: 04\n"
        f"severity: MEDIUM\n"
        f"\n=== PROBLEM STATEMENT ===\nTest\n\n=== SOLUTION ===\nTest\n\n=== FILES ===\n- test\n"
    )
    (cand_dir / "task.txt").write_text(task_content, encoding="utf-8")

    report = {
        "round_id": round_id,
        "status": "completed",
        "canonical_branch": "work/canonical-mainline-repair-001",
        "canonical_head": "e3b29539d4d7c7eed307317753eef8353812f836",
        "test_count": 10,
        "tests_passed": 10,
        "tests_failed": 0,
    }
    (cand_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    evidence = {
        "trace_id": f"{round_id.lower()}-001",
        "law_compliance": "04",
        "evidence_type": "governance_test_round",
        "round": round_id,
        "phase": "governance",
        "append_only_audit": True,
    }
    (cand_dir / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    (cand_dir / "candidate.diff").write_text("diff content\n", encoding="utf-8")
    (cand_dir / "no-aider-used.txt").write_text("NO-AIDER-USED CERTIFICATION\nAider used: NO\n", encoding="utf-8")
    (cand_dir / "test-results.txt").write_text("TEST RESULTS\n10 passed\n0 failed\n", encoding="utf-8")

    return cand_dir


class TestConsistentPackage:
    """A fully consistent package must pass all cross-file integrity rules."""

    def test_consistent_package_passes(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_consistent_package(tmp_path, "TEST-INTEGRITY")
        valid, issues = checker.validate_evidence_cross_file_integrity(cand_dir)
        assert valid is True, f"Consistent package should pass, got issues={issues}"


class TestRoundIdIdentity:
    """Rule 1: round_id must match across report.json, evidence.json, task.txt."""

    def test_round_id_mismatch_report_vs_evidence(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_consistent_package(tmp_path, "INTEGRITY-R1")
        (cand_dir / "evidence.json").write_text(
            json.dumps({"trace_id": "x", "law_compliance": "04", "evidence_type": "t",
                         "round": "DIFFERENT-ROUND", "phase": "t", "append_only_audit": True}),
            encoding="utf-8",
        )
        valid, issues = checker.validate_evidence_cross_file_integrity(cand_dir)
        assert valid is False
        assert any("integrity:round_id_mismatch" in i for i in issues)

    def test_round_id_mismatch_report_vs_task(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_consistent_package(tmp_path, "INTEGRITY-R1B")
        (cand_dir / "task.txt").write_text(
            "=== TASK DESCRIPTION ===\ntask_id: DIFFERENT-TASK\nlaw_compliance: 04\ntask_type: t\nphase: t\n",
            encoding="utf-8",
        )
        valid, issues = checker.validate_evidence_cross_file_integrity(cand_dir)
        assert valid is False
        assert any("integrity:round_id_mismatch" in i for i in issues)

    def test_all_three_mismatch(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_consistent_package(tmp_path, "INTEGRITY-R1C")
        (cand_dir / "report.json").write_text(
            json.dumps({"round_id": "R1", "status": "completed", "canonical_branch": "b",
                         "canonical_head": "a" * 40, "test_count": 1, "tests_passed": 1}),
            encoding="utf-8",
        )
        (cand_dir / "evidence.json").write_text(
            json.dumps({"trace_id": "x", "law_compliance": "04", "evidence_type": "t",
                         "round": "R2", "phase": "t", "append_only_audit": True}),
            encoding="utf-8",
        )
        (cand_dir / "task.txt").write_text(
            "=== TASK DESCRIPTION ===\ntask_id: R3\nlaw_compliance: 04\ntask_type: t\nphase: t\n",
            encoding="utf-8",
        )
        valid, issues = checker.validate_evidence_cross_file_integrity(cand_dir)
        assert valid is False
        r1_issues = [i for i in issues if "round_id_mismatch" in i]
        assert len(r1_issues) >= 1


class TestLawComplianceConsistency:
    """Rule 2: law_compliance must match across evidence.json and task.txt."""

    def test_law_compliance_mismatch(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_consistent_package(tmp_path, "INTEGRITY-R2")
        (cand_dir / "task.txt").write_text(
            "=== TASK DESCRIPTION ===\ntask_id: INTEGRITY-R2\nlaw_compliance: 99\ntask_type: t\nphase: t\n",
            encoding="utf-8",
        )
        valid, issues = checker.validate_evidence_cross_file_integrity(cand_dir)
        assert valid is False
        assert any("integrity:law_compliance_mismatch" in i for i in issues)


class TestTestCountCoherence:
    """Rule 3: test counts in report.json must be internally consistent."""

    def test_tests_passed_exceeds_count(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_consistent_package(tmp_path, "INTEGRITY-R3A")
        (cand_dir / "report.json").write_text(
            json.dumps({"round_id": "INTEGRITY-R3A", "status": "completed",
                         "canonical_branch": "b", "canonical_head": "a" * 40,
                         "test_count": 5, "tests_passed": 10, "tests_failed": 0}),
            encoding="utf-8",
        )
        valid, issues = checker.validate_evidence_cross_file_integrity(cand_dir)
        assert valid is False
        assert any("integrity:test_count_mismatch" in i for i in issues)

    def test_tests_passed_plus_failed_exceeds_count(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_consistent_package(tmp_path, "INTEGRITY-R3B")
        (cand_dir / "report.json").write_text(
            json.dumps({"round_id": "INTEGRITY-R3B", "status": "completed",
                         "canonical_branch": "b", "canonical_head": "a" * 40,
                         "test_count": 5, "tests_passed": 3, "tests_failed": 3}),
            encoding="utf-8",
        )
        valid, issues = checker.validate_evidence_cross_file_integrity(cand_dir)
        assert valid is False
        assert any("integrity:test_count_mismatch" in i for i in issues)


class TestStatusCoherence:
    """Rule 4: report.json status must be consistent with evidence.json state."""

    def test_completed_without_append_only_audit(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_consistent_package(tmp_path, "INTEGRITY-R4")
        (cand_dir / "evidence.json").write_text(
            json.dumps({"trace_id": "x", "law_compliance": "04", "evidence_type": "t",
                         "round": "INTEGRITY-R4", "phase": "t", "append_only_audit": False}),
            encoding="utf-8",
        )
        valid, issues = checker.validate_evidence_cross_file_integrity(cand_dir)
        assert valid is False
        assert any("integrity:status_contradiction" in i for i in issues)


class TestTypeCategoryCoherence:
    """Rule 5: evidence_type and task_type must share the same category prefix."""

    def test_type_category_mismatch(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_consistent_package(tmp_path, "INTEGRITY-R5")
        (cand_dir / "evidence.json").write_text(
            json.dumps({"trace_id": "x", "law_compliance": "04", "evidence_type": "bugfix_critical",
                         "round": "INTEGRITY-R5", "phase": "t", "append_only_audit": True}),
            encoding="utf-8",
        )
        valid, issues = checker.validate_evidence_cross_file_integrity(cand_dir)
        assert valid is False
        assert any("integrity:type_category_mismatch" in i for i in issues)


class TestReplayLogOrdering:
    """Rule 6: replay_log entries must be in chronological order."""

    def test_replay_log_out_of_order(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_consistent_package(tmp_path, "INTEGRITY-R6")
        (cand_dir / "evidence.json").write_text(
            json.dumps({
                "trace_id": "x",
                "law_compliance": "04",
                "evidence_type": "governance_test_round",
                "round": "INTEGRITY-R6",
                "phase": "t",
                "append_only_audit": True,
                "replay_log": [
                    "2026-05-09: step three",
                    "2026-05-08: step two",
                    "2026-05-07: step one",
                ],
            }),
            encoding="utf-8",
        )
        valid, issues = checker.validate_evidence_cross_file_integrity(cand_dir)
        assert valid is False
        assert any("integrity:replay_log_out_of_order" in i for i in issues)


class TestCanonicalExistingPackages:
    """Existing canonical packages must pass cross-file integrity checks."""

    def _check_canonical_round(self, round_id: str) -> None:
        checker = EvidenceChecker(REPO_ROOT)
        cand_dir = CANDIDATES_ROOT / round_id
        valid, issues = checker.validate_evidence_cross_file_integrity(cand_dir)
        assert valid is True, (
            f"Canonical package {round_id} should pass integrity check, "
            f"got issues={issues}"
        )

    def test_fix_blocker_f_tests_preserved(self) -> None:
        self._check_canonical_round("FIX-BLOCKER-F-TESTS")

    def test_gov_infra_001_preserved(self) -> None:
        self._check_canonical_round("GOV-INFRA-001")

    def test_gov_infra_002_preserved(self) -> None:
        self._check_canonical_round("GOV-INFRA-002")

    def test_gov_infra_003_preserved(self) -> None:
        self._check_canonical_round("GOV-INFRA-003")

    def test_gov_infra_004_preserved(self) -> None:
        self._check_canonical_round("GOV-INFRA-004")


if __name__ == "__main__":
    passed = 0
    failed = 0
    failures: List[str] = []
    tests = [
        ("test_consistent_package_passes", TestConsistentPackage().test_consistent_package_passes),
        ("test_round_id_mismatch_report_vs_evidence", TestRoundIdIdentity().test_round_id_mismatch_report_vs_evidence),
        ("test_round_id_mismatch_report_vs_task", TestRoundIdIdentity().test_round_id_mismatch_report_vs_task),
        ("test_all_three_mismatch", TestRoundIdIdentity().test_all_three_mismatch),
        ("test_law_compliance_mismatch", TestLawComplianceConsistency().test_law_compliance_mismatch),
        ("test_tests_passed_exceeds_count", TestTestCountCoherence().test_tests_passed_exceeds_count),
        ("test_tests_passed_plus_failed_exceeds_count", TestTestCountCoherence().test_tests_passed_plus_failed_exceeds_count),
        ("test_completed_without_append_only_audit", TestStatusCoherence().test_completed_without_append_only_audit),
        ("test_type_category_mismatch", TestTypeCategoryCoherence().test_type_category_mismatch),
        ("test_replay_log_out_of_order", TestReplayLogOrdering().test_replay_log_out_of_order),
        ("test_fix_blocker_f_tests_preserved", TestCanonicalExistingPackages().test_fix_blocker_f_tests_preserved),
        ("test_gov_infra_001_preserved", TestCanonicalExistingPackages().test_gov_infra_001_preserved),
        ("test_gov_infra_002_preserved", TestCanonicalExistingPackages().test_gov_infra_002_preserved),
        ("test_gov_infra_003_preserved", TestCanonicalExistingPackages().test_gov_infra_003_preserved),
        ("test_gov_infra_004_preserved", TestCanonicalExistingPackages().test_gov_infra_004_preserved),
    ]
    for name, fn in tests:
        try:
            fn()
            print(f"PASS: {name}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {name}: {e}")
            failed += 1
            failures.append(name)
    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        print(f"Failures: {failures}")
        exit(1)
