from modules.decision_prechecklist.l0_l4_validation_chain import (
    L0BacktestEvidence,
    L1WalkForwardEvidence,
    L2MonteCarloPermutationEvidence,
    L3BlockBootstrapEvidence,
    L4MultipleTestingCorrectionEvidence,
    L0L4ValidationInput,
    L0L4ValidationResult,
    L0L4ValidationStatus,
    ValidationLevel,
    STAGE_R038B,
    FAIL_CLOSED_REASON_CODES_R038B,
    validate_l0_backtest,
    validate_l1_walk_forward,
    validate_l2_monte_carlo,
    validate_l3_block_bootstrap,
    validate_l4_multiple_testing_correction,
    validate_l0_l4_chain,
    run_r038b_l0_l4_validation_chain,
    MIN_TRADE_COUNT,
    MIN_TRAIN_WINDOWS,
    MIN_TEST_WINDOWS,
    MIN_PERMUTATION_RUNS,
    MIN_BOOTSTRAP_RUNS,
    DEFAULT_P_VALUE_THRESHOLD,
    DEFAULT_CORRECTED_P_THRESHOLD,
)
from modules.decision_prechecklist.cicd_verification_chain import (
    CICDVerificationChain,
    CICDStageResult,
    R038B_STAGE_NAME,
)


# ============================================================
# Positive tests
# ============================================================

def test_complete_l0_l4_evidence_passes():
    inp = make_complete_input()
    result = validate_l0_l4_chain(inp)
    assert result.validation_passed is True
    assert result.status == L0L4ValidationStatus.PASS
    assert len(result.failed_levels) == 0
    assert len(result.passed_levels) == 5
    assert result.order_execution_allowed is False


def test_cicd_verification_chain_calls_r038b_stage():
    chain = CICDVerificationChain()
    inp = make_complete_input()
    result = chain.validate_l0_l4_validation_chain(inp)
    assert result.validation_passed is True
    assert len(result.levels_checked) == 5


def test_cicd_verification_chain_r038b_stage_returns_deterministic_result():
    chain = CICDVerificationChain()
    inp = make_complete_input()
    result_dict = chain.run_r038b_stage(inp)
    assert result_dict["stage"] == STAGE_R038B
    assert result_dict["validation_passed"] is True
    assert result_dict["net_of_cost_required"] is True
    assert result_dict["market_reality_required"] is True
    assert result_dict["replay_required"] is True
    assert result_dict["tradingview_only_rejected"] is True
    assert result_dict["order_execution_allowed"] is False


def test_cicd_pipeline_r038b_stage_type():
    chain = CICDVerificationChain()
    inp = make_complete_input()
    stages = [{"type": "r038b_l0_l4", "name": "R038b_test", "input": inp}]
    pipeline_result = chain.run_pipeline(stages)
    assert pipeline_result.all_passed is True
    assert len(pipeline_result.stages) == 1
    assert pipeline_result.stages[0].passed is True
    assert pipeline_result.stages[0].name == "R038b_test"


def test_run_r038b_l0_l4_validation_chain_returns_dict():
    inp = make_complete_input()
    result_dict = run_r038b_l0_l4_validation_chain(inp)
    assert isinstance(result_dict, dict)
    assert result_dict["stage"] == STAGE_R038B
    assert result_dict["validation_passed"] is True
    for level in ["L0", "L1", "L2", "L3", "L4"]:
        assert level in result_dict["levels_checked"]


def test_l0_backtest_valid_evidence_no_codes():
    ev = make_l0_complete()
    codes = validate_l0_backtest(ev)
    assert len(codes) == 0


def test_l1_walk_forward_valid_evidence_no_codes():
    ev = make_l1_complete()
    codes = validate_l1_walk_forward(ev)
    assert len(codes) == 0


def test_l2_monte_carlo_valid_evidence_no_codes():
    ev = make_l2_complete()
    codes = validate_l2_monte_carlo(ev)
    assert len(codes) == 0


def test_l3_block_bootstrap_valid_evidence_no_codes():
    ev = make_l3_complete()
    codes = validate_l3_block_bootstrap(ev)
    assert len(codes) == 0


def test_l4_multiple_testing_correction_valid_evidence_no_codes():
    ev = make_l4_complete()
    codes = validate_l4_multiple_testing_correction(ev)
    assert len(codes) == 0


def test_validation_level_enum_values():
    assert ValidationLevel.L0.value == "L0"
    assert ValidationLevel.L1.value == "L1"
    assert ValidationLevel.L2.value == "L2"
    assert ValidationLevel.L3.value == "L3"
    assert ValidationLevel.L4.value == "L4"


