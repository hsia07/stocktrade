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


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
