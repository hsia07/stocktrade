from __future__ import annotations
import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


STAGE_R038C = "R038c_l5_l9_validation_chain"


class L5L9ValidationLevel(str, Enum):
    L5 = "L5"
    L6 = "L6"
    L7 = "L7"
    L8 = "L8"
    L9 = "L9"


class L5L9ValidationStatus(str, Enum):
    PASS = "pass"
    FAIL_CLOSED = "fail_closed"
    LEVEL_FAILED = "level_failed"
    BLOCKED_TRADINGVIEW_ONLY = "blocked_tradingview_only"
    BLOCKED_ORDER_EXECUTION_ALLOWED = "blocked_order_execution_allowed"

    @classmethod
    def _missing_(cls, value: object) -> L5L9ValidationStatus | None:
        return None


FAIL_CLOSED_REASON_CODES_R038C: dict[str, str] = {
    # L5 Walk-Forward OOS
    "L5_OOS_WINDOWS_MISSING": "L5 walk-forward has no out_of_sample_windows",
    "L5_FINAL_OOS_PERIOD_MISSING": "L5 walk-forward missing final_out_of_sample_period",
    "L5_OOS_WINDOW_COUNT_BELOW_THRESHOLD": "L5 OOS window count below minimum threshold",
    "L5_TRAIN_TEST_OVERLAP": "L5 walk-forward has training_overlap_with_oos, must be FALSE",
    "L5_FUTURE_LEAK": "L5 walk-forward has future_leak flag, no_future_leak must be TRUE",
    "L5_AS_OF_REPLAY_NOT_COMPATIBLE": "L5 walk-forward missing as_of_replay_compatible",
    "L5_OOS_RESULT_GROSS_ONLY": "L5 walk-forward OOS result is gross-only, net_of_cost_oos_result required",
    "L5_COST_MODEL_MISSING": "L5 walk-forward missing cost_model_version",
    "L5_SLIPPAGE_MODEL_MISSING": "L5 walk-forward missing slippage_model_version",
    "L5_MARKET_REALITY_NOT_COMPATIBLE": "L5 walk-forward not market_reality_compatible",
    "L5_RISK_GATE_REPLAY_NOT_COMPATIBLE": "L5 walk-forward not risk_gate_replay_compatible",
    "L5_OOS_NEGATIVE_AFTER_COST": "L5 walk-forward OOS result is negative after cost",
    "L5_TRADINGVIEW_ONLY": "L5 evidence is TradingView/Pine/DeepTest only, formal Python backtest required",
    # L6 Regime Segmentation
    "L6_SINGLE_REGIME_ONLY": "L6 regime segmentation has only one regime, at least 2 required",
    "L6_REGIME_LABELS_MISSING": "L6 regime segmentation missing regime labels",
    "L6_INSUFFICIENT_SAMPLES_PER_REGIME": "L6 regime segmentation has insufficient samples per regime",
    "L6_PER_REGIME_RESULT_GROSS_ONLY": "L6 per-regime result is gross-only, net_of_cost required per regime",
    "L6_AGGREGATE_ONLY_HIDES_FAILED": "L6 aggregate-only result may hide failed regime - individual per-regime results required",
    "L6_HINDSIGHT_REGIME_FOR_LIVE": "L6 hindsight/smoothed regime used for live decision, must be FALSE for live",
    "L6_ONLINE_FILTER_POSTERIOR_MISSING": "L6 missing online filter or posterior policy for regime active decision",
    "L6_UNCERTAINTY_THRESHOLD_MISSING": "L6 missing uncertainty threshold or entropy gate for regime classification",
    "L6_REGIME_MARKET_REALITY_NOT_COMPATIBLE": "L6 regime segmentation not market reality compatible per regime",
    # L7 Combinatorial Purged CV
    "L7_ORDINARY_RANDOM_KFOLD_ONLY": "L7 uses ordinary random K-fold only, combinatorial purged CV required",
    "L7_PURGE_WINDOW_MISSING": "L7 combinatorial purged CV missing purge_window",
    "L7_EMBARGO_WINDOW_MISSING": "L7 combinatorial purged CV missing embargo_window",
    "L7_FOLD_COUNT_BELOW_THRESHOLD": "L7 combinatorial purged CV fold count below minimum threshold",
    "L7_COMBO_SPLIT_COUNT_BELOW_THRESHOLD": "L7 combinatorial split count below minimum threshold",
    "L7_TIME_SERIES_ORDER_NOT_PRESERVED": "L7 combinatorial purged CV time_series_order_preserved must be TRUE",
    "L7_LABEL_OVERLAP_LEAKAGE": "L7 combinatorial purged CV overlapping_label_protection must be TRUE",
    "L7_LEAKAGE_GAP_NOT_DECLARED": "L7 combinatorial purged CV leakage_gap_declared must be TRUE",
    "L7_PER_FOLD_RESULT_GROSS_ONLY": "L7 per-fold result is gross-only, net_of_cost required per fold",
    "L7_COST_SLIPPAGE_OMITTED_FROM_FOLDS": "L7 cost/slippage omitted from folds, net_of_cost required per fold",
    # L8 PSR / Reality Check / SPA
    "L8_RAW_SHARPE_ONLY": "L8 raw Sharpe ratio only, PSR/Reality Check/SPA evidence required",
    "L8_PSR_MISSING": "L8 missing Probabilistic Sharpe Ratio or equivalent statistical test",
    "L8_REALITY_CHECK_MISSING": "L8 missing Reality Check / SPA test result",
    "L8_BENCHMARK_BASELINE_MISSING": "L8 missing benchmark or strategy family baseline for SPA",
    "L8_ADJUSTED_P_VALUE_MISSING": "L8 missing multiple-testing adjusted p_value",
    "L8_ADJUSTED_P_ABOVE_THRESHOLD": "L8 adjusted p_value above required threshold",
    "L8_BOOTSTRAP_METHOD_MISSING": "L8 missing bootstrap or resampling method",
    "L8_INSUFFICIENT_TRADE_COUNT": "L8 insufficient trade count for statistical test",
    "L8_TAIL_RISK_IGNORED": "L8 ignores skew/kurtosis/tail risk, non_normality_adjustment required",
    "L8_GROSS_METRIC_USED": "L8 gross metric used instead of net_of_cost metric",
    # L9 Paper Trading Readiness
    "L9_PAPER_DURATION_BELOW_MINIMUM": "L9 paper trading duration below minimum required months",
    "L9_INSUFFICIENT_TRADING_DAYS": "L9 insufficient paper trading days",
    "L9_INSUFFICIENT_PAPER_TRADES": "L9 insufficient paper trade count",
    "L9_PAPER_NET_OF_COST_MISSING": "L9 missing net_of_cost paper PnL result",
    "L9_SLIPPAGE_DRIFT_OVER_THRESHOLD": "L9 slippage drift (expected vs actual) exceeds threshold",
    "L9_FILL_RATE_DRIFT_OVER_THRESHOLD": "L9 fill-rate drift (expected vs actual) exceeds threshold",
    "L9_PAPER_LIVE_DRIFT_POLICY_MISSING": "L9 missing paper_live drift policy",
    "L9_STRATEGY_TTL_EXPIRY_MISSING": "L9 missing strategy TTL or promotion expiry",
    "L9_REVALIDATION_BEFORE_LIVE_MISSING": "L9 missing revalidation_before_live requirement",
    "L9_HUMAN_APPROVAL_MISSING": "L9 missing human_approval_required_for_live",
    "L9_LIVE_ORDER_PATH_PRESENT": "L9 has broker/live/order/runtime path, no_live_order_path must be TRUE",
    "L9_ORDER_EXECUTION_ALLOWED_TRUE": "L9 order_execution_allowed must be FALSE for validation",
    # General
    "GENERAL_MISSING_REPLAY_COMPATIBILITY": "L5-L9 validation input missing replay compatibility flag",
    "GENERAL_MISSING_RISK_GATE_REPLAY_COMPATIBILITY": "L5-L9 validation input missing risk gate replay compatibility flag",
    "GENERAL_ORDER_EXECUTION_ALLOWED_NOT_FALSE": "order_execution_allowed must be FALSE in validation context",
    "GENERAL_TRADINGVIEW_ONLY": "evidence is TradingView/Pine/DeepTest only, formal Python backtest required",
}

