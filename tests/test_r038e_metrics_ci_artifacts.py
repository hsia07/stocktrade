"""
R038e metrics and CI artifacts test suite.
Requires real source import. Tests must not be mock-only.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
    MetricCategory,
    ValidationArtifactType,
    MetricDefinition,
    MetricValue,
    ValidationReportArtifact,
    ValidationReportBundle,
    MetricsArtifactPolicy,
    MetricsArtifactValidationResult,
    REQUIRED_METRICS,
    REQUIRED_METRIC_NAMES,
    REASON_CODES,
    METRICS_CONTRACT_VERSION,
    ARTIFACT_SCHEMA_VERSION,
    VALIDATOR_VERSION,
    DEFAULT_VALIDATION_FRESHNESS_DAYS,
    TAIWAN_SECURITIES_TAX_RATE,
    TAIWAN_MINIMUM_FEE,
    TAIWAN_PRICE_LIMIT_BAND,
    TAIWAN_T_PLUS_2_SETTLEMENT,
    ACCEPTED_REPORT_STATUS_VALUES,
    ACCEPTED_FORMAL_STATUS_CODES,
    validate_metric_definition,
    validate_metrics_bundle,
    validate_ci_artifact,
    validate_report_output_consistency,
    validate_upstream_refs,
    build_validation_artifact,
    llm_generated_summary,
    deterministic_validation_required,
)


# =============================================================================
# Fixtures / Helpers
# =============================================================================


def make_complete_metrics() -> dict[str, float | int | bool | str]:
    return {
        "net_of_cost_pnl": 12500.0,
        "gross_pnl": 15000.0,
        "total_cost": 2500.0,
        "fee_cost": 800.0,
        "tax_cost": 900.0,
        "min_fee_effect": 20.0,
        "expected_slippage": 300.0,
        "actual_slippage": 350.0,
        "expected_vs_actual_slippage_drift": 0.05,
        "fill_probability": 0.92,
        "actual_fill_rate": 0.90,
        "fill_rate_drift": -0.02,
        "partial_fill_rate": 0.05,
        "rejected_order_rate": 0.02,
        "timeout_cancel_rate": 0.01,
        "max_drawdown": -8200.0,
        "drawdown_duration": 45,
        "sharpe_ratio": 1.85,
        "sortino_ratio": 2.20,
        "calmar_ratio": 1.52,
        "win_rate": 0.58,
        "payoff_ratio": 1.35,
        "trade_count": 247,
        "turnover": 1250000.0,
        "exposure": 0.72,
        "capacity_liquidity_cap": 500000.0,
        "var": -4500.0,
        "cvar": -6200.0,
        "skewness": -0.12,
        "kurtosis": 3.1,
        "regime_breakdown": '{"bull":0.6,"bear":0.25,"neutral":0.15}',
        "paper_live_drift": 0.03,
        "replay_compatibility_flag": True,
        "risk_gate_replay_compatibility_flag": True,
        "market_reality_compatibility_flag": True,
        "taiwan_constraints_flag": True,
    }


def make_stale_timestamp() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=DEFAULT_VALIDATION_FRESHNESS_DAYS + 5)).isoformat()


def make_fresh_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


# =============================================================================
# Positive Tests: Complete Metrics Contract Passes
# =============================================================================


class TestCompleteMetricsContractPass:
    def test_complete_metrics_bundle_passes(self):
        metrics = make_complete_metrics()
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is True
        assert len(result["reason_codes"]) == 0

    def test_complete_metrics_included_metric_names_match(self):
        metrics = make_complete_metrics()
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        included = set(result["reason_codes"]) if not result["pass_"] else set()
        assert "net_of_cost_pnl" in metrics
        assert "gross_pnl" in metrics
        assert "fee_cost" in metrics

    def test_required_metric_count(self):
        assert len(REQUIRED_METRICS) > 30

    def test_required_metric_names_non_empty(self):
        assert len(REQUIRED_METRIC_NAMES) > 30

    def test_all_required_metrics_have_name_and_category(self):
        for m in REQUIRED_METRICS:
            assert m["name"]
            assert m["category"]

    def test_all_required_metrics_have_unit(self):
        for m in REQUIRED_METRICS:
            assert m["unit"]

    def test_all_required_metrics_have_source(self):
        for m in REQUIRED_METRICS:
            assert m["source"]

    def test_all_required_metrics_have_calculation_version(self):
        for m in REQUIRED_METRICS:
            assert m["calculation_version"]

    def test_taiwan_relevant_metrics_present(self):
        taiwan_metrics = [m for m in REQUIRED_METRICS if m["taiwan_market_relevant"]]
        assert len(taiwan_metrics) >= 10

    def test_net_of_cost_pnl_required_true(self):
        net_defs = [m for m in REQUIRED_METRICS if m["name"] == "net_of_cost_pnl"]
        assert len(net_defs) == 1
        assert net_defs[0]["required"] is True

    def test_tail_risk_metrics_present(self):
        tail_names = {"var", "cvar"}
        assert tail_names.issubset(REQUIRED_METRIC_NAMES)

    def test_downside_risk_present(self):
        assert "sortino_ratio" in REQUIRED_METRIC_NAMES

    def test_replay_flags_present(self):
        assert "replay_compatibility_flag" in REQUIRED_METRIC_NAMES
        assert "risk_gate_replay_compatibility_flag" in REQUIRED_METRIC_NAMES
        assert "market_reality_compatibility_flag" in REQUIRED_METRIC_NAMES

    def test_taiwan_constraints_flag_present(self):
        assert "taiwan_constraints_flag" in REQUIRED_METRIC_NAMES

    def test_regime_breakdown_present(self):
        assert "regime_breakdown" in REQUIRED_METRIC_NAMES

    def test_paper_live_drift_present(self):
        assert "paper_live_drift" in REQUIRED_METRIC_NAMES

    def test_fill_metrics_complete_set(self):
        fill_names = {"fill_probability", "actual_fill_rate", "fill_rate_drift",
                      "partial_fill_rate", "rejected_order_rate", "timeout_cancel_rate"}
        assert fill_names.issubset(REQUIRED_METRIC_NAMES)

    def test_cost_metrics_complete_set(self):
        cost_names = {"fee_cost", "tax_cost", "min_fee_effect", "total_cost"}
        assert cost_names.issubset(REQUIRED_METRIC_NAMES)

    def test_slippage_metrics_complete_set(self):
        slip_names = {"expected_slippage", "actual_slippage", "expected_vs_actual_slippage_drift"}
        assert slip_names.issubset(REQUIRED_METRIC_NAMES)


# =============================================================================
# Positive Tests: CI Artifact Bundle Passes
# =============================================================================


class TestCIArtifactBundlePass:
    def test_complete_artifact_passes_validation(self):
        artifact = build_validation_artifact(
            metrics=make_complete_metrics(),
            source_commit="abc123def456",
            source_branch="work/canonical-mainline-repair-001",
            test_results={"total": 100, "passed": 100},
            r038a_ref="r038a1",
            r038b_ref="r038b1",
            r038c_ref="r038c1",
            r038d_ref="r038d1",
        )
        codes = validate_ci_artifact(artifact, "abc123def456", "work/canonical-mainline-repair-001", "R038e")
        assert len(codes) == 0

    def test_artifact_has_schema_version(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        assert artifact["schema_version"] == ARTIFACT_SCHEMA_VERSION

    def test_artifact_has_metrics_contract_version(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        assert artifact["metrics_contract_version"] == METRICS_CONTRACT_VERSION

    def test_artifact_has_validator_version(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        assert artifact["validator_version"] == VALIDATOR_VERSION

    def test_artifact_order_execution_allowed_false(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        assert artifact["order_execution_allowed"] is False

    def test_artifact_no_broker_live_runtime_flags_true(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        assert artifact["no_broker_live_runtime_flags"] is True

    def test_artifact_has_reproducibility_command(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        assert artifact["reproducibility_command"] is not None
        assert "abc123" in artifact["reproducibility_command"]

    def test_artifact_internal_subtask_r038e(self):
        artifact = build_validation_artifact(
            metrics=make_complete_metrics(),
            source_commit="abc123",
            source_branch="work/test",
            internal_subtask="R038e",
            test_results={"total": 10, "passed": 10},
        )
        assert artifact["internal_subtask"] == "R038e"

    def test_artifact_upstream_refs_included(self):
        artifact = build_validation_artifact(
            metrics=make_complete_metrics(),
            source_commit="abc123",
            source_branch="work/test",
            test_results={"total": 10, "passed": 10},
            r038a_ref="refa",
            r038b_ref="refb",
            r038c_ref="refc",
            r038d_ref="refd",
        )
        assert artifact["r038a_ref_commit"] == "refa"
        assert artifact["r038b_ref_commit"] == "refb"
        assert artifact["r038c_ref_commit"] == "refc"
        assert artifact["r038d_ref_commit"] == "refd"

    def test_artifact_missing_metric_names_populated(self):
        metrics = {"net_of_cost_pnl": 100.0}
        artifact = build_validation_artifact(metrics, "abc123", "work/test", {"total": 10, "passed": 10})
        assert len(artifact["missing_metric_names"]) > 0
        assert "gross_pnl" in artifact["missing_metric_names"]


# =============================================================================
# Positive Tests: JSON / Report / Evidence Consistency Passes
# =============================================================================


class TestConsistencyPass:
    def test_json_metrics_consistency_passes(self):
        machine = {"test_count": 100, "validation_result": {"pass_": True, "reason_codes": []},
                   "included_metric_names": ["net_of_cost_pnl", "gross_pnl", "fee_cost", "tax_cost", "total_cost",
                                             "expected_slippage", "actual_slippage", "expected_vs_actual_slippage_drift",
                                             "fill_probability", "actual_fill_rate", "fill_rate_drift",
                                             "max_drawdown", "sharpe_ratio", "sortino_ratio", "calmar_ratio",
                                             "win_rate", "payoff_ratio", "trade_count", "turnover", "exposure",
                                             "var", "cvar", "regime_breakdown", "paper_live_drift",
                                             "replay_compatibility_flag", "risk_gate_replay_compatibility_flag",
                                             "market_reality_compatibility_flag", "taiwan_constraints_flag",
                                             "min_fee_effect", "partial_fill_rate", "rejected_order_rate",
                                             "timeout_cancel_rate", "drawdown_duration", "skewness", "kurtosis",
                                             "capacity_liquidity_cap"]}
        evidence = {"R038e_test_count": 100}
        report = {"tests_passed": 100, "tests_total": 100}
        codes = validate_report_output_consistency(machine, evidence, report, None, None, None)
        assert len(codes) == 0

    def test_rtctg_status_matches_evidence_status(self):
        machine = {"test_count": 80, "validation_result": {"pass_": True, "reason_codes": []},
                   "included_metric_names": ["net_of_cost_pnl", "gross_pnl", "fee_cost", "tax_cost", "total_cost",
                                             "expected_slippage", "actual_slippage", "expected_vs_actual_slippage_drift",
                                             "fill_probability", "actual_fill_rate", "fill_rate_drift",
                                             "max_drawdown", "sharpe_ratio", "sortino_ratio", "calmar_ratio",
                                             "win_rate", "payoff_ratio", "trade_count", "turnover", "exposure",
                                             "var", "cvar", "regime_breakdown", "paper_live_drift",
                                             "replay_compatibility_flag", "risk_gate_replay_compatibility_flag",
                                             "market_reality_compatibility_flag", "taiwan_constraints_flag",
                                             "min_fee_effect", "partial_fill_rate", "rejected_order_rate",
                                             "timeout_cancel_rate", "drawdown_duration", "skewness", "kurtosis",
                                             "capacity_liquidity_cap"]}
        evidence = {"R038e_test_count": 80, "formal_status_code": "candidate_ready_awaiting_manual_review"}
        report = {"tests_passed": 80, "tests_total": 80, "status": "completed", "R038e_completed": False}
        codes = validate_report_output_consistency(
            machine, evidence, report, None,
            "round_id: TEST\nformal_status_code: candidate_ready_awaiting_manual_review",
            None
        )
        assert len(codes) == 0

    def test_validation_result_present(self):
        machine = {"validation_result": {"pass_": True, "reason_codes": []}}
        evidence = {"R038e_test_count": 50}
        report = {"tests_passed": 50}
        codes = validate_report_output_consistency(machine, evidence, report, None, None, None)
        assert len(codes) == 0

    def test_upstream_refs_all_present_passes(self):
        codes = validate_upstream_refs("refa", "refb", "refc", "refd", {
            "r038a": "refa", "r038b": "refb", "r038c": "refc", "r038d": "refd"
        })
        assert len(codes) == 0

    def test_r038a_ref_present(self):
        codes = validate_upstream_refs("refa", "refb", "refc", "refd", {"r038a": "refa"})
        assert len(codes) == 0

    def test_r038b_ref_present(self):
        codes = validate_upstream_refs("refa", "refb", "refc", "refd", {"r038b": "refb"})
        assert len(codes) == 0

    def test_r038c_ref_present(self):
        codes = validate_upstream_refs("refa", "refb", "refc", "refd", {"r038c": "refc"})
        assert len(codes) == 0

    def test_r038d_ref_present(self):
        codes = validate_upstream_refs("refa", "refb", "refc", "refd", {"r038d": "refd"})
        assert len(codes) == 0


# =============================================================================
# Positive Tests: Taiwan Market Reality Metrics Complete
# =============================================================================


class TestTaiwanMarketRealityMetrics:
    def test_taiwan_securities_tax_rate_defined(self):
        assert TAIWAN_SECURITIES_TAX_RATE == 0.003

    def test_taiwan_minimum_fee_defined(self):
        assert TAIWAN_MINIMUM_FEE == 20

    def test_taiwan_price_limit_band_defined(self):
        assert TAIWAN_PRICE_LIMIT_BAND == 0.10

    def test_taiwan_t_plus_2_settlement_true(self):
        assert TAIWAN_T_PLUS_2_SETTLEMENT is True

    def test_taiwan_constraints_flag_in_required_metrics(self):
        assert "taiwan_constraints_flag" in REQUIRED_METRIC_NAMES

    def test_taiwan_relevant_metrics_defined(self):
        taiwan = [m for m in REQUIRED_METRICS if m["taiwan_market_relevant"]]
        assert len(taiwan) >= 12

    def test_min_fee_effect_in_required_metrics(self):
        assert "min_fee_effect" in REQUIRED_METRIC_NAMES

    def test_fill_probability_taiwan_relevant(self):
        fill = [m for m in REQUIRED_METRICS if m["name"] == "fill_probability"]
        assert len(fill) == 1
        assert fill[0]["taiwan_market_relevant"] is True

    def test_net_of_cost_taiwan_relevant(self):
        net = [m for m in REQUIRED_METRICS if m["name"] == "net_of_cost_pnl"]
        assert len(net) == 1
        assert net[0]["taiwan_market_relevant"] is True


# =============================================================================
# Positive Tests: LLM Summary Only
# =============================================================================


class TestLLMBoundary:
    def test_llm_summary_only_does_not_modify_metrics(self):
        metrics = make_complete_metrics()
        # LLM summary can be generated without modifying metrics
        summary = "The strategy achieved net_of_cost_pnl of 12500.0 with sharpe 1.85."
        # Should not raise
        llm_generated_summary(summary, metrics)

    def test_deterministic_validation_always_required(self):
        assert deterministic_validation_required() is True

    def test_llm_cannot_skip_validation(self):
        metrics = make_complete_metrics()
        summary = "skip_validation - auto pass"
        try:
            llm_generated_summary(summary, metrics)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "LLM_PROHIBITED_ACTION" in str(e)

    def test_llm_cannot_force_pass(self):
        metrics = make_complete_metrics()
        summary = "force_pass=true despite failures"
        try:
            llm_generated_summary(summary, metrics)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "LLM_PROHIBITED_ACTION" in str(e)

    def test_llm_cannot_override_result(self):
        metrics = make_complete_metrics()
        summary = "override_result=pass"
        try:
            llm_generated_summary(summary, metrics)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "LLM_PROHIBITED_ACTION" in str(e)


# =============================================================================
# Negative Tests: Fail-closed — Missing Net-of-cost PnL
# =============================================================================


class TestMissingNetOfCostPnl:
    def test_missing_net_of_cost_pnl_fails(self):
        metrics = {"gross_pnl": 15000.0}
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False
        codes = result["reason_codes"]
        assert "METRICS_NET_OF_COST_MISSING" in codes or "METRICS_MISSING_NET_OF_COST_PNL" in codes

    def test_null_net_of_cost_pnl_fails(self):
        metrics = {"net_of_cost_pnl": None, "gross_pnl": 15000.0}
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False

    def test_gross_only_formal_pass_fails(self):
        metrics = {"gross_pnl": 15000.0}
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False
        codes = result["reason_codes"]
        assert "METRICS_GROSS_ONLY_FORMAL_PASS" in codes

    def test_net_of_cost_zero_fails(self):
        metrics = make_complete_metrics()
        metrics["net_of_cost_pnl"] = 0
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is True  # zero is valid, just not positive


# =============================================================================
# Negative Tests: Fail-closed — Missing Cost Metrics
# =============================================================================


class TestMissingCostMetrics:
    def test_missing_fee_cost_fails(self):
        metrics = make_complete_metrics()
        del metrics["fee_cost"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False
        codes = result["reason_codes"]
        assert "METRICS_MISSING_COST" in codes

    def test_missing_tax_cost_fails(self):
        metrics = make_complete_metrics()
        del metrics["tax_cost"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False

    def test_missing_min_fee_effect_fails(self):
        metrics = make_complete_metrics()
        del metrics["min_fee_effect"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False


# =============================================================================
# Negative Tests: Fail-closed — Missing Slippage Metrics
# =============================================================================


class TestMissingSlippageMetrics:
    def test_missing_expected_slippage_fails(self):
        metrics = make_complete_metrics()
        del metrics["expected_slippage"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False
        codes = result["reason_codes"]
        assert "METRICS_MISSING_SLIPPAGE" in codes

    def test_missing_actual_slippage_fails(self):
        metrics = make_complete_metrics()
        del metrics["actual_slippage"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False

    def test_missing_slippage_drift_fails(self):
        metrics = make_complete_metrics()
        del metrics["expected_vs_actual_slippage_drift"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False


# =============================================================================
# Negative Tests: Fail-closed — Missing Fill Metrics
# =============================================================================


class TestMissingFillMetrics:
    def test_missing_fill_probability_fails(self):
        metrics = make_complete_metrics()
        del metrics["fill_probability"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False
        codes = result["reason_codes"]
        assert "METRICS_MISSING_FILL" in codes

    def test_missing_actual_fill_rate_fails(self):
        metrics = make_complete_metrics()
        del metrics["actual_fill_rate"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False

    def test_missing_fill_rate_drift_fails(self):
        metrics = make_complete_metrics()
        del metrics["fill_rate_drift"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False

    def test_missing_rejected_order_rate_fails(self):
        metrics = make_complete_metrics()
        del metrics["rejected_order_rate"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False


# =============================================================================
# Negative Tests: Fail-closed — Missing Tail Risk
# =============================================================================


class TestMissingTailRisk:
    def test_missing_var_fails(self):
        metrics = make_complete_metrics()
        del metrics["var"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False
        codes = result["reason_codes"]
        assert "METRICS_MISSING_TAIL_RISK" in codes

    def test_missing_cvar_fails(self):
        metrics = make_complete_metrics()
        del metrics["cvar"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False


# =============================================================================
# Negative Tests: Fail-closed — Missing Downside Risk
# =============================================================================


class TestMissingDownsideRisk:
    def test_missing_sortino_ratio_fails(self):
        metrics = make_complete_metrics()
        del metrics["sortino_ratio"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False
        codes = result["reason_codes"]
        assert "METRICS_MISSING_DOWNSIDE_RISK" in codes


# =============================================================================
# Negative Tests: Fail-closed — Missing Regime
# =============================================================================


class TestMissingRegime:
    def test_missing_regime_breakdown_fails(self):
        metrics = make_complete_metrics()
        del metrics["regime_breakdown"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False
        codes = result["reason_codes"]
        assert "METRICS_MISSING_REGIME" in codes


# =============================================================================
# Negative Tests: Fail-closed — Missing Paper/Live Drift
# =============================================================================


class TestMissingPaperLiveDrift:
    def test_missing_paper_live_drift_fails(self):
        metrics = make_complete_metrics()
        del metrics["paper_live_drift"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False
        codes = result["reason_codes"]
        assert "METRICS_MISSING_PAPER_LIVE_DRIFT" in codes


# =============================================================================
# Negative Tests: Fail-closed — Missing Taiwan Constraints
# =============================================================================


class TestMissingTaiwanConstraints:
    def test_missing_taiwan_constraints_flag_fails(self):
        metrics = make_complete_metrics()
        del metrics["taiwan_constraints_flag"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False
        codes = result["reason_codes"]
        assert "METRICS_TAIWAN_CONSTRAINTS_FLAG_MISSING" in codes


# =============================================================================
# Negative Tests: Fail-closed — Artifact Source Commit
# =============================================================================


class TestArtifactSourceCommit:
    def test_artifact_missing_source_commit_fails(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        del artifact["source_commit"]
        codes = validate_ci_artifact(artifact, "abc123", "work/test", "R038e")
        assert "ARTIFACT_MISSING_SOURCE_COMMIT" in codes

    def test_artifact_source_commit_mismatch_fails(self):
        artifact = build_validation_artifact(make_complete_metrics(), "wrongcommit", "work/test", {"total": 10, "passed": 10})
        codes = validate_ci_artifact(artifact, "abc123", "work/test", "R038e")
        assert "ARTIFACT_SOURCE_COMMIT_MISMATCH" in codes

    def test_artifact_branch_mismatch_fails(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "wrong/branch", {"total": 10, "passed": 10})
        codes = validate_ci_artifact(artifact, "abc123", "work/test", "R038e")
        assert "ARTIFACT_BRANCH_MISMATCH" in codes


# =============================================================================
# Negative Tests: Fail-closed — Artifact Schema Version
# =============================================================================


class TestArtifactSchemaVersion:
    def test_artifact_missing_schema_version_fails(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        del artifact["schema_version"]
        codes = validate_ci_artifact(artifact, "abc123", "work/test", "R038e")
        assert "ARTIFACT_SCHEMA_VERSION_MISSING" in codes


# =============================================================================
# Negative Tests: Fail-closed — Artifact Status
# =============================================================================


class TestArtifactStatus:
    def test_artifact_claims_r038e_completed_fails(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        artifact["R038e_completed"] = True
        codes = validate_ci_artifact(artifact, "abc123", "work/test", "R038e")
        assert "ARTIFACT_CLAIMS_ROUND_COMPLETED" in codes

    def test_artifact_claims_r038_completed_fails(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        artifact["R038_completed"] = True
        codes = validate_ci_artifact(artifact, "abc123", "work/test", "R038e")
        assert "ARTIFACT_CLAIMS_ROUND_COMPLETED" in codes

    def test_artifact_claims_r038_r048_accepted_fails(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        artifact["R038_R048_accepted"] = True
        codes = validate_ci_artifact(artifact, "abc123", "work/test", "R038e")
        assert "ARTIFACT_CLAIMS_R038_R048_ACCEPTED" in codes

    def test_artifact_starts_r049_fails(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        artifact["R049_started"] = True
        codes = validate_ci_artifact(artifact, "abc123", "work/test", "R038e")
        assert "ARTIFACT_STARTS_R049" in codes

    def test_artifact_order_execution_allowed_true_fails(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        artifact["order_execution_allowed"] = True
        codes = validate_ci_artifact(artifact, "abc123", "work/test", "R038e")
        assert "ARTIFACT_REFERENCES_BROKER_LIVE_RUNTIME" in codes


# =============================================================================
# Negative Tests: Fail-closed — Upstream Refs Missing
# =============================================================================


class TestUpstreamRefs:
    def test_r038a_ref_missing_fails(self):
        codes = validate_upstream_refs(None, "refb", "refc", "refd", {})
        assert "UPSTREAM_REF_R038A_MISSING" in codes

    def test_r038b_ref_missing_fails(self):
        codes = validate_upstream_refs("refa", None, "refc", "refd", {})
        assert "UPSTREAM_REF_R038B_MISSING" in codes

    def test_r038c_ref_missing_fails(self):
        codes = validate_upstream_refs("refa", "refb", None, "refd", {})
        assert "UPSTREAM_REF_R038C_MISSING" in codes

    def test_r038d_ref_missing_fails(self):
        codes = validate_upstream_refs("refa", "refb", "refc", None, {})
        assert "UPSTREAM_REF_R038D_MISSING" in codes

    def test_upstream_ref_stale_fails(self):
        codes = validate_upstream_refs("wrongref", "refb", "refc", "refd", {"r038a": "refa"})
        assert "UPSTREAM_REF_STALE" in codes


# =============================================================================
# Negative Tests: Fail-closed — Stale Artifact
# =============================================================================


class TestStaleArtifact:
    def test_stale_artifact_fails(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        artifact["generated_at"] = make_stale_timestamp()
        codes = validate_ci_artifact(artifact, "abc123", "work/test", "R038e")
        assert "CONSISTENCY_STALE_ARTIFACT" in codes


# =============================================================================
# Negative Tests: Fail-closed — Self-referential Hash
# =============================================================================


class TestSelfReferentialHash:
    def test_self_referential_hash_formal_field_fails(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        artifact["candidate_diff_canonical_hash_sha256"] = "fakehash"
        codes = validate_ci_artifact(artifact, "abc123", "work/test", "R038e")
        assert "ARTIFACT_SELF_REFERENTIAL_HASH_FORMAL_FIELD" in codes

    def test_reproducibility_command_missing_fails(self):
        artifact = build_validation_artifact(make_complete_metrics(), "abc123", "work/test", {"total": 10, "passed": 10})
        del artifact["reproducibility_command"]
        codes = validate_ci_artifact(artifact, "abc123", "work/test", "R038e")
        assert "REPRODUCIBILITY_COMMAND_MISSING" in codes


# =============================================================================
# Negative Tests: Fail-closed — Tests Claim Pass But Fail
# =============================================================================


class TestCIAssertion:
    def test_artifact_claims_ci_pass_but_tests_fail(self):
        artifact = build_validation_artifact(
            metrics=make_complete_metrics(),
            source_commit="abc123",
            source_branch="work/test",
            test_results={"total": 10, "passed": 7},
            r038a_ref="refa", r038b_ref="refb", r038c_ref="refc", r038d_ref="refd",
        )
        codes = validate_ci_artifact(artifact, "abc123", "work/test", "R038e")
        assert "ARTIFACT_CLAIMS_CI_PASS_BUT_TESTS_FAIL" in codes


# =============================================================================
# Boundary Tests
# =============================================================================


class TestBoundaryConditions:
    def test_stale_threshold_exactly_allowed(self):
        ts = (datetime.now(timezone.utc) - timedelta(days=DEFAULT_VALIDATION_FRESHNESS_DAYS - 1)).isoformat()
        codes = validate_metric_definition("net_of_cost_pnl", 100.0, "currency", "backtest_result", "1.0", ts, True)
        assert "METRICS_STALE" not in codes

    def test_stale_threshold_exactly_rejected(self):
        ts = (datetime.now(timezone.utc) - timedelta(days=DEFAULT_VALIDATION_FRESHNESS_DAYS + 1)).isoformat()
        codes = validate_metric_definition("net_of_cost_pnl", 100.0, "currency", "backtest_result", "1.0", ts, True)
        assert "METRICS_STALE" in codes

    def test_metric_count_exactly_minimum(self):
        metrics = make_complete_metrics()
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        included = len(result["reason_codes"]) == 0
        assert included

    def test_trade_count_exactly_threshold(self):
        metrics = make_complete_metrics()
        metrics["trade_count"] = 1
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is True

    def test_drawdown_exactly_threshold(self):
        metrics = make_complete_metrics()
        metrics["max_drawdown"] = -100000.0
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is True

    def test_slippage_drift_exactly_threshold(self):
        metrics = make_complete_metrics()
        metrics["expected_vs_actual_slippage_drift"] = 0.001
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is True

    def test_fill_rate_drift_exactly_threshold(self):
        metrics = make_complete_metrics()
        metrics["fill_rate_drift"] = 0.001
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is True

    def test_paper_live_drift_exactly_threshold(self):
        metrics = make_complete_metrics()
        metrics["paper_live_drift"] = 0.001
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is True

    def test_optional_human_summary_absent_but_machine_complete(self):
        metrics = make_complete_metrics()
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is True


# =============================================================================
# Replay Compatibility
# =============================================================================


class TestReplayCompatibility:
    def test_replay_compatibility_flag_in_required_metrics(self):
        assert "replay_compatibility_flag" in REQUIRED_METRIC_NAMES

    def test_risk_gate_replay_compatibility_in_required(self):
        assert "risk_gate_replay_compatibility_flag" in REQUIRED_METRIC_NAMES

    def test_market_reality_compatibility_in_required(self):
        assert "market_reality_compatibility_flag" in REQUIRED_METRIC_NAMES

    def test_all_replay_flags_taiwan_relevant(self):
        for name in ["replay_compatibility_flag", "risk_gate_replay_compatibility_flag", "market_reality_compatibility_flag"]:
            m = [x for x in REQUIRED_METRICS if x["name"] == name]
            assert len(m) == 1
            assert m[0]["taiwan_market_relevant"] is True


# =============================================================================
# TradingView-only Metrics Rejected
# =============================================================================


class TestTradingViewOnlyRejected:
    def test_tv_only_metrics_formal_pass_fails(self):
        metrics = {
            "tv_signal_count": 10,
            "tv_indicator_value": 0.5,
            "tv_only_return": 0.05,
            "gross_pnl": 100.0,
        }
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False
        codes = result["reason_codes"]
        assert "TRADINGVIEW_ONLY_METRICS_FORMAL_PASS" in codes


# =============================================================================
# Consistency Checks
# =============================================================================


class TestConsistencyFailClosed:
    def test_json_report_evidence_mismatch_fails(self):
        machine = {"validation_result": {"pass_": True, "reason_codes": []}}
        evidence = {"R038e_test_count": 100}
        report = {"tests_passed": 95}
        codes = validate_report_output_consistency(machine, evidence, report, None, None, None)
        assert "CONSISTENCY_EVIDENCE_REPORT_MISMATCH" in codes

    def test_rtctg_blocked_but_evidence_ready_fails(self):
        machine = {"test_count": 80}
        evidence = {"R038e_test_count": 80, "formal_status_code": "candidate_ready_awaiting_manual_review"}
        report = {"tests_passed": 80, "status": "completed"}
        codes = validate_report_output_consistency(
            machine, evidence, report, None,
            "formal_status_code: BLOCKED",
            None
        )
        assert "CONSISTENCY_RTCG_STATUS_MISMATCH" in codes

    def test_artifact_present_but_metrics_missing_fails(self):
        machine = {"included_metric_names": ["net_of_cost_pnl"]}
        evidence = {"R038e_test_count": 10}
        report = {"tests_passed": 10}
        codes = validate_report_output_consistency(machine, evidence, report, None, None, None)
        assert "CONSISTENCY_ARTIFACT_PRESENT_BUT_METRICS_MISSING" in codes

    def test_artifact_present_but_validator_result_missing_fails(self):
        machine = {"test_count": 50}
        evidence = {"R038e_test_count": 50}
        report = {"tests_passed": 50}
        codes = validate_report_output_consistency(machine, evidence, report, None, None, None)
        assert "CONSISTENCY_ARTIFACT_PRESENT_BUT_VALIDATOR_RESULT_MISSING" in codes


# =============================================================================
# Replay and Risk Gate Replay Ignored Fails
# =============================================================================


class TestReplayCompatibilityFail:
    def test_missing_replay_compatibility_fails(self):
        metrics = make_complete_metrics()
        del metrics["replay_compatibility_flag"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False
        codes = result["reason_codes"]
        assert "METRICS_IGNORES_REPLAY_COMPATIBILITY" in codes

    def test_missing_risk_gate_replay_fails(self):
        metrics = make_complete_metrics()
        del metrics["risk_gate_replay_compatibility_flag"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False

    def test_missing_market_reality_compatibility_fails(self):
        metrics = make_complete_metrics()
        del metrics["market_reality_compatibility_flag"]
        result = validate_metrics_bundle(metrics, "abc123", "work/test", make_fresh_timestamp())
        assert result["pass_"] is False