"""
GOV-INFRA-004 runtime tests: evidence content schema validation.

Verifies:
- All 6 files with valid content → PASS
- Each schema violation (missing section, missing key, wrong type,
  wrong value, empty file, missing content) → FAIL with specific error code
- All existing canonical packages (FIX-BLOCKER-F-TESTS, GOV-INFRA-001,
  GOV-INFRA-002, GOV-INFRA-003) still pass
- CONTENT_SCHEMA constant has all 6 files defined
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from automation.control.evidence_checker import EvidenceChecker

REPO_ROOT = Path(__file__).parent.parent.parent.parent
CANDIDATES_ROOT = REPO_ROOT / "automation" / "control" / "candidates"

SCHEMA_FILE_KEYS = {
    "task.txt",
    "report.json",
    "evidence.json",
    "candidate.diff",
    "no-aider-used.txt",
    "test-results.txt",
}


def _make_valid_package(tmp_path: Path, round_id: str) -> Path:
    """Create a candidate package with all 6 files having valid content."""
    cand_dir = tmp_path / "candidates" / round_id
    cand_dir.mkdir(parents=True, exist_ok=True)

    task_content = (
        f"=== TASK DESCRIPTION ===\n"
        f"task_id: {round_id}\n"
        f"task_type: governance_infrastructure_hardening\n"
        f"phase: governance_infrastructure\n"
        f"law_compliance: 04\n"
        f"severity: MEDIUM\n"
        f"\n"
        f"=== PROBLEM STATEMENT ===\n"
        f"Test problem statement.\n"
        f"\n"
        f"=== SOLUTION ===\n"
        f"Test solution.\n"
        f"\n"
        f"=== FILES ===\n"
        f"- test file\n"
    )
    (cand_dir / "task.txt").write_text(task_content, encoding="utf-8")

    report = {
        "round_id": round_id,
        "status": "completed",
        "canonical_branch": "work/canonical-mainline-repair-001",
        "canonical_head": "8727f2399b4b74d9a4d06fd3fe95d677027531a5",
        "test_count": 12,
        "tests_passed": 12,
    }
    (cand_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    evidence = {
        "trace_id": f"{round_id.lower()}-001",
        "law_compliance": "04",
        "evidence_type": "governance_infrastructure_hardening",
        "round": round_id,
        "phase": "governance_infrastructure",
        "append_only_audit": True,
    }
    (cand_dir / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    (cand_dir / "candidate.diff").write_text("diff --git a/file b/file\nindex abc..def 100644\n--- a/file\n+++ b/file\n@@ -1 +1 @@\n-old\n+new\n", encoding="utf-8")
    (cand_dir / "no-aider-used.txt").write_text("NO-AIDER-USED CERTIFICATION\nAider used: NO\nThis round used no aider.\n", encoding="utf-8")
    (cand_dir / "test-results.txt").write_text(f"{round_id} TEST RESULTS\n12 passed\n0 failed\n", encoding="utf-8")

    return cand_dir


class TestValidContentPackage:
    """A package with all 6 files having valid content must pass schema check."""

    def test_all_files_valid_passes(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_valid_package(tmp_path, "TEST-SCHEMA-VALID")
        valid, issues = checker.validate_evidence_content_schema(cand_dir)
        assert valid is True, f"Valid package should pass, got issues={issues}"


class TestTaskTxtSchema:
    """task.txt content schema violations."""

    def test_missing_task_description_section(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_valid_package(tmp_path, "MISSING-SECTION")
        (cand_dir / "task.txt").write_text("garbage content\n", encoding="utf-8")
        valid, issues = checker.validate_evidence_content_schema(cand_dir)
        assert valid is False
        assert any("missing_section" in i for i in issues)


class TestReportJsonSchema:
    """report.json content schema violations."""

    def test_missing_required_key(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_valid_package(tmp_path, "MISSING-KEY")
        (cand_dir / "report.json").write_text(json.dumps({"round_id": "x"}), encoding="utf-8")
        valid, issues = checker.validate_evidence_content_schema(cand_dir)
        assert valid is False
        assert any("missing_key" in i for i in issues)

    def test_wrong_field_type(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_valid_package(tmp_path, "WRONG-TYPE")
        (cand_dir / "report.json").write_text(
            json.dumps({
                "round_id": "x",
                "status": "completed",
                "canonical_branch": "b",
                "canonical_head": "a" * 40,
                "test_count": "not_an_int",
                "tests_passed": 1,
            }),
            encoding="utf-8",
        )
        valid, issues = checker.validate_evidence_content_schema(cand_dir)
        assert valid is False
        assert any("wrong_type" in i for i in issues)


class TestEvidenceJsonSchema:
    """evidence.json content schema violations."""

    def test_wrong_law_compliance_value(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_valid_package(tmp_path, "WRONG-LAW")
        (cand_dir / "evidence.json").write_text(
            json.dumps({
                "trace_id": "x",
                "law_compliance": "99",
                "evidence_type": "t",
                "round": "T",
                "phase": "t",
                "append_only_audit": True,
            }),
            encoding="utf-8",
        )
        valid, issues = checker.validate_evidence_content_schema(cand_dir)
        assert valid is False
        assert any("wrong_value" in i and "law_compliance" in i for i in issues)


class TestCandidateDiffSchema:
    """candidate.diff content schema violations."""

    def test_empty_diff_fails(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_valid_package(tmp_path, "EMPTY-DIFF")
        (cand_dir / "candidate.diff").write_text("", encoding="utf-8")
        valid, issues = checker.validate_evidence_content_schema(cand_dir)
        assert valid is False
        assert any("empty" in i for i in issues)


class TestNoAiderUsedSchema:
    """no-aider-used.txt content schema violations."""

    def test_missing_certification_header(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_valid_package(tmp_path, "NO-CERT")
        (cand_dir / "no-aider-used.txt").write_text("random content\n", encoding="utf-8")
        valid, issues = checker.validate_evidence_content_schema(cand_dir)
        assert valid is False
        assert any("missing_pattern" in i for i in issues)


class TestTestResultsSchema:
    """test-results.txt content schema violations."""

    def test_missing_test_results_header(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_valid_package(tmp_path, "NO-HEADER")
        (cand_dir / "test-results.txt").write_text("some log output\n", encoding="utf-8")
        valid, issues = checker.validate_evidence_content_schema(cand_dir)
        assert valid is False
        assert any("missing_content" in i for i in issues)

    def test_missing_passed_failed_counts(self, tmp_path: Path) -> None:
        checker = EvidenceChecker(tmp_path)
        cand_dir = _make_valid_package(tmp_path, "NO-COUNTS")
        (cand_dir / "test-results.txt").write_text("TEST RESULTS\nno counts here\n", encoding="utf-8")
        valid, issues = checker.validate_evidence_content_schema(cand_dir)
        assert valid is False
        assert any("missing_content:passed" in i or "missing_content:failed" in i for i in issues)


class TestCanonicalExistingPackages:
    """Existing canonical packages must still pass content schema check."""

    def _check_canonical_round(self, round_id: str) -> None:
        checker = EvidenceChecker(REPO_ROOT)
        cand_dir = CANDIDATES_ROOT / round_id
        valid, issues = checker.validate_evidence_content_schema(cand_dir)
        assert valid is True, (
            f"Canonical package {round_id} should pass schema check, "
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


class TestContentSchemaConstant:
    """CONTENT_SCHEMA must define all 6 files and not be accidentally trimmed."""

    def test_schema_has_all_6_files(self) -> None:
        checker = EvidenceChecker()
        schema_keys = set(checker.CONTENT_SCHEMA.keys())
        expected = SCHEMA_FILE_KEYS
        missing_files = expected - schema_keys
        extra_files = schema_keys - expected
        assert not missing_files, f"CONTENT_SCHEMA missing: {missing_files}"
        assert not extra_files, f"CONTENT_SCHEMA has extras: {extra_files}"
        assert len(checker.CONTENT_SCHEMA) == 6, (
            f"Expected exactly 6 schema entries, got {len(checker.CONTENT_SCHEMA)}"
        )


if __name__ == "__main__":
    passed = 0
    failed = 0
    failures: List[str] = []
    tests = [
        ("test_all_files_valid_passes", TestValidContentPackage().test_all_files_valid_passes),
        ("test_missing_task_description_section", TestTaskTxtSchema().test_missing_task_description_section),
        ("test_missing_required_key", TestReportJsonSchema().test_missing_required_key),
        ("test_wrong_field_type", TestReportJsonSchema().test_wrong_field_type),
        ("test_wrong_law_compliance_value", TestEvidenceJsonSchema().test_wrong_law_compliance_value),
        ("test_empty_diff_fails", TestCandidateDiffSchema().test_empty_diff_fails),
        ("test_missing_certification_header", TestNoAiderUsedSchema().test_missing_certification_header),
        ("test_missing_test_results_header", TestTestResultsSchema().test_missing_test_results_header),
        ("test_missing_passed_failed_counts", TestTestResultsSchema().test_missing_passed_failed_counts),
        ("test_fix_blocker_f_tests_preserved", TestCanonicalExistingPackages().test_fix_blocker_f_tests_preserved),
        ("test_gov_infra_001_preserved", TestCanonicalExistingPackages().test_gov_infra_001_preserved),
        ("test_gov_infra_002_preserved", TestCanonicalExistingPackages().test_gov_infra_002_preserved),
        ("test_gov_infra_003_preserved", TestCanonicalExistingPackages().test_gov_infra_003_preserved),
        ("test_schema_has_all_6_files", TestContentSchemaConstant().test_schema_has_all_6_files),
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