MIN_OOS_WINDOW_COUNT = 2
MIN_REGIME_COUNT = 2
MIN_SAMPLES_PER_REGIME = 20
MIN_FOLD_COUNT = 3
MIN_COMBO_SPLIT_COUNT = 2
MIN_PAPER_MONTHS = 6
MAX_PAPER_MONTHS = 12
MIN_PAPER_TRADING_DAYS = 60
MIN_PAPER_TRADE_COUNT = 30
DEFAULT_PAPER_DURATION_MONTHS = 6
DEFAULT_ADJUSTED_P_THRESHOLD = 0.05
DEFAULT_SLIPPAGE_DRIFT_THRESHOLD = 0.20
DEFAULT_FILL_RATE_DRIFT_THRESHOLD = 0.15
DEFAULT_EVIDENCE_SOURCE_PYTHON = "python_backtest"


@dataclass
class L5WalkForwardOOSEvidence:
    final_out_of_sample_period: str = ""
    oos_window_count: int = 0
    walk_forward_oos_splits: list[dict[str, Any]] = field(default_factory=list)
    no_training_overlap_with_oos: bool = False
    no_future_leak: bool = False
    as_of_replay_compatible: bool = False
    net_of_cost_oos_result: float | None = None
    gross_oos_result: float | None = None
    cost_model_version: str = ""
    slippage_model_version: str = ""
    market_reality_compatible: bool = False
    risk_gate_replay_compatible: bool = False
    evidence_source: str = DEFAULT_EVIDENCE_SOURCE_PYTHON

    @property
    def is_tradingview_only(self) -> bool:
        return self.evidence_source in ("tradingview", "pine", "deeptest")


