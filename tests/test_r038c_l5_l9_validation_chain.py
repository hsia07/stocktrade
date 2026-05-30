from modules.decision_prechecklist.l5_l9_validation_chain import (
    L5WalkForwardOOSEvidence,
    L6RegimeSegmentEvidence,
    L7CombinatorialPurgedCVEvidence,
    L8PSRRealityCheckSPAEvidence,
    L9PaperTradingReadinessEvidence,
    L5L9ValidationInput,
    L5L9ValidationResult,
    L5L9ValidationStatus,
    L5L9ValidationLevel,
    STAGE_R038C,
    FAIL_CLOSED_REASON_CODES_R038C,
    validate_l5_walk_forward_oos,
    validate_l6_regime_segmentation,
    validate_l7_combinatorial_purged_cv,
    validate_l8_psr_reality_check_spa,
    validate_l9_paper_trading_readiness,
    validate_l5_l9_chain,
    run_r038c_l5_l9_validation_chain,
    MIN_OOS_WINDOW_COUNT,
    MIN_REGIME_COUNT,
    MIN_SAMPLES_PER_REGIME,
    MIN_FOLD_COUNT,
    MIN_COMBO_SPLIT_COUNT,
    MIN_PAPER_MONTHS,
    MIN_PAPER_TRADING_DAYS,
    MIN_PAPER_TRADE_COUNT,
    DEFAULT_ADJUSTED_P_THRESHOLD,
    DEFAULT_SLIPPAGE_DRIFT_THRESHOLD,
    DEFAULT_FILL_RATE_DRIFT_THRESHOLD,
)
from modules.decision_prechecklist.cicd_verification_chain import (
    CICDVerificationChain,
    CICDStageResult,
    R038C_STAGE_NAME,
)


# ============================================================
# Positive tests
# ============================================================

def test_complete_l5_l9_evidence_passes():
    inp = make_complete_input()
    result = validate_l5_l9_chain(inp)
    assert result.validation_passed is True
    assert result.status == L5L9ValidationStatus.PASS
    assert len(result.failed_levels) == 0
    assert len(result.passed_levels) == 5
    assert result.order_execution_allowed is False


def test_cicd_verification_chain_calls_r038c_stage():
    chain = CICDVerificationChain()
    inp = make_complete_input()
    result = chain.validate_l5_l9_validation_chain(inp)
    assert result.validation_passed is True
    assert len(result.levels_checked) == 5


def test_cicd_verification_chain_r038c_stage_returns_deterministic_result():
    chain = CICDVerificationChain()
    inp = make_complete_input()
    result_dict = chain.run_r038c_stage(inp)
    assert result_dict["stage"] == STAGE_R038C
    assert result_dict["validation_passed"] is True
    assert result_dict["net_of_cost_required"] is True
    assert result_dict["market_reality_required"] is True
    assert result_dict["replay_required"] is True
    assert result_dict["tradingview_only_rejected"] is True
    assert result_dict["order_execution_allowed"] is False


def test_cicd_pipeline_r038c_stage_type():
    chain = CICDVerificationChain()
    inp = make_complete_input()
    stages = [{"type": "r038c_l5_l9", "name": "R038c_test", "input": inp}]
    pipeline_result = chain.run_pipeline(stages)
    assert pipeline_result.all_passed is True
    assert len(pipeline_result.stages) == 1
    assert pipeline_result.stages[0].passed is True
    assert pipeline_result.stages[0].name == "R038c_test"


def test_run_r038c_l5_l9_validation_chain_returns_dict():
    inp = make_complete_input()
    result_dict = run_r038c_l5_l9_validation_chain(inp)
    assert isinstance(result_dict, dict)
    assert result_dict["stage"] == STAGE_R038C
    assert result_dict["validation_passed"] is True
    for level in ["L5", "L6", "L7", "L8", "L9"]:
        assert level in result_dict["levels_checked"]


def test_l5_walk_forward_valid_evidence_no_codes():
    ev = make_l5_complete()
    codes = validate_l5_walk_forward_oos(ev)
    assert len(codes) == 0


def test_l6_regime_segmentation_valid_evidence_no_codes():
    ev = make_l6_complete()
    codes = validate_l6_regime_segmentation(ev)
    assert len(codes) == 0


def test_l7_combinatorial_purged_cv_valid_evidence_no_codes():
    ev = make_l7_complete()
    codes = validate_l7_combinatorial_purged_cv(ev)
    assert len(codes) == 0


