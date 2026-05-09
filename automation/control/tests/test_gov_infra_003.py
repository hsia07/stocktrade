"""
GOV-INFRA-003 runtime tests: 6/6 evidence package completeness enforcement.

Verifies:
- Complete 6/6 package → PASS
- Missing each of the 6 required files individually → FAIL
- All existing canonical packages (FIX-BLOCKER-F-TESTS, GOV-INFRA-001, GOV-INFRA-002) still pass
"""

from __future__ import annotations

import json
from pathlib import Path

from automation.control.evidence_checker import EvidenceChecker

REPO_ROOT = Path(__file__).parent.parent.parent.parent
CANDIDATES_ROOT = REPO_ROOT / "automation" / "control" / "candidates"

REQUIRED_SIX = [
    "task.txt",
    "report.json",
    "evidence.json",
    "candidate.diff",
    "no-aider-used.txt",
    "test-results.txt",
]


def _make_complete_6of6_package(tmp_path: Path, round_id: str) -> Path:
    """Create a complete 6/6 candidate evidence package in tmp_path."""
    cand_dir = tmp_path / "candidates" / round_id
    cand_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "round_id": round_id,
        "status": "completed",
        "canonical_branch": "work/canonical-mainline-repair-001",
    }
    (cand_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    evidence = {
        "trace_id": f"{round_id.lower()}-001",
        "law_compliance": "04",
        "phase": "governance",
        "round": round_id,
    }
    (cand_dir / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    (cand_dir / "task.txt").write_text(f"=== {round_id} ===\n", encoding="utf-8")
    (cand_dir / "candidate.diff").write_text("diff content\n", encoding="utf-8")
    (cand_dir / "no-aider-used.txt").write_text("NO-AIDER-USED\n", encoding="utf-8")
    (cand_dir / "test-results.txt").write_text("All tests passed\n", encoding="utf-8")

    return cand_dir


def _make_package_missing_file(tmp_path: Path, round_id: str, skip_file: str) -> Path:
    """Create a candidate package with one required file missing."""
    cand_dir = _make_complete_6of6_package(tmp_path, round_id)
    file_path = cand_dir / skip_file
    if file_path.exists():
        file_path.unlink()
    return cand_dir


class TestComplete6of6Package:
    """A complete 6/6 evidence package must pass."""

    def test_all_6_files_present_passes(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_complete_6of6_package(tmp_path, "TEST-6OF6")
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is True, f"6/6 package should pass, got missing={missing}"


class TestMissingFileBlocked:
    """Missing any of the 6 required files must fail."""

    def test_missing_task_txt_blocked(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_package_missing_file(tmp_path, "MISSING-TASK", "task.txt")
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is False
        assert any("missing:task.txt" in m for m in missing)

    def test_missing_report_json_blocked(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_package_missing_file(tmp_path, "MISSING-REPORT", "report.json")
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is False
        assert any("missing:report.json" in m for m in missing)

    def test_missing_evidence_json_blocked(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_package_missing_file(tmp_path, "MISSING-EVIDENCE", "evidence.json")
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is False
        assert any("missing:evidence.json" in m for m in missing)

    def test_missing_candidate_diff_blocked(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_package_missing_file(tmp_path, "MISSING-DIFF", "candidate.diff")
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is False
        assert any("missing:candidate.diff" in m for m in missing)

    def test_missing_no_aider_blocked(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_package_missing_file(tmp_path, "MISSING-AIDER", "no-aider-used.txt")
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is False
        assert any("missing:no-aider-used.txt" in m for m in missing)

    def test_missing_test_results_blocked(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_package_missing_file(tmp_path, "MISSING-TESTRES", "test-results.txt")
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is False
        assert any("missing:test-results.txt" in m for m in missing)


class TestCanonicalExistingPackages:
    """Existing canonical packages must still pass with 6/6 rule."""

    def _check_canonical_round(self, round_id: str) -> None:
        checker = EvidenceChecker(REPO_ROOT)
        cand_dir = CANDIDATES_ROOT / round_id
        complete, missing = checker.check_completeness(cand_dir)
        assert complete is True, (
            f"Canonical package {round_id} should pass 6/6 check, "
            f"got missing={missing}"
        )

    def test_fix_blocker_f_tests_preserved(self) -> None:
        self._check_canonical_round("FIX-BLOCKER-F-TESTS")

    def test_gov_infra_001_preserved(self) -> None:
        self._check_canonical_round("GOV-INFRA-001")

    def test_gov_infra_002_preserved(self) -> None:
        self._check_canonical_round("GOV-INFRA-002")


class TestRequiredFilesConstant:
    """REQUIRED_FILES must contain exactly the 6 standard files."""

    def test_required_files_has_all_6(self) -> None:
        checker = EvidenceChecker()
        expected = set(REQUIRED_SIX)
        actual = set(checker.REQUIRED_FILES)
        missing_files = expected - actual
        extra_files = actual - expected
        assert not missing_files, f"REQUIRED_FILES missing: {missing_files}"
        assert not extra_files, f"REQUIRED_FILES has extras: {extra_files}"
        assert len(checker.REQUIRED_FILES) == 6, (
            f"Expected exactly 6 required files, got {len(checker.REQUIRED_FILES)}"
        )


if __name__ == "__main__":
    passed = 0
    failed = 0
    failures = []
    tests = [
        ("test_all_6_files_present_passes", TestComplete6of6Package().test_all_6_files_present_passes),
        ("test_missing_task_txt_blocked", TestMissingFileBlocked().test_missing_task_txt_blocked),
        ("test_missing_report_json_blocked", TestMissingFileBlocked().test_missing_report_json_blocked),
        ("test_missing_evidence_json_blocked", TestMissingFileBlocked().test_missing_evidence_json_blocked),
        ("test_missing_candidate_diff_blocked", TestMissingFileBlocked().test_missing_candidate_diff_blocked),
        ("test_missing_no_aider_blocked", TestMissingFileBlocked().test_missing_no_aider_blocked),
        ("test_missing_test_results_blocked", TestMissingFileBlocked().test_missing_test_results_blocked),
        ("test_fix_blocker_f_tests_preserved", TestCanonicalExistingPackages().test_fix_blocker_f_tests_preserved),
        ("test_gov_infra_001_preserved", TestCanonicalExistingPackages().test_gov_infra_001_preserved),
        ("test_gov_infra_002_preserved", TestCanonicalExistingPackages().test_gov_infra_002_preserved),
        ("test_required_files_has_all_6", TestRequiredFilesConstant().test_required_files_has_all_6),
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