@dataclass
class L6RegimeSegmentEvidence:
    regime_count: int = 0
    regime_labels: list[str] = field(default_factory=list)
    per_regime_sample_count: dict[str, int] = field(default_factory=dict)
    per_regime_net_of_cost_result: dict[str, float] = field(default_factory=dict)
    per_regime_gross_result: dict[str, float] = field(default_factory=dict)
    aggregate_net_of_cost_result: float | None = None
    regime_definition_version: str = ""
    offline_labeler_vs_online_filter_declared: bool = False
    hindsight_regime_smoothed_for_live: bool = False
    no_hindsight_regime_for_live: bool = False
    regime_uncertainty_policy_present: bool = False
    uncertainty_threshold_or_entropy_gate: str = ""
    market_reality_compatible_per_regime: bool = False
    evidence_source: str = DEFAULT_EVIDENCE_SOURCE_PYTHON

    @property
    def is_tradingview_only(self) -> bool:
        return self.evidence_source in ("tradingview", "pine", "deeptest")


@dataclass
class L7CombinatorialPurgedCVEvidence:
    combinatorial_split_count: int = 0
    purge_window: int = 0
    embargo_window: int = 0
    fold_count: int = 0
    time_series_order_preserved: bool = False
    overlapping_label_protection: bool = False
    leakage_gap_declared: bool = False
    per_fold_net_of_cost_result: list[float] = field(default_factory=list)
    per_fold_gross_result: list[float] = field(default_factory=list)
    cost_model_version: str = ""
    slippage_model_version: str = ""
    evidence_source: str = DEFAULT_EVIDENCE_SOURCE_PYTHON

    @property
    def is_tradingview_only(self) -> bool:
        return self.evidence_source in ("tradingview", "pine", "deeptest")


@dataclass
class L8PSRRealityCheckSPAEvidence:
    probabilistic_sharpe_ratio: float | None = None
    raw_sharpe_ratio: float | None = None
    reality_check_p_value: float | None = None
    spa_p_value: float | None = None
    benchmark_or_strategy_family_baseline: str = ""
    multiple_testing_adjusted_p_value: float | None = None
    bootstrap_or_resampling_method: str = ""
    non_normality_or_tail_risk_adjustment: str = ""
    trade_count: int = 0
    net_of_cost_metric_used: bool = False
    raw_sharpe_not_sufficient: bool = False
    gross_metric_used: bool = False
    evidence_source: str = DEFAULT_EVIDENCE_SOURCE_PYTHON

    @property
    def is_tradingview_only(self) -> bool:
        return self.evidence_source in ("tradingview", "pine", "deeptest")