def test_l8_psr_reality_check_spa_valid_evidence_no_codes():
    ev = make_l8_complete()
    codes = validate_l8_psr_reality_check_spa(ev)
    assert len(codes) == 0


def test_l9_paper_trading_readiness_valid_evidence_no_codes():
    ev = make_l9_complete()
    codes = validate_l9_paper_trading_readiness(ev)
    assert len(codes) == 0


def test_l5_l9_validation_level_enum_values():
    assert L5L9ValidationLevel.L5.value == "L5"
    assert L5L9ValidationLevel.L6.value == "L6"
    assert L5L9ValidationLevel.L7.value == "L7"
    assert L5L9ValidationLevel.L8.value == "L8"
    assert L5L9ValidationLevel.L9.value == "L9"


def test_stage_r038c_constant():
    assert STAGE_R038C == "R038c_l5_l9_validation_chain"


def test_fail_closed_reason_codes_populated():
    assert len(FAIL_CLOSED_REASON_CODES_R038C) > 0
    assert "L5_OOS_WINDOWS_MISSING" in FAIL_CLOSED_REASON_CODES_R038C
    assert "L6_SINGLE_REGIME_ONLY" in FAIL_CLOSED_REASON_CODES_R038C
    assert "L7_ORDINARY_RANDOM_KFOLD_ONLY" in FAIL_CLOSED_REASON_CODES_R038C
    assert "L8_RAW_SHARPE_ONLY" in FAIL_CLOSED_REASON_CODES_R038C
    assert "L9_PAPER_DURATION_BELOW_MINIMUM" in FAIL_CLOSED_REASON_CODES_R038C


def test_result_to_dict_and_hash():
    inp = make_complete_input()
    result = validate_l5_l9_chain(inp)
    d = result.to_dict()
    assert d["stage"] == STAGE_R038C
    assert isinstance(d["reason_codes"], list)
    h = result.compute_result_hash()
    assert isinstance(h, str)
    assert len(h) == 64


# ============================================================
# Negative / fail-closed tests - L5 Walk-Forward OOS
# ============================================================

def test_l5_missing_oos_windows_fails():
    ev = make_l5_complete()
    ev.oos_window_count = 0
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_OOS_WINDOWS_MISSING" in codes


def test_l5_missing_final_oos_period_fails():
    ev = make_l5_complete()
    ev.final_out_of_sample_period = ""
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_FINAL_OOS_PERIOD_MISSING" in codes


def test_l5_oos_window_count_below_threshold_fails():
    ev = make_l5_complete()
    ev.oos_window_count = MIN_OOS_WINDOW_COUNT - 1
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_OOS_WINDOW_COUNT_BELOW_THRESHOLD" in codes


def test_l5_train_test_overlap_fails():
    ev = make_l5_complete()
    ev.no_training_overlap_with_oos = False
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_TRAIN_TEST_OVERLAP" in codes


def test_l5_future_leak_fails():
    ev = make_l5_complete()
    ev.no_future_leak = False
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_FUTURE_LEAK" in codes


def test_l5_replay_not_compatible_fails():
    ev = make_l5_complete()
    ev.as_of_replay_compatible = False
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_AS_OF_REPLAY_NOT_COMPATIBLE" in codes


def test_l5_oos_result_gross_only_fails():
    ev = make_l5_complete()
    ev.net_of_cost_oos_result = None
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_OOS_RESULT_GROSS_ONLY" in codes


def test_l5_cost_model_missing_fails():
    ev = make_l5_complete()
    ev.cost_model_version = ""
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_COST_MODEL_MISSING" in codes


def test_l5_slippage_model_missing_fails():
    ev = make_l5_complete()
    ev.slippage_model_version = ""
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_SLIPPAGE_MODEL_MISSING" in codes


def test_l5_market_reality_not_compatible_fails():
    ev = make_l5_complete()
    ev.market_reality_compatible = False
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_MARKET_REALITY_NOT_COMPATIBLE" in codes


def test_l5_risk_gate_replay_not_compatible_fails():
    ev = make_l5_complete()
    ev.risk_gate_replay_compatible = False
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_RISK_GATE_REPLAY_NOT_COMPATIBLE" in codes


def test_l5_oos_negative_after_cost_fails():
    ev = make_l5_complete()
    ev.net_of_cost_oos_result = -100.0
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_OOS_NEGATIVE_AFTER_COST" in codes


def test_l5_tradingview_only_fails():
    ev = make_l5_complete()
    ev.evidence_source = "tradingview"
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_TRADINGVIEW_ONLY" in codes


