"""
GOV-INFRA-006 runtime tests: evidence gate orchestrator.

Verifies:
- All 3 gates pass -> verdict=PASS
- Completeness fail -> schema+integrity skipped
- Schema fail -> integrity skipped
- Integrity fail -> BLOCKED at integrity
- Gate report JSON with all required fields
- per_check_results round mapping correct
- Existing canonical rounds (GOV-INFRA-001/002/003/004/005) still pass
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from automation.control.evidence_checker import EvidenceChecker
from automation.control.evidence_gate_orchestrator import (
    EvidenceGateOrchestrator,
    GATE_ROUND_MAPPING,
)

REPO_ROOT = Path(__file__).parent.parent.parent.parent
CANDIDATES_ROOT = REPO_ROOT / "automation" / "control" / "candidates"

GOV_INFRA_ROUNDS = [
    "GOV-INFRA-001",
    "GOV-INFRA-002",
    "GOV-INFRA-003",
    "GOV-INFRA-004",
    "GOV-INFRA-005",
]


@pytest.fixture
def orchestrator() -> EvidenceGateOrchestrator:
    return EvidenceGateOrchestrator(repo_root=REPO_ROOT)


def _make_consistent_package(tmp_path: Path, round_id: str) -> Path:
    """Create a package that passes all 3 gates."""
    cand_dir = tmp_path / "candidates" / round_id
    cand_dir.mkdir(parents=True, exist_ok=True)

    task_content = (
        "=== TASK DESCRIPTION ===\n"
        f"task_id: {round_id}\n"
        "task_type: governance_test_round\n"
        "phase: governance\n"
        "law_compliance: 04\n"
        "severity: MEDIUM\n"
        "\n=== PROBLEM STATEMENT ===\nTest\n\n=== SOLUTION ===\nTest\n\n=== FILES ===\n- test\n"
    )
    (cand_dir / "task.txt").write_text(task_content, encoding="utf-8")

    report = {
        "round_id": round_id,
        "status": "completed",
        "canonical_branch": "work/canonical-mainline-repair-001",
        "canonical_head": "2308f89d3a259957012add4cf2280f14ef378009",
        "test_count": 10,
        "tests_passed": 10,
        "tests_failed": 0,
    }
    (cand_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    evidence = {
        "round": round_id,
        "evidence_type": "governance_test_round",
        "law_compliance": "04",
        "law_compliance_authority": "Law 04 Article 261",
        "phase": "governance",
        "append_only_audit": True,
        "trace_id": f"trace_{round_id.lower()}",
        "replay_log": ["2026-05-09T10:00: test init"],
        "test_results": {"passed": 10, "failed": 0},
    }
    (cand_dir / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    (cand_dir / "candidate.diff").write_text(
        "diff --git a/test.py b/test.py\nnew file mode 100644\n", encoding="utf-8"
    )
    (cand_dir / "no-aider-used.txt").write_text(
        "NO-AIDER-USED CERTIFICATION\n"
        "Aider used: NO\n"
        f"Round: {round_id}\n",
        encoding="utf-8",
    )
    (cand_dir / "test-results.txt").write_text(
        "TEST RESULTS\ntests_passed: 10\ntests_failed: 0\nall passed\n", encoding="utf-8"
    )

    return cand_dir


def _make_completeness_fail_package(tmp_path: Path, round_id: str) -> Path:
    """Create a package that fails completeness (missing required files)."""
    cand_dir = tmp_path / "candidates" / round_id
    cand_dir.mkdir(parents=True, exist_ok=True)
    (cand_dir / "task.txt").write_text("incomplete", encoding="utf-8")
    (cand_dir / "evidence.json").write_text(
        json.dumps({"law_compliance": "04", "test_results": {"passed": 1, "failed": 0}}),
        encoding="utf-8",
    )
    return cand_dir


def _make_schema_fail_package(tmp_path: Path, round_id: str) -> Path:
    """Create a package that passes completeness but fails schema validation."""
    cand_dir = _make_consistent_package(tmp_path, round_id)
    evidence_path = cand_dir / "evidence.json"
    ev = json.loads(evidence_path.read_text(encoding="utf-8"))
    ev["trace_id"] = ["not_a_string"]
    evidence_path.write_text(json.dumps(ev, indent=2), encoding="utf-8")
    return cand_dir


def _make_integrity_fail_package(tmp_path: Path, round_id: str) -> Path:
    """Create a package that passes completeness+schema but fails integrity."""
    cand_dir = _make_consistent_package(tmp_path, round_id)
    report_path = cand_dir / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["round_id"] = "OTHER-ROUND"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return cand_dir


class TestAllGatesPass:
    def test_consistent_package_returns_pass(self, tmp_path: Path, orchestrator: EvidenceGateOrchestrator):
        cand_dir = _make_consistent_package(tmp_path, "TEST-PASS-ALL")
        report = orchestrator.run_evidence_gate(cand_dir)
        assert report["verdict"] == "PASS", f"Expected PASS, got {report['verdict']}"
        assert report["blocked_at_gate"] is None
        assert len(report["per_check_results"]) == 3
        for r in report["per_check_results"]:
            assert r["status"] == "passed", f"Gate {r['gate']} should be passed: {r}"

    def test_gate_report_contains_all_required_fields(self, tmp_path: Path, orchestrator: EvidenceGateOrchestrator):
        cand_dir = _make_consistent_package(tmp_path, "TEST-FIELDS")
        report = orchestrator.run_evidence_gate(cand_dir)
        for field in ["report_type", "round_id", "candidate_dir", "timestamp", "verdict", "blocked_at_gate", "per_check_results"]:
            assert field in report, f"Missing field: {field}"
        for r in report["per_check_results"]:
            for field in ["gate", "gov_infra_rounds", "status", "errors", "error_codes"]:
                assert field in r, f"Missing per_check_results field: {field}"


class TestCompletenessFailFast:
    def test_completeness_fail_skips_schema_and_integrity(self, tmp_path: Path, orchestrator: EvidenceGateOrchestrator):
        cand_dir = _make_completeness_fail_package(tmp_path, "TEST-COMP-FAIL")
        report = orchestrator.run_evidence_gate(cand_dir)
        assert report["verdict"] == "BLOCKED", f"Expected BLOCKED, got {report['verdict']}"
        assert report["blocked_at_gate"] == "completeness"
        results = report["per_check_results"]
        assert results[0]["gate"] == "completeness"
        assert results[0]["status"] == "failed"
        assert results[1]["gate"] == "schema"
        assert results[1]["status"] == "skipped"
        assert results[2]["gate"] == "integrity"
        assert results[2]["status"] == "skipped"


class TestSchemaFailFast:
    def test_schema_fail_skips_integrity(self, tmp_path: Path, orchestrator: EvidenceGateOrchestrator):
        cand_dir = _make_schema_fail_package(tmp_path, "TEST-SCHEMA-FAIL")
        report = orchestrator.run_evidence_gate(cand_dir)
        assert report["verdict"] == "BLOCKED", f"Expected BLOCKED, got {report['verdict']}"
        assert report["blocked_at_gate"] == "schema"
        results = report["per_check_results"]
        assert results[0]["gate"] == "completeness"
        assert results[0]["status"] == "passed"
        assert results[1]["gate"] == "schema"
        assert results[1]["status"] == "failed"
        assert results[2]["gate"] == "integrity"
        assert results[2]["status"] == "skipped"


class TestIntegrityFailFast:
    def test_integrity_fail_blocks(self, tmp_path: Path, orchestrator: EvidenceGateOrchestrator):
        cand_dir = _make_integrity_fail_package(tmp_path, "TEST-INT-FAIL")
        report = orchestrator.run_evidence_gate(cand_dir)
        assert report["verdict"] == "BLOCKED", f"Expected BLOCKED, got {report['verdict']}"
        assert report["blocked_at_gate"] == "integrity"
        results = report["per_check_results"]
        assert results[0]["gate"] == "completeness"
        assert results[0]["status"] == "passed"
        assert results[1]["gate"] == "schema"
        assert results[1]["status"] == "passed"
        assert results[2]["gate"] == "integrity"
        assert results[2]["status"] == "failed"


class TestRoundMapping:
    def test_mapping_has_correct_gov_infra_rounds(self):
        assert GATE_ROUND_MAPPING["completeness"] == ["GOV-INFRA-002", "GOV-INFRA-003"]
        assert GATE_ROUND_MAPPING["schema"] == ["GOV-INFRA-004"]
        assert GATE_ROUND_MAPPING["integrity"] == ["GOV-INFRA-005"]

    def test_per_check_results_mapping_consistent(self, tmp_path: Path, orchestrator: EvidenceGateOrchestrator):
        cand_dir = _make_consistent_package(tmp_path, "TEST-MAP")
        report = orchestrator.run_evidence_gate(cand_dir)
        for r in report["per_check_results"]:
            assert r["gov_infra_rounds"] == GATE_ROUND_MAPPING.get(r["gate"], []), (
                f"Gate {r['gate']} has wrong round mapping: {r['gov_infra_rounds']}"
            )


class TestGateReportWrite:
    def test_gate_report_json_writable(self, tmp_path: Path, orchestrator: EvidenceGateOrchestrator):
        cand_dir = _make_consistent_package(tmp_path, "TEST-WRITE")
        report = orchestrator.run_evidence_gate(cand_dir)
        report_path = tmp_path / "GOV-INFRA-006_gate_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        assert report_path.exists(), f"Gate report not written: {report_path}"
        loaded = json.loads(report_path.read_text(encoding="utf-8"))
        assert loaded["report_type"] == "evidence_gate_report"
        assert loaded["round_id"] == "GOV-INFRA-006"
        assert "timestamp" in loaded
        assert loaded["verdict"] in ("PASS", "BLOCKED")


class TestExistingRoundsPreserved:
    def _check_round(self, round_id: str):
        checker = EvidenceChecker(repo_root=REPO_ROOT)
        passed, errors = checker.validate_evidence_cross_file_integrity(
            CANDIDATES_ROOT / round_id
        )
        assert passed, f"{round_id} cross-file integrity failed: {errors}"

    def test_gov_infra_001_still_valid(self):
        self._check_round("GOV-INFRA-001")

    def test_gov_infra_002_still_valid(self):
        self._check_round("GOV-INFRA-002")

    def test_gov_infra_003_still_valid(self):
        self._check_round("GOV-INFRA-003")

    def test_gov_infra_004_still_valid(self):
        self._check_round("GOV-INFRA-004")

    def test_gov_infra_005_still_valid(self):
        self._check_round("GOV-INFRA-005")
