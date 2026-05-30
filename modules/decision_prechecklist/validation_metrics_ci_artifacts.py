"""
R038e: Metrics contract, CI artifacts contract, and validation report output consistency.
Internal subtask only. Not R038 completion. Not R038-R048 acceptance. Not R049.
order_execution_allowed must remain FALSE. No broker/live/runtime/order path.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, NotRequired, TypedDict


# =============================================================================
# Enums
# =============================================================================


class MetricCategory(str, Enum):
    PNL = "pnl"
    COST = "cost"
    SLIPPAGE = "slippage"
    FILL = "fill"
    RISK = "risk"
    DRAWdown = "drawdown"
    REGIME = "regime"
    DRIFT = "drift"
    REPLAY = "replay"
    TAIWAN_MARKET = "taiwan_market"
    CONSISTENCY = "consistency"
    ARTIFACT = "artifact"


class ValidationArtifactType(str, Enum):
    METRICS_BUNDLE = "metrics_bundle"
    CI_EVIDENCE_ARTIFACT = "ci_evidence_artifact"
    VALIDATION_REPORT = "validation_report"
    EVIDENCE_JSON = "evidence_json"
    TEST_RESULTS = "test_results"
    RETURN_TO_CHATGPT = "return_to_chatgpt"


# =============================================================================
# Dataclasses / TypedDicts
# =============================================================================


class MetricDefinition(TypedDict):
    name: str
    category: str
    unit: str
    required: bool
    source: str
    calculation_version: str
    time_window_days: int | None
    taiwan_market_relevant: bool
    description: str


class MetricValue(TypedDict):
    name: str
    value: float | int | bool | str | None
    unit: str
    source: str
    generated_at: str
    calculation_version: str
    stale: bool


class ValidationReportArtifact(TypedDict):
    artifact_id: str
    artifact_type: str
    generated_at: str
    source_commit: str
    source_branch: str
    internal_subtask: str
    validation_stage: str
    schema_version: str
    metrics_contract_version: str
    validator_version: str
    test_suite_results: dict[str, Any]
    required_metric_names: list[str]
    included_metric_names: list[str]
    missing_metric_names: list[str]
    report_status: str
    formal_status_code: str
    evidence_hash_policy: str
    self_reference_policy: str
    reproducibility_command: str | None
    no_broker_live_runtime_flags: bool
    order_execution_allowed: bool
    r038a_ref_commit: str | None
    r038b_ref_commit: str | None
    r038c_ref_commit: str | None
    r038d_ref_commit: str | None


class ValidationReportBundle(TypedDict):
    machine_readable: dict[str, Any]
    human_readable_summary: str | None
    artifacts: list[ValidationReportArtifact]
    upstream_refs: dict[str, str]


class MetricsArtifactPolicy(TypedDict):
    self_reference_policy: str
    hash_excluded_paths: list[str]
    reproducibility_command: str
    allowed_artifact_types: list[str]
    required_status_fields: list[str]
    fail_closed_status_codes: list[str]


class MetricsArtifactValidationResult(TypedDict):
    pass_: bool
    reason_codes: list[str]
    failed_metric_names: list[str]
    failed_artifact_checks: list[str]
    consistency_failures: list[str]
    upstream_ref_failures: list[str]


# =============================================================================
# Required Metrics Contract
# =============================================================================


REQUIRED_METRICS: list[MetricDefinition] = [
    # PnL
    MetricDefinition(name="net_of_cost_pnl", category=MetricCategory.PNL, unit="currency", required=True,
                     source="backtest_result", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Net PnL after all costs"),
    MetricDefinition(name="gross_pnl", category=MetricCategory.PNL, unit="currency", required=True,
                     source="backtest_result", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Gross PnL before costs"),
    MetricDefinition(name="total_cost", category=MetricCategory.COST, unit="currency", required=True,
                     source="transaction_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Total trading cost"),
    MetricDefinition(name="fee_cost", category=MetricCategory.COST, unit="currency", required=True,
                     source="transaction_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Brokerage fee"),
    MetricDefinition(name="tax_cost", category=MetricCategory.COST, unit="currency", required=True,
                     source="transaction_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Taiwan securities transaction tax"),
    MetricDefinition(name="min_fee_effect", category=MetricCategory.COST, unit="currency", required=True,
                     source="transaction_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Minimum fee effect for small trades"),
    # Slippage
    MetricDefinition(name="expected_slippage", category=MetricCategory.SLIPPAGE, unit="currency", required=True,
                     source="market_data", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Expected slippage cost"),
    MetricDefinition(name="actual_slippage", category=MetricCategory.SLIPPAGE, unit="currency", required=True,
                     source="execution_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Actual slippage observed"),
    MetricDefinition(name="expected_vs_actual_slippage_drift", category=MetricCategory.SLIPPAGE, unit="percent", required=True,
                     source="execution_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Drift between expected and actual slippage"),
    # Fill
    MetricDefinition(name="fill_probability", category=MetricCategory.FILL, unit="percent", required=True,
                     source="execution_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Order fill probability"),
    MetricDefinition(name="actual_fill_rate", category=MetricCategory.FILL, unit="percent", required=True,
                     source="execution_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Actual fill rate"),
    MetricDefinition(name="fill_rate_drift", category=MetricCategory.FILL, unit="percent", required=True,
                     source="execution_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Drift between expected and actual fill rate"),
    MetricDefinition(name="partial_fill_rate", category=MetricCategory.FILL, unit="percent", required=True,
                     source="execution_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Partial fill rate"),
    MetricDefinition(name="rejected_order_rate", category=MetricCategory.FILL, unit="percent", required=True,
                     source="execution_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Rejected order rate"),
    MetricDefinition(name="timeout_cancel_rate", category=MetricCategory.FILL, unit="percent", required=True,
                     source="execution_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Timeout cancel rate"),
    # Risk
    MetricDefinition(name="max_drawdown", category=MetricCategory.DRAWdown, unit="currency", required=True,
                     source="equity_curve", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=False, description="Maximum drawdown"),
    MetricDefinition(name="drawdown_duration", category=MetricCategory.DRAWdown, unit="days", required=True,
                     source="equity_curve", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=False, description="Drawdown duration"),
    MetricDefinition(name="sharpe_ratio", category=MetricCategory.RISK, unit="ratio", required=True,
                     source="equity_curve", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=False, description="Sharpe ratio"),
    MetricDefinition(name="sortino_ratio", category=MetricCategory.RISK, unit="ratio", required=True,
                     source="equity_curve", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=False, description="Sortino ratio (downside risk)"),
    MetricDefinition(name="calmar_ratio", category=MetricCategory.RISK, unit="ratio", required=True,
                     source="equity_curve", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=False, description="Calmar ratio"),
    MetricDefinition(name="win_rate", category=MetricCategory.RISK, unit="percent", required=True,
                     source="trade_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=False, description="Win rate"),
    MetricDefinition(name="payoff_ratio", category=MetricCategory.RISK, unit="ratio", required=True,
                     source="trade_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=False, description="Payoff ratio"),
    MetricDefinition(name="trade_count", category=MetricCategory.RISK, unit="count", required=True,
                     source="trade_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=False, description="Total trade count"),
    MetricDefinition(name="turnover", category=MetricCategory.RISK, unit="currency", required=True,
                     source="trade_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=False, description="Portfolio turnover"),
    MetricDefinition(name="exposure", category=MetricCategory.RISK, unit="percent", required=True,
                     source="position_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=False, description="Portfolio exposure"),
    MetricDefinition(name="capacity_liquidity_cap", category=MetricCategory.RISK, unit="currency", required=True,
                     source="market_data", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Liquidity cap for position sizing"),
    MetricDefinition(name="var", category=MetricCategory.RISK, unit="currency", required=True,
                     source="equity_curve", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=False, description="Value at Risk"),
    MetricDefinition(name="cvar", category=MetricCategory.RISK, unit="currency", required=True,
                     source="equity_curve", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=False, description="Conditional Value at Risk"),
    MetricDefinition(name="skewness", category=MetricCategory.RISK, unit="ratio", required=True,
                     source="equity_curve", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=False, description="Return distribution skewness"),
    MetricDefinition(name="kurtosis", category=MetricCategory.RISK, unit="ratio", required=True,
                     source="equity_curve", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=False, description="Return distribution kurtosis"),
    # Regime
    MetricDefinition(name="regime_breakdown", category=MetricCategory.REGIME, unit="json", required=True,
                     source="regime_classifier", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=False, description="Regime segmentation breakdown"),
    # Drift
    MetricDefinition(name="paper_live_drift", category=MetricCategory.DRIFT, unit="percent", required=True,
                     source="comparison_log", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Paper vs live performance drift"),
    # Replay
    MetricDefinition(name="replay_compatibility_flag", category=MetricCategory.REPLAY, unit="bool", required=True,
                     source="backtest_result", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Replay compatibility confirmed"),
    MetricDefinition(name="risk_gate_replay_compatibility_flag", category=MetricCategory.REPLAY, unit="bool", required=True,
                     source="risk_gate_result", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Risk gate replay compatibility confirmed"),
    MetricDefinition(name="market_reality_compatibility_flag", category=MetricCategory.REPLAY, unit="bool", required=True,
                     source="market_reality_result", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Market Reality compatibility confirmed"),
    # Taiwan market
    MetricDefinition(name="taiwan_constraints_flag", category=MetricCategory.TAIWAN_MARKET, unit="bool", required=True,
                     source="taiwan_validator", calculation_version="1.0", time_window_days=None,
                     taiwan_market_relevant=True, description="Taiwan market constraints acknowledged"),
]

REQUIRED_METRIC_NAMES = {m["name"] for m in REQUIRED_METRICS}

# =============================================================================
# Reason Codes
# =============================================================================

REASON_CODES = {
    "METRICS_MISSING_NET_OF_COST_PNL": "required metric net_of_cost_pnl missing or null",
    "METRICS_GROSS_ONLY_FORMAL_PASS": "gross-only PnL used as formal pass criterion; net-of-cost required",
    "METRICS_MISSING_COST": "required cost metrics (fee/tax/min_fee_effect) missing",
    "METRICS_MISSING_SLIPPAGE": "required slippage metrics (expected/actual/drift) missing",
    "METRICS_MISSING_FILL": "required fill metrics (probability/rate/drift/partial/rejected/timeout) missing",
    "METRICS_MISSING_TAIL_RISK": "required tail-risk metrics (VaR/CVaR) missing",
    "METRICS_MISSING_DOWNSIDE_RISK": "required downside-risk metric (Sortino) missing",
    "METRICS_MISSING_REGIME": "required regime breakdown missing",
    "METRICS_MISSING_PAPER_LIVE_DRIFT": "required paper_live_drift metric missing",
    "METRICS_MISSING_REQUIRED": "required metric missing from artifact",
    "METRICS_VALUE_TYPE_INVALID": "metric value type is invalid or wrong",
    "METRICS_UNIT_MISSING": "metric unit missing",
    "METRICS_SOURCE_MISSING": "metric source missing",
    "METRICS_CALCULATION_VERSION_MISSING": "metric calculation_version missing",
    "METRICS_TIME_WINDOW_MISSING": "metric time_window missing for time-bounded metric",
    "METRICS_STALE": "metric value is stale (generated_at too old)",
    "ARTIFACT_MISSING_SOURCE_COMMIT": "artifact source_commit missing",
    "ARTIFACT_SOURCE_COMMIT_MISMATCH": "artifact source_commit does not match expected HEAD",
    "ARTIFACT_BRANCH_MISMATCH": "artifact source_branch does not match expected branch",
    "ARTIFACT_SCHEMA_VERSION_MISSING": "artifact schema_version missing",
    "ARTIFACT_INTERNAL_SUBTASK_MISMATCH": "artifact internal_subtask does not match R038e",
    "ARTIFACT_FORMAL_STATUS_CODE_INVALID": "artifact formal_status_code is not an accepted value",
    "ARTIFACT_REPORT_STATUS_INVALID": "artifact report_status is not accepted by evidence checker",
    "ARTIFACT_CLAIMS_CI_PASS_BUT_TESTS_FAIL": "artifact claims CI pass but not all tests passed",
    "ARTIFACT_CLAIMS_ROUND_COMPLETED": "artifact incorrectly claims R038e_completed or R038_completed",
    "ARTIFACT_CLAIMS_R038_R048_ACCEPTED": "artifact incorrectly claims R038-R048 acceptance",
    "ARTIFACT_STARTS_R049": "artifact incorrectly starts or references R049",
    "ARTIFACT_SELF_REFERENTIAL_HASH_FORMAL_FIELD": "artifact contains self-referential hash as formal pass field",
    "ARTIFACT_HASH_MISMATCH_IGNORED": "artifact hash mismatch is ignored by validator",
    "ARTIFACT_GENERATED_OUTSIDE_ALLOWED_PATH": "artifact generated outside allowed evidence path",
    "ARTIFACT_REFERENCES_BROKER_LIVE_RUNTIME": "artifact references broker/live/runtime/order path",
    "CONSISTENCY_JSON_REPORT_MISMATCH": "JSON artifact and markdown/report metrics are inconsistent",
    "CONSISTENCY_EVIDENCE_REPORT_MISMATCH": "evidence.json and report.json test count are inconsistent",
    "CONSISTENCY_RTCG_STATUS_MISMATCH": "RETURN_TO_CHATGPT formal_status does not match evidence.json status",
    "CONSISTENCY_REPORT_STATUS_SEMANTICS_CONFUSED": "report status value confuses R038e_completed with R038_completed",
    "CONSISTENCY_METRICS_COUNT_MISMATCH": "required metrics list count does not match included metrics count",
    "CONSISTENCY_STALE_ARTIFACT": "artifact has stale generated_at or source_commit hash",
    "CONSISTENCY_ARTIFACT_PRESENT_BUT_METRICS_MISSING": "artifact is present but required metrics are missing",
    "CONSISTENCY_ARTIFACT_PRESENT_BUT_VALIDATOR_RESULT_MISSING": "artifact present but validation result is missing",
    "UPSTREAM_REF_R038A_MISSING": "R038a upstream reference missing from artifact",
    "UPSTREAM_REF_R038B_MISSING": "R038b upstream reference missing from artifact",
    "UPSTREAM_REF_R038C_MISSING": "R038c upstream reference missing from artifact",
    "UPSTREAM_REF_R038D_MISSING": "R038d upstream reference missing from artifact",
    "UPSTREAM_REF_STALE": "upstream reference points to stale commit",
    "UPSTREAM_REF_FAILED": "upstream reference indicates failed validation",
    "TRADINGVIEW_ONLY_METRICS_FORMAL_PASS": "TradingView-only metrics used as formal pass; real market data required",
    "LLM_EDITED_METRIC_VALUE": "LLM or API modified metric value",
    "LLM_MARKED_CI_PASS": "LLM or API marked CI as pass without deterministic validation",
    "API_FAILURE_DEFAULTS_PASS": "API failure defaults to pass without local deterministic validation",
    "DETERMINISTIC_VALIDATION_RESULT_MISSING": "local deterministic validation result is missing",
    "METRICS_IGNORES_TAIWAN_COSTS": "metrics ignore Taiwan-specific costs (tax, min fee, slippage)",
    "METRICS_IGNORES_LIQUIDITY": "metrics ignore liquidity constraints",
    "METRICS_IGNORES_FILL_REALISM": "metrics ignore fill probability / partial fill realism",
    "METRICS_IGNORES_NET_OF_COST": "metrics allow pass without net-of-cost calculation",
    "METRICS_IGNORES_REPLAY_COMPATIBILITY": "metrics ignore replay/risk gate replay compatibility",
    "REPRODUCIBILITY_COMMAND_MISSING": "artifact reproducibility command is missing",
    "REPRODUCIBILITY_FAILED": "artifact cannot be reproduced from reproducibility command",
    "METRICS_TAIWAN_CONSTRAINTS_FLAG_MISSING": "Taiwan market constraints flag missing from metrics",
    "METRICS_NET_OF_COST_MISSING": "net-of-cost PnL metric missing",
}


# =============================================================================
# Policy Constants
# =============================================================================

METRICS_CONTRACT_VERSION = "1.0"
ARTIFACT_SCHEMA_VERSION = "1.0"
VALIDATOR_VERSION = "1.0"
DEFAULT_VALIDATION_FRESHNESS_DAYS = 30

# Taiwan market constants
TAIWAN_SECURITIES_TAX_RATE = 0.003  # 0.3% for stock transactions
TAIWAN_MINIMUM_FEE = 20  # TWD minimum brokerage fee
TAIWAN_PRICE_LIMIT_BAND = 0.10  # ±10% daily price limit
TAIWAN_T_PLUS_2_SETTLEMENT = True  # T+2 settlement

# Acceptable report status values
ACCEPTED_REPORT_STATUS_VALUES = [
    "completed",
    "ready_for_merge_signoff",
    "candidate_ready_awaiting_manual_review",
    "merge_completed",
    "evidence_package_complete",
]

# Acceptable formal status codes
ACCEPTED_FORMAL_STATUS_CODES = [
    "candidate_ready_awaiting_manual_review",
    "BLOCKED",
    "FAILED",
    "R038E_METRICS_AND_CI_ARTIFACTS_MANUAL_REVIEW_PASS",
    "R038E_METRICS_AND_CI_ARTIFACTS_MANUAL_REVIEW_BLOCKED",
    "candidate_in_construction",
]

# Forbidden status: round completion
FORBIDDEN_STATUS_COMBINATIONS = [
    ("R038e_completed", True, "R038e_completed must remain FALSE until full pipeline review"),
    ("R038_completed", True, "R038_completed must remain FALSE until official close"),
    ("R038_R048_accepted", True, "R038-R048 acceptance is not authorized"),
    ("R049_started", True, "R049 is not started"),
    ("order_execution_allowed", True, "order_execution_allowed must remain FALSE"),
]

# =============================================================================
# Validation Functions
# =============================================================================


def validate_metric_definition(name: str, value: Any, unit: str, source: str,
                                calculation_version: str,
                                generated_at: str | None,
                                is_required: bool,
                                taiwan_market_relevant: bool = False) -> list[str]:
    """
    Validate a single metric against the contract.
    Returns list of reason codes (empty = pass).
    """
    codes: list[str] = []

    if value is None:
        if is_required:
            codes.append("METRICS_MISSING_REQUIRED")
            if name == "net_of_cost_pnl":
                codes.append("METRICS_NET_OF_COST_MISSING")
        return codes

    if not isinstance(value, (int, float, bool, str)):
        codes.append("METRICS_VALUE_TYPE_INVALID")

    if not unit:
        codes.append("METRICS_UNIT_MISSING")

    if not source:
        codes.append("METRICS_SOURCE_MISSING")

    if not calculation_version:
        codes.append("METRICS_CALCULATION_VERSION_MISSING")

    if generated_at:
        try:
            ts = datetime.fromisoformat(generated_at)
            age = (datetime.now(timezone.utc) - ts).days
            if age > DEFAULT_VALIDATION_FRESHNESS_DAYS:
                codes.append("METRICS_STALE")
        except Exception:
            codes.append("METRICS_STALE")

    # Special case: net_of_cost_pnl must exist
    if name == "net_of_cost_pnl" and (value is None or not isinstance(value, (int, float))):
        codes.append("METRICS_NET_OF_COST_MISSING")
        codes.append("METRICS_MISSING_NET_OF_COST_PNL")

    # Special case: Taiwan-relevant metrics must have Taiwan constraints
    if taiwan_market_relevant:
        # cost/slippage/fill metrics must not be missing for Taiwan market
        cost_metrics = {"fee_cost", "tax_cost", "min_fee_effect", "expected_slippage", "actual_slippage",
                        "fill_probability", "actual_fill_rate", "rejected_order_rate"}
        slippage_metrics = {"expected_slippage", "actual_slippage", "expected_vs_actual_slippage_drift"}
        fill_metrics = {"fill_probability", "actual_fill_rate", "partial_fill_rate",
                        "rejected_order_rate", "timeout_cancel_rate"}

        if name in cost_metrics and value is None:
            codes.append("METRICS_IGNORES_TAIWAN_COSTS")
        if name in slippage_metrics and value is None:
            codes.append("METRICS_IGNORES_TAIWAN_COSTS")
        if name in fill_metrics and value is None:
            codes.append("METRICS_IGNORES_FILL_REALISM")

    # Tail risk metrics check
    if name in ("var", "cvar") and value is None:
        codes.append("METRICS_MISSING_TAIL_RISK")

    # Downside risk check
    if name == "sortino_ratio" and value is None:
        codes.append("METRICS_MISSING_DOWNSIDE_RISK")

    # Regime check
    if name == "regime_breakdown" and value is None:
        codes.append("METRICS_MISSING_REGIME")

    # Drift check
    if name == "paper_live_drift" and value is None:
        codes.append("METRICS_MISSING_PAPER_LIVE_DRIFT")

    return codes


def validate_metrics_bundle(metrics: dict[str, Any],
                              source_commit: str,
                              source_branch: str,
                              generated_at: str) -> MetricsArtifactValidationResult:
    """
    Validate a complete metrics bundle against the contract.
    Returns pass/fail with detailed reason codes.
    """
    codes: list[str] = []
    failed_metrics: list[str] = []
    failed_artifact_checks: list[str] = []

    # 1. Check required metrics present
    included_names = set(metrics.keys())
    missing_names = REQUIRED_METRIC_NAMES - included_names

    if "net_of_cost_pnl" in missing_names:
        codes.append("METRICS_MISSING_NET_OF_COST_PNL")
        codes.append("METRICS_NET_OF_COST_MISSING")
        failed_metrics.append("net_of_cost_pnl")

    # Check gross-only pass
    gross_pnl = metrics.get("gross_pnl")
    net_pnl = metrics.get("net_of_cost_pnl")
    if gross_pnl is not None and net_pnl is None:
        codes.append("METRICS_GROSS_ONLY_FORMAL_PASS")
        codes.append("METRICS_IGNORES_NET_OF_COST")
        failed_metrics.append("net_of_cost_pnl")

    # Check missing cost metrics
    cost_names = {"fee_cost", "tax_cost", "min_fee_effect", "total_cost"}
    missing_cost = cost_names - included_names
    if missing_cost and "net_of_cost_pnl" in included_names:
        codes.append("METRICS_MISSING_COST")

    # Check missing slippage metrics
    slippage_names = {"expected_slippage", "actual_slippage", "expected_vs_actual_slippage_drift"}
    missing_slippage = slippage_names - included_names
    if missing_slippage:
        codes.append("METRICS_MISSING_SLIPPAGE")

    # Check missing fill metrics
    fill_names = {"fill_probability", "actual_fill_rate", "fill_rate_drift",
                  "partial_fill_rate", "rejected_order_rate", "timeout_cancel_rate"}
    missing_fill = fill_names - included_names
    if missing_fill:
        codes.append("METRICS_MISSING_FILL")

    # Check missing tail risk
    tail_names = {"var", "cvar"}
    missing_tail = tail_names - included_names
    if missing_tail:
        codes.append("METRICS_MISSING_TAIL_RISK")

    # Check missing downside risk
    if "sortino_ratio" not in included_names:
        codes.append("METRICS_MISSING_DOWNSIDE_RISK")

    # Check missing regime
    if "regime_breakdown" not in included_names:
        codes.append("METRICS_MISSING_REGIME")

    # Check missing drift
    if "paper_live_drift" not in included_names:
        codes.append("METRICS_MISSING_PAPER_LIVE_DRIFT")

    # Check missing replay flags
    for flag in ("replay_compatibility_flag", "risk_gate_replay_compatibility_flag", "market_reality_compatibility_flag"):
        if flag not in included_names:
            codes.append("METRICS_IGNORES_REPLAY_COMPATIBILITY")
            break

    # Check Taiwan constraints flag
    if "taiwan_constraints_flag" not in included_names:
        codes.append("METRICS_TAIWAN_CONSTRAINTS_FLAG_MISSING")
        codes.append("METRICS_IGNORES_TAIWAN_COSTS")

    # 2. Validate each metric
    for m_def in REQUIRED_METRICS:
        name = m_def["name"]
        if name in metrics:
            value = metrics[name]
            unit = m_def["unit"]
            source = m_def["source"]
            gen_at = generated_at
            m_codes = validate_metric_definition(
                name=name, value=value, unit=unit, source=source,
                calculation_version="1.0",
                generated_at=gen_at,
                is_required=m_def["required"],
                taiwan_market_relevant=m_def["taiwan_market_relevant"]
            )
            codes.extend(m_codes)
            if m_codes:
                failed_metrics.append(name)

    # 3. TradingView-only check
    tv_only_indicators = {"tv_signal_count", "tv_indicator_value", "tv_only_return"}
    if tv_only_indicators.issubset(included_names) and len(included_names - tv_only_indicators) < 5:
        codes.append("TRADINGVIEW_ONLY_METRICS_FORMAL_PASS")

    passed = len(codes) == 0
    return MetricsArtifactValidationResult(
        pass_=passed,
        reason_codes=codes,
        failed_metric_names=list(set(failed_metrics)),
        failed_artifact_checks=failed_artifact_checks,
        consistency_failures=[],
        upstream_ref_failures=[],
    )


def validate_ci_artifact(artifact: ValidationReportArtifact,
                          expected_source_commit: str,
                          expected_branch: str,
                          expected_internal_subtask: str = "R038e") -> list[str]:
    """
    Validate a CI artifact against the contract.
    Returns list of reason codes (empty = pass).
    """
    codes: list[str] = []

    # Source commit check
    if not artifact.get("source_commit"):
        codes.append("ARTIFACT_MISSING_SOURCE_COMMIT")
    elif artifact["source_commit"] != expected_source_commit:
        codes.append("ARTIFACT_SOURCE_COMMIT_MISMATCH")

    # Branch check
    if artifact.get("source_branch") != expected_branch:
        codes.append("ARTIFACT_BRANCH_MISMATCH")

    # Schema version check
    if not artifact.get("schema_version"):
        codes.append("ARTIFACT_SCHEMA_VERSION_MISSING")

    # Internal subtask check
    if artifact.get("internal_subtask") != expected_internal_subtask:
        codes.append("ARTIFACT_INTERNAL_SUBTASK_MISMATCH")

    # Formal status code check
    fsc = artifact.get("formal_status_code", "")
    if fsc and fsc not in ACCEPTED_FORMAL_STATUS_CODES:
        codes.append("ARTIFACT_FORMAL_STATUS_CODE_INVALID")

    # Report status check
    rs = artifact.get("report_status", "")
    if rs and rs not in ACCEPTED_REPORT_STATUS_VALUES:
        codes.append("ARTIFACT_REPORT_STATUS_INVALID")

    # Status semantics check
    if artifact.get("R038e_completed"):
        codes.append("ARTIFACT_CLAIMS_ROUND_COMPLETED")
    if artifact.get("R038_completed"):
        codes.append("ARTIFACT_CLAIMS_ROUND_COMPLETED")
    if artifact.get("R038_R048_accepted"):
        codes.append("ARTIFACT_CLAIMS_R038_R048_ACCEPTED")
    if artifact.get("R049_started"):
        codes.append("ARTIFACT_STARTS_R049")
    if artifact.get("order_execution_allowed"):
        codes.append("ARTIFACT_REFERENCES_BROKER_LIVE_RUNTIME")

    # No broker/live/runtime flags check
    if not artifact.get("no_broker_live_runtime_flags", True):
        codes.append("ARTIFACT_REFERENCES_BROKER_LIVE_RUNTIME")

    # Self-referential hash check
    if "candidate_diff_canonical_hash_sha256" in artifact:
        # This field must not be a formal pass field
        codes.append("ARTIFACT_SELF_REFERENTIAL_HASH_FORMAL_FIELD")

    # Reproducibility command check
    if not artifact.get("reproducibility_command"):
        codes.append("REPRODUCIBILITY_COMMAND_MISSING")

    # Test suite results check
    tsr = artifact.get("test_suite_results", {})
    if tsr:
        total = tsr.get("total", 0)
        passed = tsr.get("passed", 0)
        if total > 0 and passed < total:
            codes.append("ARTIFACT_CLAIMS_CI_PASS_BUT_TESTS_FAIL")

    # Upstream refs check
    if not artifact.get("r038a_ref_commit"):
        codes.append("UPSTREAM_REF_R038A_MISSING")
    if not artifact.get("r038b_ref_commit"):
        codes.append("UPSTREAM_REF_R038B_MISSING")
    if not artifact.get("r038c_ref_commit"):
        codes.append("UPSTREAM_REF_R038C_MISSING")
    if not artifact.get("r038d_ref_commit"):
        codes.append("UPSTREAM_REF_R038D_MISSING")

    # Stale artifact check
    if artifact.get("generated_at"):
        try:
            ts = datetime.fromisoformat(artifact["generated_at"])
            age = (datetime.now(timezone.utc) - ts).days
            if age > DEFAULT_VALIDATION_FRESHNESS_DAYS:
                codes.append("CONSISTENCY_STALE_ARTIFACT")
        except Exception:
            codes.append("CONSISTENCY_STALE_ARTIFACT")

    return codes


def validate_report_output_consistency(
    machine_readable: dict[str, Any],
    evidence_json: dict[str, Any] | None,
    report_json: dict[str, Any] | None,
    test_results_txt: str | None,
    return_to_chatgpt_txt: str | None,
    cicd_stage_result: dict[str, Any] | None,
) -> list[str]:
    """
    Validate consistency across multiple output formats.
    Returns list of reason codes (empty = pass).
    """
    codes: list[str] = []

    # JSON vs evidence consistency
    if evidence_json and report_json:
        ev_tests = evidence_json.get("R038e_test_count") or evidence_json.get("test_count")
        rep_tests = report_json.get("tests_passed")
        if ev_tests is not None and rep_tests is not None:
            if ev_tests != rep_tests:
                codes.append("CONSISTENCY_EVIDENCE_REPORT_MISMATCH")

    # Check formal status consistency between evidence and return_to_chatgpt
    if evidence_json and return_to_chatgpt_txt:
        ev_status = evidence_json.get("formal_status_code", "")
        if "candidate_ready_awaiting_manual_review" in return_to_chatgpt_txt:
            if ev_status and "BLOCKED" in ev_status:
                codes.append("CONSISTENCY_RTCG_STATUS_MISMATCH")
        if "BLOCKED" in return_to_chatgpt_txt and "candidate_ready" in ev_status:
            codes.append("CONSISTENCY_RTCG_STATUS_MISMATCH")

    # Check report status semantics
    if report_json:
        rs = report_json.get("status", "")
        r038e_comp = report_json.get("R038e_completed", False)
        r038_comp = report_json.get("R038_completed", False)
        if rs == "completed" and (r038e_comp or r038_comp):
            codes.append("CONSISTENCY_REPORT_STATUS_SEMANTICS_CONFUSED")
        if (r038e_comp or r038_comp) and rs != "completed":
            pass  # semantic may still be valid
        if rs == "completed" and not r038e_comp and not r038_comp:
            pass  # semantically "report metadata complete", not round complete

    # Check test count vs metrics consistency
    if machine_readable:
        mr_tests = machine_readable.get("test_count", 0)
        if evidence_json:
            ev_tests = evidence_json.get("R038e_test_count") or evidence_json.get("test_count")
            if mr_tests and ev_tests and mr_tests != ev_tests:
                codes.append("CONSISTENCY_METRICS_COUNT_MISMATCH")

    # Check consistency of required metric count
    if machine_readable:
        mr_metric_count = len(machine_readable.get("included_metric_names", []))
        required_count = len(REQUIRED_METRIC_NAMES)
        if mr_metric_count > 0 and mr_metric_count < required_count:
            codes.append("CONSISTENCY_ARTIFACT_PRESENT_BUT_METRICS_MISSING")

    # Check consistency of validator result
    if machine_readable and "validation_result" not in machine_readable:
        codes.append("CONSISTENCY_ARTIFACT_PRESENT_BUT_VALIDATOR_RESULT_MISSING")

    return codes


def validate_upstream_refs(
    r038a_commit: str | None,
    r038b_commit: str | None,
    r038c_commit: str | None,
    r038d_commit: str | None,
    known_good_commits: dict[str, str],
) -> list[str]:
    """
    Validate upstream R038a-d references are present and non-stale.
    Returns list of reason codes (empty = pass).
    """
    codes: list[str] = []

    refs = {
        "R038A": r038a_commit,
        "R038B": r038b_commit,
        "R038C": r038c_commit,
        "R038D": r038d_commit,
    }

    for ref_key, commit in refs.items():
        if not commit:
            codes.append(f"UPSTREAM_REF_{ref_key}_MISSING")
        else:
            # Normalize known_good_commits keys to uppercase for comparison
            normalized_known = {k.upper(): v for k, v in known_good_commits.items()}
            known = normalized_known.get(ref_key.upper())
            if known and commit != known:
                codes.append("UPSTREAM_REF_STALE")

    return codes


def build_validation_artifact(
    metrics: dict[str, Any],
    source_commit: str,
    source_branch: str,
    internal_subtask: str = "R038e",
    validation_stage: str = "r038e_metrics_and_ci_artifacts",
    test_results: dict[str, Any] | None = None,
    r038a_ref: str | None = None,
    r038b_ref: str | None = None,
    r038c_ref: str | None = None,
    r038d_ref: str | None = None,
    generated_at: str | None = None,
) -> ValidationReportArtifact:
    """
    Build a validation artifact from metrics and metadata.
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat()

    included = list(metrics.keys())
    missing = list(REQUIRED_METRIC_NAMES - set(included))
    test_total = test_results.get("total", 0) if test_results else 0
    test_passed = test_results.get("passed", 0) if test_results else 0

    artifact: ValidationReportArtifact = {
        "artifact_id": f"r038e-{source_commit[:12]}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "artifact_type": ValidationArtifactType.CI_EVIDENCE_ARTIFACT.value,
        "generated_at": generated_at,
        "source_commit": source_commit,
        "source_branch": source_branch,
        "internal_subtask": internal_subtask,
        "validation_stage": validation_stage,
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "metrics_contract_version": METRICS_CONTRACT_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "test_suite_results": {
            "total": test_total,
            "passed": test_passed,
            "failed": test_total - test_passed,
        } if test_results else {},
        "required_metric_names": sorted(list(REQUIRED_METRIC_NAMES)),
        "included_metric_names": sorted(included),
        "missing_metric_names": sorted(missing),
        "report_status": "candidate_ready_awaiting_manual_review" if test_passed >= test_total and test_total > 0 else "in_construction",
        "formal_status_code": "candidate_ready_awaiting_manual_review" if test_passed >= test_total and test_total > 0 else "candidate_in_construction",
        "evidence_hash_policy": "diagnostic_obsolete_by_design_indirect_self_reference_prohibited",
        "self_reference_policy": "exclude_self_referential_fields_from_formal_pass",
        "reproducibility_command": f"git diff --binary {source_commit}~1..{source_commit} -- .",
        "no_broker_live_runtime_flags": True,
        "order_execution_allowed": False,
        "r038a_ref_commit": r038a_ref,
        "r038b_ref_commit": r038b_ref,
        "r038c_ref_commit": r038c_ref,
        "r038d_ref_commit": r038d_ref,
    }
    return artifact