def test_l5_pine_only_fails():
    ev = make_l5_complete()
    ev.evidence_source = "pine"
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_TRADINGVIEW_ONLY" in codes


def test_l5_deeptest_only_fails():
    ev = make_l5_complete()
    ev.evidence_source = "deeptest"
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_TRADINGVIEW_ONLY" in codes


def test_l5_none_evidence_fails():
    codes = validate_l5_walk_forward_oos(None)
    assert "L5_OOS_WINDOWS_MISSING" in codes
    assert "L5_FINAL_OOS_PERIOD_MISSING" in codes
    assert "L5_COST_MODEL_MISSING" in codes


# ============================================================
# Negative / fail-closed tests - L6 Regime Segmentation
# ============================================================

def test_l6_single_regime_only_fails():
    ev = make_l6_complete()
    ev.regime_count = 1
    codes = validate_l6_regime_segmentation(ev)
    assert "L6_SINGLE_REGIME_ONLY" in codes


def test_l6_regime_labels_missing_fails():
    ev = make_l6_complete()
    ev.regime_labels = []
    codes = validate_l6_regime_segmentation(ev)
    assert "L6_REGIME_LABELS_MISSING" in codes


def test_l6_insufficient_samples_per_regime_fails():
    ev = make_l6_complete()
    ev.per_regime_sample_count = {"bull": 5, "bear": 3}
    codes = validate_l6_regime_segmentation(ev)
    assert "L6_INSUFFICIENT_SAMPLES_PER_REGIME" in codes


def test_l6_per_regime_result_gross_only_fails():
    ev = make_l6_complete()
    ev.per_regime_net_of_cost_result = {}
    codes = validate_l6_regime_segmentation(ev)
    assert "L6_PER_REGIME_RESULT_GROSS_ONLY" in codes


def test_l6_aggregate_only_hides_failed_fails():
    ev = make_l6_complete()
    ev.per_regime_net_of_cost_result = {}
    ev.aggregate_net_of_cost_result = 1000.0
    codes = validate_l6_regime_segmentation(ev)
    assert "L6_AGGREGATE_ONLY_HIDES_FAILED" in codes


def test_l6_hindsight_regime_for_live_fails():
    ev = make_l6_complete()
    ev.hindsight_regime_smoothed_for_live = True
    codes = validate_l6_regime_segmentation(ev)
    assert "L6_HINDSIGHT_REGIME_FOR_LIVE" in codes


def test_l6_no_hindsight_regime_for_live_also_fails_when_not_set():
    ev = make_l6_complete()
    ev.hindsight_regime_smoothed_for_live = False
    ev.no_hindsight_regime_for_live = False
    codes = validate_l6_regime_segmentation(ev)
    assert "L6_HINDSIGHT_REGIME_FOR_LIVE" in codes


def test_l6_online_filter_posterior_missing_fails():
    ev = make_l6_complete()
    ev.offline_labeler_vs_online_filter_declared = False
    codes = validate_l6_regime_segmentation(ev)
    assert "L6_ONLINE_FILTER_POSTERIOR_MISSING" in codes


def test_l6_uncertainty_threshold_missing_fails():
    ev = make_l6_complete()
    ev.regime_uncertainty_policy_present = False
    codes = validate_l6_regime_segmentation(ev)
    assert "L6_UNCERTAINTY_THRESHOLD_MISSING" in codes


def test_l6_regime_market_reality_not_compatible_fails():
    ev = make_l6_complete()
    ev.market_reality_compatible_per_regime = False
    codes = validate_l6_regime_segmentation(ev)
    assert "L6_REGIME_MARKET_REALITY_NOT_COMPATIBLE" in codes


def test_l6_none_evidence_fails():
    codes = validate_l6_regime_segmentation(None)
    assert "L6_SINGLE_REGIME_ONLY" in codes
    assert "L6_REGIME_LABELS_MISSING" in codes
    assert "L6_PER_REGIME_RESULT_GROSS_ONLY" in codes


# ============================================================
# Negative / fail-closed tests - L7 Combinatorial Purged CV
# ============================================================

def test_l7_ordinary_random_kfold_only_fails():
    ev = make_l7_complete()
    ev.fold_count = 0
    ev.combinatorial_split_count = 0
    codes = validate_l7_combinatorial_purged_cv(ev)
    assert "L7_ORDINARY_RANDOM_KFOLD_ONLY" in codes


