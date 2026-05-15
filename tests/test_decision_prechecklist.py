import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.decision_prechecklist import (
    DecisionPreChecklist,
    TradeCandidate,
    NEAEngine,
    PositionSizingEngine,
    ConfidenceCalibrationGuard,
    ConfidenceSourceDecomposer,
)


def make_candidate(**overrides) -> TradeCandidate:
    params = dict(
        symbol="2330.TW",
        side="buy",
        quantity=1000,
        price=150.0,
        signal_source="strategy_backtest",
        confidence_raw=0.8,
        strategy="momentum",
        expected_return=5000.0,
        cost_estimate=0.001,
        slippage_estimate=0.002,
        fill_probability=0.95,
        regime_uncertainty=0.1,
        risk_budget=50000.0,
        current_exposure=100000.0,
        portfolio_value=1000000.0,
        cash_available=200000.0,
        t_plus_2_hold=50000.0,
        avg_daily_volume=5000000,
        max_pct_of_volume=0.01,
        max_position_pct_of_portfolio=0.05,
        strategy_max_pct=0.1,
        regime_max_pct=0.15,
        historical_brier_score=0.2,
        num_past_decisions=50,
        is_taiwan_stock=True,
        taiwan_price_limit_pct=0.1,
        is_collection_auction=False,
        is_odd_lot=False,
        is_suspended=False,
        is_disposition_stock=False,
        is_near_limit_up=False,
        is_near_limit_down=False,
        liquidity_score=0.8,
    )
    params.update(overrides)
    return TradeCandidate(**params)


def test_single_signal_technical_indicator_blocked():
    checklist = DecisionPreChecklist()
    result = checklist.evaluate(make_candidate(signal_source="technical_indicator"))
    assert not result.passed
    assert result.veto_reason_code == "SINGLE_SIGNAL_DIRECT_TRADE"


def test_event_news_social_blocked():
    checklist = DecisionPreChecklist()
    result = checklist.evaluate(make_candidate(signal_source="news_headline"))
    assert not result.passed
    assert result.veto_reason_code == "HIGH_IMPACT_UNCONFIRMED_EVENT"


def test_social_sentiment_blocked():
    checklist = DecisionPreChecklist()
    result = checklist.evaluate(make_candidate(signal_source="social_sentiment"))
    assert not result.passed
    assert result.veto_reason_code == "HIGH_IMPACT_UNCONFIRMED_EVENT"


def test_single_signal_ai_score_blocked():
    checklist = DecisionPreChecklist()
    result = checklist.evaluate(make_candidate(signal_source="ai_score"))
    assert not result.passed
    assert result.veto_reason_code == "SINGLE_SIGNAL_DIRECT_TRADE"


def test_llm_source_blocked():
    checklist = DecisionPreChecklist()
    result = checklist.evaluate(make_candidate(signal_source="llm_recommendation"))
    assert not result.passed
    assert result.veto_reason_code == "LLM_IS_TRADE_CORE"


def test_normal_strategy_passes():
    checklist = DecisionPreChecklist()
    result = checklist.evaluate(make_candidate())
    assert result.passed
    assert result.trace is not None
    assert result.trace.final_decision in ("EXECUTE", "PASS_NO_TRADE")


def test_taiwan_suspended_blocked():
    checklist = DecisionPreChecklist()
    result = checklist.evaluate(make_candidate(is_suspended=True))
    assert not result.passed
    assert any(v["reason_code"] == "TAIWAN_CONSTRAINT" for v in result.vetoes)


def test_taiwan_disposition_stock_blocked():
    checklist = DecisionPreChecklist()
    result = checklist.evaluate(make_candidate(is_disposition_stock=True))
    assert not result.passed
    assert any(v["reason_code"] == "TAIWAN_CONSTRAINT" for v in result.vetoes)


def test_taiwan_near_limit_up_blocked():
    checklist = DecisionPreChecklist()
    result = checklist.evaluate(make_candidate(is_near_limit_up=True))
    assert not result.passed
    assert any(v["reason_code"] == "TAIWAN_CONSTRAINT" for v in result.vetoes)


def test_taiwan_liquidity_insufficient_blocked():
    checklist = DecisionPreChecklist()
    result = checklist.evaluate(make_candidate(liquidity_score=0.2))
    assert not result.passed
    assert any(v["reason_code"] == "TAIWAN_CONSTRAINT" for v in result.vetoes)


def test_nea_edge_below_minimum_blocked():
    nea = NEAEngine(min_net_edge=0.01)
    checklist = DecisionPreChecklist(nea_engine=nea)
    result = checklist.evaluate(make_candidate(expected_return=0.001))
    assert not result.passed
    assert any(v["reason_code"] == "NEA_FAIL" for v in result.vetoes)


def test_nea_fill_probability_low_blocked():
    nea = NEAEngine(min_fill_probability=0.5)
    checklist = DecisionPreChecklist(nea_engine=nea)
    result = checklist.evaluate(make_candidate(fill_probability=0.1))
    assert not result.passed
    assert any(v["reason_code"] == "NEA_FAIL" for v in result.vetoes)