def test_stage_r038b_constant():
    assert STAGE_R038B == "R038b_l0_l4_validation_chain"


def test_fail_closed_reason_codes_populated():
    assert len(FAIL_CLOSED_REASON_CODES_R038B) > 0
    assert "L0_GROSS_ONLY_RESULT" in FAIL_CLOSED_REASON_CODES_R038B
    assert "L0_ORDER_FILL_PNL_SCHEMA_INCOMPATIBLE" in FAIL_CLOSED_REASON_CODES_R038B
    assert "L1_LOOKAHEAD_LEAK" in FAIL_CLOSED_REASON_CODES_R038B
    assert "L2_P_VALUE_ABOVE_THRESHOLD" in FAIL_CLOSED_REASON_CODES_R038B
    assert "L3_CONFIDENCE_INTERVAL_MISSING" in FAIL_CLOSED_REASON_CODES_R038B
    assert "L4_CORRECTED_P_VALUE_MISSING" in FAIL_CLOSED_REASON_CODES_R038B


def test_result_to_dict_and_hash():
    inp = make_complete_input()
    result = validate_l0_l4_chain(inp)
    d = result.to_dict()
    assert d["stage"] == STAGE_R038B
    assert isinstance(d["reason_codes"], list)
    h = result.compute_result_hash()
    assert isinstance(h, str)
    assert len(h) == 64


# ============================================================
# Negative / fail-closed tests
# ============================================================

def test_l0_gross_only_result_fails():
    ev = make_l0_complete()
    ev.net_of_cost_pnl = None
    codes = validate_l0_backtest(ev)
    assert "L0_GROSS_ONLY_RESULT" in codes


def test_l0_missing_cost_model_fails():
    ev = make_l0_complete()
    ev.cost_model_version = ""
    codes = validate_l0_backtest(ev)
    assert "L0_COST_MODEL_MISSING" in codes


def test_l0_missing_slippage_model_fails():
    ev = make_l0_complete()
    ev.slippage_model_version = ""
    codes = validate_l0_backtest(ev)
    assert "L0_SLIPPAGE_MODEL_MISSING" in codes


def test_l0_trade_count_insufficient_fails():
    ev = make_l0_complete()
    ev.trade_count = MIN_TRADE_COUNT - 1
    codes = validate_l0_backtest(ev)
    assert "L0_TRADE_COUNT_INSUFFICIENT" in codes


def test_l0_order_fill_pnl_schema_incompatible_fails():
    ev = make_l0_complete()
    ev.order_fill_pnl_schema_compatible = False
    codes = validate_l0_backtest(ev)
    assert "L0_ORDER_FILL_PNL_SCHEMA_INCOMPATIBLE" in codes


def test_l0_missing_market_reality_compatibility_fails():
    ev = make_l0_complete()
    ev.market_reality_compatible = False
    codes = validate_l0_backtest(ev)
    assert "L0_MARKET_REALITY_NOT_COMPATIBLE" in codes


def test_l0_missing_replay_compatibility_fails():
    ev = make_l0_complete()
    ev.replay_compatible = False
    codes = validate_l0_backtest(ev)
    assert "L0_REPLAY_NOT_COMPATIBLE" in codes


def test_l0_missing_risk_gate_replay_compatibility_fails():
    ev = make_l0_complete()
    ev.risk_gate_replay_compatible = False
    codes = validate_l0_backtest(ev)
    assert "L0_RISK_GATE_REPLAY_NOT_COMPATIBLE" in codes


def test_l0_missing_drawdown_fails():
    ev = make_l0_complete()
    ev.max_drawdown = None
    codes = validate_l0_backtest(ev)
    assert "L0_DRAWDOWN_MISSING" in codes


def test_l1_missing_oos_windows_fails():
    ev = make_l1_complete()
    ev.out_of_sample_windows = 0
    codes = validate_l1_walk_forward(ev)
    assert "L1_OOS_WINDOWS_MISSING" in codes


def test_l1_lookahead_leak_fails():
    ev = make_l1_complete()
    ev.no_lookahead_leak = False
    codes = validate_l1_walk_forward(ev)
    assert "L1_LOOKAHEAD_LEAK" in codes


def test_l1_window_result_gross_only_fails():
    ev = make_l1_complete()
    ev.window_level_net_of_cost = False
    codes = validate_l1_walk_forward(ev)
    assert "L1_WINDOW_RESULT_GROSS_ONLY" in codes