def test_l7_purge_window_missing_fails():
    ev = make_l7_complete()
    ev.purge_window = 0
    codes = validate_l7_combinatorial_purged_cv(ev)
    assert "L7_PURGE_WINDOW_MISSING" in codes


def test_l7_embargo_window_missing_fails():
    ev = make_l7_complete()
    ev.embargo_window = 0
    codes = validate_l7_combinatorial_purged_cv(ev)
    assert "L7_EMBARGO_WINDOW_MISSING" in codes


def test_l7_fold_count_below_threshold_fails():
    ev = make_l7_complete()
    ev.fold_count = MIN_FOLD_COUNT - 1
    codes = validate_l7_combinatorial_purged_cv(ev)
    assert "L7_FOLD_COUNT_BELOW_THRESHOLD" in codes


def test_l7_combo_split_count_below_threshold_fails():
    ev = make_l7_complete()
    ev.combinatorial_split_count = MIN_COMBO_SPLIT_COUNT - 1
    codes = validate_l7_combinatorial_purged_cv(ev)
    assert "L7_COMBO_SPLIT_COUNT_BELOW_THRESHOLD" in codes


def test_l7_time_series_order_not_preserved_fails():
    ev = make_l7_complete()
    ev.time_series_order_preserved = False
    codes = validate_l7_combinatorial_purged_cv(ev)
    assert "L7_TIME_SERIES_ORDER_NOT_PRESERVED" in codes


def test_l7_label_overlap_leakage_fails():
    ev = make_l7_complete()
    ev.overlapping_label_protection = False
    codes = validate_l7_combinatorial_purged_cv(ev)
    assert "L7_LABEL_OVERLAP_LEAKAGE" in codes


def test_l7_leakage_gap_not_declared_fails():
    ev = make_l7_complete()
    ev.leakage_gap_declared = False
    codes = validate_l7_combinatorial_purged_cv(ev)
    assert "L7_LEAKAGE_GAP_NOT_DECLARED" in codes


def test_l7_per_fold_result_gross_only_fails():
    ev = make_l7_complete()
    ev.per_fold_net_of_cost_result = []
    codes = validate_l7_combinatorial_purged_cv(ev)
    assert "L7_PER_FOLD_RESULT_GROSS_ONLY" in codes


def test_l7_cost_slippage_omitted_from_folds_fails():
    ev = make_l7_complete()
    ev.cost_model_version = ""
    ev.slippage_model_version = ""
    ev.per_fold_gross_result = [100.0, 200.0]
    ev.per_fold_net_of_cost_result = []
    codes = validate_l7_combinatorial_purged_cv(ev)
    assert "L7_COST_SLIPPAGE_OMITTED_FROM_FOLDS" in codes


def test_l7_none_evidence_fails():
    codes = validate_l7_combinatorial_purged_cv(None)
    assert "L7_ORDINARY_RANDOM_KFOLD_ONLY" in codes
    assert "L7_PURGE_WINDOW_MISSING" in codes
    assert "L7_EMBARGO_WINDOW_MISSING" in codes
    assert "L7_PER_FOLD_RESULT_GROSS_ONLY" in codes


# ============================================================
# Negative / fail-closed tests - L8 PSR / Reality Check / SPA
# ============================================================

def test_l8_raw_sharpe_only_fails():
    ev = make_l8_complete()
    ev.probabilistic_sharpe_ratio = None
    ev.reality_check_p_value = None
    ev.spa_p_value = None
    codes = validate_l8_psr_reality_check_spa(ev)
    assert "L8_RAW_SHARPE_ONLY" in codes


def test_l8_psr_missing_fails():
    ev = make_l8_complete()
    ev.probabilistic_sharpe_ratio = None
    ev.reality_check_p_value = None
    ev.spa_p_value = None
    codes = validate_l8_psr_reality_check_spa(ev)
    assert "L8_PSR_MISSING" in codes


def test_l8_reality_check_missing_fails():
    ev = make_l8_complete()
    ev.reality_check_p_value = None
    ev.spa_p_value = None
    codes = validate_l8_psr_reality_check_spa(ev)
    assert "L8_REALITY_CHECK_MISSING" in codes


def test_l8_benchmark_baseline_missing_fails():
    ev = make_l8_complete()
    ev.benchmark_or_strategy_family_baseline = ""
    codes = validate_l8_psr_reality_check_spa(ev)
    assert "L8_BENCHMARK_BASELINE_MISSING" in codes


def test_l8_adjusted_p_value_missing_fails():
    ev = make_l8_complete()
    ev.multiple_testing_adjusted_p_value = None
    codes = validate_l8_psr_reality_check_spa(ev)
    assert "L8_ADJUSTED_P_VALUE_MISSING" in codes


