import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.decision_prechecklist.decision_comparator import (
    DecisionComparator,
    DecisionComparisonReport,
    ComparisonFieldDiff,
)
from modules.decision_prechecklist.replay_trace import ReplayTrace


def test_comparator_initialization():
    comp = DecisionComparator()
    assert comp is not None


def test_compare_identical():
    comp = DecisionComparator()
    before = {
        "trace_id": "trace-001", "symbol": "2330.TW", "side": "buy",
        "final_decision": "EXECUTE", "decision_chain": [],
        "vetoes": [],
    }
    after = dict(before)
    report = comp.compare(before, after)
    assert not report.decision_changed
    assert report.changed_field_count == 0
    assert report.summary == "no differences"


def test_compare_different_decision():
    comp = DecisionComparator()
    before = {
        "trace_id": "trace-001", "symbol": "2330.TW", "side": "buy",
        "final_decision": "BLOCKED", "decision_chain": [],
        "vetoes": [],
    }
    after = dict(before)
    after["final_decision"] = "EXECUTE"
    report = comp.compare(before, after)
    assert report.decision_changed
    assert report.decision_before == "BLOCKED"
    assert report.decision_after == "EXECUTE"
    assert "decision changed" in report.summary


def test_compare_different_symbol():
    comp = DecisionComparator()
    before = {
        "trace_id": "trace-001", "symbol": "2330.TW", "side": "buy",
        "final_decision": "EXECUTE", "decision_chain": [],
        "vetoes": [],
    }
    after = dict(before)
    after["symbol"] = "2317.TW"
    report = comp.compare(before, after)
    assert report.changed_field_count >= 1
    symbol_diff = [f for f in report.fields if f.field_name == "symbol"]
    assert len(symbol_diff) == 1
    assert symbol_diff[0].changed
    assert symbol_diff[0].before_value == "2330.TW"
    assert symbol_diff[0].after_value == "2317.TW"


def test_compare_step_added():
    comp = DecisionComparator()
    before = {
        "trace_id": "trace-001", "symbol": "2330.TW", "side": "buy",
        "final_decision": "EXECUTE",
        "decision_chain": [
            {"step_name": "gate_1", "result": "PASS", "detail": "ok"},
        ],
        "vetoes": [],
    }
    after = dict(before)
    after["decision_chain"] = [
        {"step_name": "gate_1", "result": "PASS", "detail": "ok"},
        {"step_name": "gate_2", "result": "PASS", "detail": "ok"},
    ]
    report = comp.compare(before, after)
    assert len(report.step_diffs) == 1
    assert report.step_diffs[0]["step"] == "gate_2"
    assert report.step_diffs[0]["type"] == "added"


def test_compare_step_removed():
    comp = DecisionComparator()
    before = {
        "trace_id": "trace-001", "symbol": "2330.TW", "side": "buy",
        "final_decision": "EXECUTE",
        "decision_chain": [
            {"step_name": "gate_1", "result": "PASS", "detail": "ok"},
            {"step_name": "gate_2", "result": "PASS", "detail": "ok"},
        ],
        "vetoes": [],
    }
    after = dict(before)
    after["decision_chain"] = [
        {"step_name": "gate_1", "result": "PASS", "detail": "ok"},
    ]
    report = comp.compare(before, after)
    assert len(report.step_diffs) == 1
    assert report.step_diffs[0]["step"] == "gate_2"
    assert report.step_diffs[0]["type"] == "removed"


def test_compare_step_result_changed():
    comp = DecisionComparator()
    before = {
        "trace_id": "trace-001", "symbol": "2330.TW", "side": "buy",
        "final_decision": "BLOCKED",
        "decision_chain": [
            {"step_name": "confidence_calibration", "result": "PASS", "detail": "raw=0.8"},
        ],
        "vetoes": [{"gate": "single_signal", "reason_code": "SINGLE_SIGNAL"}],
    }
    after = dict(before)
    after["final_decision"] = "EXECUTE"
    after["decision_chain"] = [
        {"step_name": "confidence_calibration", "result": "PASS", "detail": "raw=0.9"},
    ]
    report = comp.compare(before, after)
    assert len(report.step_diffs) >= 1


def test_compare_veto_added():
    comp = DecisionComparator()
    before = {
        "trace_id": "trace-001", "symbol": "2330.TW", "side": "buy",
        "final_decision": "EXECUTE",
        "decision_chain": [],
        "vetoes": [],
    }
    after = dict(before)
    after["vetoes"] = [{"gate": "risk_gate", "reason_code": "RISK_LIMIT"}]
    report = comp.compare(before, after)
    assert len(report.veto_diffs) == 1
    assert report.veto_diffs[0]["type"] == "added"


def test_compare_from_traces():
    comp = DecisionComparator()
    trace1 = ReplayTrace.new("2330.TW", "buy", "BUY 1000 @ 150")
    trace1.finalize("BLOCKED")
    trace2 = ReplayTrace.new("2330.TW", "buy", "BUY 1000 @ 150")
    trace2.finalize("EXECUTE")
    report = comp.compare_from_traces(trace1, trace2)
    assert report.decision_changed
    assert report.decision_before == "BLOCKED"
    assert report.decision_after == "EXECUTE"