@dataclass
class L9PaperTradingReadinessEvidence:
    paper_duration_months: int = 0
    paper_trading_days: int = 0
    paper_trade_count: int = 0
    paper_net_of_cost_pnl: float | None = None
    paper_gross_pnl: float | None = None
    expected_vs_actual_slippage_drift: float | None = None
    expected_vs_actual_fill_rate_drift: float | None = None
    paper_live_drift_policy_present: bool = False
    strategy_ttl_or_promotion_expiry: str = ""
    revalidation_required_before_live: bool = False
    human_approval_required_for_live: bool = False
    no_live_order_path: bool = False
    order_execution_allowed: bool = False
    evidence_source: str = DEFAULT_EVIDENCE_SOURCE_PYTHON

    @property
    def is_tradingview_only(self) -> bool:
        return self.evidence_source in ("tradingview", "pine", "deeptest")


@dataclass
class L5L9ValidationInput:
    input_id: str = ""
    l5_evidence: L5WalkForwardOOSEvidence | None = None
    l6_evidence: L6RegimeSegmentEvidence | None = None
    l7_evidence: L7CombinatorialPurgedCVEvidence | None = None
    l8_evidence: L8PSRRealityCheckSPAEvidence | None = None
    l9_evidence: L9PaperTradingReadinessEvidence | None = None
    adjusted_p_threshold: float = DEFAULT_ADJUSTED_P_THRESHOLD
    paper_duration_months: int = DEFAULT_PAPER_DURATION_MONTHS
    slippage_drift_threshold: float = DEFAULT_SLIPPAGE_DRIFT_THRESHOLD
    fill_rate_drift_threshold: float = DEFAULT_FILL_RATE_DRIFT_THRESHOLD
    order_execution_allowed: bool = False
    market_reality_compatible_required: bool = True
    replay_compatible_required: bool = True
    risk_gate_replay_required: bool = True
    evidence_source_override: str = ""