def test_l8_adjusted_p_above_threshold_fails():
    ev = make_l8_complete()
    ev.multiple_testing_adjusted_p_value = DEFAULT_ADJUSTED_P_THRESHOLD + 0.01
    codes = validate_l8_psr_reality_check_spa(ev)
    assert "L8_ADJUSTED_P_ABOVE_THRESHOLD" in codes


def test_l8_bootstrap_method_missing_fails():
    ev = make_l8_complete()
    ev.bootstrap_or_resampling_method = ""
    codes = validate_l8_psr_reality_check_spa(ev)
    assert "L8_BOOTSTRAP_METHOD_MISSING" in codes


def test_l8_insufficient_trade_count_fails():
    ev = make_l8_complete()
    ev.trade_count = 0
    codes = validate_l8_psr_reality_check_spa(ev)
    assert "L8_INSUFFICIENT_TRADE_COUNT" in codes


def test_l8_tail_risk_ignored_fails():
    ev = make_l8_complete()
    ev.non_normality_or_tail_risk_adjustment = ""
    codes = validate_l8_psr_reality_check_spa(ev)
    assert "L8_TAIL_RISK_IGNORED" in codes


def test_l8_gross_metric_used_fails():
    ev = make_l8_complete()
    ev.net_of_cost_metric_used = False
    codes = validate_l8_psr_reality_check_spa(ev)
    assert "L8_GROSS_METRIC_USED" in codes


def test_l8_none_evidence_fails():
    codes = validate_l8_psr_reality_check_spa(None)
    assert "L8_RAW_SHARPE_ONLY" in codes
    assert "L8_PSR_MISSING" in codes
    assert "L8_REALITY_CHECK_MISSING" in codes
    assert "L8_ADJUSTED_P_VALUE_MISSING" in codes
    assert "L8_BOOTSTRAP_METHOD_MISSING" in codes
    assert "L8_GROSS_METRIC_USED" in codes


# ============================================================
# Negative / fail-closed tests - L9 Paper Trading Readiness
# ============================================================

def test_l9_paper_duration_below_minimum_fails():
    ev = make_l9_complete()
    ev.paper_duration_months = MIN_PAPER_MONTHS - 1
    codes = validate_l9_paper_trading_readiness(ev)
    assert "L9_PAPER_DURATION_BELOW_MINIMUM" in codes


def test_l9_insufficient_trading_days_fails():
    ev = make_l9_complete()
    ev.paper_trading_days = MIN_PAPER_TRADING_DAYS - 1
    codes = validate_l9_paper_trading_readiness(ev)
    assert "L9_INSUFFICIENT_TRADING_DAYS" in codes


def test_l9_insufficient_paper_trades_fails():
    ev = make_l9_complete()
    ev.paper_trade_count = MIN_PAPER_TRADE_COUNT - 1
    codes = validate_l9_paper_trading_readiness(ev)
    assert "L9_INSUFFICIENT_PAPER_TRADES" in codes


def test_l9_paper_net_of_cost_missing_fails():
    ev = make_l9_complete()
    ev.paper_net_of_cost_pnl = None
    codes = validate_l9_paper_trading_readiness(ev)
    assert "L9_PAPER_NET_OF_COST_MISSING" in codes


def test_l9_slippage_drift_over_threshold_fails():
    ev = make_l9_complete()
    ev.expected_vs_actual_slippage_drift = DEFAULT_SLIPPAGE_DRIFT_THRESHOLD + 0.01
    codes = validate_l9_paper_trading_readiness(ev)
    assert "L9_SLIPPAGE_DRIFT_OVER_THRESHOLD" in codes


def test_l9_fill_rate_drift_over_threshold_fails():
    ev = make_l9_complete()
    ev.expected_vs_actual_fill_rate_drift = DEFAULT_FILL_RATE_DRIFT_THRESHOLD + 0.01
    codes = validate_l9_paper_trading_readiness(ev)
    assert "L9_FILL_RATE_DRIFT_OVER_THRESHOLD" in codes


def test_l9_paper_live_drift_policy_missing_fails():
    ev = make_l9_complete()
    ev.paper_live_drift_policy_present = False
    codes = validate_l9_paper_trading_readiness(ev)
    assert "L9_PAPER_LIVE_DRIFT_POLICY_MISSING" in codes


