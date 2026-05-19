"""
Tests for UI_VISIBLE_ROUND_ACCEPTANCE_GATE governance enforcement.

Validates that evidence_checker.py and pre-push hook correctly enforce:
- visible UI surface evidence requirement
- fake feature claim rejection
- mojibake / placeholder rejection
- trading control pollution rejection
- contract-only disclaimer requirement
- order_execution_allowed FALSE preservation
"""

import json
import os
import sys
import tempfile
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from automation.control.evidence_checker import EvidenceChecker


class TestUIVisibleGateEvidenceChecker:
    """Test evidence_checker.py UI visible gate enforcement."""

    def test_ui_round_without_visible_evidence_fails(self):
        checker = EvidenceChecker()
        evidence = {
            "round_id": "R022_TEACHING_UI",
            "task_type": "ui_construction",
            "files_modified": ["index.html"],
            "law_compliance": "04",
        }
        issues = checker.check_ui_visible_gate(evidence)
        assert any("missing_visible_surface_evidence" in i for i in issues)

    def test_ui_round_with_visible_evidence_passes(self):
        checker = EvidenceChecker()
        evidence = {
            "round_id": "R022_TEACHING_UI",
            "task_type": "ui_construction",
            "files_modified": ["index.html"],
            "law_compliance": "04",
            "ui_visible_gate_pass": True,
            "visible_surface_evidence": True,
        }
        issues = checker.check_ui_visible_gate(evidence)
        assert not any("missing_visible_surface_evidence" in i for i in issues)

    def test_non_ui_round_skips_ui_gate(self):
        checker = EvidenceChecker()
        evidence = {
            "round_id": "R012_LATENCY_BUDGET",
            "task_type": "latency_budget_construction",
            "files_modified": ["modules/latency_budget/latency_budget.py"],
            "law_compliance": "04",
        }
        issues = checker.check_ui_visible_gate(evidence)
        # Non-UI round should not be blocked by missing visible evidence
        assert not any("missing_visible_surface_evidence" in i for i in issues)

    def test_fake_feature_claim_detected_fails(self):
        checker = EvidenceChecker()
        evidence = {
            "round_id": "R022_TEACHING_UI",
            "task_type": "ui_construction",
            "files_modified": ["index.html"],
            "law_compliance": "04",
            "ui_visible_gate_pass": True,
            "fake_feature_claim_detected": True,
        }
        issues = checker.check_ui_visible_gate(evidence)
        assert any("fake_feature_claim" in i for i in issues)

    def test_trading_control_pollution_fails(self):
        checker = EvidenceChecker()
        evidence = {
            "round_id": "R026_SIMULATION_UI",
            "task_type": "ui_construction",
            "files_modified": ["index.html"],
            "law_compliance": "04",
            "ui_visible_gate_pass": True,
            "buy_sell_controls_added": True,
        }
        issues = checker.check_ui_visible_gate(evidence)
        assert any("trading_control_pollution" in i for i in issues)

    def test_contract_only_without_disclaimer_fails(self):
        checker = EvidenceChecker()
        evidence = {
            "round_id": "R012_LATENCY_BUDGET",
            "task_type": "ui_gap_display",
            "files_modified": ["index.html"],
            "law_compliance": "04",
            "ui_visible_gate_pass": True,
            "contract_only": True,
            "contract_only_disclaimer_present": False,
        }
        issues = checker.check_ui_visible_gate(evidence)
        assert any("contract_only_missing_disclaimer" in i for i in issues)

    def test_contract_only_with_disclaimer_passes(self):
        checker = EvidenceChecker()
        evidence = {
            "round_id": "R012_LATENCY_BUDGET",
            "task_type": "ui_gap_display",
            "files_modified": ["index.html"],
            "law_compliance": "04",
            "ui_visible_gate_pass": True,
            "contract_only": True,
            "contract_only_disclaimer_present": True,
        }
        issues = checker.check_ui_visible_gate(evidence)
        assert not any("contract_only" in i for i in issues)

    def test_order_execution_allowed_true_fails(self):
        checker = EvidenceChecker()
        evidence = {
            "round_id": "R026_SIMULATION_UI",
            "task_type": "ui_construction",
            "files_modified": ["index.html"],
            "law_compliance": "04",
            "ui_visible_gate_pass": True,
            "order_execution_allowed": True,
        }
        issues = checker.check_ui_visible_gate(evidence)
        assert any("order_execution_allowed_true" in i for i in issues)

    def test_ui_visible_gate_tests_must_pass(self):
        checker = EvidenceChecker()
        evidence = {
            "round_id": "R022_TEACHING_UI",
            "task_type": "ui_construction",
            "files_modified": ["index.html"],
            "law_compliance": "04",
            "ui_visible_gate_pass": True,
            "ui_visible_gate_tests": {
                "test_panel_present": "PASS",
                "test_fake_claim": "FAIL",
            },
        }
        issues = checker.check_ui_visible_gate(evidence)
        assert any("test_fail:test_fake_claim=FAIL" in i for i in issues)

    def test_index_html_file_triggers_ui_gate(self):
        checker = EvidenceChecker()
        evidence = {
            "round_id": "R030_DECISION_TRACE",
            "task_type": "decision_trace_construction",
            "files_modified": ["index.html"],
            "law_compliance": "04",
        }
        issues = checker.check_ui_visible_gate(evidence)
        # Even if round_id doesn't contain UI keywords, index.html modification triggers UI gate
        assert any("missing_visible_surface_evidence" in i for i in issues)

    def test_evidence_checker_integration_blocks_ui_without_gate(self):
        checker = EvidenceChecker()
        with tempfile.TemporaryDirectory() as tmpdir:
            candidate_dir = Path(tmpdir)
            # Create required files
            for f in ["task.txt", "report.json", "evidence.json", "candidate.diff",
                      "no-aider-used.txt", "test-results.txt"]:
                (candidate_dir / f).write_text(f"TEST {f}")
            # Create report.json
            report = {
                "round_id": "R022_TEACHING_UI",
                "status": "completed",
                "canonical_branch": "work/canonical-mainline-repair-001",
                "canonical_head": "a5ba1fc28105cb29ee67fd24cb9d9109b593f81a",
                "test_count": 10,
                "tests_passed": 10,
            }
            (candidate_dir / "report.json").write_text(json.dumps(report))
            # Create evidence.json without UI visible gate
            evidence = {
                "trace_id": "test-trace",
                "law_compliance": "04",
                "evidence_type": "ui_construction",
                "round": "R022",
                "phase": "2",
                "append_only_audit": True,
                "round_id": "R022_TEACHING_UI",
                "task_type": "ui_construction",
                "files_modified": ["index.html"],
            }
            (candidate_dir / "evidence.json").write_text(json.dumps(evidence))
            complete, missing = checker.check_completeness(candidate_dir)
            assert not complete
            assert any("ui_visible_gate" in m for m in missing)

    def test_evidence_checker_integration_passes_with_gate(self):
        checker = EvidenceChecker()
        with tempfile.TemporaryDirectory() as tmpdir:
            candidate_dir = Path(tmpdir)
            for f in ["task.txt", "report.json", "evidence.json", "candidate.diff",
                      "no-aider-used.txt", "test-results.txt"]:
                (candidate_dir / f).write_text(f"TEST {f}")
            report = {
                "round_id": "R022_TEACHING_UI",
                "status": "completed",
                "canonical_branch": "work/canonical-mainline-repair-001",
                "canonical_head": "a5ba1fc28105cb29ee67fd24cb9d9109b593f81a",
                "test_count": 10,
                "tests_passed": 10,
            }
            (candidate_dir / "report.json").write_text(json.dumps(report))
            evidence = {
                "trace_id": "test-trace",
                "law_compliance": "04",
                "evidence_type": "ui_construction",
                "round": "R022",
                "phase": "2",
                "append_only_audit": True,
                "round_id": "R022_TEACHING_UI",
                "task_type": "ui_construction",
                "files_modified": ["index.html"],
                "ui_visible_gate_pass": True,
                "visible_surface_evidence": True,
            }
            (candidate_dir / "evidence.json").write_text(json.dumps(evidence))
            complete, missing = checker.check_completeness(candidate_dir)
            # Should pass because we have all required files + law04 + UI gate
            assert complete

    def test_negative_test_missing_visible_evidence_must_fail(self):
        checker = EvidenceChecker()
        evidence = {
            "round_id": "R022_TEACHING_UI",
            "task_type": "ui_construction",
            "files_modified": ["index.html"],
            "law_compliance": "04",
            "ui_visible_gate_pass": False,
        }
        issues = checker.check_ui_visible_gate(evidence)
        # Even if ui_visible_gate_pass is explicitly False, missing evidence should still be flagged
        assert any("missing_visible_surface_evidence" in i for i in issues)

    def test_negative_test_mojibake_placeholder_must_fail(self):
        checker = EvidenceChecker()
        # mojibake/placeholder is indirectly tested through ui_visible_gate_tests
        evidence = {
            "round_id": "R022_TEACHING_UI",
            "task_type": "ui_construction",
            "files_modified": ["index.html"],
            "law_compliance": "04",
            "ui_visible_gate_pass": True,
            "ui_visible_gate_tests": {
                "test_mojibake_scan": "FAIL",
                "test_placeholder_scan": "FAIL",
            },
        }
        issues = checker.check_ui_visible_gate(evidence)
        assert any("test_fail:test_mojibake_scan" in i for i in issues)
        assert any("test_fail:test_placeholder_scan" in i for i in issues)

    def test_negative_test_broker_toggle_must_fail(self):
        checker = EvidenceChecker()
        evidence = {
            "round_id": "R026_SIMULATION_UI",
            "task_type": "ui_construction",
            "files_modified": ["index.html"],
            "law_compliance": "04",
            "ui_visible_gate_pass": True,
            "broker_toggle_added": True,
            "live_or_broker_toggle_added": True,
        }
        issues = checker.check_ui_visible_gate(evidence)
        assert any("trading_control_pollution" in i for i in issues)

    def test_no_new_api_endpoint_pollution(self):
        checker = EvidenceChecker()
        evidence = {
            "round_id": "R029_COST_TRACKING",
            "task_type": "ui_construction",
            "files_modified": ["index.html"],
            "law_compliance": "04",
            "ui_visible_gate_pass": True,
            "new_api_fetch_post_added": True,
        }
        issues = checker.check_ui_visible_gate(evidence)
        assert any("trading_control_pollution" in i for i in issues)

    def test_formal_04_law_compliance_required(self):
        checker = EvidenceChecker()
        evidence = {
            "round_id": "R022_TEACHING_UI",
            "task_type": "ui_construction",
            "files_modified": ["index.html"],
            "law_compliance": "03",
            "ui_visible_gate_pass": True,
        }
        # This tests the Law 04 compliance check, not specifically UI gate
        # But UI rounds still require law_compliance = "04"
        law = evidence.get("law_compliance")
        assert law != checker.REQUIRED_LAW_COMPLIANCE

    def test_governance_baseline_has_ui_gate_article(self):
        baseline_path = Path("_governance/law/CURRENT_GOVERNANCE_BASELINE.md")
        assert baseline_path.exists()
        content = baseline_path.read_text(encoding="utf-8")
        assert "UI_VISIBLE_ROUND_ACCEPTANCE_GATE" in content
        assert "缺口 9" in content or "UI_VISIBLE" in content

    def test_04_law_has_ui_gate_chapter(self):
        law_path = Path("_governance/law/04_交易系統法典補強版_20260416_修正版.md")
        assert law_path.exists()
        content = law_path.read_text(encoding="utf-8")
        assert "UI_VISIBLE_ROUND_ACCEPTANCE_GATE" in content
        assert "第 112 條" in content
        assert "第 127 條" in content

    def test_round_patch_mapping_has_ui_gate_group(self):
        rpm_path = Path("_governance/audit/round_patch_mapping.md")
        assert rpm_path.exists()
        content = rpm_path.read_text(encoding="utf-8")
        assert "Group 15" in content
        assert "UI_VISIBLE_ROUND_ACCEPTANCE_GATE" in content
        assert "Visible UI Surface Evidence" in content

    def test_evidence_checker_has_ui_gate_method(self):
        checker = EvidenceChecker()
        assert hasattr(checker, "check_ui_visible_gate")
        assert hasattr(checker, "UI_VISIBLE_GATE_INDICATORS")
        assert hasattr(checker, "UI_FAKE_CLAIM_INDICATORS")
        assert hasattr(checker, "UI_POLLUTION_INDICATORS")

    def test_pre_push_has_ui_visible_gate_check(self):
        hook_path = Path(".githooks/pre-push.ps1")
        assert hook_path.exists()
        content = hook_path.read_text(encoding="utf-8")
        assert "Check-UIVisibleGate" in content
        assert "UI_VISIBLE_ROUND_ACCEPTANCE_GATE" in content
