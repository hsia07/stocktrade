"""
GOV-INT-001 runtime tests: evidence gate orchestrator wired into auto_advance.

Verifies:
- Orchestrator PASS -> can_auto_advance returns True
- Completeness blocked -> False with evidence_blocked:gate=completeness
- Schema blocked -> False with evidence_blocked:gate=schema
- Integrity blocked -> False with evidence_blocked:gate=integrity
- Existing auto_advance tests unaffected
- Existing GOV-INFRA-006 tests unaffected
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from automation.control.auto_advance import AutoAdvanceController
from automation.control.evidence_gate_orchestrator import EvidenceGateOrchestrator

REPO_ROOT = Path(__file__).parent.parent.parent.parent


@pytest.fixture
def controller() -> AutoAdvanceController:
    ctrl = AutoAdvanceController(REPO_ROOT)
    ctrl.pause_manager.clear_pause()
    return ctrl


def _make_consistent_package(tmp_path: Path, round_id: str) -> Path:
    """Create a package that passes all 3 orchestration gates."""
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
        "round_id": round_id, "status": "completed",
        "canonical_branch": "work/canonical-mainline-repair-001",
        "canonical_head": "9929b5b5795c745a493d241d10af6ba8bd7343da",
        "test_count": 10, "tests_passed": 10, "tests_failed": 0,
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
    (cand_dir / "candidate.diff").write_text("diff --git a/test.py b/test.py\nnew file mode 100644\n", encoding="utf-8")
    (cand_dir / "no-aider-used.txt").write_text(
        "NO-AIDER-USED CERTIFICATION\nAider used: NO\n", encoding="utf-8"
    )
    (cand_dir / "test-results.txt").write_text(
        "TEST RESULTS\ntests_passed: 10\ntests_failed: 0\nall passed\n", encoding="utf-8"
    )

    return cand_dir


def _make_round_result(evidence_dir: Path, **overrides) -> dict:
    defaults = {
        "round_id": "GOV-INT-001",
        "status": "completed",
        "formal_status_code": "manual_review_completed",
        "blockers_found": [],
        "evidence_directory": str(evidence_dir),
        "merge_gate_encountered": False,
        "push_gate_encountered": False,
        "activation_gate_encountered": False,
        "authorization_gate_encountered": False,
    }
    defaults.update(overrides)
    return defaults


class TestOrchestratorPass:
    def test_orchestrator_pass_allows_advance(self, tmp_path: Path, controller: AutoAdvanceController):
        ev_dir = _make_consistent_package(tmp_path, "INT-TEST-PASS")
        result = _make_round_result(ev_dir)
        can, reason, gate = controller.can_auto_advance(result)
        assert can is True, f"Expected True, got can={can}, reason={reason}, gate={gate}"
        assert gate == "none", f"Expected gate=none, got {gate}"


class TestCompletenessBlocked:
    def test_incomplete_evidence_blocks_with_completeness_detail(self, tmp_path: Path, controller: AutoAdvanceController):
        ev_dir = tmp_path / "candidates" / "INT-COMP-FAIL"
        ev_dir.mkdir(parents=True, exist_ok=True)
        (ev_dir / "task.txt").write_text("incomplete", encoding="utf-8")
        (ev_dir / "evidence.json").write_text(
            json.dumps({"law_compliance": "04", "test_results": {"passed": 1, "failed": 0}}),
            encoding="utf-8",
        )
        result = _make_round_result(ev_dir)
        can, reason, gate = controller.can_auto_advance(result)
        assert can is False, f"Expected False, got {can}"
        assert gate == "evidence_gate", f"Expected evidence_gate, got {gate}"
        assert "gate=completeness" in reason, f"Expected completeness in reason, got: {reason}"


class TestSchemaBlocked:
    def test_schema_fail_blocks_with_schema_detail(self, tmp_path: Path, controller: AutoAdvanceController):
        ev_dir = _make_consistent_package(tmp_path, "INT-SCHEMA-FAIL")
        evidence_path = ev_dir / "evidence.json"
        ev = json.loads(evidence_path.read_text(encoding="utf-8"))
        ev["trace_id"] = ["not_a_string"]
        evidence_path.write_text(json.dumps(ev, indent=2), encoding="utf-8")
        result = _make_round_result(ev_dir)
        can, reason, gate = controller.can_auto_advance(result)
        assert can is False, f"Expected False, got {can}"
        assert gate == "evidence_gate", f"Expected evidence_gate, got {gate}"
        assert "gate=schema" in reason, f"Expected schema in reason, got: {reason}"


class TestIntegrityBlocked:
    def test_integrity_fail_blocks_with_integrity_detail(self, tmp_path: Path, controller: AutoAdvanceController):
        ev_dir = _make_consistent_package(tmp_path, "INT-INTEGRITY-FAIL")
        report_path = ev_dir / "report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["round_id"] = "OTHER-ROUND"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        result = _make_round_result(ev_dir)
        can, reason, gate = controller.can_auto_advance(result)
        assert can is False, f"Expected False, got {can}"
        assert gate == "evidence_gate", f"Expected evidence_gate, got {gate}"
        assert "gate=integrity" in reason, f"Expected integrity in reason, got: {reason}"