def test_l1_missing_cost_slippage_per_window_fails():
    ev = make_l1_complete()
    ev.window_cost_model_version = ""
    codes = validate_l1_walk_forward(ev)
    assert "L1_WINDOW_COST_SLIPPAGE_MISSING" in codes


def test_l2_insufficient_permutation_count_fails():
    ev = make_l2_complete()
    ev.monte_carlo_runs = MIN_PERMUTATION_RUNS - 1
    codes = validate_l2_monte_carlo(ev)
    assert "L2_RUN_COUNT_BELOW_THRESHOLD" in codes


def test_l2_missing_p_value_fails():
    ev = make_l2_complete()
    ev.p_value = None
    codes = validate_l2_monte_carlo(ev)
    assert "L2_P_VALUE_MISSING" in codes


def test_l2_p_value_above_threshold_fails():
    ev = make_l2_complete()
    ev.p_value = DEFAULT_P_VALUE_THRESHOLD + 0.01
    codes = validate_l2_monte_carlo(ev)
    assert "L2_P_VALUE_ABOVE_THRESHOLD" in codes


def test_l3_missing_block_size_fails():
    ev = make_l3_complete()
    ev.block_size = 0
    codes = validate_l3_block_bootstrap(ev)
    assert "L3_BLOCK_SIZE_MISSING" in codes


def test_l3_bootstrap_runs_insufficient_fails():
    ev = make_l3_complete()
    ev.bootstrap_runs = MIN_BOOTSTRAP_RUNS - 1
    codes = validate_l3_block_bootstrap(ev)
    assert "L3_RUNS_BELOW_THRESHOLD" in codes


def test_l3_missing_confidence_interval_fails():
    ev = make_l3_complete()
    ev.confidence_interval = {}
    codes = validate_l3_block_bootstrap(ev)
    assert "L3_CONFIDENCE_INTERVAL_MISSING" in codes


def test_l3_serial_dependence_ignored_fails():
    ev = make_l3_complete()
    ev.regime_serial_dependence_aware = False
    codes = validate_l3_block_bootstrap(ev)
    assert "L3_SERIAL_DEPENDENCE_IGNORED" in codes


def test_l4_missing_corrected_p_value_fails():
    ev = make_l4_complete()
    ev.corrected_p_value = None
    codes = validate_l4_multiple_testing_correction(ev)
    assert "L4_CORRECTED_P_VALUE_MISSING" in codes


def test_l4_raw_p_value_used_without_correction_fails():
    ev = make_l4_complete()
    ev.corrected_p_value = None
    ev.raw_p_value = 0.03
    codes = validate_l4_multiple_testing_correction(ev)
    assert "L4_RAW_P_USED_WITHOUT_CORRECTION" in codes


def test_l4_corrected_p_above_threshold_fails():
    ev = make_l4_complete()
    ev.corrected_p_value = DEFAULT_CORRECTED_P_THRESHOLD + 0.01
    codes = validate_l4_multiple_testing_correction(ev)
    assert "L4_CORRECTED_P_ABOVE_THRESHOLD" in codes


def test_l4_trial_count_inconsistent_with_ledger_fails():
    ev = make_l4_complete()
    ev.search_ledger = [{"param": "x"}]
    codes = validate_l4_multiple_testing_correction(ev)
    assert "L4_TRIAL_COUNT_INCONSISTENT" in codes


def test_l4_fragility_isolated_best_parameter_fails():
    ev = make_l4_complete()
    ev.fragility_marker = "high_fragility"
    codes = validate_l4_multiple_testing_correction(ev)
    assert "L4_FRAGILITY_ISOLATED_BEST" in codes


def test_tradingview_only_evidence_fails():
    ev = make_l0_complete()
    ev.evidence_source = "tradingview"
    codes = validate_l0_backtest(ev)
    assert "L0_TRADINGVIEW_ONLY" in codes


def test_pine_only_evidence_fails():
    ev = make_l0_complete()
    ev.evidence_source = "pine"
    codes = validate_l0_backtest(ev)
    assert "L0_TRADINGVIEW_ONLY" in codes


def test_deeptest_only_evidence_fails():
    ev = make_l0_complete()
    ev.evidence_source = "deeptest"
    codes = validate_l0_backtest(ev)
    assert "L0_TRADINGVIEW_ONLY" in codes