# =============================================================================
# LLM / API Boundary
# =============================================================================


def llm_generated_summary(summary: str, metrics: dict[str, Any]) -> None:
    """
    LLM can generate human-readable summary from metrics.
    LLM must NOT modify metric values, override validation, or mark CI pass.
    This function validates the boundary.
    """
    if "net_of_cost_pnl" in summary and metrics.get("net_of_cost_pnl") is None:
        raise ValueError("LLM_CANNED_MODIFY_METRICS: LLM summary references metric not in validated bundle")

    for key in ["skip_validation", "force_pass", "override_result"]:
        if key.lower() in summary.lower():
            raise ValueError(f"LLM_PROHIBITED_ACTION: LLM cannot use '{key}' to modify validation")


def deterministic_validation_required() -> bool:
    """
    Local deterministic validation is always required.
    API failures must not result in default-pass.
    """
    return True


# =============================================================================
# CICDVerificationChain Integration
# =============================================================================

STAGE_R038E = "r038e_metrics_and_ci_artifacts"

# Filter R038e-specific reason codes
FAIL_CLOSED_REASON_CODES_R038E = {k: v for k, v in REASON_CODES.items() if any(
    k.startswith(p) for p in [
        "METRICS_", "ARTIFACT_", "CONSISTENCY_", "UPSTREAM_REF_",
        "TRADINGVIEW_", "LLM_", "REPRODUCIBILITY_",
    ]
)}