def test_l9_strategy_ttl_expiry_missing_fails():
    ev = make_l9_complete()
    ev.strategy_ttl_or_promotion_expiry = ""
    codes = validate_l9_paper_trading_readiness(ev)
    assert "L9_STRATEGY_TTL_EXPIRY_MISSING" in codes


def test_l9_revalidation_before_live_missing_fails():
    ev = make_l9_complete()
    ev.revalidation_required_before_live = False
    codes = validate_l9_paper_trading_readiness(ev)
    assert "L9_REVALIDATION_BEFORE_LIVE_MISSING" in codes


def test_l9_human_approval_missing_fails():
    ev = make_l9_complete()
    ev.human_approval_required_for_live = False
    codes = validate_l9_paper_trading_readiness(ev)
    assert "L9_HUMAN_APPROVAL_MISSING" in codes


def test_l9_live_order_path_present_fails():
    ev = make_l9_complete()
    ev.no_live_order_path = False
    codes = validate_l9_paper_trading_readiness(ev)
    assert "L9_LIVE_ORDER_PATH_PRESENT" in codes


def test_l9_order_execution_allowed_true_fails():
    ev = make_l9_complete()
    ev.order_execution_allowed = True
    codes = validate_l9_paper_trading_readiness(ev)
    assert "L9_ORDER_EXECUTION_ALLOWED_TRUE" in codes


def test_l9_none_evidence_fails():
    codes = validate_l9_paper_trading_readiness(None)
    assert "L9_PAPER_DURATION_BELOW_MINIMUM" in codes
    assert "L9_INSUFFICIENT_TRADING_DAYS" in codes
    assert "L9_INSUFFICIENT_PAPER_TRADES" in codes
    assert "L9_PAPER_NET_OF_COST_MISSING" in codes
    assert "L9_PAPER_LIVE_DRIFT_POLICY_MISSING" in codes
    assert "L9_REVALIDATION_BEFORE_LIVE_MISSING" in codes
    assert "L9_HUMAN_APPROVAL_MISSING" in codes
    assert "L9_LIVE_ORDER_PATH_PRESENT" in codes


# ============================================================
# General compatibility fail-closed tests
# ============================================================

def test_missing_replay_compatibility_global_fails():
    ev = make_l5_complete()
    ev.as_of_replay_compatible = False
    inp = make_complete_input()
    inp.l5_evidence = ev
    result = validate_l5_l9_chain(inp)
    assert result.validation_passed is False
    assert "GENERAL_MISSING_REPLAY_COMPATIBILITY" in result.reason_codes


def test_missing_risk_gate_replay_compatibility_global_fails():
    ev = make_l5_complete()
    ev.risk_gate_replay_compatible = False
    inp = make_complete_input()
    inp.l5_evidence = ev
    result = validate_l5_l9_chain(inp)
    assert result.validation_passed is False
    assert "GENERAL_MISSING_RISK_GATE_REPLAY_COMPATIBILITY" in result.reason_codes


def test_order_execution_allowed_true_fails():
    inp = make_complete_input()
    inp.order_execution_allowed = True
    result = validate_l5_l9_chain(inp)
    assert result.validation_passed is False
    assert result.order_execution_allowed is False
    assert "GENERAL_ORDER_EXECUTION_ALLOWED_NOT_FALSE" in result.reason_codes


def test_general_tradingview_only_fails():
    ev = make_l5_complete()
    ev.evidence_source = "tradingview"
    inp = make_complete_input()
    inp.l5_evidence = ev
    result = validate_l5_l9_chain(inp)
    assert result.validation_passed is False
    assert "GENERAL_TRADINGVIEW_ONLY" in result.reason_codes


# ============================================================
# Integration tests - CICD verification chain
# ============================================================

def test_cicd_verification_chain_supports_r038c_stage_name():
    chain = CICDVerificationChain()
    inp = make_complete_input()
    stages = [{"type": "r038c_l5_l9", "name": R038C_STAGE_NAME, "input": inp}]
    pipeline_result = chain.run_pipeline(stages)
    assert pipeline_result.stages[0].name == R038C_STAGE_NAME
    assert pipeline_result.all_passed is True


def test_cicd_pipeline_multiple_stages():
    chain = CICDVerificationChain()
    inp = make_complete_input()
    stages = [
        {"type": "chain_verify", "name": "pre_check", "chain": make_trace_chain()},
        {"type": "r038c_l5_l9", "name": "R038c_l5_l9", "input": inp},
    ]
    pipeline_result = chain.run_pipeline(stages)
    assert pipeline_result.all_passed is True
    assert len(pipeline_result.stages) == 2


