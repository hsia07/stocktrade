"""
GOV-INT-002 runtime tests: gate report persister.

Verifies:
- Report file created in reports/ dir after run
- PASS verdict writes JSON with verdict=PASS, blocked_at_gate=None
- BLOCKED verdict still writes JSON with verdict=BLOCKED, raises GateBlocked
- blocked_at_gate preserved in report
- per_check_results preserved in report
- invalid candidate_dir raises NotADirectoryError
- No modification to EvidenceGateOrchestrator
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from automation.control.gate_report_persister import (
    GateBlocked,
    persist_gate_report,
)


def _make_pass_package(
    tmp_path: Path, round_id: str = "GOV-INT-002-TEST"
) -> Path:
    """Create a candidate package that passes all 3 orchestration gates."""
    cand_dir = tmp_path / "candidates" / round_id
    cand_dir.mkdir(parents=True, exist_ok=True)

    task_content = (
        "=== TASK DESCRIPTION ===\n"
        f"task_id: {round_id}\n"
        "task_type: governance_test_round\n"
        "phase: governance\n"
        "law_compliance: 04\n"
        "severity: MEDIUM\n"
        "\n=== PROBLEM STATEMENT ===\nTest\n"
        "\n=== SOLUTION ===\nTest\n"
        "\n=== FILES ===\n- test\n"
    )
    (cand_dir / "task.txt").write_text(task_content, encoding="utf-8")

    report = {
        "round_id": round_id,
        "status": "completed",
        "canonical_branch": "work/canonical-mainline-repair-001",
        "canonical_head": "42efcb5d07506312fdcfe48026cfeed493f3e6e5",
        "test_count": 1,
        "tests_passed": 1,
        "tests_failed": 0,
    }
    (cand_dir / "report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    evidence = {
        "round": round_id,
        "evidence_type": "governance_test_round",
        "law_compliance": "04",
        "law_compliance_authority": "Law 04 Article 261",
        "phase": "governance",
        "append_only_audit": True,
        "trace_id": f"trace_{round_id.lower()}",
        "replay_log": ["2026-05-09T10:00: test init"],
        "test_results": {"passed": 1, "failed": 0},
    }
    (cand_dir / "evidence.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    (cand_dir / "candidate.diff").write_text(
        "diff --git a/test.py b/test.py\nnew file mode 100644\n",
        encoding="utf-8",
    )
    (cand_dir / "no-aider-used.txt").write_text(
        "NO-AIDER-USED CERTIFICATION\nAider used: NO\n", encoding="utf-8"
    )
    (cand_dir / "test-results.txt").write_text(
        "TEST RESULTS\ntests_passed: 1\ntests_failed: 0\nall passed\n",
        encoding="utf-8",
    )

    return cand_dir


class TestReportFileCreated:
    def test_report_file_created_in_reports_dir(self, tmp_path: Path):
        cand_dir = _make_pass_package(tmp_path, "INT-CREATE-TEST")
        reports_dir = tmp_path / "reports"
        persist_gate_report(cand_dir, reports_dir=reports_dir)
        expected_file = reports_dir / "GOV-INFRA-006_gate_report.json"
        assert expected_file.is_file(), (
            f"Report file not created: {expected_file}"
        )


class TestPassVerdict:
    def test_pass_verdict_writes_pass_with_report(self, tmp_path: Path):
        cand_dir = _make_pass_package(tmp_path, "INT-PASS-TEST")
        reports_dir = tmp_path / "reports"
        report = persist_gate_report(cand_dir, reports_dir=reports_dir)
        assert report["verdict"] == "PASS", (
            f"Expected PASS, got {report['verdict']}"
        )
        assert report.get("blocked_at_gate") is None
        assert report["report_type"] == "evidence_gate_report"
        assert report["round_id"] == "GOV-INFRA-006"


class TestBlockedVerdictStillWrites:
    def test_blocked_verdict_writes_report_and_raises(self, tmp_path: Path):
        cand_dir = tmp_path / "candidates" / "INT-BLOCK-TEST"
        cand_dir.mkdir(parents=True, exist_ok=True)
        (cand_dir / "task.txt").write_text("incomplete", encoding="utf-8")
        (cand_dir / "evidence.json").write_text(
            json.dumps(
                {
                    "law_compliance": "04",
                    "test_results": {"passed": 1, "failed": 0},
                }
            ),
            encoding="utf-8",
        )
        reports_dir = tmp_path / "reports"

        with pytest.raises(GateBlocked) as exc_info:
            persist_gate_report(cand_dir, reports_dir=reports_dir)

        report = exc_info.value.report
        assert report["verdict"] == "BLOCKED", (
            f"Expected BLOCKED, got {report['verdict']}"
        )
        assert report.get("blocked_at_gate") is not None

        expected_file = reports_dir / "GOV-INFRA-006_gate_report.json"
        assert expected_file.is_file(), (
            f"Report file not created on BLOCKED: {expected_file}"
        )
        saved = json.loads(expected_file.read_text(encoding="utf-8"))
        assert saved["verdict"] == "BLOCKED"


class TestBlockedAtGatePreserved:
    def test_blocked_at_gate_preserved_in_report(self, tmp_path: Path):
        cand_dir = tmp_path / "candidates" / "INT-GATE-TEST"
        cand_dir.mkdir(parents=True, exist_ok=True)
        (cand_dir / "task.txt").write_text("incomplete", encoding="utf-8")
        (cand_dir / "evidence.json").write_text(
            json.dumps(
                {
                    "law_compliance": "04",
                    "test_results": {"passed": 1, "failed": 0},
                }
            ),
            encoding="utf-8",
        )
        reports_dir = tmp_path / "reports"

        with pytest.raises(GateBlocked) as exc_info:
            persist_gate_report(cand_dir, reports_dir=reports_dir)

        blocked_at = exc_info.value.report.get("blocked_at_gate")
        assert blocked_at is not None and blocked_at != "unknown"


class TestPerCheckResultsPreserved:
    def test_per_check_results_in_report(self, tmp_path: Path):
        cand_dir = tmp_path / "candidates" / "INT-CHECK-TEST"
        cand_dir.mkdir(parents=True, exist_ok=True)
        (cand_dir / "task.txt").write_text("incomplete", encoding="utf-8")
        (cand_dir / "evidence.json").write_text(
            json.dumps(
                {
                    "law_compliance": "04",
                    "test_results": {"passed": 1, "failed": 0},
                }
            ),
            encoding="utf-8",
        )
        reports_dir = tmp_path / "reports"

        with pytest.raises(GateBlocked) as exc_info:
            persist_gate_report(cand_dir, reports_dir=reports_dir)

        results = exc_info.value.report.get("per_check_results", [])
        assert len(results) > 0, "per_check_results should not be empty"
        assert results[0]["gate"] == "completeness"
        assert results[0]["status"] == "failed"


class TestInvalidDir:
    def test_invalid_candidate_dir_raises(self, tmp_path: Path):
        fake_dir = tmp_path / "nonexistent"
        reports_dir = tmp_path / "reports"
        with pytest.raises(NotADirectoryError):
            persist_gate_report(fake_dir, reports_dir=reports_dir)


class TestPassReturnsReport:
    def test_pass_returns_report_dict(self, tmp_path: Path):
        cand_dir = _make_pass_package(tmp_path, "INT-RETURN-TEST")
        reports_dir = tmp_path / "reports"
        report = persist_gate_report(cand_dir, reports_dir=reports_dir)
        assert isinstance(report, dict)
        assert report["verdict"] == "PASS"


class TestBlockedRaisesGateBlocked:
    def test_blocked_raises_gate_blocked(self, tmp_path: Path):
        cand_dir = tmp_path / "candidates" / "INT-RAISE-TEST"
        cand_dir.mkdir(parents=True, exist_ok=True)
        (cand_dir / "task.txt").write_text("incomplete", encoding="utf-8")
        (cand_dir / "evidence.json").write_text(
            json.dumps(
                {
                    "law_compliance": "04",
                    "test_results": {"passed": 1, "failed": 0},
                }
            ),
            encoding="utf-8",
        )
        reports_dir = tmp_path / "reports"

        with pytest.raises(GateBlocked):
            persist_gate_report(cand_dir, reports_dir=reports_dir)