def test_missing_replay_compatibility_global_fails():
    ev = make_l0_complete()
    ev.replay_compatible = False
    inp = make_complete_input()
    inp.l0_evidence = ev
    result = validate_l0_l4_chain(inp)
    assert result.validation_passed is False
    assert "GENERAL_MISSING_REPLAY_COMPATIBILITY" in result.reason_codes


def test_missing_risk_gate_replay_compatibility_global_fails():
    ev = make_l0_complete()
    ev.risk_gate_replay_compatible = False
    inp = make_complete_input()
    inp.l0_evidence = ev
    result = validate_l0_l4_chain(inp)
    assert result.validation_passed is False
    assert "GENERAL_MISSING_RISK_GATE_REPLAY_COMPATIBILITY" in result.reason_codes


def test_order_execution_allowed_true_fails_forced_false():
    inp = make_complete_input()
    inp.order_execution_allowed = True
    result = validate_l0_l4_chain(inp)
    assert result.validation_passed is False
    assert result.order_execution_allowed is False
    assert "GENERAL_ORDER_EXECUTION_ALLOWED_NOT_FALSE" in result.reason_codes


def test_l0_backtest_none_fails():
    codes = validate_l0_backtest(None)
    assert "L0_GROSS_ONLY_RESULT" in codes


def test_l1_walk_forward_none_fails():
    codes = validate_l1_walk_forward(None)
    assert "L1_WINDOWS_MISSING" in codes


def test_l2_monte_carlo_none_fails():
    codes = validate_l2_monte_carlo(None)
    assert "L2_PERMUTATION_RESULT_MISSING" in codes


def test_l3_block_bootstrap_none_fails():
    codes = validate_l3_block_bootstrap(None)
    assert "L3_BOOTSTRAP_RESULT_MISSING" in codes


def test_l4_multiple_testing_correction_none_fails():
    codes = validate_l4_multiple_testing_correction(None)
    assert "L4_TRIAL_COUNT_MISSING" in codes


def test_l0_trade_count_zero_fails():
    ev = make_l0_complete()
    ev.trade_count = 0
    codes = validate_l0_backtest(ev)
    assert "L0_TRADE_COUNT_MISSING" in codes


def test_l1_insufficient_train_windows_fails():
    ev = make_l1_complete()
    ev.train_window_count = MIN_TRAIN_WINDOWS - 1
    codes = validate_l1_walk_forward(ev)
    assert "L1_INSUFFICIENT_TRAIN_WINDOWS" in codes


def test_l1_insufficient_test_windows_fails():
    ev = make_l1_complete()
    ev.test_window_count = MIN_TEST_WINDOWS - 1
    codes = validate_l1_walk_forward(ev)
    assert "L1_INSUFFICIENT_TEST_WINDOWS" in codes


def test_l2_missing_seed_fails():
    ev = make_l2_complete()
    ev.random_seed = None
    codes = validate_l2_monte_carlo(ev)
    assert "L2_MISSING_SEED" in codes


def test_l2_missing_tail_risk_fails():
    ev = make_l2_complete()
    ev.tail_risk_metric = {}
    codes = validate_l2_monte_carlo(ev)
    assert "L2_TAIL_RISK_MISSING" in codes


def test_l4_missing_search_ledger_fails():
    ev = make_l4_complete()
    ev.search_ledger = []
    codes = validate_l4_multiple_testing_correction(ev)
    assert "L4_SEARCH_LEDGER_MISSING" in codes


def test_l3_block_size_invalid_fails():
    ev = make_l3_complete()
    ev.block_size = -1
    codes = validate_l3_block_bootstrap(ev)
    assert "L3_BLOCK_SIZE_INVALID" in codes


# ============================================================
# Boundary tests
# ============================================================

def test_trade_count_exactly_minimum_passes():
    ev = make_l0_complete()
    ev.trade_count = MIN_TRADE_COUNT
    codes = validate_l0_backtest(ev)
    assert "L0_TRADE_COUNT_INSUFFICIENT" not in codes
    assert len(codes) == 0


def test_p_value_exactly_threshold_passes():
    ev = make_l2_complete()
    ev.p_value = DEFAULT_P_VALUE_THRESHOLD
    codes = validate_l2_monte_carlo(ev)
    assert "L2_P_VALUE_ABOVE_THRESHOLD" not in codes


def test_corrected_p_value_exactly_threshold_passes():
    ev = make_l4_complete()
    ev.corrected_p_value = DEFAULT_CORRECTED_P_THRESHOLD
    codes = validate_l4_multiple_testing_correction(ev)
    assert "L4_CORRECTED_P_ABOVE_THRESHOLD" not in codes


