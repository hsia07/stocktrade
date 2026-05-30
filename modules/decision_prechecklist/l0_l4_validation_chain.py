from __future__ import annotations
import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


STAGE_R038B = "R038b_l0_l4_validation_chain"


class ValidationLevel(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


class L0L4ValidationStatus(str, Enum):
    PASS = "pass"
    FAIL_CLOSED = "fail_closed"
    LEVEL_FAILED = "level_failed"
    BLOCKED_TRADINGVIEW_ONLY = "blocked_tradingview_only"
    BLOCKED_ORDER_EXECUTION_ALLOWED = "blocked_order_execution_allowed"

    @classmethod
    def _missing_(cls, value: object) -> L0L4ValidationStatus | None:
        return None


FAIL_CLOSED_REASON_CODES_R038B: dict[str, str] = {
    # L0 Backtest
    "L0_GROSS_ONLY_RESULT": "L0 backtest result is gross PnL only, net_of_cost_pnl required",
    "L0_COST_MODEL_MISSING": "L0 backtest cost_model_version is required",
    "L0_SLIPPAGE_MODEL_MISSING": "L0 backtest slippage_model_version is required",
    "L0_ORDER_FILL_PNL_SCHEMA_INCOMPATIBLE": "L0 backtest order_fill_pnl_schema_compatible must be True for formal pass",
    "L0_TRADE_COUNT_MISSING": "L0 backtest trade_count is required",
    "L0_TRADE_COUNT_INSUFFICIENT": "L0 backtest trade_count is below minimum threshold",
    "L0_DRAWDOWN_MISSING": "L0 backtest max_drawdown or equivalent risk metric is required",
    "L0_MARKET_REALITY_NOT_COMPATIBLE": "L0 backtest is not market reality compatible",
    "L0_REPLAY_NOT_COMPATIBLE": "L0 backtest is not replay compatible",
    "L0_RISK_GATE_REPLAY_NOT_COMPATIBLE": "L0 backtest is not risk gate replay compatible",
    "L0_TRADINGVIEW_ONLY": "L0 evidence is TradingView/Pine/DeepTest only, formal Python backtest required",
    # L1 Walk-Forward
    "L1_WINDOWS_MISSING": "L1 walk-forward train_window_count or test_window_count is missing",
    "L1_OOS_WINDOWS_MISSING": "L1 walk-forward has no out_of_sample_windows",
    "L1_INSUFFICIENT_TRAIN_WINDOWS": "L1 walk-forward train windows below minimum threshold",
    "L1_INSUFFICIENT_TEST_WINDOWS": "L1 walk-forward test windows below minimum threshold",
    "L1_LOOKAHEAD_LEAK": "L1 walk-forward has lookahead/future leak flag set",
    "L1_WINDOW_RESULT_GROSS_ONLY": "L1 walk-forward window result is gross-only, net_of_cost required per window",
    "L1_WINDOW_COST_SLIPPAGE_MISSING": "L1 walk-forward window missing cost or slippage model version",
    # L2 Monte Carlo / permutation
    "L2_PERMUTATION_RESULT_MISSING": "L2 monte carlo or permutation result is missing",
    "L2_RUN_COUNT_BELOW_THRESHOLD": "L2 permutation/monte carlo run count below minimum threshold",
    "L2_MISSING_SEED": "L2 monte carlo missing random_seed, reproducibility not verifiable",
    "L2_P_VALUE_MISSING": "L2 monte carlo missing p_value or significance output",
    "L2_P_VALUE_ABOVE_THRESHOLD": "L2 monte carlo p_value is above required threshold",
    "L2_TAIL_RISK_MISSING": "L2 monte carlo missing tail risk metric or drawdown distribution",
    # L3 Block Bootstrap
    "L3_BOOTSTRAP_RESULT_MISSING": "L3 block bootstrap result is missing",
    "L3_BLOCK_SIZE_MISSING": "L3 block bootstrap missing block_size",
    "L3_BLOCK_SIZE_INVALID": "L3 block bootstrap block_size is invalid (zero or negative)",
    "L3_RUNS_BELOW_THRESHOLD": "L3 block bootstrap run count below minimum threshold",
    "L3_CONFIDENCE_INTERVAL_MISSING": "L3 block bootstrap missing confidence_interval or distribution interval",
    "L3_SERIAL_DEPENDENCE_IGNORED": "L3 block bootstrap ignores serial dependence (regime flag not set)",
    # L4 Multiple Testing Correction
    "L4_TRIAL_COUNT_MISSING": "L4 multiple testing correction missing trial_count",
    "L4_CORRECTED_P_VALUE_MISSING": "L4 multiple testing correction missing corrected_p_value",
    "L4_CORRECTED_P_ABOVE_THRESHOLD": "L4 corrected_p_value is above required threshold",
    "L4_TRIAL_COUNT_INCONSISTENT": "L4 trial_count is inconsistent with search ledger",
    "L4_SEARCH_LEDGER_MISSING": "L4 multiple testing correction missing search ledger or parameter trial count marker",
    "L4_RAW_P_USED_WITHOUT_CORRECTION": "L4 raw p-value used without multiple testing correction",
    "L4_FRAGILITY_ISOLATED_BEST": "L4 best parameter isolated with high fragility risk",
    # General
    "GENERAL_MISSING_REPLAY_COMPATIBILITY": "validation input missing replay compatibility flag",
    "GENERAL_MISSING_RISK_GATE_REPLAY_COMPATIBILITY": "validation input missing risk gate replay compatibility flag",
    "GENERAL_ORDER_EXECUTION_ALLOWED_NOT_FALSE": "order_execution_allowed must be FALSE in validation context",
}

MIN_TRADE_COUNT = 10
MIN_TRAIN_WINDOWS = 2
MIN_TEST_WINDOWS = 2
MIN_PERMUTATION_RUNS = 100
MIN_BOOTSTRAP_RUNS = 500
DEFAULT_P_VALUE_THRESHOLD = 0.05
DEFAULT_CORRECTED_P_THRESHOLD = 0.05


@dataclass
class L0BacktestEvidence:
    net_of_cost_pnl: float | None = None
    gross_pnl: float | None = None
    cost_model_version: str = ""
    slippage_model_version: str = ""
    trade_count: int = 0
    max_drawdown: float | None = None
    order_fill_pnl_schema_compatible: bool = False
    market_reality_compatible: bool = False
    replay_compatible: bool = False
    risk_gate_replay_compatible: bool = False
    evidence_source: str = "python_backtest"

    @property
    def is_tradingview_only(self) -> bool:
        return self.evidence_source in ("tradingview", "pine", "deeptest")

    def compute_deterministic_hash(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


@dataclass
class L1WalkForwardEvidence:
    train_window_count: int = 0
    test_window_count: int = 0
    out_of_sample_windows: int = 0
    walk_forward_splits: list[dict[str, Any]] = field(default_factory=list)
    no_lookahead_leak: bool = False
    window_level_net_of_cost: bool = False
    window_cost_model_version: str = ""
    window_slippage_model_version: str = ""


@dataclass
class L2MonteCarloPermutationEvidence:
    permutation_count: int = 0
    monte_carlo_runs: int = 0
    p_value: float | None = None
    random_seed: int | None = None
    tail_risk_metric: dict[str, Any] = field(default_factory=dict)


@dataclass
class L3BlockBootstrapEvidence:
    block_count: int = 0
    block_size: int = 0
    bootstrap_runs: int = 0
    confidence_interval: dict[str, float] = field(default_factory=dict)
    regime_serial_dependence_aware: bool = False


@dataclass
class L4MultipleTestingCorrectionEvidence:
    trial_count: int = 0
    family_count: int = 0
    raw_p_value: float | None = None
    corrected_p_value: float | None = None
    correction_method: str = ""
    search_ledger: list[dict[str, Any]] = field(default_factory=list)
    overfit_risk_flag: str = ""
    fragility_marker: str = ""


@dataclass
class L0L4ValidationInput:
    input_id: str = ""
    l0_evidence: L0BacktestEvidence | None = None
    l1_evidence: L1WalkForwardEvidence | None = None
    l2_evidence: L2MonteCarloPermutationEvidence | None = None
    l3_evidence: L3BlockBootstrapEvidence | None = None
    l4_evidence: L4MultipleTestingCorrectionEvidence | None = None
    p_value_threshold: float = DEFAULT_P_VALUE_THRESHOLD
    corrected_p_threshold: float = DEFAULT_CORRECTED_P_THRESHOLD
    order_execution_allowed: bool = False


@dataclass
class L0L4ValidationResult:
    input_id: str = ""
    stage: str = STAGE_R038B
    validation_passed: bool = False
    fail_closed: bool = False
    status: L0L4ValidationStatus = L0L4ValidationStatus.FAIL_CLOSED
    reason_codes: list[str] = field(default_factory=list)
    levels_checked: list[str] = field(default_factory=list)
    level_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    passed_levels: list[str] = field(default_factory=list)
    failed_levels: list[str] = field(default_factory=list)
    order_execution_allowed: bool = False
    net_of_cost_required: bool = True
    market_reality_required: bool = True
    replay_required: bool = True
    tradingview_only_rejected: bool = True
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
            "tradingview_only_rejected": self.tradingview_only_rejected,
            "timestamp": self.timestamp,
        }

    def compute_result_hash(self) -> str:
        d = self.to_dict()
        d.pop("input_id", None)
        d.pop("timestamp", None)
        raw = json.dumps(d, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def validate_l0_backtest(evidence: L0BacktestEvidence | None) -> list[str]:
    codes: list[str] = []
    if evidence is None:
        codes.append("L0_GROSS_ONLY_RESULT")
        return codes
    if evidence.net_of_cost_pnl is None:
        codes.append("L0_GROSS_ONLY_RESULT")
    if not evidence.cost_model_version:
        codes.append("L0_COST_MODEL_MISSING")
    if not evidence.slippage_model_version:
        codes.append("L0_SLIPPAGE_MODEL_MISSING")
    if evidence.trade_count <= 0:
        codes.append("L0_TRADE_COUNT_MISSING")
    elif evidence.trade_count < MIN_TRADE_COUNT:
        codes.append("L0_TRADE_COUNT_INSUFFICIENT")
    if evidence.max_drawdown is None:
        codes.append("L0_DRAWDOWN_MISSING")
    if not evidence.order_fill_pnl_schema_compatible:
        codes.append("L0_ORDER_FILL_PNL_SCHEMA_INCOMPATIBLE")
    if not evidence.market_reality_compatible:
        codes.append("L0_MARKET_REALITY_NOT_COMPATIBLE")
    if not evidence.replay_compatible:
        codes.append("L0_REPLAY_NOT_COMPATIBLE")
    if not evidence.risk_gate_replay_compatible:
        codes.append("L0_RISK_GATE_REPLAY_NOT_COMPATIBLE")
    if evidence.is_tradingview_only:
        codes.append("L0_TRADINGVIEW_ONLY")
    return codes


def validate_l1_walk_forward(evidence: L1WalkForwardEvidence | None) -> list[str]:
    codes: list[str] = []
    if evidence is None:
        codes.append("L1_WINDOWS_MISSING")
        return codes
    if evidence.train_window_count <= 0 or evidence.test_window_count <= 0:
        codes.append("L1_WINDOWS_MISSING")
    if evidence.out_of_sample_windows <= 0:
        codes.append("L1_OOS_WINDOWS_MISSING")
    if evidence.train_window_count < MIN_TRAIN_WINDOWS:
        codes.append("L1_INSUFFICIENT_TRAIN_WINDOWS")
    if evidence.test_window_count < MIN_TEST_WINDOWS:
        codes.append("L1_INSUFFICIENT_TEST_WINDOWS")
    if not evidence.no_lookahead_leak:
        codes.append("L1_LOOKAHEAD_LEAK")
    if not evidence.window_level_net_of_cost:
        codes.append("L1_WINDOW_RESULT_GROSS_ONLY")
    if not evidence.window_cost_model_version:
        codes.append("L1_WINDOW_COST_SLIPPAGE_MISSING")
    if not evidence.window_slippage_model_version:
        codes.append("L1_WINDOW_COST_SLIPPAGE_MISSING")
    return codes


def validate_l2_monte_carlo(evidence: L2MonteCarloPermutationEvidence | None,
                             p_threshold: float = DEFAULT_P_VALUE_THRESHOLD) -> list[str]:
    codes: list[str] = []
    if evidence is None:
        codes.append("L2_PERMUTATION_RESULT_MISSING")
        return codes
    runs = evidence.monte_carlo_runs or evidence.permutation_count
    if runs <= 0:
        codes.append("L2_PERMUTATION_RESULT_MISSING")
    elif runs < MIN_PERMUTATION_RUNS:
        codes.append("L2_RUN_COUNT_BELOW_THRESHOLD")
    if evidence.random_seed is None:
        codes.append("L2_MISSING_SEED")
    if evidence.p_value is None:
        codes.append("L2_P_VALUE_MISSING")
    elif evidence.p_value > p_threshold:
        codes.append("L2_P_VALUE_ABOVE_THRESHOLD")
    if not evidence.tail_risk_metric:
        codes.append("L2_TAIL_RISK_MISSING")
    return codes


def validate_l3_block_bootstrap(evidence: L3BlockBootstrapEvidence | None) -> list[str]:
    codes: list[str] = []
    if evidence is None:
        codes.append("L3_BOOTSTRAP_RESULT_MISSING")
        return codes
    if evidence.block_size <= 0 and evidence.block_count <= 0:
        codes.append("L3_BOOTSTRAP_RESULT_MISSING")
    if evidence.block_size == 0:
        codes.append("L3_BLOCK_SIZE_MISSING")
    elif evidence.block_size < 0:
        codes.append("L3_BLOCK_SIZE_INVALID")
    if evidence.bootstrap_runs < MIN_BOOTSTRAP_RUNS:
        codes.append("L3_RUNS_BELOW_THRESHOLD")
    if not evidence.confidence_interval:
        codes.append("L3_CONFIDENCE_INTERVAL_MISSING")
    if not evidence.regime_serial_dependence_aware:
        codes.append("L3_SERIAL_DEPENDENCE_IGNORED")
    return codes


def validate_l4_multiple_testing_correction(
    evidence: L4MultipleTestingCorrectionEvidence | None,
    corrected_threshold: float = DEFAULT_CORRECTED_P_THRESHOLD,
) -> list[str]:
    codes: list[str] = []
    if evidence is None:
        codes.append("L4_TRIAL_COUNT_MISSING")
        return codes
    if evidence.trial_count <= 0:
        codes.append("L4_TRIAL_COUNT_MISSING")
    if evidence.corrected_p_value is None:
        codes.append("L4_CORRECTED_P_VALUE_MISSING")
    elif evidence.corrected_p_value > corrected_threshold:
        codes.append("L4_CORRECTED_P_ABOVE_THRESHOLD")
    if evidence.trial_count > 0 and evidence.search_ledger:
        if len(evidence.search_ledger) != evidence.trial_count:
            codes.append("L4_TRIAL_COUNT_INCONSISTENT")
    if not evidence.search_ledger:
        codes.append("L4_SEARCH_LEDGER_MISSING")
    if evidence.raw_p_value is not None and evidence.corrected_p_value is None:
        codes.append("L4_RAW_P_USED_WITHOUT_CORRECTION")
    if evidence.fragility_marker or evidence.overfit_risk_flag:
        codes.append("L4_FRAGILITY_ISOLATED_BEST")
    return codes


def validate_general_compatibility(
    l0_evidence: L0BacktestEvidence | None,
    order_execution_allowed: bool,
) -> list[str]:
    codes: list[str] = []
    if l0_evidence is None:
        codes.append("GENERAL_MISSING_REPLAY_COMPATIBILITY")
        codes.append("GENERAL_MISSING_RISK_GATE_REPLAY_COMPATIBILITY")
    else:
        if not l0_evidence.replay_compatible:
            codes.append("GENERAL_MISSING_REPLAY_COMPATIBILITY")
        if not l0_evidence.risk_gate_replay_compatible:
            codes.append("GENERAL_MISSING_RISK_GATE_REPLAY_COMPATIBILITY")
    if order_execution_allowed is not False:
        codes.append("GENERAL_ORDER_EXECUTION_ALLOWED_NOT_FALSE")
    return codes


def validate_l0_l4_chain(input_data: L0L4ValidationInput) -> L0L4ValidationResult:
    input_id = input_data.input_id or uuid.uuid4().hex[:16]
    result = L0L4ValidationResult(
        input_id=input_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    all_reason_codes: list[str] = []
    level_results: dict[str, dict[str, Any]] = {}
    passed_levels: list[str] = []
    failed_levels: list[str] = []
    levels_checked: list[str] = []

    # General compatibility
    general_codes = validate_general_compatibility(
        input_data.l0_evidence, input_data.order_execution_allowed,
    )
    all_reason_codes.extend(general_codes)

    # L0 Backtest
    l0_codes = validate_l0_backtest(input_data.l0_evidence)
    all_reason_codes.extend(l0_codes)
    levels_checked.append("L0")
    l0_pass = len(l0_codes) == 0
    level_results["L0"] = {
        "pass": l0_pass,
        "reason_codes": l0_codes,
    }
    if l0_pass:
        passed_levels.append("L0")
    else:
        failed_levels.append("L0")

    # L1 Walk-Forward
    l1_codes = validate_l1_walk_forward(input_data.l1_evidence)
    all_reason_codes.extend(l1_codes)
    levels_checked.append("L1")
    l1_pass = len(l1_codes) == 0
    level_results["L1"] = {
        "pass": l1_pass,
        "reason_codes": l1_codes,
    }
    if l1_pass:
        passed_levels.append("L1")
    else:
        failed_levels.append("L1")

    # L2 Monte Carlo / permutation
    l2_codes = validate_l2_monte_carlo(input_data.l2_evidence, input_data.p_value_threshold)
    all_reason_codes.extend(l2_codes)
    levels_checked.append("L2")
    l2_pass = len(l2_codes) == 0
    level_results["L2"] = {
        "pass": l2_pass,
        "reason_codes": l2_codes,
    }
    if l2_pass:
        passed_levels.append("L2")
    else:
        failed_levels.append("L2")

    # L3 Block Bootstrap
    l3_codes = validate_l3_block_bootstrap(input_data.l3_evidence)
    all_reason_codes.extend(l3_codes)
    levels_checked.append("L3")
    l3_pass = len(l3_codes) == 0
    level_results["L3"] = {
        "pass": l3_pass,
        "reason_codes": l3_codes,
    }
    if l3_pass:
        passed_levels.append("L3")
    else:
        failed_levels.append("L3")

    # L4 Multiple Testing Correction
    l4_codes = validate_l4_multiple_testing_correction(input_data.l4_evidence, input_data.corrected_p_threshold)
    all_reason_codes.extend(l4_codes)
    levels_checked.append("L4")
    l4_pass = len(l4_codes) == 0
    level_results["L4"] = {
        "pass": l4_pass,
        "reason_codes": l4_codes,
    }
    if l4_pass:
        passed_levels.append("L4")
    else:
        failed_levels.append("L4")

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
        result.status = L0L4ValidationStatus.BLOCKED_ORDER_EXECUTION_ALLOWED
    elif has_tradingview_only:
        result.status = L0L4ValidationStatus.BLOCKED_TRADINGVIEW_ONLY
    elif has_fail_closed:
        result.status = L0L4ValidationStatus.FAIL_CLOSED
    else:
        result.status = L0L4ValidationStatus.PASS

    return result


def run_r038b_l0_l4_validation_chain(
    input_data: L0L4ValidationInput,
) -> dict[str, Any]:
    result = validate_l0_l4_chain(input_data)
    return result.to_dict()
