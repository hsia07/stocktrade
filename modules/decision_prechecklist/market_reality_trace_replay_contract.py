from __future__ import annotations
import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


STAGE_R038A = "R038a_market_reality_trace_replay"


class ReplayValidationStatus(str, Enum):
    PASS = "pass"
    FAIL_CLOSED = "fail_closed"
    FAIL_CONTINUE = "fail_continue"
    BLOCKED_MISSING_CONTRACT = "blocked_missing_contract"
    BLOCKED_ORDER_EXECUTION_ALLOWED = "blocked_order_execution_allowed"
    BLOCKED_MISSING_ASOF_CONTRACT = "blocked_missing_asof_contract"

    @classmethod
    def _missing_(cls, value: object) -> ReplayValidationStatus | None:
        return None


FAIL_CLOSED_REASON_CODES: dict[str, str] = {
    "MARKET_REALITY_SNAPSHOT_MISSING": "market_reality_snapshot is required but missing",
    "COST_MODEL_VERSION_MISSING": "cost_model_version is required but missing",
    "SLIPPAGE_MODEL_VERSION_MISSING": "slippage_model_version is required but missing",
    "FILL_PROBABILITY_MISSING": "estimated_fill_probability is required",
    "FILL_PROBABILITY_OUT_OF_RANGE": "estimated_fill_probability must be in [0.0, 1.0]",
    "LIQUIDITY_SCORE_MISSING": "liquidity_score is required",
    "LIQUIDITY_SCORE_OUT_OF_RANGE": "liquidity_score must be in [0.0, 1.0]",
    "EXPECTED_NET_RR_MISSING": "expected_net_rr is required",
    "EXPECTED_NET_RR_NOT_POSITIVE": "expected_net_rr must be positive (> 0)",
    "EXPECTED_COST_NEGATIVE": "expected_cost must be non-negative",
    "EXPECTED_SLIPPAGE_NEGATIVE": "expected_slippage must be non-negative",
    "MARKET_SESSION_STATE_MISSING": "market_session_state is required but missing",
    "MARKET_SESSION_STATE_INVALID": "market_session_state is not in allowed session values",
    "RISK_GATE_REPLAY_MISSING": "risk_gate replay result is required",
    "RISK_GATE_VETO_EXISTS": "risk gate veto exists, decision blocked",
    "LIQUIDITY_VETO_REASON_EXISTS": "liquidity veto reason exists, execution not feasible",
    "EXECUTION_ABORT_REASON_EXISTS": "execution abort reason exists, trade aborted",
    "LIMIT_UP_DOWN_NEAR_LIMIT": "limit up/down distance near boundary without explicit pass",
    "ORDER_EXECUTION_ALLOWED_NOT_FALSE": "order_execution_allowed must be FALSE in replay context",
    "DECISION_TS_BEFORE_TRADABLE_TS": "decision_ts is before tradable_ts (as-of violation)",
    "TRADABLE_CONTRACT_MISSING": "tradable/as-of contract is required but missing",
    "TAIWAN_PRICE_LIMIT_NOT_CHECKED": "Taiwan price limit (±10%) not checked",
    "T_PLUS_2_NOT_CHECKED": "T+2 settlement not checked",
    "AUCTION_SESSION_NOT_CHECKED": "auction session constraints not checked",
    "ODD_LOT_ROUND_LOT_NOT_CHECKED": "odd lot / round lot rules not checked",
    "TAIWAN_REALITY_CONTRACT_MISSING": "TaiwanRealityContract is required but missing",
    "FEE_RATE_NEGATIVE": "fee_rate must be non-negative",
    "TAX_RATE_NEGATIVE": "tax_rate must be non-negative",
    "MINIMUM_FEE_NEGATIVE": "minimum_fee must be non-negative",
    "MINIMUM_FEE_AWARE_NOT_TRUE": "minimum_fee_aware must be True",
    "HALT_DISPOSITION_ATTENTION_SET": "halt/disposition/attention risk flag is set, trade blocked",
    "LIQUIDITY_INSUFFICIENCY_SET": "liquidity_insufficiency flag is set, trade blocked",
    "FILL_REJECTED_OR_FAILED": "fill status is rejected or execution abort",
    "FILL_UNFILLED": "fill status is unfilled",
    "FILL_TIMEOUT_CANCEL": "fill status is timeout / cancel pending",
    "PARTIAL_FILL_WITHOUT_SAFE_POLICY": "partial fill without explicit partial_fill_accepted flag",
    "AS_OF_SOURCE_TS_MISSING": "as_of_source_ts is required but missing",
    "AS_OF_PUBLISH_TS_MISSING": "as_of_publish_ts is required but missing",
    "AS_OF_INGEST_TS_MISSING": "as_of_ingest_ts is required but missing",
    "AS_OF_MONOTONIC_ORDER_VIOLATED": "as-of timestamp monotonic order violated (source <= publish <= ingest <= tradable <= decision)",
}


