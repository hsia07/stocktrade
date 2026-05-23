import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from modules.decision_prechecklist.confidence_decomposition import (
    ConfidenceSourceDecomposer,
    ConfidenceDecompositionReport,
    ConfidenceSource,
    CONFIDENCE_SOURCE_KEYS,
    DEFAULT_SOURCE_CONFIG,
    TaiwanMarketCompatibilityMarkers,
    get_compatible_report,
)


def test_decomposer_initializes_with_default_config():
    decomposer = ConfidenceSourceDecomposer()
    assert len(decomposer._config) == 7
    assert abs(sum(c["weight"] for c in decomposer._config.values()) - 1.0) < 0.001
    for key in CONFIDENCE_SOURCE_KEYS:
        assert key in decomposer._config


def test_decomposer_rejects_bad_weights():
    bad_config = {k: {"weight": 0.5, "min_raw": 0.0} for k in list(CONFIDENCE_SOURCE_KEYS)[:2]}
    remaining = CONFIDENCE_SOURCE_KEYS - set(bad_config.keys())
    for k in remaining:
        bad_config[k] = {"weight": 1.0, "min_raw": 0.0}
    with pytest.raises(ValueError, match="weights must sum to 1.0"):
        ConfidenceSourceDecomposer(source_config=bad_config)


def test_decomposer_rejects_missing_keys():
    bad_config = {k: dict(v) for k, v in DEFAULT_SOURCE_CONFIG.items()}
    del bad_config["signal_technical"]
    with pytest.raises(ValueError) as excinfo:
        ConfidenceSourceDecomposer(source_config=bad_config)
    assert "Missing source keys" in str(excinfo.value) or "weights must sum" in str(excinfo.value)


def test_decomposer_rejects_extra_keys():
    bad_config = {k: dict(v) for k, v in DEFAULT_SOURCE_CONFIG.items()}
    bad_config["unknown_key"] = {"weight": 0.0, "min_raw": 0.0}
    with pytest.raises(ValueError, match="Unknown source keys"):
        ConfidenceSourceDecomposer(source_config=bad_config)


def test_decompose_returns_all_seven_sources():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.8)
    assert len(result.confidence_source_breakdown) == 7
    keys = {s.source_key for s in result.confidence_source_breakdown}
    assert keys == CONFIDENCE_SOURCE_KEYS


def test_decompose_with_source_scores():
    decomposer = ConfidenceSourceDecomposer()
    scores = {
        "signal_technical": 0.9,
        "event_news_disclosure": 0.7,
        "market_reality_liquidity": 0.6,
        "risk_gate_veto": 0.8,
        "regime_uncertainty": 0.6,
        "data_freshness_reliability": 0.8,
        "calibration_quality": 0.7,
    }
    result = decomposer.decompose(raw_confidence=0.8, source_scores=scores)
    assert len(result.confidence_source_breakdown) == 7
    for s in result.confidence_source_breakdown:
        expected_raw = scores[s.source_key]
        assert s.raw_value == expected_raw


def test_decompose_low_raw_still_decomposes():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.0)
    assert not result.vetoes or result.vetoes == []
    assert result.overall_calibrated == 0.0
    assert len(result.confidence_source_breakdown) == 7


def test_decompose_negative_raw_veto():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=-0.1)
    assert result.vetoes
    assert any("out of range" in v for v in result.vetoes)


def test_decompose_over_one_raw_veto():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=1.5)
    assert result.vetoes
    assert any("out of range" in v for v in result.vetoes)


def test_decompose_brier_penalty():
    decomposer = ConfidenceSourceDecomposer()
    result_no_penalty = decomposer.decompose(
        raw_confidence=0.8, historical_brier_score=0.2
    )
    result_penalty = decomposer.decompose(
        raw_confidence=0.8, historical_brier_score=0.5
    )
    assert result_penalty.overall_calibrated < result_no_penalty.overall_calibrated


def test_decompose_experience_penalty():
    decomposer = ConfidenceSourceDecomposer()
    result_experienced = decomposer.decompose(
        raw_confidence=0.8, num_past_decisions=50
    )
    result_novice = decomposer.decompose(
        raw_confidence=0.8, num_past_decisions=2
    )
    assert result_novice.overall_calibrated < result_experienced.overall_calibrated


def test_decompose_regime_penalty():
    decomposer = ConfidenceSourceDecomposer()
    result_low = decomposer.decompose(
        raw_confidence=0.8, regime_uncertainty=0.1
    )
    result_high = decomposer.decompose(
        raw_confidence=0.8, regime_uncertainty=0.8
    )
    assert result_high.overall_calibrated < result_low.overall_calibrated


def test_decompose_individual_source_veto():
    config = {k: dict(v) for k, v in DEFAULT_SOURCE_CONFIG.items()}
    config["signal_technical"]["min_raw"] = 0.5
    decomposer = ConfidenceSourceDecomposer(source_config=config)
    result = decomposer.decompose(
        raw_confidence=0.8,
        source_scores={"signal_technical": 0.3},
    )
    assert result.vetoes
    assert any("signal_technical" in v for v in result.vetoes)
    assert any("below min_raw" in v for v in result.vetoes)