def test_bootstrap_runs_exactly_minimum_passes():
    ev = make_l3_complete()
    ev.bootstrap_runs = MIN_BOOTSTRAP_RUNS
    codes = validate_l3_block_bootstrap(ev)
    assert "L3_RUNS_BELOW_THRESHOLD" not in codes


def test_all_levels_pass_but_one_warning_no_bypass_fail_closed():
    inp = make_complete_input()
    inp.l0_evidence.trade_count = 0
    result = validate_l0_l4_chain(inp)
    assert result.validation_passed is False
    assert result.fail_closed is True
    assert "L0_TRADE_COUNT_MISSING" in result.reason_codes


def test_cicd_verification_chain_supports_r038b_stage_name():
    chain = CICDVerificationChain()
    inp = make_complete_input()
    stages = [{"type": "r038b_l0_l4", "name": R038B_STAGE_NAME, "input": inp}]
    pipeline_result = chain.run_pipeline(stages)
    assert pipeline_result.stages[0].name == R038B_STAGE_NAME
    assert pipeline_result.all_passed is True


def test_l0_is_tradingview_only_property():
    ev = make_l0_complete()
    assert ev.is_tradingview_only is False
    ev.evidence_source = "tradingview"
    assert ev.is_tradingview_only is True
    ev.evidence_source = "pine"
    assert ev.is_tradingview_only is True
    ev.evidence_source = "deeptest"
    assert ev.is_tradingview_only is True


def test_l0_backtest_deterministic_hash():
    ev1 = make_l0_complete()
    ev2 = make_l0_complete()
    assert ev1.compute_deterministic_hash() == ev2.compute_deterministic_hash()


def test_result_deterministic_hash():
    inp = make_complete_input()
    r1 = validate_l0_l4_chain(inp)
    r2 = validate_l0_l4_chain(inp)
    assert r1.compute_result_hash() == r2.compute_result_hash()


# ============================================================
# Helpers
# ============================================================

def make_l0_complete() -> L0BacktestEvidence:
    return L0BacktestEvidence(
        net_of_cost_pnl=15000.0,
        gross_pnl=20000.0,
        cost_model_version="cost_v3",
        slippage_model_version="slippage_v2",
        trade_count=50,
        max_drawdown=-0.15,
        order_fill_pnl_schema_compatible=True,
        market_reality_compatible=True,
        replay_compatible=True,
        risk_gate_replay_compatible=True,
        evidence_source="python_backtest",
    )


def make_l1_complete() -> L1WalkForwardEvidence:
    return L1WalkForwardEvidence(
        train_window_count=10,
        test_window_count=5,
        out_of_sample_windows=3,
        walk_forward_splits=[{"train": 1, "test": 1}],
        no_lookahead_leak=True,
        window_level_net_of_cost=True,
        window_cost_model_version="cost_v3",
        window_slippage_model_version="slippage_v2",
    )


def make_l2_complete() -> L2MonteCarloPermutationEvidence:
    return L2MonteCarloPermutationEvidence(
        permutation_count=1000,
        monte_carlo_runs=1000,
        p_value=0.03,
        random_seed=42,
        tail_risk_metric={"var_95": -0.25, "cvar_95": -0.35},
    )


def make_l3_complete() -> L3BlockBootstrapEvidence:
    return L3BlockBootstrapEvidence(
        block_count=200,
        block_size=20,
        bootstrap_runs=1000,
        confidence_interval={"lower": 0.01, "upper": 0.99},
        regime_serial_dependence_aware=True,
    )


def make_l4_complete() -> L4MultipleTestingCorrectionEvidence:
    return L4MultipleTestingCorrectionEvidence(
        trial_count=50,
        family_count=5,
        raw_p_value=0.03,
        corrected_p_value=0.01,
        correction_method="bonferroni",
        search_ledger=[{"param": f"p{i}"} for i in range(50)],
        overfit_risk_flag="",
        fragility_marker="",
    )


def make_complete_input() -> L0L4ValidationInput:
    return L0L4ValidationInput(
        input_id="r038b_test_complete",
        l0_evidence=make_l0_complete(),
        l1_evidence=make_l1_complete(),
        l2_evidence=make_l2_complete(),
        l3_evidence=make_l3_complete(),
        l4_evidence=make_l4_complete(),
        p_value_threshold=DEFAULT_P_VALUE_THRESHOLD,
        corrected_p_threshold=DEFAULT_CORRECTED_P_THRESHOLD,
        order_execution_allowed=False,
    )