FILL_REJECT_REASON_CODES = frozenset({
    "PARTIAL_FILL",
    "UNFILLED",
    "REJECTED",
    "TIMEOUT_CANCEL",
    "FILL_PRICE_IMPROVED",
    "FILL_PRICE_HARMED",
})


ALLOWED_MARKET_SESSION_STATES = frozenset({
    "intraday",
    "auction_open",
    "auction_close",
    "pre_market",
    "close_auction",
    "odd_lot",
    "regular",
    "after_hours",
    "closed",
})


@dataclass
class MarketRealityReplaySnapshot:
    cost_model_version: str = ""
    slippage_model_version: str = ""
    liquidity_score: float = 0.0
    estimated_fill_probability: float = 0.0
    expected_cost: float = 0.0
    expected_slippage: float = 0.0
    expected_net_rr: float = 0.0
    market_session_state: str = ""
    limit_up_down_distance: float = 0.0
    liquidity_veto_reason: str = ""
    execution_abort_reason: str = ""
    taiwan_price_limit_checked: bool = False
    t_plus_2_checked: bool = False
    auction_session_checked: bool = False
    odd_lot_round_lot_checked: bool = False

    def compute_deterministic_hash(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


@dataclass
class DecisionTraceReplayInput:
    trace_id: str = ""
    decision_ts: str = ""
    strategy_id: str = ""
    strategy_version: str = ""
    candidate_action: str = ""
    decision_chain: list[dict[str, Any]] = field(default_factory=list)
    market_reality_snapshot: MarketRealityReplaySnapshot | None = None
    risk_gate_replay_result: RiskGateReplayResult | None = None
    order_ref: OptionalOrderRef | None = None
    fill_ref: OptionalFillRef | None = None
    pnl_ref: OptionalPnlRef | None = None
    taiwan_reality_contract: TaiwanRealityContract | None = None
    threshold_config_version: str = ""
    tradable_ts: str = ""
    as_of_source_ts: str = ""
    as_of_publish_ts: str = ""
    as_of_ingest_ts: str = ""


@dataclass
class OptionalOrderRef:
    order_id: str = ""
    order_intent_id: str = ""
    order_type: str = ""
    order_side: str = ""
    order_quantity: int = 0
    order_price: float = 0.0
    time_in_force: str = ""


@dataclass
class OptionalFillRef:
    fill_id: str = ""
    fill_qty: int = 0
    fill_price: float = 0.0
    fill_status: str = ""
    reject_reason: str = ""
    partial_fill_qty: int = 0
    partial_fill_accepted: bool = False

    @property
    def is_rejected(self) -> bool:
        return self.fill_status in ("REJECTED", "TIMEOUT_CANCEL")

    @property
    def is_partial(self) -> bool:
        return self.fill_status == "PARTIAL_FILL" or (self.partial_fill_qty > 0 and self.partial_fill_qty < self.fill_qty)


@dataclass
class OptionalPnlRef:
    pnl_id: str = ""
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    cost_basis: float = 0.0
    net_of_cost_pnl: float = 0.0


@dataclass
class RiskGateReplayResult:
    risk_gate_results: dict[str, str] = field(default_factory=dict)
    veto_reason_codes: list[str] = field(default_factory=list)
    veto_actor: str = ""
    veto_stage: str = ""
    no_trade_reason: str = ""
    reduce_size_reason: str = ""
    wait_confirmation_reason: str = ""

    def has_veto(self) -> bool:
        return any(r == "veto" for r in self.risk_gate_results.values()) or bool(self.veto_reason_codes)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaiwanRealityContract:
    limit_up_down_pct: float = 10.0
    t_plus_2_settlement_aware: bool = False
    auction_session_state: str = ""
    odd_lot_round_lot_mode: str = ""
    halt_disposition_attention: str = ""
    liquidity_insufficiency: str = ""
    pre_market_session_active: bool = False
    close_auction_session_active: bool = False
    intraday_session_active: bool = False
    price_limit_checked: bool = False
    t_plus_2_checked: bool = False
    auction_session_checked: bool = False
    odd_lot_round_lot_checked: bool = False
    minimum_fee_aware: bool = False
    tax_rate: float = 0.003
    fee_rate: float = 0.001425
    minimum_fee: float = 1.0


@dataclass
class DecisionTraceReplayResult:
    trace_id: str = ""
    stage: str = STAGE_R038A
    replay_passed: bool = False
    fail_closed: bool = False
    vetoed: bool = False
    status: ReplayValidationStatus = ReplayValidationStatus.FAIL_CLOSED
    reason_codes: list[str] = field(default_factory=list)
    market_reality_snapshot_hash: str = ""
    market_reality_snapshot_fields: dict[str, Any] = field(default_factory=dict)
    risk_gate_replay_fields: dict[str, Any] = field(default_factory=dict)
    order_execution_allowed: bool = False
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "stage": self.stage,
            "replay_passed": self.replay_passed,
            "fail_closed": self.fail_closed,
            "vetoed": self.vetoed,
            "status": self.status.value if self.status else "unknown",
            "reason_codes": self.reason_codes,
            "market_reality_snapshot_hash": self.market_reality_snapshot_hash,
            "market_reality_snapshot_fields": self.market_reality_snapshot_fields,
            "risk_gate_replay_fields": self.risk_gate_replay_fields,
            "order_execution_allowed": self.order_execution_allowed,
            "timestamp": self.timestamp,
        }

    def compute_result_hash(self) -> str:
        payload = self.to_dict()
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def validate_market_reality_snapshot(
    snapshot: MarketRealityReplaySnapshot | None,
) -> list[str]:
    codes: list[str] = []
    if snapshot is None:
        codes.append("MARKET_REALITY_SNAPSHOT_MISSING")
        return codes
    if not snapshot.cost_model_version:
        codes.append("COST_MODEL_VERSION_MISSING")
    if not snapshot.slippage_model_version:
        codes.append("SLIPPAGE_MODEL_VERSION_MISSING")
    if snapshot.estimated_fill_probability is None:
        codes.append("FILL_PROBABILITY_MISSING")
    elif not (0.0 <= snapshot.estimated_fill_probability <= 1.0):
        codes.append("FILL_PROBABILITY_OUT_OF_RANGE")
    if snapshot.liquidity_score is None:
        codes.append("LIQUIDITY_SCORE_MISSING")
    elif not (0.0 <= snapshot.liquidity_score <= 1.0):
        codes.append("LIQUIDITY_SCORE_OUT_OF_RANGE")
    if snapshot.expected_net_rr is None:
        codes.append("EXPECTED_NET_RR_MISSING")
    elif snapshot.expected_net_rr <= 0:
        codes.append("EXPECTED_NET_RR_NOT_POSITIVE")
    if snapshot.expected_cost < 0:
        codes.append("EXPECTED_COST_NEGATIVE")
    if snapshot.expected_slippage < 0:
        codes.append("EXPECTED_SLIPPAGE_NEGATIVE")
    if not snapshot.market_session_state:
        codes.append("MARKET_SESSION_STATE_MISSING")
    elif snapshot.market_session_state not in ALLOWED_MARKET_SESSION_STATES:
        codes.append("MARKET_SESSION_STATE_INVALID")
    if snapshot.liquidity_veto_reason:
        codes.append("LIQUIDITY_VETO_REASON_EXISTS")
    if snapshot.execution_abort_reason:
        codes.append("EXECUTION_ABORT_REASON_EXISTS")
    if not snapshot.taiwan_price_limit_checked:
        codes.append("TAIWAN_PRICE_LIMIT_NOT_CHECKED")
    if not snapshot.t_plus_2_checked:
        codes.append("T_PLUS_2_NOT_CHECKED")
    if not snapshot.auction_session_checked:
        codes.append("AUCTION_SESSION_NOT_CHECKED")
    if not snapshot.odd_lot_round_lot_checked:
        codes.append("ODD_LOT_ROUND_LOT_NOT_CHECKED")
    return codes