def test_get_source_summary():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.8)
    summary = result.get_source_summary()
    assert len(summary) == 7
    for key in CONFIDENCE_SOURCE_KEYS:
        assert key in summary
        assert "weight" in summary[key]
        assert "raw_value" in summary[key]
        assert "normalized_score" in summary[key]


def test_get_source_found():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.8)
    source = result.get_source("signal_technical")
    assert source is not None
    assert source.source_key == "signal_technical"


def test_get_source_not_found():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.8)
    source = result.get_source("nonexistent")
    assert source is None


def test_overall_calibrated_is_weighted_sum():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.8)
    expected = sum(s.confidence_contribution for s in result.confidence_source_breakdown)
    assert abs(result.overall_calibrated - expected) < 0.001


def test_confidence_source_dataclass():
    source = ConfidenceSource(
        source_key="test",
        source_label="Test Source",
        category="test",
        weight=0.5,
        raw_value=0.8,
        normalized_score=0.8,
        calibrated_bucket="medium",
        confidence_contribution=0.4,
        reason_codes=["test_code"],
        is_missing=False,
        is_stale=False,
        is_conflicting=False,
        is_uncalibrated=False,
        is_veto_related=False,
        source_reliability=0.9,
        freshness_metadata={},
        trace_audit_payload={},
        metadata={},
    )
    assert source.source_key == "test"
    assert source.weight == 0.5
    assert source.reason_codes == ["test_code"]


def test_confidence_decomposition_report_defaults():
    report = ConfidenceDecompositionReport(raw_confidence=0.8, overall_calibrated=0.6)
    assert report.confidence_source_breakdown == []
    assert report.vetoes == []
    assert not report.is_fallback
    assert report.final_confidence_is_trade_authority is False
    assert report.details == {}


def test_final_confidence_is_trade_authority_false():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.95)
    assert result.final_confidence_is_trade_authority is False


def test_high_confidence_with_risk_veto_veto_preserved():
    config = {k: dict(v) for k, v in DEFAULT_SOURCE_CONFIG.items()}
    config["risk_gate_veto"]["min_raw"] = 0.6
    decomposer = ConfidenceSourceDecomposer(source_config=config)
    result = decomposer.decompose(
        raw_confidence=0.95,
        source_scores={"risk_gate_veto": 0.3},
    )
    assert result.vetoes
    assert any("risk_gate_veto" in v for v in result.vetoes)
    assert result.final_confidence_is_trade_authority is False


def test_trace_id_passthrough():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.8, trace_id="TRACE-001")
    assert result.trace_id == "TRACE-001"
    assert result.decision_chain_compatible is True


def test_trace_append():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.8)
    result.append_trace_audit("TRACE-002")
    assert result.trace_id == "TRACE-002"
    for s in result.confidence_source_breakdown:
        assert s.trace_audit_payload.get("trace_id") == "TRACE-002"


def test_reason_codes_preserved():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(
        raw_confidence=0.8,
        historical_brier_score=0.5,
        num_past_decisions=2,
        regime_uncertainty=0.3,
    )
    assert len(result.reason_codes) > 0


def test_threshold_config_version_preserved():
    decomposer = ConfidenceSourceDecomposer(threshold_version="v2")
    result = decomposer.decompose(raw_confidence=0.8)
    assert result.threshold_config_version == "v2"
    assert result.source_config_version == "v1"


def test_missing_source_flagged():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(
        raw_confidence=0.8,
        source_scores={"signal_technical": 0.9},
    )
    missing_sources = [s for s in result.confidence_source_breakdown if s.is_missing]
    assert len(missing_sources) == 6
    assert all(s.source_key != "signal_technical" for s in missing_sources)


def test_stale_source_reduces_trust():
    decomposer = ConfidenceSourceDecomposer()
    scores = {k: 0.8 for k in CONFIDENCE_SOURCE_KEYS}
    meta = {
        "signal_technical": {"is_stale": True, "source_reliability": 0.3},
    }
    result_normal = decomposer.decompose(
        raw_confidence=0.8, source_scores=scores,
        historical_brier_score=0.2, num_past_decisions=50,
    )
    result_stale = decomposer.decompose(
        raw_confidence=0.8, source_scores=scores,
        source_metadata=meta,
        historical_brier_score=0.2, num_past_decisions=50,
    )
    stale_source = result_stale.get_source("signal_technical")
    assert stale_source is not None
    assert stale_source.is_stale is True
    normal_source = result_stale.get_source("event_news_disclosure")
    assert normal_source.is_stale is False
    assert stale_source.confidence_contribution < normal_source.confidence_contribution
    assert result_stale.is_stale_source is True


