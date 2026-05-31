"""
R038f: Net Expected Advantage / deterministic NEA gate / calibrated payoff bucket /
score breakdown / deterministic NEA gate.
Internal subtask only. Not R038 completion. Not R038-R048 acceptance. Not R049.
order_execution_allowed must remain FALSE. No broker/live/runtime/order path.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, TypedDict


# =============================================================================
# Enums
# =============================================================================


class PayoffBucket(str, Enum):
    HIGH_CONVICTION_BUY = "high_conviction_buy"
    MODERATE_CONVICTION_BUY = "moderate_conviction_buy"
    LOW_CONVICTION_BUY = "low_conviction_buy"
    NEUTRAL = "neutral"
    LOW_CONVICTION_SELL = "low_conviction_sell"
    MODERATE_CONVICTION_SELL = "moderate_conviction_sell"
    HIGH_CONVICTION_SELL = "high_conviction_sell"
    BLOCKED = "blocked"


class FinalNEADecision(str, Enum):
    PASS = "pass"
    BLOCKED = "blocked"
    FAIL_CLOSED = "fail_closed"


# =============================================================================
# Constants / Thresholds
# =============================================================================

NEA_MIN_NET_EDGE = 0.0
NEA_MIN_EXPECTED_NET_RR = 1.0
NEA_MIN_FILL_PROBABILITY = 0.5
NEA_MAX_REGIME_UNCERTAINTY = 0.4

NEA_TAIWAN_SECURITIES_TAX_RATE = 0.003
NEA_TAIWAN_MINIMUM_FEE = 20.0
NEA_TAIWAN_PRICE_LIMIT_BAND = 0.10
NEA_TAIWAN_T_PLUS_2_SETTLEMENT = True

NEA_THRESHOLD_CONFIG_VERSION = "r038f_v1"
NEA_CALIBRATION_VERSION = "r038f_cal_v1"

NEA_CONTRACT_VERSION = "r038f_v1"

# =============================================================================
# Reason Codes
# =============================================================================

REASON_CODES: dict[str, str] = {
    # Fail-closed: missing inputs (source)
    "P_HAT_MISSING": "p_hat (calibrated win probability) is missing",
    "W_HAT_MISSING": "W_hat (expected win / upside) is missing",
    "L_HAT_MISSING": "L_hat (expected loss / downside) is missing",
    "COST_MISSING": "cost component C (fee/tax/min fee) is missing",
    "SLIPPAGE_MISSING": "slippage component S is missing",
    "BORROW_COST_MISSING": "borrow/margin/funding cost B is missing",
    "LATENCY_COST_MISSING": "latency/stale data cost T is missing",
    "TAIL_RISK_MISSING": "tail risk / CVaR penalty R is missing",
    "REGIME_UNCERTAINTY_MISSING": "regime uncertainty / event conflict penalty U is missing",
    "FILL_PROBABILITY_MISSING": "fill probability is missing",
    "MARKET_REALITY_SNAPSHOT_MISSING": "market reality snapshot is missing",
    "RISK_SNAPSHOT_MISSING": "risk snapshot is missing",
    "TAIWAN_CONSTRAINTS_MISSING": "Taiwan market constraints are missing",
    "CALIBRATION_VERSION_MISSING": "calibration version is missing",

    # Fail-closed: raw confidence violations
    "RAW_CONFIDENCE_USED_DIRECTLY": "raw confidence used directly instead of calibrated p_hat",
    "RAW_CONFIDENCE_POSITION_SIZING": "raw confidence used directly for position sizing",
    "RAW_CONFIDENCE_ADDED_DIRECTLY": "raw confidence values added directly without calibration",

    # Fail-closed: calibration
    "STALE_CALIBRATION": "calibration data is stale",
    "BRIER_SCORE_MISSING": "Brier score or equivalent calibration metric is missing",
    "CALIBRATION_METRIC_MISSING": "calibration metric is missing",

    # Fail-closed: threshold violations
    "NET_EDGE_NOT_POSITIVE": "net_edge <= 0",
    "EXPECTED_NET_RR_BELOW_THRESHOLD": "expected net risk-reward below threshold",
    "FILL_PROBABILITY_BELOW_THRESHOLD": "fill probability below threshold",
    "REGIME_UNCERTAINTY_EXCEEDS_THRESHOLD": "regime uncertainty exceeds threshold",

    # Fail-closed: Taiwan constraints
    "TAIWAN_PRICE_LIMIT_VIOLATION": "price outside ±10% daily limit",
    "TAIWAN_T_PLUS_2_VIOLATION": "T+2 settlement constraint violated",
    "TAIWAN_MIN_FEE_VIOLATION": "minimum fee not met",
    "TAIWAN_PRICE_MISSING": "Taiwan price is missing",
    "TAIWAN_REF_PRICE_MISSING": "Taiwan reference price is missing",

    # Fail-closed: gross-only edge
    "GROSS_ONLY_EDGE_PASS": "gross-only edge passed without net-of-cost check",
    "COST_NOT_DEDUCTED": "costs not deducted from edge",

    # Fail-closed: risk gate
    "RISK_FINAL_GATE_MISSING": "risk final gate not present",
    "RISK_FINAL_GATE_FAILED": "risk final gate failed",
    "MARKET_REALITY_CHECK_FAILED": "market reality check failed",
    "NO_MARKET_REALITY_PASS": "no market reality pass",

    # Fail-closed: veto
    "VETO_PRESENT": "veto present in vetoes list",

    # Fail-closed: LLM / API
    "LLM_MARKS_PASS": "LLM attempted to mark NEA pass",
    "LLM_MODIFIES_CALIBRATION": "LLM attempted to modify calibration",
    "API_DECIDES_FINAL_GATE": "API/LLM decides final gate instead of deterministic",

    # Fail-closed: broker/live/order/runtime pollution
    "BROKER_LIVE_ORDER_POLLUTION": "broker/live/order/runtime path contamination detected",
    "ORDER_EXECUTION_ALLOWED_TRUE": "order_execution_allowed is TRUE but must remain FALSE",

    # Fail-closed: veto list entries
    "BROKER_API_CALLED_VETO": "broker API called",
    "TRADING_RUNTIME_STARTED_VETO": "trading runtime started",
    "ORDER_EXECUTED_VETO": "order executed during this contract",
}

FAIL_CLOSED_REASON_CODES_R038F = {k: v for k, v in REASON_CODES.items() if any(
    k.startswith(p) for p in [
        "P_HAT_", "W_HAT_", "L_HAT_", "COST_", "SLIPPAGE_", "BORROW_", "LATENCY_",
        "TAIL_RISK_", "REGIME_UNCERTAINTY_", "FILL_PROBABILITY_", "MARKET_REALITY_",
        "RISK_", "TAIWAN_", "CALIBRATION_", "RAW_CONFIDENCE_", "STALE_", "BRIER_",
        "NET_EDGE_", "EXPECTED_NET_RR_", "FILL_", "REGIME_", "GROSS_", "LLM_",
        "API_", "BROKER_", "ORDER_", "VETO_", "NO_",
    ]
)}


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class ScoreBreakdown:
    p_hat: float
    W_hat: float
    L_hat: float
    C: float
    S: float
    B: float
    T: float
    R: float
    U: float
    net_edge: float
    expected_net_rr: float
    fill_probability: float
    regime_uncertainty: float
    market_reality_snapshot: dict[str, Any]
    risk_snapshot: dict[str, Any]
    threshold_config_version: str
    calibration_version: str
    vetoes: list[str]
    final_nea_decision: str
    reason_codes: list[str]
    taiwan_reality_contract: dict[str, Any] | None = None
    payoff_bucket: str = PayoffBucket.BLOCKED.value
    generated_at: str = ""


# =============================================================================
# Core Deterministic Formula
# =============================================================================


def compute_net_edge(
    p_hat: float,
    W_hat: float,
    L_hat: float,
    C: float,
    S: float,
    B: float,
    T: float,
    R: float,
    U: float,
) -> float:
    net_edge = p_hat * W_hat - (1.0 - p_hat) * L_hat - C - S - B - T - R - U
    return net_edge


def compute_expected_net_rr(net_edge: float, max_loss: float) -> float:
    if max_loss <= 0.0:
        return 0.0
    return net_edge / max_loss


# =============================================================================
# Input / Output TypedDicts
# =============================================================================


class NEAGateInput(TypedDict):
    p_hat: float
    W_hat: float
    L_hat: float
    C: float
    S: float
    B: float
    T: float
    R: float
    U: float
    fill_probability: float
    regime_uncertainty: float
    market_reality_snapshot: dict[str, Any]
    risk_snapshot: dict[str, Any]
    threshold_config_version: str
    calibration_version: str
    taiwan_reality_contract: dict[str, Any] | None
    order_execution_allowed: bool
    calibration_brier_score: float | None
    calibration_sample_count: int
    calibration_timestamp: str
    raw_confidence_not_used: bool
    vetoes: list[str]
    llm_summary_only: bool


class NEAGateOutput(TypedDict):
    passed: bool
    net_edge: float
    expected_net_rr: float
    payoff_bucket: str
    score_breakdown: dict[str, Any]
    vetoes: list[str]
    reason_codes: list[str]
    final_nea_decision: str
    stage: str


# =============================================================================
# Deterministic Validation Functions
# =============================================================================


def _check_missing_inputs(input_data: NEAGateInput) -> list[str]:
    codes: list[str] = []
    required_fields: list[tuple[str, Any, str]] = [
        ("p_hat", input_data.get("p_hat"), "P_HAT_MISSING"),
        ("W_hat", input_data.get("W_hat"), "W_HAT_MISSING"),
        ("L_hat", input_data.get("L_hat"), "L_HAT_MISSING"),
        ("C", input_data.get("C"), "COST_MISSING"),
        ("S", input_data.get("S"), "SLIPPAGE_MISSING"),
        ("B", input_data.get("B"), "BORROW_COST_MISSING"),
        ("T", input_data.get("T"), "LATENCY_COST_MISSING"),
        ("R", input_data.get("R"), "TAIL_RISK_MISSING"),
        ("U", input_data.get("U"), "REGIME_UNCERTAINTY_MISSING"),
        ("fill_probability", input_data.get("fill_probability"), "FILL_PROBABILITY_MISSING"),
    ]
    for name, val, code in required_fields:
        if val is None:
            codes.append(code)
    return codes


def _check_calibration(input_data: NEAGateInput) -> list[str]:
    codes: list[str] = []
    cal_version = input_data.get("calibration_version")
    if not cal_version:
        codes.append("CALIBRATION_VERSION_MISSING")
    brier = input_data.get("calibration_brier_score")
    if brier is None:
        codes.append("BRIER_SCORE_MISSING")
    raw_not_used = input_data.get("raw_confidence_not_used", False)
    if not raw_not_used:
        codes.append("RAW_CONFIDENCE_USED_DIRECTLY")
    return codes


def _check_raw_confidence_vetoes(input_data: NEAGateInput) -> list[str]:
    codes: list[str] = []
    if not input_data.get("raw_confidence_not_used", False):
        codes.append("RAW_CONFIDENCE_USED_DIRECTLY")
    return codes


def _check_thresholds(
    net_edge: float,
    expected_net_rr: float,
    fill_probability: float,
    regime_uncertainty: float,
) -> list[str]:
    codes: list[str] = []
    if net_edge <= NEA_MIN_NET_EDGE:
        codes.append("NET_EDGE_NOT_POSITIVE")
    if expected_net_rr < NEA_MIN_EXPECTED_NET_RR:
        codes.append("EXPECTED_NET_RR_BELOW_THRESHOLD")
    if fill_probability < NEA_MIN_FILL_PROBABILITY:
        codes.append("FILL_PROBABILITY_BELOW_THRESHOLD")
    if regime_uncertainty > NEA_MAX_REGIME_UNCERTAINTY:
        codes.append("REGIME_UNCERTAINTY_EXCEEDS_THRESHOLD")
    return codes


def _check_taiwan_constraints(
    taiwan_reality_contract: dict[str, Any] | None,
) -> list[str]:
    codes: list[str] = []
    if taiwan_reality_contract is None:
        return ["TAIWAN_CONSTRAINTS_MISSING"]
    price = taiwan_reality_contract.get("price")
    ref_price = taiwan_reality_contract.get("reference_price")
    if price is None:
        codes.append("TAIWAN_PRICE_MISSING")
    if ref_price is None:
        codes.append("TAIWAN_REF_PRICE_MISSING")
    if price is not None and ref_price is not None and ref_price > 0:
        change = abs(price - ref_price) / ref_price
        if change > NEA_TAIWAN_PRICE_LIMIT_BAND:
            codes.append("TAIWAN_PRICE_LIMIT_VIOLATION")
    # Taiwan min fee check
    fee = taiwan_reality_contract.get("fee", 0)
    if fee < NEA_TAIWAN_MINIMUM_FEE:
        codes.append("TAIWAN_MIN_FEE_VIOLATION")
    return codes


def _check_market_reality(input_data: NEAGateInput) -> list[str]:
    codes: list[str] = []
    snapshot = input_data.get("market_reality_snapshot")
    if not snapshot:
        return ["MARKET_REALITY_SNAPSHOT_MISSING"]
    return codes


def _check_risk_gate(input_data: NEAGateInput) -> list[str]:
    codes: list[str] = []
    snapshot = input_data.get("risk_snapshot")
    if not snapshot:
        return ["RISK_SNAPSHOT_MISSING", "RISK_FINAL_GATE_MISSING"]
    return codes


def _check_vetoes(vetoes: list[str]) -> list[str]:
    codes: list[str] = []
    brokerage_vetoes = [
        "BROKER_API_CALLED_VETO", "TRADING_RUNTIME_STARTED_VETO",
        "ORDER_EXECUTED_VETO", "BROKER_LIVE_ORDER_POLLUTION",
    ]
    for v in vetoes:
        if v in brokerage_vetoes:
            codes.append("BROKER_LIVE_ORDER_POLLUTION")
            break
    if vetoes:
        codes.append("VETO_PRESENT")
    return codes


def _check_llm_boundary(input_data: NEAGateInput) -> list[str]:
    codes: list[str] = []
    if not input_data.get("llm_summary_only", True):
        codes.append("LLM_MARKS_PASS")
    return codes


def _check_order_execution_allowed(input_data: NEAGateInput) -> list[str]:
    codes: list[str] = []
    if input_data.get("order_execution_allowed", True):
        codes.append("ORDER_EXECUTION_ALLOWED_TRUE")
    return codes


def _compute_payoff_bucket(
    net_edge: float,
    expected_net_rr: float,
    fill_probability: float,
    regime_uncertainty: float,
    p_hat: float,
    vetoes: list[str],
    reason_codes: list[str],
) -> str:
    if reason_codes or vetoes:
        return PayoffBucket.BLOCKED.value
    if net_edge <= NEA_MIN_NET_EDGE:
        return PayoffBucket.BLOCKED.value
    if expected_net_rr < NEA_MIN_EXPECTED_NET_RR:
        return PayoffBucket.BLOCKED.value
    if fill_probability < NEA_MIN_FILL_PROBABILITY:
        return PayoffBucket.BLOCKED.value
    if regime_uncertainty > NEA_MAX_REGIME_UNCERTAINTY:
        return PayoffBucket.BLOCKED.value

    if p_hat >= 0.8 and net_edge > 0.05:
        return PayoffBucket.HIGH_CONVICTION_BUY.value
    if p_hat >= 0.65 and net_edge > 0.02:
        return PayoffBucket.MODERATE_CONVICTION_BUY.value
    if p_hat >= 0.55 and net_edge > 0.0:
        return PayoffBucket.LOW_CONVICTION_BUY.value
    if p_hat <= 0.2 and net_edge < -0.05:
        return PayoffBucket.HIGH_CONVICTION_SELL.value
    if p_hat <= 0.35 and net_edge < -0.02:
        return PayoffBucket.MODERATE_CONVICTION_SELL.value
    if p_hat <= 0.45 and net_edge < 0.0:
        return PayoffBucket.LOW_CONVICTION_SELL.value
    return PayoffBucket.NEUTRAL.value


# =============================================================================
# Main Validation Entry Point
# =============================================================================


def validate_nea_gate(input_data: NEAGateInput) -> NEAGateOutput:
    codes: list[str] = []

    codes.extend(_check_missing_inputs(input_data))

    codes.extend(_check_order_execution_allowed(input_data))

    codes.extend(_check_raw_confidence_vetoes(input_data))

    codes.extend(_check_calibration(input_data))

    codes.extend(_check_taiwan_constraints(input_data.get("taiwan_reality_contract")))

    codes.extend(_check_market_reality(input_data))

    codes.extend(_check_risk_gate(input_data))

    codes.extend(_check_llm_boundary(input_data))

    vetoes = input_data.get("vetoes", [])
    codes.extend(_check_vetoes(vetoes))

    if codes:
        fail_breakdown = ScoreBreakdown(
            p_hat=input_data.get("p_hat", 0.0),
            W_hat=input_data.get("W_hat", 0.0),
            L_hat=input_data.get("L_hat", 0.0),
            C=input_data.get("C", 0.0),
            S=input_data.get("S", 0.0),
            B=input_data.get("B", 0.0),
            T=input_data.get("T", 0.0),
            R=input_data.get("R", 0.0),
            U=input_data.get("U", 0.0),
            net_edge=0.0,
            expected_net_rr=0.0,
            fill_probability=input_data.get("fill_probability", 0.0),
            regime_uncertainty=input_data.get("regime_uncertainty", 0.0),
            market_reality_snapshot=input_data.get("market_reality_snapshot", {}),
            risk_snapshot=input_data.get("risk_snapshot", {}),
            threshold_config_version=input_data.get("threshold_config_version", NEA_THRESHOLD_CONFIG_VERSION),
            calibration_version=input_data.get("calibration_version", ""),
            vetoes=vetoes,
            final_nea_decision=FinalNEADecision.FAIL_CLOSED.value,
            reason_codes=codes,
            taiwan_reality_contract=input_data.get("taiwan_reality_contract"),
            payoff_bucket=PayoffBucket.BLOCKED.value,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        return NEAGateOutput(
            passed=False,
            net_edge=0.0,
            expected_net_rr=0.0,
            payoff_bucket=PayoffBucket.BLOCKED.value,
            score_breakdown=vars(fail_breakdown) if hasattr(fail_breakdown, "__dataclass_fields__") else fail_breakdown.__dict__,
            vetoes=vetoes,
            reason_codes=codes,
            final_nea_decision=FinalNEADecision.FAIL_CLOSED.value,
            stage=STAGE_R038F,
        )

    p_hat = input_data["p_hat"]
    W_hat = input_data["W_hat"]
    L_hat = input_data["L_hat"]
    C = input_data["C"]
    S = input_data["S"]
    B = input_data["B"]
    T = input_data["T"]
    R = input_data["R"]
    U = input_data["U"]
    fill_prob = input_data["fill_probability"]
    regime_uncertainty = input_data["regime_uncertainty"]

    net_edge = compute_net_edge(p_hat, W_hat, L_hat, C, S, B, T, R, U)
    expected_net_rr = compute_expected_net_rr(net_edge, L_hat)

    threshold_codes = _check_thresholds(
        net_edge, expected_net_rr, fill_prob, regime_uncertainty,
    )
    codes.extend(threshold_codes)

    payoff_bucket = _compute_payoff_bucket(
        net_edge, expected_net_rr, fill_prob, regime_uncertainty,
        p_hat, vetoes, codes,
    )

    passed = len(codes) == 0 and len(vetoes) == 0 and not input_data.get("order_execution_allowed", False)

    breakdown = ScoreBreakdown(
        p_hat=p_hat,
        W_hat=W_hat,
        L_hat=L_hat,
        C=C,
        S=S,
        B=B,
        T=T,
        R=R,
        U=U,
        net_edge=net_edge,
        expected_net_rr=expected_net_rr,
        fill_probability=fill_prob,
        regime_uncertainty=regime_uncertainty,
        market_reality_snapshot=input_data.get("market_reality_snapshot", {}),
        risk_snapshot=input_data.get("risk_snapshot", {}),
        threshold_config_version=input_data.get("threshold_config_version", NEA_THRESHOLD_CONFIG_VERSION),
        calibration_version=input_data.get("calibration_version", ""),
        vetoes=vetoes,
        final_nea_decision=FinalNEADecision.PASS.value if passed else FinalNEADecision.BLOCKED.value,
        reason_codes=codes,
        taiwan_reality_contract=input_data.get("taiwan_reality_contract"),
        payoff_bucket=payoff_bucket,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    return NEAGateOutput(
        passed=passed,
        net_edge=net_edge,
        expected_net_rr=expected_net_rr,
        payoff_bucket=payoff_bucket,
        score_breakdown=vars(breakdown) if hasattr(breakdown, "__dataclass_fields__") else breakdown.__dict__,
        vetoes=vetoes,
        reason_codes=codes,
        final_nea_decision=FinalNEADecision.PASS.value if passed else FinalNEADecision.BLOCKED.value,
        stage=STAGE_R038F,
    )


# =============================================================================
# CICDVerificationChain Integration
# =============================================================================

STAGE_R038F = "r038f_nea_confidence_calibration"

R038F_NEA_CONFIDENCE_CALIBRATION_STAGE_KEY = "nea_gate_result"


class R038fNEAConfidenceCalibrationInput(TypedDict):
    nea_input: NEAGateInput


class R038fNEAConfidenceCalibrationResult(TypedDict):
    stage: str
    pass_: bool
    reason_codes: list[str]
    net_edge: float
    expected_net_rr: float
    payoff_bucket: str
    score_breakdown: dict[str, Any]
    vetoes: list[str]
    final_nea_decision: str


def validate_r038f_nea_confidence_calibration(
    input_data: R038fNEAConfidenceCalibrationInput,
) -> R038fNEAConfidenceCalibrationResult:
    nea_input = input_data.get("nea_input", {})
    result = validate_nea_gate(nea_input)
    return R038fNEAConfidenceCalibrationResult(
        stage=STAGE_R038F,
        pass_=result["passed"],
        reason_codes=result["reason_codes"],
        net_edge=result["net_edge"],
        expected_net_rr=result["expected_net_rr"],
        payoff_bucket=result["payoff_bucket"],
        score_breakdown=result["score_breakdown"],
        vetoes=result["vetoes"],
        final_nea_decision=result["final_nea_decision"],
    )


def run_r038f_nea_confidence_calibration(
    p_hat: float,
    W_hat: float,
    L_hat: float,
    C: float,
    S: float,
    B: float,
    T: float,
    R: float,
    U: float,
    fill_probability: float,
    regime_uncertainty: float,
    market_reality_snapshot: dict[str, Any] | None = None,
    risk_snapshot: dict[str, Any] | None = None,
    threshold_config_version: str | None = None,
    calibration_version: str | None = None,
    taiwan_reality_contract: dict[str, Any] | None = None,
    order_execution_allowed: bool = False,
    calibration_brier_score: float | None = None,
    calibration_sample_count: int = 0,
    calibration_timestamp: str | None = None,
    raw_confidence_not_used: bool = True,
    vetoes: list[str] | None = None,
    llm_summary_only: bool = True,
) -> R038fNEAConfidenceCalibrationResult:
    if market_reality_snapshot is None:
        market_reality_snapshot = {}
    if risk_snapshot is None:
        risk_snapshot = {}
    if threshold_config_version is None:
        threshold_config_version = NEA_THRESHOLD_CONFIG_VERSION
    if calibration_version is None:
        calibration_version = ""
    if calibration_timestamp is None:
        calibration_timestamp = datetime.now(timezone.utc).isoformat()
    if vetoes is None:
        vetoes = []

    input_data: NEAGateInput = {
        "p_hat": p_hat,
        "W_hat": W_hat,
        "L_hat": L_hat,
        "C": C,
        "S": S,
        "B": B,
        "T": T,
        "R": R,
        "U": U,
        "fill_probability": fill_probability,
        "regime_uncertainty": regime_uncertainty,
        "market_reality_snapshot": market_reality_snapshot,
        "risk_snapshot": risk_snapshot,
        "threshold_config_version": threshold_config_version,
        "calibration_version": calibration_version,
        "taiwan_reality_contract": taiwan_reality_contract,
        "order_execution_allowed": order_execution_allowed,
        "calibration_brier_score": calibration_brier_score,
        "calibration_sample_count": calibration_sample_count,
        "calibration_timestamp": calibration_timestamp,
        "raw_confidence_not_used": raw_confidence_not_used,
        "vetoes": vetoes,
        "llm_summary_only": llm_summary_only,
    }
    gate_result = validate_nea_gate(input_data)
    return R038fNEAConfidenceCalibrationResult(
        stage=STAGE_R038F,
        pass_=gate_result["passed"],
        reason_codes=gate_result["reason_codes"],
        net_edge=gate_result["net_edge"],
        expected_net_rr=gate_result["expected_net_rr"],
        payoff_bucket=gate_result["payoff_bucket"],
        score_breakdown=gate_result["score_breakdown"],
        vetoes=gate_result["vetoes"],
        final_nea_decision=gate_result["final_nea_decision"],
    )