def check_limit_up_down(snapshot: MarketRealityReplaySnapshot) -> str:
    dist = abs(snapshot.limit_up_down_distance)
    if dist <= 2.0:
        return "LIMIT_UP_DOWN_NEAR_LIMIT"
    return ""


def validate_risk_gate(input_data: DecisionTraceReplayInput) -> list[str]:
    codes: list[str] = []
    if input_data.risk_gate_replay_result is None:
        codes.append("RISK_GATE_REPLAY_MISSING")
        return codes
    if input_data.risk_gate_replay_result.has_veto():
        codes.append("RISK_GATE_VETO_EXISTS")
    return codes


def validate_taiwan_reality_contract(
    contract: TaiwanRealityContract | None,
) -> list[str]:
    codes: list[str] = []
    if contract is None:
        codes.append("TAIWAN_REALITY_CONTRACT_MISSING")
        return codes
    if contract.fee_rate < 0:
        codes.append("FEE_RATE_NEGATIVE")
    if contract.tax_rate < 0:
        codes.append("TAX_RATE_NEGATIVE")
    if contract.minimum_fee < 0:
        codes.append("MINIMUM_FEE_NEGATIVE")
    if not contract.minimum_fee_aware:
        codes.append("MINIMUM_FEE_AWARE_NOT_TRUE")
    if contract.halt_disposition_attention:
        codes.append("HALT_DISPOSITION_ATTENTION_SET")
    if contract.liquidity_insufficiency:
        codes.append("LIQUIDITY_INSUFFICIENCY_SET")
    return codes