def test_comparison_report_to_dict():
    report = DecisionComparisonReport(
        trace_id_before="before", trace_id_after="after",
        symbol="2330.TW", side="buy",
        decision_before="BLOCKED", decision_after="EXECUTE",
    )
    d = report.to_dict()
    assert d["trace_id_before"] == "before"
    assert d["decision_before"] == "BLOCKED"
    assert d["decision_after"] == "EXECUTE"


def test_comparison_field_diff():
    diff = ComparisonFieldDiff(
        field_name="confidence", before_value=0.5, after_value=0.8, changed=True
    )
    assert diff.field_name == "confidence"
    assert diff.changed


def test_compare_with_order_ref_change():
    comp = DecisionComparator()
    before = {
        "trace_id": "trace-001", "symbol": "2330.TW", "side": "buy",
        "final_decision": "EXECUTE", "decision_chain": [],
        "vetoes": [], "order_ref": "", "fill_ref": "", "pnl_ref": "",
    }
    after = dict(before)
    after["order_ref"] = "ORD-123"
    report = comp.compare(before, after)
    order_diffs = [f for f in report.fields if f.field_name == "order_ref"]
    assert len(order_diffs) == 1
    assert order_diffs[0].changed


def test_compare_complex_all_diffs():
    comp = DecisionComparator()
    before = {
        "trace_id": "trace-A", "symbol": "2330.TW", "side": "buy",
        "candidate_action": "BUY 1000 @ 150",
        "final_decision": "BLOCKED",
        "order_ref": "", "fill_ref": "", "pnl_ref": "",
        "chain_link_id": "", "previous_trace_hash": "",
        "decision_chain": [
            {"step_name": "single_signal", "result": "BLOCKED", "detail": "source=technical"},
            {"step_name": "confidence", "result": "PASS", "detail": "raw=0.8"},
        ],
        "vetoes": [
            {"gate": "single_signal_gate", "reason_code": "SINGLE_SIGNAL", "detail": "blocked"},
        ],
    }
    after = dict(before)
    after["trace_id"] = "trace-B"
    after["final_decision"] = "EXECUTE"
    after["decision_chain"] = [
        {"step_name": "single_signal", "result": "PASS", "detail": "source=strategy"},
        {"step_name": "confidence", "result": "PASS", "detail": "raw=0.9"},
        {"step_name": "position_sizing", "result": "PASS", "detail": "qty=500"},
    ]
    after["vetoes"] = []
    after["order_ref"] = "ORD-123"

    report = comp.compare(before, after)
    assert report.decision_changed
    assert report.decision_before == "BLOCKED"
    assert report.decision_after == "EXECUTE"
    assert len(report.step_diffs) >= 1
    assert len(report.veto_diffs) == 1


def test_compare_normalize_steps_dataclass():
    comp = DecisionComparator()
    before = {
        "trace_id": "trace-001", "symbol": "2330.TW", "side": "buy",
        "final_decision": "EXECUTE",
        "decision_chain": [],
        "vetoes": [],
    }
    after = dict(before)
    report = comp.compare(before, after)
    assert not report.decision_changed


def test_report_properties_empty():
    report = DecisionComparisonReport(
        trace_id_before="", trace_id_after="",
        symbol="", side="",
        decision_before="", decision_after="",
    )
    assert not report.decision_changed
    assert report.changed_field_count == 0


# ── R033: comparison with reasons, market reality, confidence, as-of ──

def test_compare_with_market_reality_diffs():
    comp = DecisionComparator()
    before = {"trace_id": "t1", "symbol": "ABC", "side": "buy",
              "candidate_action": "entry", "final_decision": "EXECUTE"}
    after = dict(before)
    mr_before = {"cost_model_version": "v1", "liquidity_score": 0.8,
                 "market_session_state": "continuous"}
    mr_after = {"cost_model_version": "v2", "liquidity_score": 0.7,
                "market_session_state": "continuous"}
    report = comp.compare(before, after,
                          market_reality_before=mr_before,
                          market_reality_after=mr_after)
    assert len(report.market_reality_diffs) >= 2
    codes = report.diff_reason_codes
    assert any("market_reality_snapshot_changed" in c for c in codes)


def test_compare_with_market_reality_missing_fields():
    comp = DecisionComparator()
    before = {"trace_id": "t1", "symbol": "ABC", "side": "buy",
              "candidate_action": "entry", "final_decision": "EXECUTE"}
    after = dict(before)
    report = comp.compare(before, after)
    assert len(report.market_reality_diffs) == 0


def test_compare_with_confidence_labels():
    comp = DecisionComparator()
    before = {"trace_id": "t1", "symbol": "ABC", "side": "buy",
              "candidate_action": "entry", "final_decision": "EXECUTE"}
    after = dict(before)
    conf_before = {"raw": "0.85", "calibrated": "0.72"}
    conf_after = {"raw": "0.85", "calibrated": "0.73"}
    report = comp.compare(before, after,
                          confidence_before=conf_before,
                          confidence_after=conf_after)
    assert len(report.confidence_diffs) == 1