def test_confidence_calibration_low_raw():
    guard = ConfidenceCalibrationGuard()
    result = guard.evaluate(raw_confidence=0.3)
    assert result.veto_reason
    assert result.calibrated_confidence == 0.0


def test_confidence_calibration_high_brier():
    guard = ConfidenceCalibrationGuard()
    result = guard.evaluate(raw_confidence=0.9, historical_brier_score=0.5)
    assert result.calibrated_confidence <= 0.9 * 0.5 * 0.5


def test_position_sizing_respects_all_limits():
    sizing = PositionSizingEngine()
    result = sizing.calculate(
        symbol="2330.TW",
        side="buy",
        price=150.0,
        confidence_calibrated=0.5,
        risk_budget=30000.0,
        current_exposure=100000.0,
        portfolio_value=1000000.0,
        strategy_max_pct=0.1,
        regime_max_pct=0.15,
        cash_available=50000.0,
        t_plus_2_hold=10000.0,
        avg_daily_volume=5000000,
        max_pct_of_volume=0.01,
        max_position_pct_of_portfolio=0.05,
    )
    assert result.passed
    assert result.final_qty <= result.risk_budget_qty
    assert result.final_qty <= result.liquidity_qty
    assert result.final_qty <= result.portfolio_exposure_qty
    assert result.final_qty <= result.strategy_cap_qty
    assert result.final_qty <= result.regime_cap_qty
    assert result.final_qty <= result.cash_available_qty


def test_replay_trace_fields():
    checklist = DecisionPreChecklist()
    result = checklist.evaluate(make_candidate())
    trace = result.trace
    assert trace is not None
    assert trace.trace_id
    assert trace.symbol == "2330.TW"
    assert trace.side == "buy"
    assert trace.final_decision in ("EXECUTE", "PASS_NO_TRADE")
    assert len(trace.decision_chain) >= 4
    assert trace.timestamp
    assert isinstance(trace.risk_snapshot, dict)
    assert isinstance(trace.market_reality_snapshot, dict)


def test_extra_veto_hook():
    def hook(c):
        return "custom veto" if c.symbol == "2330.TW" else None

    checklist = DecisionPreChecklist(extra_veto_hook=hook)
    result = checklist.evaluate(make_candidate())
    assert not result.passed
    assert any(v["reason_code"] == "EXTRA_VETO" for v in result.vetoes)


def test_non_taiwan_stock_no_taiwan_checks():
    checklist = DecisionPreChecklist()
    result = checklist.evaluate(make_candidate(is_taiwan_stock=False))
    assert result.passed


def test_confidence_raw_used_directly_not_above_calibrated():
    guard = ConfidenceCalibrationGuard()
    result = guard.evaluate(raw_confidence=0.99)
    assert result.calibrated_confidence <= result.raw_confidence


def test_confidence_calibration_with_decomposition():
    guard = ConfidenceCalibrationGuard()
    decomposer = ConfidenceSourceDecomposer()
    dec_result = decomposer.decompose(raw_confidence=0.8)
    result = guard.evaluate(raw_confidence=0.8, decomposition=dec_result)
    assert not result.veto_reason
    assert result.calibrated_confidence > 0
    assert result.decomposition is not None
    assert result.decomposition.overall_calibrated > 0


def test_confidence_calibration_with_decomposition_veto():
    guard = ConfidenceCalibrationGuard()
    decomposer = ConfidenceSourceDecomposer()
    dec_result = decomposer.decompose(raw_confidence=0.0)
    result = guard.evaluate(raw_confidence=0.0, decomposition=dec_result)
    assert result.veto_reason
    assert result.calibrated_confidence == 0.0
    assert result.decomposition is not None


def test_checklist_with_decomposer_integration():
    checklist = DecisionPreChecklist()
    result = checklist.evaluate(make_candidate())
    assert result.passed
    assert result.decomposition_result is not None
    assert len(result.decomposition_result.sources) == 7


def test_checklist_decomposer_source_scores_affect_result():
    checklist = DecisionPreChecklist()
    result_good = checklist.evaluate(make_candidate())
    result_bad = checklist.evaluate(make_candidate(
        confidence_decomposition={
            "pattern": 0.1,
            "fundamental": 0.1,
            "regime_alignment": 0.1,
            "signal_source_reliability": 0.1,
            "timeframe_alignment": 0.1,
            "data_quality": 0.1,
            "contradiction_resolution": 0.1,
        }
    ))
    assert result_good.decomposition_result.overall_calibrated > 0
    assert result_bad.decomposition_result.overall_calibrated <= result_good.decomposition_result.overall_calibrated


def test_decomposition_adds_trace_step():
    checklist = DecisionPreChecklist()
    result = checklist.evaluate(make_candidate())
    assert result.trace is not None
    steps = [s for s in result.trace.decision_chain if s.step_name == "confidence_decomposition"]
    assert len(steps) == 1
    assert steps[0].result == "PASS"


def test_placeholder_for_order_fill_pnl_schema():
    assert True


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