def validate_fill_ref(fill: OptionalFillRef | None) -> list[str]:
    codes: list[str] = []
    if fill is None:
        return codes
    status = fill.fill_status
    if status in ("REJECTED", "EXECUTION_ABORT"):
        codes.append("FILL_REJECTED_OR_FAILED")
    if status == "UNFILLED":
        codes.append("FILL_UNFILLED")
    if status in ("TIMEOUT_CANCEL", "CANCEL_PENDING"):
        codes.append("FILL_TIMEOUT_CANCEL")
    if status == "PARTIAL_FILL" and not fill.partial_fill_accepted:
        codes.append("PARTIAL_FILL_WITHOUT_SAFE_POLICY")
    return codes


def check_as_of_contract(input_data: DecisionTraceReplayInput) -> list[str]:
    codes: list[str] = []
    if not input_data.tradable_ts:
        codes.append("TRADABLE_CONTRACT_MISSING")
    if not input_data.as_of_source_ts:
        codes.append("AS_OF_SOURCE_TS_MISSING")
    if not input_data.as_of_publish_ts:
        codes.append("AS_OF_PUBLISH_TS_MISSING")
    if not input_data.as_of_ingest_ts:
        codes.append("AS_OF_INGEST_TS_MISSING")
    if codes:
        return codes
    if input_data.decision_ts and input_data.decision_ts < input_data.tradable_ts:
        codes.append("DECISION_TS_BEFORE_TRADABLE_TS")
    ts_fields = [
        input_data.as_of_source_ts,
        input_data.as_of_publish_ts,
        input_data.as_of_ingest_ts,
        input_data.tradable_ts,
        input_data.decision_ts,
    ]
    if all(ts_fields):
        for i in range(len(ts_fields) - 1):
            if ts_fields[i] > ts_fields[i + 1]:
                codes.append("AS_OF_MONOTONIC_ORDER_VIOLATED")
                break
    return codes