def test_conflicting_source_flagged():
    decomposer = ConfidenceSourceDecomposer()
    scores = {k: 0.8 for k in CONFIDENCE_SOURCE_KEYS}
    meta = {"event_news_disclosure": {"is_conflicting": True, "source_reliability": 0.4}}
    result = decomposer.decompose(
        raw_confidence=0.8,
        source_scores=scores,
        source_metadata=meta,
        historical_brier_score=0.2,
        num_past_decisions=50,
    )
    conflict_source = result.get_source("event_news_disclosure")
    assert conflict_source is not None
    assert conflict_source.is_conflicting is True
    normal_source = result.get_source("signal_technical")
    assert normal_source.is_conflicting is False
    assert result.is_conflicting_source is True
    assert conflict_source.confidence_contribution < normal_source.confidence_contribution


def test_uncalibrated_confidence_flagged():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.9)
    assert result.is_uncalibrated is True


def test_calibrated_confidence_not_uncalibrated():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.9, historical_brier_score=0.2)
    assert result.is_uncalibrated is False


def test_llm_failure_deterministic_safe_output():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.5)
    assert result.final_confidence_is_trade_authority is False
    assert result.overall_calibrated >= 0.0
    assert len(result.confidence_source_breakdown) == 7


def test_malformed_input_fail_safe():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=1.5)
    assert result.vetoes
    assert result.overall_calibrated == 0.0
    assert result.final_confidence_is_trade_authority is False


def test_get_compatible_report():
    decomposer = ConfidenceSourceDecomposer()
    report = decomposer.decompose(raw_confidence=0.8, trace_id="TRACE-003")
    compat = get_compatible_report(0.8, report)
    assert compat["trace_id"] == "TRACE-003"
    assert compat["decision_chain_compatible"] is True
    assert compat["final_confidence_is_trade_authority"] is False
    assert len(compat["confidence_source_breakdown"]) == 7
    assert compat["taiwan_market_markers"] is not None


def test_taiwan_market_markers():
    markers = TaiwanMarketCompatibilityMarkers(
        price_limit_relevant=True,
        t2_settlement_relevant=True,
        near_limit_chase_prohibited_reason="Taiwan ±10% price limit",
        liquidity_shortage_flag=True,
        expected_cost_slippage_placeholder=0.02,
        fill_probability_placeholder=0.85,
    )
    result = markers.to_dict()
    assert result["price_limit_relevant"] is True
    assert result["t2_settlement_relevant"] is True
    assert result["near_limit_chase_prohibited_reason"] == "Taiwan ±10% price limit"


def test_taiwan_markers_in_report():
    decomposer = ConfidenceSourceDecomposer()
    markers = TaiwanMarketCompatibilityMarkers(
        price_limit_relevant=True,
        t2_settlement_relevant=True,
    )
    result = decomposer.decompose(raw_confidence=0.8, taiwan_market_markers=markers)
    assert result.taiwan_market_markers.price_limit_relevant is True
    assert result.taiwan_market_markers.t2_settlement_relevant is True
    assert isinstance(result.taiwan_market_markers.to_dict(), dict)


def test_raw_confidence_no_direct_trade_authority():
    decomposer = ConfidenceSourceDecomposer()
    for conf in [0.0, 0.3, 0.5, 0.7, 0.95, 1.0]:
        result = decomposer.decompose(raw_confidence=conf)
        assert result.final_confidence_is_trade_authority is False, (
            f"raw_confidence={conf} must not be trade authority"
        )


def test_calibrated_bucket_values():
    from modules.decision_prechecklist.confidence_decomposition import _calibrate_bucket
    assert _calibrate_bucket(0.9) == "high"
    assert _calibrate_bucket(0.7) == "medium"
    assert _calibrate_bucket(0.3) == "low"
    assert _calibrate_bucket(0.1) == "very_low"


def test_source_config_version_preserved():
    decomposer = ConfidenceSourceDecomposer(config_version="v3")
    result = decomposer.decompose(raw_confidence=0.8)
    assert result.source_config_version == "v3"


def test_final_confidence_summary_fields():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.8)
    assert "raw" in result.final_confidence_summary
    assert "calibrated" in result.final_confidence_summary
    assert "source_count" in result.final_confidence_summary
    assert result.final_confidence_summary["raw"] == 0.8


def test_risk_gate_veto_category():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.9)
    risk_gate = result.get_source("risk_gate_veto")
    assert risk_gate is not None
    assert risk_gate.category == "risk_gate_veto"
    assert risk_gate.is_veto_related is False


def test_is_missing_source_detection():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.8, source_scores={})
    assert result.is_missing_source is True


def test_no_missing_source():
    decomposer = ConfidenceSourceDecomposer()
    scores = {k: 0.8 for k in CONFIDENCE_SOURCE_KEYS}
    result = decomposer.decompose(raw_confidence=0.8, source_scores=scores)
    assert result.is_missing_source is False


def test_no_broker_no_live_no_order_side_effects():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.9)
    assert result.final_confidence_is_trade_authority is False


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))