R038E_METRICS_AND_CI_ARTIFACTS_STAGE_RESULT_KEY = "metrics_bundle"
R038E_VALIDATION_STAGE_RESULT_KEY = "validation_bundle"
R038E_ARTIFACT_KEY = "artifact"
R038E_CONSISTENCY_KEY = "consistency"


class R038eMetricsCIArtifactsInput(TypedDict):
    metrics: dict[str, Any]
    source_commit: str
    source_branch: str
    generated_at: str
    test_results: dict[str, Any]
    evidence_json: dict[str, Any] | None
    report_json: dict[str, Any] | None
    return_to_chatgpt_txt: str | None
    r038a_ref: str | None
    r038b_ref: str | None
    r038c_ref: str | None
    r038d_ref: str | None


class R038eMetricsCIArtifactsResult(TypedDict):
    stage: str
    pass_: bool
    reason_codes: list[str]
    failed_metric_names: list[str]
    artifact: ValidationReportArtifact | None
    upstream_ref_failures: list[str]
    consistency_failures: list[str]
    validation_result: MetricsArtifactValidationResult | None


def validate_metrics_ci_artifacts(input_data: R038eMetricsCIArtifactsInput) -> R038eMetricsCIArtifactsResult:
    """
    Validate metrics bundle, CI artifact, report consistency, and upstream refs.
    """
    codes: list[str] = []

    metrics_result = validate_metrics_bundle(
        input_data["metrics"],
        input_data["source_commit"],
        input_data["source_branch"],
        input_data["generated_at"],
    )
    codes.extend(metrics_result["reason_codes"])

    artifact = build_validation_artifact(
        metrics=input_data["metrics"],
        source_commit=input_data["source_commit"],
        source_branch=input_data["source_branch"],
        test_results=input_data["test_results"],
        r038a_ref=input_data["r038a_ref"],
        r038b_ref=input_data["r038b_ref"],
        r038c_ref=input_data["r038c_ref"],
        r038d_ref=input_data["r038d_ref"],
        generated_at=input_data["generated_at"],
    )
    artifact_codes = validate_ci_artifact(artifact, input_data["source_commit"], input_data["source_branch"], "R038e")
    codes.extend(artifact_codes)

    report_json = input_data.get("report_json")
    machine_readable = report_json.get("machine_readable") if report_json else None

    consistency_codes = validate_report_output_consistency(
        machine_readable,
        input_data.get("evidence_json"),
        report_json,
        None,
        input_data.get("return_to_chatgpt_txt"),
        None,
    )
    codes.extend(consistency_codes)

    upstream_codes = validate_upstream_refs(
        input_data["r038a_ref"],
        input_data["r038b_ref"],
        input_data["r038c_ref"],
        input_data["r038d_ref"],
        {},
    )
    codes.extend(upstream_codes)

    passed = len(codes) == 0
    return R038eMetricsCIArtifactsResult(
        stage=STAGE_R038E,
        pass_=passed,
        reason_codes=codes,
        failed_metric_names=metrics_result["failed_metric_names"],
        artifact=artifact,
        upstream_ref_failures=[c for c in codes if c.startswith("UPSTREAM_REF_")],
        consistency_failures=[c for c in codes if c.startswith("CONSISTENCY_")],
        validation_result=metrics_result,
    )


def run_r038e_metrics_ci_artifacts(
    metrics: dict[str, Any],
    source_commit: str,
    source_branch: str,
    test_results: dict[str, Any],
    r038a_ref: str | None = None,
    r038b_ref: str | None = None,
    r038c_ref: str | None = None,
    r038d_ref: str | None = None,
    generated_at: str | None = None,
) -> R038eMetricsCIArtifactsResult:
    """
    Run R038e metrics and CI artifacts stage.
    Compatible with CICDVerificationChain stage registry.
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat()

    input_data: R038eMetricsCIArtifactsInput = {
        "metrics": metrics,
        "source_commit": source_commit,
        "source_branch": source_branch,
        "generated_at": generated_at,
        "test_results": test_results,
        "evidence_json": None,
        "report_json": None,
        "return_to_chatgpt_txt": None,
        "r038a_ref": r038a_ref,
        "r038b_ref": r038b_ref,
        "r038c_ref": r038c_ref,
        "r038d_ref": r038d_ref,
    }
    return validate_metrics_ci_artifacts(input_data)