@dataclass
class L5L9ValidationResult:
    input_id: str = ""
    stage: str = STAGE_R038C
    validation_passed: bool = False
    fail_closed: bool = False
    status: L5L9ValidationStatus = L5L9ValidationStatus.FAIL_CLOSED
    reason_codes: list[str] = field(default_factory=list)
    levels_checked: list[str] = field(default_factory=list)
    level_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    passed_levels: list[str] = field(default_factory=list)
    failed_levels: list[str] = field(default_factory=list)
    order_execution_allowed: bool = False
    net_of_cost_required: bool = True
    market_reality_required: bool = True
    replay_required: bool = True
    risk_gate_replay_required: bool = True
    tradingview_only_rejected: bool = True
    paper_live_human_approval_required: bool = True
    live_runtime_forbidden: bool = True
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_id": self.input_id,
            "stage": self.stage,
            "validation_passed": self.validation_passed,
            "fail_closed": self.fail_closed,
            "status": self.status.value if self.status else "unknown",
            "reason_codes": self.reason_codes,
            "levels_checked": self.levels_checked,
            "level_results": self.level_results,
            "passed_levels": self.passed_levels,
            "failed_levels": self.failed_levels,
            "order_execution_allowed": self.order_execution_allowed,
            "net_of_cost_required": self.net_of_cost_required,
            "market_reality_required": self.market_reality_required,
            "replay_required": self.replay_required,
            "risk_gate_replay_required": self.risk_gate_replay_required,
            "tradingview_only_rejected": self.tradingview_only_rejected,
            "paper_live_human_approval_required": self.paper_live_human_approval_required,
            "live_runtime_forbidden": self.live_runtime_forbidden,
            "timestamp": self.timestamp,
        }

    def compute_result_hash(self) -> str:
        d = self.to_dict()
        d.pop("input_id", None)
        d.pop("timestamp", None)
        raw = json.dumps(d, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def _check_evidence_source(evidence: Any) -> bool:
    if hasattr(evidence, "evidence_source"):
        return evidence.evidence_source in ("tradingview", "pine", "deeptest")
    return False


def validate_l5_walk_forward_oos(
    evidence: L5WalkForwardOOSEvidence | None,
    min_oos_windows: int = MIN_OOS_WINDOW_COUNT,
) -> list[str]:
    codes: list[str] = []
    if evidence is None:
        codes.append("L5_OOS_WINDOWS_MISSING")
        codes.append("L5_FINAL_OOS_PERIOD_MISSING")
        codes.append("L5_COST_MODEL_MISSING")
        codes.append("L5_SLIPPAGE_MODEL_MISSING")
        codes.append("L5_MARKET_REALITY_NOT_COMPATIBLE")
        codes.append("L5_RISK_GATE_REPLAY_NOT_COMPATIBLE")
        return codes
    if not evidence.final_out_of_sample_period:
        codes.append("L5_FINAL_OOS_PERIOD_MISSING")
    if evidence.oos_window_count <= 0:
        codes.append("L5_OOS_WINDOWS_MISSING")
    elif evidence.oos_window_count < min_oos_windows:
        codes.append("L5_OOS_WINDOW_COUNT_BELOW_THRESHOLD")
    if not evidence.no_training_overlap_with_oos:
        codes.append("L5_TRAIN_TEST_OVERLAP")
    if not evidence.no_future_leak:
        codes.append("L5_FUTURE_LEAK")
    if not evidence.as_of_replay_compatible:
        codes.append("L5_AS_OF_REPLAY_NOT_COMPATIBLE")
    if evidence.net_of_cost_oos_result is None:
        codes.append("L5_OOS_RESULT_GROSS_ONLY")
    elif evidence.net_of_cost_oos_result < 0:
        codes.append("L5_OOS_NEGATIVE_AFTER_COST")
    if not evidence.cost_model_version:
        codes.append("L5_COST_MODEL_MISSING")
    if not evidence.slippage_model_version:
        codes.append("L5_SLIPPAGE_MODEL_MISSING")
    if not evidence.market_reality_compatible:
        codes.append("L5_MARKET_REALITY_NOT_COMPATIBLE")
    if not evidence.risk_gate_replay_compatible:
        codes.append("L5_RISK_GATE_REPLAY_NOT_COMPATIBLE")
    if evidence.is_tradingview_only:
        codes.append("L5_TRADINGVIEW_ONLY")
    return codes


def validate_l6_regime_segmentation(
    evidence: L6RegimeSegmentEvidence | None,
    min_regimes: int = MIN_REGIME_COUNT,
    min_samples: int = MIN_SAMPLES_PER_REGIME,
) -> list[str]:
    codes: list[str] = []
    if evidence is None:
        codes.append("L6_SINGLE_REGIME_ONLY")
        codes.append("L6_REGIME_LABELS_MISSING")
        codes.append("L6_PER_REGIME_RESULT_GROSS_ONLY")
        codes.append("L6_HINDSIGHT_REGIME_FOR_LIVE")
        codes.append("L6_UNCERTAINTY_THRESHOLD_MISSING")
        codes.append("L6_REGIME_MARKET_REALITY_NOT_COMPATIBLE")
        return codes
    if evidence.regime_count < min_regimes:
        codes.append("L6_SINGLE_REGIME_ONLY")
    if not evidence.regime_labels:
        codes.append("L6_REGIME_LABELS_MISSING")
    if evidence.per_regime_sample_count:
        insufficient = any(
            cnt < min_samples for cnt in evidence.per_regime_sample_count.values()
        )
        if insufficient:
            codes.append("L6_INSUFFICIENT_SAMPLES_PER_REGIME")
    if not evidence.per_regime_net_of_cost_result:
        codes.append("L6_PER_REGIME_RESULT_GROSS_ONLY")
    if evidence.aggregate_net_of_cost_result is not None and not evidence.per_regime_net_of_cost_result:
        codes.append("L6_AGGREGATE_ONLY_HIDES_FAILED")
    if evidence.hindsight_regime_smoothed_for_live:
        codes.append("L6_HINDSIGHT_REGIME_FOR_LIVE")
    if not evidence.no_hindsight_regime_for_live:
        if not evidence.hindsight_regime_smoothed_for_live:
            pass
        codes.append("L6_HINDSIGHT_REGIME_FOR_LIVE")
    if not evidence.offline_labeler_vs_online_filter_declared:
        codes.append("L6_ONLINE_FILTER_POSTERIOR_MISSING")
    if not evidence.regime_uncertainty_policy_present:
        codes.append("L6_UNCERTAINTY_THRESHOLD_MISSING")
    if not evidence.market_reality_compatible_per_regime:
        codes.append("L6_REGIME_MARKET_REALITY_NOT_COMPATIBLE")
    return codes


def validate_l7_combinatorial_purged_cv(
    evidence: L7CombinatorialPurgedCVEvidence | None,
    min_folds: int = MIN_FOLD_COUNT,
    min_splits: int = MIN_COMBO_SPLIT_COUNT,
) -> list[str]:
    codes: list[str] = []
    if evidence is None:
        codes.append("L7_ORDINARY_RANDOM_KFOLD_ONLY")
        codes.append("L7_PURGE_WINDOW_MISSING")
        codes.append("L7_EMBARGO_WINDOW_MISSING")
        codes.append("L7_PER_FOLD_RESULT_GROSS_ONLY")
        return codes
    if evidence.fold_count <= 0 and evidence.combinatorial_split_count <= 0:
        codes.append("L7_ORDINARY_RANDOM_KFOLD_ONLY")
    if evidence.purge_window <= 0:
        codes.append("L7_PURGE_WINDOW_MISSING")
    if evidence.embargo_window <= 0:
        codes.append("L7_EMBARGO_WINDOW_MISSING")
    if evidence.fold_count < min_folds:
        codes.append("L7_FOLD_COUNT_BELOW_THRESHOLD")
    if evidence.combinatorial_split_count < min_splits:
        codes.append("L7_COMBO_SPLIT_COUNT_BELOW_THRESHOLD")
    if not evidence.time_series_order_preserved:
        codes.append("L7_TIME_SERIES_ORDER_NOT_PRESERVED")
    if not evidence.overlapping_label_protection:
        codes.append("L7_LABEL_OVERLAP_LEAKAGE")
    if not evidence.leakage_gap_declared:
        codes.append("L7_LEAKAGE_GAP_NOT_DECLARED")
    if not evidence.per_fold_net_of_cost_result:
        codes.append("L7_PER_FOLD_RESULT_GROSS_ONLY")
    if not evidence.cost_model_version and not evidence.slippage_model_version:
        if evidence.per_fold_gross_result and not evidence.per_fold_net_of_cost_result:
            codes.append("L7_COST_SLIPPAGE_OMITTED_FROM_FOLDS")
    return codes


def validate_l8_psr_reality_check_spa(
    evidence: L8PSRRealityCheckSPAEvidence | None,
    adjusted_p_threshold: float = DEFAULT_ADJUSTED_P_THRESHOLD,
) -> list[str]:
    codes: list[str] = []
    if evidence is None:
        codes.append("L8_RAW_SHARPE_ONLY")
        codes.append("L8_PSR_MISSING")
        codes.append("L8_REALITY_CHECK_MISSING")
        codes.append("L8_ADJUSTED_P_VALUE_MISSING")
        codes.append("L8_BOOTSTRAP_METHOD_MISSING")
        codes.append("L8_GROSS_METRIC_USED")
        return codes
    if evidence.raw_sharpe_ratio is not None and evidence.probabilistic_sharpe_ratio is None:
        if not evidence.reality_check_p_value and not evidence.spa_p_value:
            codes.append("L8_RAW_SHARPE_ONLY")
    if evidence.probabilistic_sharpe_ratio is None:
        if not evidence.reality_check_p_value and not evidence.spa_p_value:
            codes.append("L8_PSR_MISSING")
    if not evidence.reality_check_p_value and not evidence.spa_p_value:
        codes.append("L8_REALITY_CHECK_MISSING")
    if not evidence.benchmark_or_strategy_family_baseline:
        codes.append("L8_BENCHMARK_BASELINE_MISSING")
    if evidence.multiple_testing_adjusted_p_value is None:
        codes.append("L8_ADJUSTED_P_VALUE_MISSING")
    elif evidence.multiple_testing_adjusted_p_value > adjusted_p_threshold:
        codes.append("L8_ADJUSTED_P_ABOVE_THRESHOLD")
    if not evidence.bootstrap_or_resampling_method:
        codes.append("L8_BOOTSTRAP_METHOD_MISSING")
    if evidence.trade_count <= 0:
        codes.append("L8_INSUFFICIENT_TRADE_COUNT")
    elif evidence.trade_count < 30:
        codes.append("L8_INSUFFICIENT_TRADE_COUNT")
    if not evidence.non_normality_or_tail_risk_adjustment:
        codes.append("L8_TAIL_RISK_IGNORED")
    if not evidence.net_of_cost_metric_used:
        codes.append("L8_GROSS_METRIC_USED")
    if evidence.gross_metric_used:
        codes.append("L8_GROSS_METRIC_USED")
    return codes


def validate_l9_paper_trading_readiness(
    evidence: L9PaperTradingReadinessEvidence | None,
    min_paper_months: int = MIN_PAPER_MONTHS,
    min_trading_days: int = MIN_PAPER_TRADING_DAYS,
    min_trades: int = MIN_PAPER_TRADE_COUNT,
    slippage_threshold: float = DEFAULT_SLIPPAGE_DRIFT_THRESHOLD,
    fill_rate_threshold: float = DEFAULT_FILL_RATE_DRIFT_THRESHOLD,
) -> list[str]:
    codes: list[str] = []
    if evidence is None:
        codes.append("L9_PAPER_DURATION_BELOW_MINIMUM")
        codes.append("L9_INSUFFICIENT_TRADING_DAYS")
        codes.append("L9_INSUFFICIENT_PAPER_TRADES")
        codes.append("L9_PAPER_NET_OF_COST_MISSING")
        codes.append("L9_PAPER_LIVE_DRIFT_POLICY_MISSING")
        codes.append("L9_REVALIDATION_BEFORE_LIVE_MISSING")
        codes.append("L9_HUMAN_APPROVAL_MISSING")
        codes.append("L9_LIVE_ORDER_PATH_PRESENT")
        return codes
    if evidence.paper_duration_months < min_paper_months:
        codes.append("L9_PAPER_DURATION_BELOW_MINIMUM")
    if evidence.paper_trading_days < min_trading_days:
        codes.append("L9_INSUFFICIENT_TRADING_DAYS")
    if evidence.paper_trade_count < min_trades:
        codes.append("L9_INSUFFICIENT_PAPER_TRADES")
    if evidence.paper_net_of_cost_pnl is None:
        codes.append("L9_PAPER_NET_OF_COST_MISSING")
    if evidence.expected_vs_actual_slippage_drift is not None:
        if evidence.expected_vs_actual_slippage_drift > slippage_threshold:
            codes.append("L9_SLIPPAGE_DRIFT_OVER_THRESHOLD")
    if evidence.expected_vs_actual_fill_rate_drift is not None:
        if evidence.expected_vs_actual_fill_rate_drift > fill_rate_threshold:
            codes.append("L9_FILL_RATE_DRIFT_OVER_THRESHOLD")
    if not evidence.paper_live_drift_policy_present:
        codes.append("L9_PAPER_LIVE_DRIFT_POLICY_MISSING")
    if not evidence.strategy_ttl_or_promotion_expiry:
        codes.append("L9_STRATEGY_TTL_EXPIRY_MISSING")
    if not evidence.revalidation_required_before_live:
        codes.append("L9_REVALIDATION_BEFORE_LIVE_MISSING")
    if not evidence.human_approval_required_for_live:
        codes.append("L9_HUMAN_APPROVAL_MISSING")
    if not evidence.no_live_order_path:
        codes.append("L9_LIVE_ORDER_PATH_PRESENT")
    if evidence.order_execution_allowed:
        codes.append("L9_ORDER_EXECUTION_ALLOWED_TRUE")
    return codes


def validate_l5_l9_general_compatibility(
    any_evidence: Any,
    order_execution_allowed: bool,
) -> list[str]:
    codes: list[str] = []
    if any_evidence is None:
        codes.append("GENERAL_MISSING_REPLAY_COMPATIBILITY")
        codes.append("GENERAL_MISSING_RISK_GATE_REPLAY_COMPATIBILITY")
    else:
        if hasattr(any_evidence, "as_of_replay_compatible"):
            if not any_evidence.as_of_replay_compatible:
                codes.append("GENERAL_MISSING_REPLAY_COMPATIBILITY")
        if hasattr(any_evidence, "risk_gate_replay_compatible"):
            if not any_evidence.risk_gate_replay_compatible:
                codes.append("GENERAL_MISSING_RISK_GATE_REPLAY_COMPATIBILITY")
    if _check_evidence_source(any_evidence):
        codes.append("GENERAL_TRADINGVIEW_ONLY")
    if order_execution_allowed is not False:
        codes.append("GENERAL_ORDER_EXECUTION_ALLOWED_NOT_FALSE")
    return codes


def validate_l5_l9_chain(input_data: L5L9ValidationInput) -> L5L9ValidationResult:
    input_id = input_data.input_id or uuid.uuid4().hex[:16]
    result = L5L9ValidationResult(
        input_id=input_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    all_reason_codes: list[str] = []
    level_results: dict[str, dict[str, Any]] = {}
    passed_levels: list[str] = []
    failed_levels: list[str] = []
    levels_checked: list[str] = []

    first_evidence = input_data.l5_evidence or input_data.l6_evidence or input_data.l7_evidence or input_data.l8_evidence or input_data.l9_evidence
    general_codes = validate_l5_l9_general_compatibility(
        first_evidence, input_data.order_execution_allowed,
    )
    all_reason_codes.extend(general_codes)

    # L5 Walk-Forward OOS
    l5_codes = validate_l5_walk_forward_oos(input_data.l5_evidence)
    all_reason_codes.extend(l5_codes)
    levels_checked.append("L5")
    l5_pass = len(l5_codes) == 0
    level_results["L5"] = {
        "pass": l5_pass,
        "reason_codes": l5_codes,
    }
    if l5_pass:
        passed_levels.append("L5")
    else:
        failed_levels.append("L5")

    # L6 Regime Segmentation
    l6_codes = validate_l6_regime_segmentation(input_data.l6_evidence)
    all_reason_codes.extend(l6_codes)
    levels_checked.append("L6")
    l6_pass = len(l6_codes) == 0
    level_results["L6"] = {
        "pass": l6_pass,
        "reason_codes": l6_codes,
    }
    if l6_pass:
        passed_levels.append("L6")
    else:
        failed_levels.append("L6")

    # L7 Combinatorial Purged CV
    l7_codes = validate_l7_combinatorial_purged_cv(input_data.l7_evidence)
    all_reason_codes.extend(l7_codes)
    levels_checked.append("L7")
    l7_pass = len(l7_codes) == 0
    level_results["L7"] = {
        "pass": l7_pass,
        "reason_codes": l7_codes,
    }
    if l7_pass:
        passed_levels.append("L7")
    else:
        failed_levels.append("L7")

    # L8 PSR / Reality Check / SPA
    l8_codes = validate_l8_psr_reality_check_spa(input_data.l8_evidence, input_data.adjusted_p_threshold)
    all_reason_codes.extend(l8_codes)
    levels_checked.append("L8")
    l8_pass = len(l8_codes) == 0
    level_results["L8"] = {
        "pass": l8_pass,
        "reason_codes": l8_codes,
    }
    if l8_pass:
        passed_levels.append("L8")
    else:
        failed_levels.append("L8")

    # L9 Paper Trading Readiness
    l9_codes = validate_l9_paper_trading_readiness(
        input_data.l9_evidence,
        slippage_threshold=input_data.slippage_drift_threshold,
        fill_rate_threshold=input_data.fill_rate_drift_threshold,
    )
    all_reason_codes.extend(l9_codes)
    levels_checked.append("L9")
    l9_pass = len(l9_codes) == 0
    level_results["L9"] = {
        "pass": l9_pass,
        "reason_codes": l9_codes,
    }
    if l9_pass:
        passed_levels.append("L9")
    else:
        failed_levels.append("L9")

    has_fail_closed = bool(all_reason_codes)
    has_tradingview_only = any("TRADINGVIEW_ONLY" in c for c in all_reason_codes)
    has_order_execution = any("ORDER_EXECUTION_ALLOWED" in c for c in all_reason_codes)

    result.reason_codes = all_reason_codes
    result.levels_checked = levels_checked
    result.level_results = level_results
    result.passed_levels = passed_levels
    result.failed_levels = failed_levels
    result.validation_passed = not has_fail_closed
    result.fail_closed = has_fail_closed
    result.order_execution_allowed = False

    if has_order_execution:
        result.status = L5L9ValidationStatus.BLOCKED_ORDER_EXECUTION_ALLOWED
    elif has_tradingview_only:
        result.status = L5L9ValidationStatus.BLOCKED_TRADINGVIEW_ONLY
    elif has_fail_closed:
        result.status = L5L9ValidationStatus.FAIL_CLOSED
    else:
        result.status = L5L9ValidationStatus.PASS

    return result


def run_r038c_l5_l9_validation_chain(
    input_data: L5L9ValidationInput,
) -> dict[str, Any]:
    result = validate_l5_l9_chain(input_data)
    return result.to_dict()
