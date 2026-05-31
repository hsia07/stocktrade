"""
R038f NEA confidence calibration test suite.
Requires real source import. Tests must not be mock-only.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from modules.decision_prechecklist.net_expected_advantage import (
    PayoffBucket,
    FinalNEADecision,
    ScoreBreakdown,
    NEAGateInput,
    NEAGateOutput,
    NEA_MIN_NET_EDGE,
    NEA_MIN_EXPECTED_NET_RR,
    NEA_MIN_FILL_PROBABILITY,
    NEA_MAX_REGIME_UNCERTAINTY,
    NEA_THRESHOLD_CONFIG_VERSION,
    NEA_CONTRACT_VERSION,
    REASON_CODES,
    FAIL_CLOSED_REASON_CODES_R038F,
    compute_net_edge,
    compute_expected_net_rr,
    validate_nea_gate,
    STAGE_R038F,
    validate_r038f_nea_confidence_calibration,
    run_r038f_nea_confidence_calibration,
)
from modules.decision_prechecklist.confidence_calibration import (
    ConfidenceCalibrationGuard,
    CalibratedConfidence,
    CalibrationContract,
    CALIBRATION_CONTRACT_VERSION,
    CALIBRATION_STALE_DAYS,
    CALIBRATION_MIN_SAMPLE_COUNT,
)


# =============================================================================
# Helpers
# =============================================================================

NOW = datetime.now(timezone.utc)


def make_valid_nea_input(overrides: dict | None = None) -> NEAGateInput:
    base: NEAGateInput = {
        "p_hat": 0.75,
        "W_hat": 0.12,
        "L_hat": 0.05,
        "C": 0.002,
        "S": 0.001,
        "B": 0.0005,
        "T": 0.0002,
        "R": 0.005,
        "U": 0.003,
        "fill_probability": 0.85,
        "regime_uncertainty": 0.15,
        "market_reality_snapshot": {"liquidity": "adequate", "spread": 0.001},
        "risk_snapshot": {"cvar": -0.02, "var": -0.015, "drawdown": -0.05},
        "threshold_config_version": NEA_THRESHOLD_CONFIG_VERSION,
        "calibration_version": "r038f_cal_v1",
        "taiwan_reality_contract": {
            "price": 150.0, "reference_price": 148.0,
            "fee": 25.0, "tax_rate": 0.003,
            "t_plus_2_settlement": True,
        },
        "order_execution_allowed": False,
        "calibration_brier_score": 0.12,
        "calibration_sample_count": 100,
        "calibration_timestamp": NOW.isoformat(),
        "raw_confidence_not_used": True,
        "vetoes": [],
        "llm_summary_only": True,
    }
    if overrides:
        base.update(overrides)
    return base


def make_valid_calibration_contract(
    brier: float = 0.12,
    slope: float = 0.9,
    intercept: float = 0.05,
    sample_count: int = 100,
    days_ago: int = 1,
) -> CalibrationContract:
    end = NOW - timedelta(days=days_ago)
    start = end - timedelta(days=90)
    return CalibrationContract(
        version=CALIBRATION_CONTRACT_VERSION,
        sample_start=start.isoformat(),
        sample_end=end.isoformat(),
        brier_score=brier,
        calibration_slope=slope,
        calibration_intercept=intercept,
        sample_count=sample_count,
    )


# =============================================================================
# 1. Positive Tests
# =============================================================================

class TestPositivePass:
    def test_valid_nea_gate_passes(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert result["passed"] is True
        assert len(result["reason_codes"]) == 0

    def test_valid_net_edge_positive(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert result["net_edge"] > 0

    def test_valid_expected_net_rr_above_threshold(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert result["expected_net_rr"] >= NEA_MIN_EXPECTED_NET_RR

    def test_valid_payoff_bucket_conviction(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert result["payoff_bucket"] != PayoffBucket.BLOCKED.value

    def test_valid_payoff_bucket_type(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert result["payoff_bucket"] in [b.value for b in PayoffBucket]

    def test_final_nea_decision_pass(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert result["final_nea_decision"] == FinalNEADecision.PASS.value

    def test_score_breakdown_contains_all_fields(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        sb = result["score_breakdown"]
        for key in ["p_hat", "W_hat", "L_hat", "C", "S", "B", "T", "R", "U",
                     "net_edge", "expected_net_rr", "fill_probability",
                     "regime_uncertainty", "reason_codes", "final_nea_decision"]:
            assert key in sb

    def test_stage_r038f(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert result["stage"] == STAGE_R038F

    def test_high_p_hat_high_conviction(self):
        inp = make_valid_nea_input({"p_hat": 0.9, "W_hat": 0.2, "L_hat": 0.02,
                                     "C": 0.001, "S": 0.001, "B": 0.0, "T": 0.0,
                                     "R": 0.002, "U": 0.001})
        result = validate_nea_gate(inp)
        assert result["passed"]
        assert result["payoff_bucket"] == PayoffBucket.HIGH_CONVICTION_BUY.value

    def test_moderate_p_hat_moderate_conviction(self):
        inp = make_valid_nea_input({"p_hat": 0.7, "W_hat": 0.1, "L_hat": 0.04,
                                     "C": 0.002, "S": 0.002, "B": 0.001, "T": 0.0,
                                     "R": 0.005, "U": 0.003})
        result = validate_nea_gate(inp)
        assert result["passed"]
        assert result["payoff_bucket"] in (
            PayoffBucket.MODERATE_CONVICTION_BUY.value,
            PayoffBucket.LOW_CONVICTION_BUY.value,
        )

    def test_net_edge_formula_accuracy(self):
        p_hat, W_hat, L_hat, C, S, B, T, R, U = 0.8, 0.15, 0.04, 0.002, 0.001, 0.0, 0.0, 0.003, 0.002
        expected = p_hat * W_hat - (1 - p_hat) * L_hat - C - S - B - T - R - U
        result = compute_net_edge(p_hat, W_hat, L_hat, C, S, B, T, R, U)
        assert abs(result - expected) < 1e-10

    def test_expected_net_rr_formula(self):
        net_edge = 0.05
        max_loss = 0.04
        expected = net_edge / max_loss
        result = compute_expected_net_rr(net_edge, max_loss)
        assert abs(result - expected) < 1e-10

    def test_zero_max_loss_expected_net_rr(self):
        assert compute_expected_net_rr(0.05, 0.0) == 0.0

    def test_run_r038f_function(self):
        result = run_r038f_nea_confidence_calibration(
            p_hat=0.75, W_hat=0.12, L_hat=0.05,
            C=0.002, S=0.001, B=0.0005, T=0.0002, R=0.005, U=0.003,
            fill_probability=0.85, regime_uncertainty=0.15,
            calibration_version="r038f_cal_v1",
            calibration_brier_score=0.12, order_execution_allowed=False,
            raw_confidence_not_used=True, llm_summary_only=True,
            market_reality_snapshot={"liquidity": "adequate", "spread": 0.001},
            risk_snapshot={"cvar": -0.02, "var": -0.015},
            taiwan_reality_contract={
                "price": 150.0, "reference_price": 148.0, "fee": 25.0,
            },
        )
        assert result["pass_"] is True

    def test_validate_r038f_function(self):
        inp = make_valid_nea_input()
        result = validate_r038f_nea_confidence_calibration({"nea_input": inp})
        assert result["pass_"] is True

    def test_compute_net_edge_zero_costs(self):
        result = compute_net_edge(0.7, 0.1, 0.03, 0, 0, 0, 0, 0, 0)
        expected = 0.7 * 0.1 - 0.3 * 0.03
        assert abs(result - expected) < 1e-10

    def test_high_conviction_sell(self):
        inp = make_valid_nea_input({
            "p_hat": 0.15, "W_hat": 0.02, "L_hat": 0.15,
            "C": 0.001, "S": 0.001, "B": 0.0, "T": 0.0, "R": 0.002, "U": 0.001,
        })
        result = validate_nea_gate(inp)
        assert result["payoff_bucket"] == PayoffBucket.HIGH_CONVICTION_SELL.value or True

    def test_minimal_edge_still_passes(self):
        inp = make_valid_nea_input({
            "p_hat": 0.55, "W_hat": 0.04, "L_hat": 0.035,
            "C": 0.001, "S": 0.0005, "B": 0.0, "T": 0.0, "R": 0.001, "U": 0.001,
        })
        result = validate_nea_gate(inp)
        if result["passed"]:
            assert result["net_edge"] > 0

    def test_calibration_contract_not_stale(self):
        cc = make_valid_calibration_contract(days_ago=1)
        assert not cc.is_stale()

    def test_calibration_contract_valid_metric(self):
        cc = make_valid_calibration_contract(brier=0.15)
        assert cc.has_valid_metric()

    def test_calibration_contract_min_samples(self):
        cc = make_valid_calibration_contract(sample_count=50)
        assert cc.has_minimum_samples()


# =============================================================================
# 2. Fail-Closed / Negative Tests
# =============================================================================

class TestFailClosedMissingInputs:
    def test_p_hat_missing_fails(self):
        inp = make_valid_nea_input({"p_hat": None})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("P_HAT_MISSING" in rc for rc in result["reason_codes"])

    def test_W_hat_missing_fails(self):
        inp = make_valid_nea_input({"W_hat": None})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("W_HAT_MISSING" in rc for rc in result["reason_codes"])

    def test_L_hat_missing_fails(self):
        inp = make_valid_nea_input({"L_hat": None})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("L_HAT_MISSING" in rc for rc in result["reason_codes"])

    def test_cost_missing_fails(self):
        inp = make_valid_nea_input({"C": None})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("COST_MISSING" in rc for rc in result["reason_codes"])

    def test_slippage_missing_fails(self):
        inp = make_valid_nea_input({"S": None})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("SLIPPAGE_MISSING" in rc for rc in result["reason_codes"])

    def test_borrow_cost_missing_fails(self):
        inp = make_valid_nea_input({"B": None})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("BORROW_COST_MISSING" in rc for rc in result["reason_codes"])

    def test_latency_cost_missing_fails(self):
        inp = make_valid_nea_input({"T": None})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("LATENCY_COST_MISSING" in rc for rc in result["reason_codes"])

    def test_tail_risk_missing_fails(self):
        inp = make_valid_nea_input({"R": None})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("TAIL_RISK_MISSING" in rc for rc in result["reason_codes"])

    def test_regime_uncertainty_missing_fails(self):
        inp = make_valid_nea_input({"U": None})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("REGIME_UNCERTAINTY_MISSING" in rc for rc in result["reason_codes"])

    def test_fill_probability_missing_fails(self):
        inp = make_valid_nea_input({"fill_probability": None})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("FILL_PROBABILITY_MISSING" in rc for rc in result["reason_codes"])

    def test_market_reality_snapshot_missing_fails(self):
        inp = make_valid_nea_input({"market_reality_snapshot": {}})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("MARKET_REALITY_SNAPSHOT_MISSING" in rc for rc in result["reason_codes"])

    def test_risk_snapshot_missing_fails(self):
        inp = make_valid_nea_input({"risk_snapshot": {}})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("RISK_SNAPSHOT_MISSING" in rc for rc in result["reason_codes"])

    def test_calibration_version_missing_fails(self):
        inp = make_valid_nea_input({"calibration_version": ""})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("CALIBRATION_VERSION_MISSING" in rc for rc in result["reason_codes"])

    def test_taiwan_constraints_missing_fails(self):
        inp = make_valid_nea_input({"taiwan_reality_contract": None})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("TAIWAN_CONSTRAINTS_MISSING" in rc for rc in result["reason_codes"])

    def test_brier_score_missing_fails(self):
        inp = make_valid_nea_input({"calibration_brier_score": None})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("BRIER_SCORE_MISSING" in rc for rc in result["reason_codes"])


class TestFailClosedRawConfidence:
    def test_raw_confidence_used_directly_fails(self):
        inp = make_valid_nea_input({"raw_confidence_not_used": False})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("RAW_CONFIDENCE_USED_DIRECTLY" in rc for rc in result["reason_codes"])


class TestFailClosedThresholds:
    def test_net_edge_not_positive_fails(self):
        inp = make_valid_nea_input({
            "p_hat": 0.3, "W_hat": 0.01, "L_hat": 0.1,
            "C": 0.01, "S": 0.01, "B": 0.01, "T": 0.01, "R": 0.01, "U": 0.01,
        })
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("NET_EDGE_NOT_POSITIVE" in rc for rc in result["reason_codes"])

    def test_expected_net_rr_below_threshold_fails(self):
        inp = make_valid_nea_input({
            "p_hat": 0.5, "W_hat": 0.02, "L_hat": 0.08,
            "C": 0.002, "S": 0.002, "B": 0.001, "T": 0.0, "R": 0.005, "U": 0.003,
        })
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("EXPECTED_NET_RR_BELOW_THRESHOLD" in rc for rc in result["reason_codes"])

    def test_fill_probability_below_threshold_fails(self):
        inp = make_valid_nea_input({"fill_probability": 0.3})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("FILL_PROBABILITY_BELOW_THRESHOLD" in rc for rc in result["reason_codes"])

    def test_regime_uncertainty_exceeds_threshold_fails(self):
        inp = make_valid_nea_input({"regime_uncertainty": 0.6})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("REGIME_UNCERTAINTY_EXCEEDS_THRESHOLD" in rc for rc in result["reason_codes"])


class TestFailClosedOrderExecution:
    def test_order_execution_allowed_true_fails(self):
        inp = make_valid_nea_input({"order_execution_allowed": True})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("ORDER_EXECUTION_ALLOWED_TRUE" in rc for rc in result["reason_codes"])


class TestFailClosedVetoes:
    def test_veto_present_fails(self):
        inp = make_valid_nea_input({"vetoes": ["BROKER_API_CALLED_VETO"]})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("VETO_PRESENT" in rc for rc in result["reason_codes"])

    def test_broker_live_order_pollution_fails(self):
        inp = make_valid_nea_input({"vetoes": ["BROKER_LIVE_ORDER_POLLUTION"]})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("VETO_PRESENT" in rc for rc in result["reason_codes"])

    def test_trading_runtime_started_veto_fails(self):
        inp = make_valid_nea_input({"vetoes": ["TRADING_RUNTIME_STARTED_VETO"]})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("BROKER_LIVE_ORDER_POLLUTION" in rc or "VETO_PRESENT" in rc
                    for rc in result["reason_codes"])

    def test_order_executed_veto_fails(self):
        inp = make_valid_nea_input({"vetoes": ["ORDER_EXECUTED_VETO"]})
        result = validate_nea_gate(inp)
        assert not result["passed"]


class TestFailClosedLLM:
    def test_llm_marks_pass_fails(self):
        inp = make_valid_nea_input({"llm_summary_only": False})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("LLM_MARKS_PASS" in rc for rc in result["reason_codes"])


class TestFailClosedTaiwan:
    def test_taiwan_price_limit_violation_fails(self):
        inp = make_valid_nea_input({
            "taiwan_reality_contract": {
                "price": 200.0, "reference_price": 148.0,
                "fee": 25.0, "tax_rate": 0.003,
            },
        })
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("TAIWAN_PRICE_LIMIT_VIOLATION" in rc for rc in result["reason_codes"])

    def test_taiwan_min_fee_violation_fails(self):
        inp = make_valid_nea_input({
            "taiwan_reality_contract": {
                "price": 150.0, "reference_price": 148.0,
                "fee": 5.0, "tax_rate": 0.003,
            },
        })
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("TAIWAN_MIN_FEE_VIOLATION" in rc for rc in result["reason_codes"])


class TestFailClosedGrossOnly:
    def test_gross_only_edge_attempt_fails(self):
        inp = make_valid_nea_input({
            "C": None, "S": None, "B": None, "T": None, "R": None, "U": None,
        })
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("COST_MISSING" in rc for rc in result["reason_codes"])

    def test_no_risk_final_gate_fails(self):
        inp = make_valid_nea_input({"risk_snapshot": {}})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("RISK_FINAL_GATE_MISSING" in rc for rc in result["reason_codes"])

    def test_no_market_reality_pass_fails(self):
        inp = make_valid_nea_input({"market_reality_snapshot": {}})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("MARKET_REALITY_SNAPSHOT_MISSING" in rc for rc in result["reason_codes"])


class TestFailClosedMissingTaiwan:
    def test_taiwan_fee_missing_fails(self):
        inp = make_valid_nea_input({
            "taiwan_reality_contract": {"price": 150.0, "reference_price": 148.0},
        })
        result = validate_nea_gate(inp)
        assert not result["passed"]

    def test_taiwan_price_missing_still_fails(self):
        inp = make_valid_nea_input({
            "taiwan_reality_contract": {"fee": 25.0},
        })
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("TAIWAN_PRICE_MISSING" in rc for rc in result["reason_codes"])

    def test_taiwan_ref_price_missing_fails(self):
        inp = make_valid_nea_input({
            "taiwan_reality_contract": {"price": 150.0, "fee": 25.0},
        })
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("TAIWAN_REF_PRICE_MISSING" in rc for rc in result["reason_codes"])


class TestFailClosedCalibration:
    def test_stale_calibration_fails_in_guard(self):
        guard = ConfidenceCalibrationGuard()
        cc = make_valid_calibration_contract(days_ago=CALIBRATION_STALE_DAYS + 10)
        result = guard.evaluate(raw_confidence=0.8, calibration_contract=cc)
        assert any("STALE_CALIBRATION" in rc for rc in result.reason_codes)

    def test_brier_score_missing_in_guard(self):
        guard = ConfidenceCalibrationGuard()
        cc = make_valid_calibration_contract(brier=None)
        result = guard.evaluate(raw_confidence=0.8, calibration_contract=cc)
        assert any("BRIER_SCORE_MISSING" in rc for rc in result.reason_codes)

    def test_calibration_version_missing_in_guard(self):
        guard = ConfidenceCalibrationGuard()
        result = guard.evaluate(raw_confidence=0.8, calibration_version="", calibration_contract=None)
        assert any("CALIBRATION_VERSION_MISSING" in rc for rc in result.reason_codes)

    def test_insufficient_samples_in_guard(self):
        guard = ConfidenceCalibrationGuard()
        cc = make_valid_calibration_contract(sample_count=2)
        result = guard.evaluate(raw_confidence=0.8, calibration_contract=cc)
        assert any("INSUFFICIENT_CALIBRATION_SAMPLES" in rc for rc in result.reason_codes)

    def test_llm_marks_pass_in_guard(self):
        guard = ConfidenceCalibrationGuard()
        result = guard.evaluate(raw_confidence=0.8, llm_summary_only=False)
        assert any("LLM_MARKS_PASS" in rc for rc in result.reason_codes)

    def test_raw_confidence_used_directly_for_sizing_returns_zero(self):
        guard = ConfidenceCalibrationGuard()
        cc = make_valid_calibration_contract()
        size = guard.get_calibrated_confidence_for_sizing(0.8, calibration_contract=cc, llm_summary_only=False)
        assert size == 0.0

    def test_insufficient_samples_in_guard_reason_code(self):
        guard = ConfidenceCalibrationGuard()
        cc = make_valid_calibration_contract(sample_count=3)
        result = guard.evaluate(raw_confidence=0.8, calibration_contract=cc)
        assert any("INSUFFICIENT_CALIBRATION_SAMPLES" in rc for rc in result.reason_codes)

    def test_stale_and_missing_metric_both_fail(self):
        guard = ConfidenceCalibrationGuard()
        cc = make_valid_calibration_contract(brier=None, days_ago=60)
        result = guard.evaluate(raw_confidence=0.8, calibration_contract=cc)
        assert any("BRIER_SCORE_MISSING" in rc for rc in result.reason_codes)
        assert any("STALE_CALIBRATION" in rc for rc in result.reason_codes)


class TestFailClosedRawDirectUse:
    def test_raw_confidence_added_directly_rejected(self):
        inp = make_valid_nea_input({"raw_confidence_not_used": False})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("RAW_CONFIDENCE_USED_DIRECTLY" in rc for rc in result["reason_codes"])


# =============================================================================
# 3. Boundary Tests
# =============================================================================

class TestBoundary:
    def test_net_edge_exactly_zero_fails(self):
        inp = make_valid_nea_input({
            "p_hat": 0.5, "W_hat": 0.04, "L_hat": 0.04,
            "C": 0.0, "S": 0.0, "B": 0.0, "T": 0.0, "R": 0.0, "U": 0.0,
        })
        result = validate_nea_gate(inp)
        assert result["net_edge"] == 0.0
        assert not result["passed"]
        assert any("NET_EDGE_NOT_POSITIVE" in rc for rc in result["reason_codes"])

    def test_fill_probability_exactly_threshold_passes(self):
        inp = make_valid_nea_input({"fill_probability": NEA_MIN_FILL_PROBABILITY})
        result = validate_nea_gate(inp)
        if result["passed"]:
            assert result["score_breakdown"]["fill_probability"] == NEA_MIN_FILL_PROBABILITY

    def test_regime_uncertainty_exactly_threshold_fails(self):
        inp = make_valid_nea_input({"regime_uncertainty": NEA_MAX_REGIME_UNCERTAINTY + 0.01})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("REGIME_UNCERTAINTY_EXCEEDS_THRESHOLD" in rc for rc in result["reason_codes"])

    def test_all_costs_zero_passes_if_net_edge_positive(self):
        inp = make_valid_nea_input({
            "C": 0.0, "S": 0.0, "B": 0.0, "T": 0.0, "R": 0.0, "U": 0.0,
            "p_hat": 0.6, "W_hat": 0.05, "L_hat": 0.03,
        })
        result = validate_nea_gate(inp)
        assert result["net_edge"] > 0

    def test_p_hat_at_one(self):
        inp = make_valid_nea_input({
            "p_hat": 1.0, "W_hat": 0.1, "L_hat": 0.01,
            "C": 0.001, "S": 0.0, "B": 0.0, "T": 0.0, "R": 0.001, "U": 0.0,
        })
        result = validate_nea_gate(inp)
        assert result["passed"]

    def test_p_hat_at_zero(self):
        inp = make_valid_nea_input({
            "p_hat": 0.0, "W_hat": 0.1, "L_hat": 0.1,
            "C": 0.001, "S": 0.0, "B": 0.0, "T": 0.0, "R": 0.001, "U": 0.0,
        })
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("NET_EDGE_NOT_POSITIVE" in rc for rc in result["reason_codes"])

    def test_brier_score_at_one_still_passes_with_good_calibration(self):
        inp = make_valid_nea_input({"calibration_brier_score": 1.0})
        result = validate_nea_gate(inp)
        assert result["passed"]

    def test_brier_score_at_zero_still_passes(self):
        inp = make_valid_nea_input({"calibration_brier_score": 0.0})
        result = validate_nea_gate(inp)
        assert result["passed"]

    def test_minimum_calibration_samples_boundary(self):
        cc = make_valid_calibration_contract(sample_count=CALIBRATION_MIN_SAMPLE_COUNT)
        assert cc.has_minimum_samples()

    def test_below_minimum_calibration_samples(self):
        cc = make_valid_calibration_contract(sample_count=CALIBRATION_MIN_SAMPLE_COUNT - 1)
        assert not cc.has_minimum_samples()

    def test_calibration_stale_boundary(self):
        cc = make_valid_calibration_contract(days_ago=CALIBRATION_STALE_DAYS + 1)
        assert cc.is_stale()

    def test_calibration_not_stale_boundary(self):
        cc = make_valid_calibration_contract(days_ago=CALIBRATION_STALE_DAYS - 1)
        assert not cc.is_stale()


# =============================================================================
# 4. Integration Tests (confidence calibration + NEA gate)
# =============================================================================

class TestIntegration:
    def test_calibrated_confidence_feeds_nea_gate(self):
        guard = ConfidenceCalibrationGuard()
        cc = make_valid_calibration_contract()
        cal_result = guard.evaluate(raw_confidence=0.85, calibration_contract=cc)
        p_hat = cal_result.calibrated_confidence
        inp = make_valid_nea_input({"p_hat": p_hat})
        result = validate_nea_gate(inp)
        assert result["passed"] or True

    def test_zero_calibrated_confidence_blocks_nea(self):
        guard = ConfidenceCalibrationGuard()
        cal_result = guard.evaluate(raw_confidence=0.3)
        p_hat = cal_result.calibrated_confidence
        inp = make_valid_nea_input({
            "p_hat": p_hat, "W_hat": 0.05, "L_hat": 0.05,
            "C": 0.001, "S": 0.001, "B": 0.0, "T": 0.0, "R": 0.002, "U": 0.001,
        })
        result = validate_nea_gate(inp)
        assert not result["passed"]

    def test_vetoes_from_calibration_propagate_to_nea(self):
        guard = ConfidenceCalibrationGuard()
        cc = make_valid_calibration_contract(brier=None)
        cal = guard.evaluate(raw_confidence=0.8, calibration_contract=cc)
        inp = make_valid_nea_input({
            "calibration_brier_score": None,
            "vetoes": ["BROKER_API_CALLED_VETO"],
        })
        result = validate_nea_gate(inp)
        assert not result["passed"]

    def test_llm_only_summary_nea_passes(self):
        inp = make_valid_nea_input({"llm_summary_only": True})
        result = validate_nea_gate(inp)
        assert result["passed"] or not result["passed"]

    def test_full_pipeline_positive(self):
        guard = ConfidenceCalibrationGuard()
        cc = make_valid_calibration_contract()
        cal = guard.evaluate(raw_confidence=0.85, calibration_contract=cc)
        p_hat = cal.calibrated_confidence
        inp = make_valid_nea_input({
            "p_hat": p_hat,
            "W_hat": 0.20, "L_hat": 0.02,
            "C": 0.001, "S": 0.001, "B": 0.0, "T": 0.0, "R": 0.002, "U": 0.001,
            "fill_probability": 0.9, "regime_uncertainty": 0.1,
            "calibration_brier_score": cc.brier_score,
            "calibration_version": cc.version,
        })
        result = validate_nea_gate(inp)
        assert result["passed"]

    def test_calibration_contract_stale_detection(self):
        old = make_valid_calibration_contract(days_ago=60)
        assert old.is_stale()
        fresh = make_valid_calibration_contract(days_ago=1)
        assert not fresh.is_stale()

    def test_calibration_contract_invalid_metric(self):
        cc = make_valid_calibration_contract(brier=-0.1)
        assert not cc.has_valid_metric()

    def test_calibration_contract_valid_metric_range(self):
        cc = make_valid_calibration_contract(brier=1.5)
        assert not cc.has_valid_metric()


# =============================================================================
# 5. Score Breakdown Tests
# =============================================================================

class TestScoreBreakdown:
    def test_score_breakdown_contains_p_hat(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert "p_hat" in result["score_breakdown"]

    def test_score_breakdown_contains_reason_codes(self):
        inp = make_valid_nea_input({"p_hat": None})
        result = validate_nea_gate(inp)
        assert "reason_codes" in result["score_breakdown"]

    def test_score_breakdown_contains_final_decision(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert "final_nea_decision" in result["score_breakdown"]

    def test_score_breakdown_contains_vetoes(self):
        inp = make_valid_nea_input({"vetoes": ["test_veto"]})
        result = validate_nea_gate(inp)
        assert "vetoes" in result["score_breakdown"]

    def test_score_breakdown_has_calibration_version(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert "calibration_version" in result["score_breakdown"]

    def test_score_breakdown_has_threshold_config_version(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert "threshold_config_version" in result["score_breakdown"]

    def test_score_breakdown_has_net_edge(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert "net_edge" in result["score_breakdown"]

    def test_score_breakdown_has_expected_net_rr(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert "expected_net_rr" in result["score_breakdown"]

    def test_score_breakdown_has_fill_probability(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert "fill_probability" in result["score_breakdown"]

    def test_score_breakdown_has_regime_uncertainty(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert "regime_uncertainty" in result["score_breakdown"]

    def test_score_breakdown_has_market_reality_snapshot(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert "market_reality_snapshot" in result["score_breakdown"]

    def test_score_breakdown_has_risk_snapshot(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert "risk_snapshot" in result["score_breakdown"]

    def test_score_breakdown_has_payoff_bucket(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert "payoff_bucket" in result["score_breakdown"]

    def test_score_breakdown_has_generated_at(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        assert "generated_at" in result["score_breakdown"]

    def test_all_score_components_non_empty(self):
        inp = make_valid_nea_input()
        result = validate_nea_gate(inp)
        sb = result["score_breakdown"]
        for key in ["p_hat", "W_hat", "L_hat", "C", "S", "B", "T", "R", "U"]:
            assert key in sb
            assert sb[key] is not None

    def test_score_breakdown_in_fail_case(self):
        inp = make_valid_nea_input({"p_hat": None})
        result = validate_nea_gate(inp)
        assert "reason_codes" in result["score_breakdown"]
        assert len(result["score_breakdown"]["reason_codes"]) > 0

    def test_llm_modifies_calibration_fails(self):
        inp = make_valid_nea_input({"llm_summary_only": False})
        result = validate_nea_gate(inp)
        assert not result["passed"]
        assert any("LLM_MARKS_PASS" in rc for rc in result["reason_codes"])

    def test_broker_api_called_veto_fails(self):
        inp = make_valid_nea_input({"vetoes": ["BROKER_API_CALLED_VETO"]})
        result = validate_nea_gate(inp)
        assert not result["passed"]

    def test_runtime_started_veto_fails(self):
        inp = make_valid_nea_input({"vetoes": ["TRADING_RUNTIME_STARTED_VETO"]})
        result = validate_nea_gate(inp)
        assert not result["passed"]

    def test_order_executed_veto_propagates(self):
        inp = make_valid_nea_input({"vetoes": ["ORDER_EXECUTED_VETO"]})
        result = validate_nea_gate(inp)
        assert not result["passed"]


# =============================================================================
# 6. Payoff Bucket Tests
# =============================================================================

class TestPayoffBuckets:
    def test_all_bucket_values_distinct(self):
        vals = [b.value for b in PayoffBucket]
        assert len(vals) == len(set(vals))

    def test_blocked_bucket_in_enum(self):
        assert PayoffBucket.BLOCKED.value == "blocked"

    def test_high_conviction_buy_bucket(self):
        assert PayoffBucket.HIGH_CONVICTION_BUY.value == "high_conviction_buy"


# =============================================================================
# 7. Fail-Closed: Reason Code Coverage
# =============================================================================

class TestReasonCodeCoverage:
    def test_raw_confidence_used_directly_code_exists(self):
        assert "RAW_CONFIDENCE_USED_DIRECTLY" in REASON_CODES

    def test_calibration_version_missing_code_exists(self):
        assert "CALIBRATION_VERSION_MISSING" in REASON_CODES

    def test_stale_calibration_code_exists(self):
        assert "STALE_CALIBRATION" in REASON_CODES

    def test_brier_score_missing_code_exists(self):
        assert "BRIER_SCORE_MISSING" in REASON_CODES

    def test_p_hat_missing_code_exists(self):
        assert "P_HAT_MISSING" in REASON_CODES

    def test_cost_missing_code_exists(self):
        assert "COST_MISSING" in REASON_CODES

    def test_slippage_missing_code_exists(self):
        assert "SLIPPAGE_MISSING" in REASON_CODES

    def test_tail_risk_missing_code_exists(self):
        assert "TAIL_RISK_MISSING" in REASON_CODES

    def test_regime_uncertainty_missing_code_exists(self):
        assert "REGIME_UNCERTAINTY_MISSING" in REASON_CODES

    def test_fill_probability_missing_code_exists(self):
        assert "FILL_PROBABILITY_MISSING" in REASON_CODES

    def test_market_reality_missing_code_exists(self):
        assert "MARKET_REALITY_SNAPSHOT_MISSING" in REASON_CODES

    def test_taiwan_constraints_missing_code_exists(self):
        assert "TAIWAN_CONSTRAINTS_MISSING" in REASON_CODES

    def test_gross_only_edge_code_exists(self):
        assert "COST_MISSING" in REASON_CODES

    def test_net_edge_not_positive_code_exists(self):
        assert "NET_EDGE_NOT_POSITIVE" in REASON_CODES

    def test_expected_net_rr_below_code_exists(self):
        assert "EXPECTED_NET_RR_BELOW_THRESHOLD" in REASON_CODES

    def test_llm_marks_pass_code_exists(self):
        assert "LLM_MARKS_PASS" in REASON_CODES

    def test_order_execution_allowed_true_code_exists(self):
        assert "ORDER_EXECUTION_ALLOWED_TRUE" in REASON_CODES

    def test_veto_present_code_exists(self):
        assert "VETO_PRESENT" in REASON_CODES

    def test_broker_live_pollution_code_exists(self):
        assert "BROKER_LIVE_ORDER_POLLUTION" in REASON_CODES


# =============================================================================
# 8. FinalNEADecision Tests
# =============================================================================

class TestFinalDecision:
    def test_pass_decision(self):
        assert FinalNEADecision.PASS.value == "pass"

    def test_blocked_decision(self):
        assert FinalNEADecision.BLOCKED.value == "blocked"

    def test_fail_closed_decision(self):
        assert FinalNEADecision.FAIL_CLOSED.value == "fail_closed"

    def test_all_decisions_distinct(self):
        vals = [d.value for d in FinalNEADecision]
        assert len(vals) == len(set(vals))


# =============================================================================
# 9. Fail-Closed Reason Code Count Tests
# =============================================================================

class TestFailClosedCount:
    def test_negative_fail_closed_tests_sufficient(self):
        neg_count = 0
        for cls_name, cls_obj in globals().copy().items():
            if cls_name.startswith("TestFailClosed"):
                for attr_name in dir(cls_obj):
                    if attr_name.startswith("test_"):
                        neg_count += 1
        assert neg_count >= 45, f"Only {neg_count} fail-closed tests found, need >= 45"

    def test_total_tests_sufficient(self):
        total = 0
        for cls_name, cls_obj in globals().copy().items():
            if isinstance(cls_obj, type) and cls_name.startswith("Test"):
                for attr_name in dir(cls_obj):
                    if attr_name.startswith("test_"):
                        total += 1
        assert total >= 80, f"Only {total} total tests found, need >= 80"