def test_cicd_pipeline_r038c_stage_with_none_input():
    chain = CICDVerificationChain()
    stages = [{"type": "r038c_l5_l9", "name": "R038c_test"}]
    pipeline_result = chain.run_pipeline(stages)
    assert pipeline_result.all_passed is False
    assert len(pipeline_result.stages) == 1


def test_cicd_stage_result_type():
    chain = CICDVerificationChain()
    inp = make_complete_input()
    stages = [{"type": "r038c_l5_l9", "name": "R038c_test", "input": inp}]
    pipeline_result = chain.run_pipeline(stages)
    s = pipeline_result.stages[0]
    assert isinstance(s, CICDStageResult)
    assert s.name == "R038c_test"
    assert s.passed is True
    assert "L5" in s.detail
    assert "L9" in s.detail


# ============================================================
# Boundary tests
# ============================================================

def test_oos_window_count_exactly_minimum_passes():
    ev = make_l5_complete()
    ev.oos_window_count = MIN_OOS_WINDOW_COUNT
    codes = validate_l5_walk_forward_oos(ev)
    assert "L5_OOS_WINDOW_COUNT_BELOW_THRESHOLD" not in codes
    assert len(codes) == 0


def test_regime_count_exactly_minimum_passes():
    ev = make_l6_complete()
    ev.regime_count = MIN_REGIME_COUNT
    codes = validate_l6_regime_segmentation(ev)
    assert "L6_SINGLE_REGIME_ONLY" not in codes


def test_fold_count_exactly_minimum_passes():
    ev = make_l7_complete()
    ev.fold_count = MIN_FOLD_COUNT
    codes = validate_l7_combinatorial_purged_cv(ev)
    assert "L7_FOLD_COUNT_BELOW_THRESHOLD" not in codes


def test_combo_split_count_exactly_minimum_passes():
    ev = make_l7_complete()
    ev.combinatorial_split_count = MIN_COMBO_SPLIT_COUNT
    codes = validate_l7_combinatorial_purged_cv(ev)
    assert "L7_COMBO_SPLIT_COUNT_BELOW_THRESHOLD" not in codes


def test_paper_duration_exactly_minimum_passes():
    ev = make_l9_complete()
    ev.paper_duration_months = MIN_PAPER_MONTHS
    codes = validate_l9_paper_trading_readiness(ev)
    assert "L9_PAPER_DURATION_BELOW_MINIMUM" not in codes
    assert len(codes) == 0


def test_adjusted_p_value_exactly_threshold_passes():
    ev = make_l8_complete()
    ev.multiple_testing_adjusted_p_value = DEFAULT_ADJUSTED_P_THRESHOLD
    codes = validate_l8_psr_reality_check_spa(ev)
    assert "L8_ADJUSTED_P_ABOVE_THRESHOLD" not in codes


def test_all_levels_pass_but_one_warning_no_bypass_fail_closed():
    inp = make_complete_input()
    inp.l5_evidence.oos_window_count = 0
    result = validate_l5_l9_chain(inp)
    assert result.validation_passed is False
    assert result.fail_closed is True
    assert "L5_OOS_WINDOWS_MISSING" in result.reason_codes


def test_l5_is_tradingview_only_property():
    ev = make_l5_complete()
    assert ev.is_tradingview_only is False
    ev.evidence_source = "tradingview"
    assert ev.is_tradingview_only is True
    ev.evidence_source = "pine"
    assert ev.is_tradingview_only is True
    ev.evidence_source = "deeptest"
    assert ev.is_tradingview_only is True


def test_result_deterministic_hash():
    inp = make_complete_input()
    r1 = validate_l5_l9_chain(inp)
    r2 = validate_l5_l9_chain(inp)
    assert r1.compute_result_hash() == r2.compute_result_hash()


def test_status_enum_missing_returns_none():
    assert L5L9ValidationStatus._missing_("bogus") is None


# ============================================================
# Helpers
# ============================================================

def make_trace_chain():
    from modules.decision_prechecklist.traceability_chain import TraceabilityChain
    chain = TraceabilityChain(chain_id="r038c_test_chain")
    chain.add_link(
        trace_id="t1", symbol="AAPL", side="BUY",
        final_decision="ALLOW", total_steps=5, veto_count=0,
    )
    return chain