def validate_and_replay(
    input_data: DecisionTraceReplayInput,
    order_execution_allowed: bool = False,
) -> DecisionTraceReplayResult:
    trace_id = input_data.trace_id or uuid.uuid4().hex[:16]
    result = DecisionTraceReplayResult(
        trace_id=trace_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    reason_codes: list[str] = []

    if order_execution_allowed is not False:
        reason_codes.append("ORDER_EXECUTION_ALLOWED_NOT_FALSE")
        result.reason_codes = reason_codes
        result.fail_closed = True
        result.status = ReplayValidationStatus.BLOCKED_ORDER_EXECUTION_ALLOWED
        result.replay_passed = False
        return result

    snapshot = input_data.market_reality_snapshot
    snapshot_codes = validate_market_reality_snapshot(snapshot)
    reason_codes.extend(snapshot_codes)

    taiwan_codes = validate_taiwan_reality_contract(input_data.taiwan_reality_contract)
    reason_codes.extend(taiwan_codes)

    risk_codes = validate_risk_gate(input_data)
    reason_codes.extend(risk_codes)

    limit_code = ""
    if snapshot:
        limit_code = check_limit_up_down(snapshot)
        if limit_code:
            reason_codes.append(limit_code)

    fill_codes = validate_fill_ref(input_data.fill_ref)
    reason_codes.extend(fill_codes)

    as_of_codes = check_as_of_contract(input_data)
    reason_codes.extend(as_of_codes)

    # Read order_ref and pnl_ref for schema completeness (no fail-closed for absence)
    _order_ref = input_data.order_ref
    _pnl_ref = input_data.pnl_ref

    if snapshot:
        result.market_reality_snapshot_hash = snapshot.compute_deterministic_hash()
        result.market_reality_snapshot_fields = asdict(snapshot)
    if input_data.risk_gate_replay_result:
        result.risk_gate_replay_fields = input_data.risk_gate_replay_result.to_dict()

    has_fail_closed = bool(reason_codes)
    has_veto = any(
        c in reason_codes
        for c in [
            "RISK_GATE_VETO_EXISTS",
            "LIQUIDITY_VETO_REASON_EXISTS",
            "EXECUTION_ABORT_REASON_EXISTS",
        ]
    )

    result.reason_codes = reason_codes
    result.fail_closed = has_fail_closed
    result.vetoed = has_veto
    result.replay_passed = not has_fail_closed and not has_veto
    result.order_execution_allowed = False

    if has_fail_closed:
        result.status = ReplayValidationStatus.FAIL_CLOSED
        if "ORDER_EXECUTION_ALLOWED_NOT_FALSE" in reason_codes:
            result.status = ReplayValidationStatus.BLOCKED_ORDER_EXECUTION_ALLOWED
        if "TRADABLE_CONTRACT_MISSING" in reason_codes or "DECISION_TS_BEFORE_TRADABLE_TS" in reason_codes:
            result.status = ReplayValidationStatus.BLOCKED_MISSING_ASOF_CONTRACT
    else:
        result.status = ReplayValidationStatus.PASS

    return result


def run_r038a_market_reality_trace_replay(
    input_data: DecisionTraceReplayInput,
    order_execution_allowed: bool = False,
) -> dict[str, Any]:
    result = validate_and_replay(input_data, order_execution_allowed)
    return result.to_dict()