def test_compare_with_as_of_violation():
    comp = DecisionComparator()
    before = {"trace_id": "t1", "symbol": "ABC", "side": "buy",
              "candidate_action": "entry", "final_decision": "EXECUTE"}
    after = dict(before)
    as_of_before = {
        "decision_ts": "2025-01-01T09:00:00",
        "tradable_ts": "2025-01-01T10:00:00",
    }
    as_of_after = {
        "decision_ts": "2025-01-01T11:00:00",
        "tradable_ts": "2025-01-01T10:00:00",
    }
    report = comp.compare(before, after,
                          as_of_before=as_of_before,
                          as_of_after=as_of_after)
    assert report.has_as_of_violation
    assert any("decision_ts_before_tradable_ts" in c for c in report.diff_reason_codes)


def test_compare_with_future_leak():
    comp = DecisionComparator()
    before = {"trace_id": "t1", "symbol": "ABC", "side": "buy",
              "candidate_action": "entry", "final_decision": "EXECUTE"}
    after = dict(before)
    as_of_before = {
        "decision_ts": "2025-01-01T09:00:00",
        "source_ts": "2025-01-01T10:00:00",
    }
    as_of_after = {
        "decision_ts": "2025-01-01T09:00:00",
    }
    report = comp.compare(before, after,
                          as_of_before=as_of_before,
                          as_of_after=as_of_after)
    assert report.has_future_leak
    assert any("future_leak" in c for c in report.diff_reason_codes)


def test_compare_as_of_passes_valid():
    comp = DecisionComparator()
    before = {"trace_id": "t1", "symbol": "ABC", "side": "buy",
              "candidate_action": "entry", "final_decision": "EXECUTE"}
    after = dict(before)
    as_of_before = {
        "decision_ts": "2025-01-01T10:00:00",
        "tradable_ts": "2025-01-01T09:00:00",
        "source_ts": "2025-01-01T08:00:00",
    }
    as_of_after = {
        "decision_ts": "2025-01-01T10:00:00",
        "tradable_ts": "2025-01-01T09:00:00",
        "source_ts": "2025-01-01T08:00:00",
    }
    report = comp.compare(before, after,
                          as_of_before=as_of_before,
                          as_of_after=as_of_after)
    assert not report.has_as_of_violation
    assert not report.has_future_leak


def test_diffs_reason_codes_decision_changed():
    comp = DecisionComparator()
    before = {"trace_id": "t1", "symbol": "ABC", "side": "buy",
              "candidate_action": "entry", "final_decision": "EXECUTE"}
    after = dict(before)
    after["final_decision"] = "NO_TRADE"
    report = comp.compare(before, after)
    assert report.decision_changed
    assert "decision_changed" in report.diff_reason_codes


def test_diffs_reason_codes_missing_trace_id():
    comp = DecisionComparator()
    before = {"trace_id": "", "symbol": "ABC", "side": "buy",
              "candidate_action": "entry", "final_decision": "NO_TRADE"}
    after = {"trace_id": "t2", "symbol": "ABC", "side": "buy",
             "candidate_action": "entry", "final_decision": "NO_TRADE"}
    report = comp.compare(before, after)
    codes = report.diff_reason_codes
    assert any("missing_trace_id" in c for c in codes)


def test_diffs_reason_codes_missing_final_decision():
    comp = DecisionComparator()
    before = {"trace_id": "t1", "symbol": "ABC", "side": "buy",
              "candidate_action": "entry", "final_decision": ""}
    after = {"trace_id": "t2", "symbol": "ABC", "side": "buy",
             "candidate_action": "entry", "final_decision": "EXECUTE"}
    report = comp.compare(before, after)
    codes = report.diff_reason_codes
    assert any("missing_final_decision" in c for c in codes)


def test_report_has_veto_replay_mismatch():
    report = DecisionComparisonReport(
        trace_id_before="t1", trace_id_after="t2",
        symbol="ABC", side="buy",
        decision_before="NO_TRADE", decision_after="EXECUTE",
        diff_reason_codes=["veto_ignored_in_replay"],
    )
    assert report.has_veto_replay_mismatch


def test_build_replay_result():
    comp = DecisionComparator()
    before = {"trace_id": "t1", "symbol": "ABC", "side": "buy",
              "candidate_action": "entry", "final_decision": "NO_TRADE",
              "record_hash": "abc123"}
    after = dict(before)
    after["final_decision"] = "EXECUTE"
    report = comp.compare(before, after)
    result = comp.build_replay_result(report, audit_record_dict=before)
    assert result["trace_id"] == "t1"
    assert result["original_decision"] == "NO_TRADE"
    assert result["replayed_decision"] == "EXECUTE"
    assert result["replay_version"] == "r033-v1"
    assert len(result["diff_reason_codes"]) > 0


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