def make_l5_complete() -> L5WalkForwardOOSEvidence:
    return L5WalkForwardOOSEvidence(
        final_out_of_sample_period="2026-01-01..2026-03-31",
        oos_window_count=3,
        walk_forward_oos_splits=[{"train": 1, "test": 1}, {"train": 2, "test": 2}],
        no_training_overlap_with_oos=True,
        no_future_leak=True,
        as_of_replay_compatible=True,
        net_of_cost_oos_result=5000.0,
        gross_oos_result=7000.0,
        cost_model_version="cost_v3",
        slippage_model_version="slippage_v2",
        market_reality_compatible=True,
        risk_gate_replay_compatible=True,
        evidence_source="python_backtest",
    )


def make_l6_complete() -> L6RegimeSegmentEvidence:
    return L6RegimeSegmentEvidence(
        regime_count=3,
        regime_labels=["bull", "bear", "sideways"],
        per_regime_sample_count={"bull": 100, "bear": 50, "sideways": 80},
        per_regime_net_of_cost_result={"bull": 2000.0, "bear": -500.0, "sideways": 800.0},
        per_regime_gross_result={"bull": 3000.0, "bear": 0.0, "sideways": 1200.0},
        aggregate_net_of_cost_result=2300.0,
        regime_definition_version="v2",
        offline_labeler_vs_online_filter_declared=True,
        hindsight_regime_smoothed_for_live=False,
        no_hindsight_regime_for_live=True,
        regime_uncertainty_policy_present=True,
        uncertainty_threshold_or_entropy_gate="entropy<0.5",
        market_reality_compatible_per_regime=True,
        evidence_source="python_backtest",
    )


def make_l7_complete() -> L7CombinatorialPurgedCVEvidence:
    return L7CombinatorialPurgedCVEvidence(
        combinatorial_split_count=5,
        purge_window=20,
        embargo_window=10,
        fold_count=5,
        time_series_order_preserved=True,
        overlapping_label_protection=True,
        leakage_gap_declared=True,
        per_fold_net_of_cost_result=[100.0, 200.0, 150.0, 180.0, 120.0],
        per_fold_gross_result=[150.0, 280.0, 200.0, 240.0, 160.0],
        cost_model_version="cost_v3",
        slippage_model_version="slippage_v2",
        evidence_source="python_backtest",
    )


def make_l8_complete() -> L8PSRRealityCheckSPAEvidence:
    return L8PSRRealityCheckSPAEvidence(
        probabilistic_sharpe_ratio=0.85,
        raw_sharpe_ratio=0.95,
        reality_check_p_value=0.03,
        spa_p_value=0.02,
        benchmark_or_strategy_family_baseline="equal_weight_benchmark",
        multiple_testing_adjusted_p_value=0.04,
        bootstrap_or_resampling_method="stationary_bootstrap",
        non_normality_or_tail_risk_adjustment="skew_adjusted",
        trade_count=200,
        net_of_cost_metric_used=True,
        raw_sharpe_not_sufficient=True,
        gross_metric_used=False,
        evidence_source="python_backtest",
    )


def make_l9_complete() -> L9PaperTradingReadinessEvidence:
    return L9PaperTradingReadinessEvidence(
        paper_duration_months=6,
        paper_trading_days=63,
        paper_trade_count=50,
        paper_net_of_cost_pnl=12000.0,
        paper_gross_pnl=15000.0,
        expected_vs_actual_slippage_drift=0.05,
        expected_vs_actual_fill_rate_drift=0.03,
        paper_live_drift_policy_present=True,
        strategy_ttl_or_promotion_expiry="2026-12-31",
        revalidation_required_before_live=True,
        human_approval_required_for_live=True,
        no_live_order_path=True,
        order_execution_allowed=False,
        evidence_source="python_backtest",
    )


def make_complete_input() -> L5L9ValidationInput:
    return L5L9ValidationInput(
        input_id="r038c_test_complete",
        l5_evidence=make_l5_complete(),
        l6_evidence=make_l6_complete(),
        l7_evidence=make_l7_complete(),
        l8_evidence=make_l8_complete(),
        l9_evidence=make_l9_complete(),
        adjusted_p_threshold=DEFAULT_ADJUSTED_P_THRESHOLD,
        paper_duration_months=MIN_PAPER_MONTHS,
        slippage_drift_threshold=DEFAULT_SLIPPAGE_DRIFT_THRESHOLD,
        fill_rate_drift_threshold=DEFAULT_FILL_RATE_DRIFT_THRESHOLD,
        order_execution_allowed=False,
        market_reality_compatible_required=True,
        replay_compatible_required=True,
        risk_gate_replay_required=True,
    )
