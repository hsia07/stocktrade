#!/usr/bin/env python3
"""Tests for check_required_evidence.py UI-visible-surface evidence format support."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.validation.check_required_evidence import (
    check_evidence_content,
    _is_ui_visible_surface_evidence,
    _check_ui_visible_surface_evidence,
    UI_VISIBLE_GATE_INDICATORS,
    UI_EVIDENCE_QUALITY_GATES,
)


class TestIsUIVisibleSurfaceEvidence:
    def test_ui_gate_pass_true(self):
        data = {"ui_visible_gate_pass": True}
        assert _is_ui_visible_surface_evidence(data) is True

    def test_visible_surface_evidence_true(self):
        data = {"visible_surface_evidence": True}
        assert _is_ui_visible_surface_evidence(data) is True

    def test_dom_scan_pass_true(self):
        data = {"dom_scan_pass": True}
        assert _is_ui_visible_surface_evidence(data) is True

    def test_ui_panel_present_true(self):
        data = {"ui_panel_present": True}
        assert _is_ui_visible_surface_evidence(data) is True

    def test_multiple_ui_indicators_true(self):
        data = {"ui_visible_gate_pass": True, "dom_scan_pass": True}
        assert _is_ui_visible_surface_evidence(data) is True

    def test_no_ui_indicator(self):
        data = {"round_id": "TEST", "law_compliance": "04"}
        assert _is_ui_visible_surface_evidence(data) is False

    def test_ui_indicator_false(self):
        data = {"ui_visible_gate_pass": False, "visible_surface_evidence": False}
        assert _is_ui_visible_surface_evidence(data) is False

    def test_non_dict_input(self):
        assert _is_ui_visible_surface_evidence("not a dict") is False
        assert _is_ui_visible_surface_evidence(None) is False


class TestCheckUIVisibleSurfaceEvidence:
    def test_valid_ui_evidence_all_gates_pass(self, tmp_path):
        evidence = {
            "ui_visible_gate_pass": True,
            "visible_surface_evidence": True,
            "dom_scan_pass": True,
            "law_compliance": "04",
            "order_execution_allowed": False,
            "fake_feature_claim_detected": False,
            "false_completion_claim": False,
            "runtime_started": False,
            "trading_broker_execution_live_started": False,
            "broker_live_fubon_controls_detected": False,
            "fubon_api_integrated": False,
            "placeholder_detected": True,
            "mojibake_detected": False,
            "ui_gap_status_panel_visible_evidence_created": True,
        }
        path = tmp_path / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        valid, reason = check_evidence_content(path)
        assert valid is True, reason

    def test_valid_ui_evidence_using_read_only_disclaimer(self, tmp_path):
        evidence = {
            "ui_visible_gate_pass": True,
            "read_only_or_display_only_disclaimer_visible": True,
            "not_complete_disclaimer_visible": True,
            "law_compliance": "04",
            "order_execution_allowed": False,
            "fake_feature_claim_detected": False,
            "undefined_null_nan_placeholder_detected": False,
        }
        path = tmp_path / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        valid, reason = check_evidence_content(path)
        assert valid is True, reason

    def test_ui_gate_missing_fails(self, tmp_path):
        evidence = {
            "placeholder_detected": True,
            "law_compliance": "04",
            "order_execution_allowed": False,
            "fake_feature_claim_detected": False,
            "ui_visible_gate_pass": False,
            "visible_surface_evidence": False,
            "dom_scan_pass": False,
        }
        path = tmp_path / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        valid, reason = check_evidence_content(path)
        assert valid is False
        assert "NO_WORK_DONE_ITEMS" in reason

    def test_ui_gate_false_fails(self, tmp_path):
        evidence = {
            "ui_visible_gate_pass": False,
            "visible_surface_evidence": False,
            "dom_scan_pass": False,
            "placeholder_detected": True,
        }
        path = tmp_path / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        valid, reason = check_evidence_content(path)
        assert valid is False

    def test_order_execution_allowed_true_fails(self, tmp_path):
        evidence = {
            "ui_visible_gate_pass": True,
            "placeholder_detected": True,
            "law_compliance": "04",
            "order_execution_allowed": True,
        }
        path = tmp_path / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        valid, reason = check_evidence_content(path)
        assert valid is False
        assert "order_execution_allowed is TRUE" in reason

    def test_fake_feature_claim_detected_fails(self, tmp_path):
        evidence = {
            "ui_visible_gate_pass": True,
            "placeholder_detected": True,
            "law_compliance": "04",
            "fake_feature_claim_detected": True,
        }
        path = tmp_path / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        valid, reason = check_evidence_content(path)
        assert valid is False
        assert "fake/false feature claim" in reason

    def test_runtime_broker_live_pollution_fails(self, tmp_path):
        evidence = {
            "ui_visible_gate_pass": True,
            "placeholder_detected": True,
            "law_compliance": "04",
            "broker_live_fubon_controls_detected": True,
        }
        path = tmp_path / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        valid, reason = check_evidence_content(path)
        assert valid is False
        assert "runtime/broker/live pollution" in reason

    def test_no_ui_specific_indicator_fails(self, tmp_path):
        evidence = {
            "ui_visible_gate_pass": True,
            "law_compliance": "04",
            "placeholder_detected": False,
            "mojibake_detected": False,
            "undefined_null_nan_placeholder_detected": False,
            "ui_gap_status_panel_visible_evidence_created": False,
            "r022_r023_r024_r025_r026_r029_r040_status_visible": False,
            "read_only_or_display_only_disclaimer_visible": False,
            "not_complete_disclaimer_visible": False,
        }
        path = tmp_path / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        valid, reason = check_evidence_content(path)
        assert valid is False
        assert "no UI-specific indicator" in reason


class TestWorkDoneValidationPreserved:
    def test_non_ui_evidence_no_work_done_fails(self, tmp_path):
        evidence = {
            "round_id": "TEST",
            "law_compliance": "04",
            "work_done": [],
        }
        path = tmp_path / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        valid, reason = check_evidence_content(path)
        assert valid is False
        assert "NO_WORK_DONE_ITEMS" in reason

    def test_non_ui_evidence_packaging_only_fails(self, tmp_path):
        evidence = {
            "round_id": "TEST",
            "law_compliance": "04",
            "work_done": ["evidence package created", "report generated", "structure validated"],
        }
        path = tmp_path / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        valid, reason = check_evidence_content(path)
        assert valid is False
        assert "PACKAGING_ONLY_WORK_ITEMS" in reason

    def test_non_ui_evidence_real_work_done_passes(self, tmp_path):
        evidence = {
            "round_id": "TEST",
            "law_compliance": "04",
            "work_done": ["Modified server_v2.py bridge method", "Added ReplayIsolationGate"],
            "prohibited_actions_verified": {"placeholder_gate": True, "fake_claim_gate": True},
        }
        path = tmp_path / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        valid, reason = check_evidence_content(path)
        assert valid is True, reason


class TestLawComplianceAndSecretScan:
    def test_ui_evidence_missing_law_compliance_fails(self, tmp_path):
        evidence = {
            "ui_visible_gate_pass": True,
            "placeholder_detected": True,
        }
        path = tmp_path / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        valid, reason = check_evidence_content(path)
        assert valid is False
        assert "law_compliance" in reason

    def test_ui_evidence_wrong_law_compliance_fails(self, tmp_path):
        evidence = {
            "ui_visible_gate_pass": True,
            "placeholder_detected": True,
            "law_compliance": "03",
        }
        path = tmp_path / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        valid, reason = check_evidence_content(path)
        assert valid is False
        assert "law_compliance" in reason

    def test_ui_evidence_secret_detected_fails(self, tmp_path):
        evidence = {
            "ui_visible_gate_pass": True,
            "placeholder_detected": True,
            "law_compliance": "04",
            "api_key": "sk-secret",
        }
        path = tmp_path / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        valid, reason = check_evidence_content(path)
        assert valid is False
        assert "EVIDENCE_MAY_CONTAIN_SECRET" in reason

    def test_ui_evidence_invalidated_fails(self, tmp_path):
        evidence = {
            "status": "INVALIDATED",
            "ui_visible_gate_pass": True,
            "placeholder_detected": True,
            "law_compliance": "04",
        }
        path = tmp_path / "evidence.json"
        path.write_text(json.dumps(evidence), encoding="utf-8")
        valid, reason = check_evidence_content(path)
        assert valid is False
        assert "INVALIDATED" in reason