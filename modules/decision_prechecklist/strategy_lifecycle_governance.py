from __future__ import annotations
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


STAGE_R038D = "R038d_strategy_lifecycle"


DEFAULT_TTL_DAYS = 180
DEFAULT_VALIDATION_FRESHNESS_DAYS = 90
DEFAULT_PROMOTION_EXPIRY_DAYS = 30
DEFAULT_SLIPPAGE_DRIFT_THRESHOLD = 0.20
DEFAULT_FILL_RATE_DRIFT_THRESHOLD = 0.15
DEFAULT_DRAWDOWN_BREACH_THRESHOLD = 0.25
DEFAULT_NET_OF_COST_DECAY_THRESHOLD = 0.15
DEFAULT_VIRTUAL_CAPITAL_BUDGET = 1_000_000.0
DEFAULT_REAL_CAPITAL_LOCKED = 0.0


class StrategyLifecycleStatus(str, Enum):
    REGISTERED = "registered"
    ACTIVE = "active"
    PROMOTION_PENDING = "promotion_pending"
    PROMOTION_BLOCKED = "promotion_blocked"
    QUARANTINED = "quarantined"
    DISABLED = "disabled"
    EXPIRED = "expired"

    @classmethod
    def _missing_(cls, value: object) -> StrategyLifecycleStatus | None:
        return None


class StrategyLifecycleStage(str, Enum):
    RESEARCH_ONLY = "research_only"
    SHADOW = "shadow"
    PAPER = "paper"
    LIVE_SMALL = "live_small"
    LIVE_NORMAL = "live_normal"

    @classmethod
    def _missing_(cls, value: object) -> StrategyLifecycleStage | None:
        return None


class PromotionTransition(str, Enum):
    RESEARCH_TO_SHADOW = "research_only_to_shadow"
    SHADOW_TO_PAPER = "shadow_to_paper"
    PAPER_TO_LIVE_SMALL = "paper_to_live_small"
    LIVE_SMALL_TO_LIVE_NORMAL = "live_small_to_live_normal"
    CAPITAL_INCREASE = "capital_increase"

    @classmethod
    def _missing_(cls, value: object) -> PromotionTransition | None:
        return None


class DowngradeAction(str, Enum):
    DOWNGRADE_TO_RESEARCH_ONLY = "downgrade_to_research_only"
    DOWNGRADE_TO_SHADOW = "downgrade_to_shadow"
    FREEZE_PROMOTION = "freeze_promotion"
    QUARANTINE = "quarantine"
    DISABLE_CANDIDATE = "disable_candidate"
    REDUCE_SIZE_RECOMMENDATION = "reduce_size_recommendation"
    NO_TRADE_RECOMMENDATION = "no_trade_recommendation"

    @classmethod
    def _missing_(cls, value: object) -> DowngradeAction | None:
        return None


class DowngradeSignalType(str, Enum):
    DRAWDOWN_BREACH = "drawdown_breach"
    NET_OF_COST_DECAY = "net_of_cost_decay"
    SLIPPAGE_DRIFT = "slippage_drift"
    FILL_RATE_DRIFT = "fill_rate_drift"
    REGIME_MISMATCH = "regime_mismatch"
    MARKET_REALITY_FAILURE = "market_reality_failure"
    VALIDATION_STALE = "validation_stale"
    STRATEGY_TTL_EXPIRED = "strategy_ttl_expired"
    PROMOTION_EXPIRED = "promotion_expired"
    CORRELATION_CONCENTRATION = "correlation_concentration"
    LIQUIDITY_SHORTAGE = "liquidity_shortage"
    CONSECUTIVE_LOSS_COOLDOWN = "consecutive_loss_cooldown"
    MANUAL_BLOCK = "manual_block"
    GOVERNANCE_BLOCK = "governance_block"

    @classmethod
    def _missing_(cls, value: object) -> DowngradeSignalType | None:
        return None


FAIL_CLOSED_REASON_CODES_R038D: dict[str, str] = {
    "REGISTRY_MISSING_STRATEGY_ID": "registry entry missing strategy_id",
    "REGISTRY_MISSING_STRATEGY_VERSION": "registry entry missing strategy_version",
    "REGISTRY_MISSING_VALIDATION_REFS": "registry entry missing validation_refs for R038a/b/c",
    "REGISTRY_MISSING_SOURCE_COMMIT": "registry entry missing source_commit",
    "REGISTRY_MISSING_AUDIT_TRAIL_ID": "registry entry missing audit_trace_id",
    "REGISTRY_STATUS_IMPLIES_LIVE": "registry entry current_status implies live without approval",
    "REGISTRY_RESEARCH_ONLY_NOT_DEFAULT": "registry entry research_only_default is not TRUE for new strategy",
    "REGISTRY_ORDER_EXECUTION_ALLOWED_TRUE": "registry entry order_execution_allowed is TRUE",
    "REGISTRY_NO_LIVE_ORDER_PATH_FALSE": "registry entry no_live_order_path is FALSE",
    "NEW_STRATEGY_NOT_RESEARCH_ONLY": "new strategy must start at research_only stage",
    "NEW_STRATEGY_HAS_REAL_CAPITAL": "new strategy has real_capital > 0 at research_only",
    "NEW_STRATEGY_SELF_ENABLES_LIVE": "new strategy self-enables live runtime",
    "NEW_STRATEGY_LLM_APPROVED_PROMOTION": "LLM/API output directly approves promotion, deterministic gate required",
    "NEW_STRATEGY_MISSING_DETERMINISTIC_GATE": "missing deterministic gate result for new strategy",
    "PROMOTION_MISSING_R038A_REF": "promotion missing R038a market reality trace replay validation ref",
    "PROMOTION_MISSING_R038B_REF": "promotion missing R038b L0-L4 validation ref",
    "PROMOTION_MISSING_R038C_REF": "promotion missing R038c L5-L9 validation ref",
    "PROMOTION_MISSING_VALIDATION_SNAPSHOT": "promotion missing validation_snapshot_version",
    "PROMOTION_VALIDATION_STALE": "promotion validation evidence is stale",
    "PROMOTION_VALIDATION_NOT_ALL_PASSED": "promotion R038a/b/c validation not all passed",
    "PROMOTION_NET_OF_COST_NOT_POSITIVE": "promotion net_of_cost_positive required",
    "PROMOTION_REPLAY_NOT_COMPATIBLE": "promotion replay_compatible required",
    "PROMOTION_RISK_GATE_REPLAY_NOT_COMPATIBLE": "promotion risk_gate_replay_compatible required",
    "PROMOTION_MARKET_REALITY_NOT_COMPATIBLE": "promotion market_reality_compatible required",
    "PROMOTION_TAIWAN_CONSTRAINTS_MISSING": "promotion Taiwan market constraints not acknowledged",
    "PROMOTION_GROSS_ONLY_EVIDENCE": "promotion uses gross-only PnL, net_of_cost required",
    "PROMOTION_TRADINGVIEW_ONLY": "promotion TradingView/Pine only evidence rejected",
    "PROMOTION_TTL_MISSING": "promotion strategy TTL missing",
    "PROMOTION_TTL_EXPIRED": "promotion strategy TTL expired",
    "PROMOTION_EXPIRY_MISSING": "promotion expiry missing",
    "PROMOTION_EXPIRY_EXPIRED": "promotion expiry expired",
    "PROMOTION_BROKER_LIVE_PATH_PRESENT": "promotion has broker/live/order path present",
    "PROMOTION_ORDER_EXECUTION_ALLOWED_TRUE": "promotion order_execution_allowed is TRUE",
    "PROMOTION_TO_LIVE_MISSING_HUMAN_APPROVAL": "promotion to live missing human approval",
    "PROMOTION_CAPITAL_INCREASE_MISSING_HUMAN_APPROVAL": "capital increase missing human approval",
    "PROMOTION_LIVE_CORE_LOGIC_CHANGE_MISSING_HUMAN_APPROVAL": "live core logic change missing human approval",
    "PROMOTION_AUTO_LIVE_APPROVAL": "paper->live_small or live_small->live_normal auto approved",
    "PROMOTION_AUTO_CAPITAL_INCREASE": "capital increase auto approved",
    "DOWNGRADE_SIGNAL_IGNORED": "downgrade signal present but ignored",
    "DOWNGRADE_STALE_STRATEGY_PROMOTABLE": "stale strategy remains promotable despite downgrade signal",
    "DOWNGRADE_MARKET_REALITY_FAILURE_PROMOTABLE": "market reality failure strategy still promotable",
    "DOWNGRADE_SLIPPAGE_DRIFT_OVER_THRESHOLD": "slippage drift over threshold strategy still promotable",
    "DOWNGRADE_FILL_RATE_DRIFT_OVER_THRESHOLD": "fill-rate drift over threshold strategy still promotable",
    "DOWNGRADE_REGIME_MISMATCH_PROMOTABLE": "regime mismatch strategy still promotable",
    "DOWNGRADE_GOVERNANCE_BLOCK_IGNORED": "governance/manual block ignored",
    "DOWNGRADE_QUARANTINED_PROMOTABLE": "quarantined strategy still promotable",
    "DOWNGRADE_TTL_EXPIRED_PROMOTABLE": "expired TTL strategy still promotable",
    "ALLOCATION_SELF_INCREASES_CAPITAL": "strategy self-increases capital without governance",
    "ALLOCATION_LLM_CONTROLS_QTY": "LLM directly controls quantity instead of deterministic engine",
    "ALLOCATION_RISK_GATE_CANNOT_VETO": "risk gate cannot veto allocation",
    "ALLOCATION_NO_TRACE": "no allocation trace available",
    "ALLOCATION_TAIWAN_LIQUIDITY_CONSTRAINTS_MISSING": "Taiwan liquidity/settlement constraints missing from promotion evidence",
    "LLM_APPROVED_PROMOTION": "LLM/API approval treated as promotion pass",
    "LLM_SCORE_MOVES_STAGE_DIRECTLY": "LLM/API score directly moves stage without deterministic gate",
    "LLM_API_FAILURE_DEFAULTS_ALLOW": "API/LLM failure defaults to allow instead of fail-closed",
    "LLM_MISSING_LOCAL_DETERMINISTIC_GATE": "missing local deterministic gate as source of truth",
    "STRATEGY_STALE_VALIDATION_ALLOWS_PROMOTION": "stale validation evidence still allows promotion",
    "STRATEGY_MISSING_TTL": "strategy missing TTL configuration",
    "STRATEGY_EXPIRED_TTL": "strategy TTL has expired",
    "STRATEGY_MISSING_VALIDATION_TIMESTAMP": "strategy missing validation timestamp",
    "STRATEGY_EXPIRED_VALIDATION": "strategy validation has expired",
    "STRATEGY_EXPIRED_PROMOTION": "strategy promotion has expired",
    "STRATEGY_REVALIDATION_BEFORE_LIVE_MISSING": "revalidation_before_live flag missing",
}


@dataclass
class StrategyValidationEvidenceRef:
    r038a_passed: bool = False
    r038a_reason_codes: list[str] = field(default_factory=list)
    r038a_snapshot_ref: str = ""
    r038b_passed: bool = False
    r038b_reason_codes: list[str] = field(default_factory=list)
    r038b_snapshot_ref: str = ""
    r038c_passed: bool = False
    r038c_reason_codes: list[str] = field(default_factory=list)
    r038c_snapshot_ref: str = ""
    validation_snapshot_ts: str = ""
    validation_expiry_ts: str = ""
    validation_snapshot_version: str = ""

    def is_complete(self) -> bool:
        return (
            self.r038a_snapshot_ref != ""
            and self.r038b_snapshot_ref != ""
            and self.r038c_snapshot_ref != ""
            and self.validation_snapshot_version != ""
        )

    def all_passed(self) -> bool:
        return self.r038a_passed and self.r038b_passed and self.r038c_passed


@dataclass
class StrategyRegistryEntry:
    strategy_id: str = ""
    strategy_version: str = ""
    strategy_family: str = ""
    created_at: str = ""
    registered_at: str = ""
    current_status: str = StrategyLifecycleStatus.REGISTERED.value
    current_stage: str = StrategyLifecycleStage.RESEARCH_ONLY.value
    lifecycle_state: str = ""
    source_round: str = ""
    source_candidate: str = ""
    source_commit: str = ""
    validation_refs: StrategyValidationEvidenceRef | None = None
    latest_validation_level_passed: str = ""
    research_only_default: bool = True
    no_live_order_path: bool = True
    order_execution_allowed: bool = False
    owner: str = ""
    proposer: str = ""
    reviewer: str = ""
    approval_chain: list[str] = field(default_factory=list)
    config_version: str = ""
    threshold_version: str = ""
    reason_codes: list[str] = field(default_factory=list)
    audit_trace_id: str = ""
    real_capital: float = DEFAULT_REAL_CAPITAL_LOCKED
    live_enabled: bool = False
    broker_access: bool = False
    capital_bucket: str = ""
    virtual_capital_budget: float = DEFAULT_VIRTUAL_CAPITAL_BUDGET


@dataclass
class StrategyPromotionRequest:
    strategy_id: str = ""
    strategy_version: str = ""
    current_stage: str = ""
    requested_transition: str = ""
    validation_refs: StrategyValidationEvidenceRef | None = None
    net_of_cost_positive: bool = False
    replay_compatible: bool = False
    risk_gate_replay_compatible: bool = False
    market_reality_compatible: bool = False
    taiwan_constraints_acknowledged: bool = False
    evidence_source: str = "python_backtest"
    strategy_ttl_days: int = DEFAULT_TTL_DAYS
    strategy_ttl_remaining_days: int = DEFAULT_TTL_DAYS
    promotion_expiry_ts: str = ""
    no_live_order_path: bool = True
    order_execution_allowed: bool = False
    human_approval_received: bool = False
    human_approval_record_ref: str = ""
    human_approval_required: bool = False
    capital_increase_amount: float = 0.0
    capital_increase_human_approved: bool = False
    live_core_logic_change: bool = False
    live_core_logic_change_human_approved: bool = False
    llm_approval_present: bool = False
    llm_approval_used_as_deterministic: bool = False
    deterministic_gate_result: bool = False
    audit_trace_id: str = ""
    timestamp: str = ""

    @property
    def is_tradingview_only(self) -> bool:
        return self.evidence_source in ("tradingview", "pine", "deeptest")


@dataclass
class StrategyPromotionDecision:
    strategy_id: str = ""
    strategy_version: str = ""
    promotion_allowed: bool = False
    transition: str = ""
    fail_closed: bool = False
    reason_codes: list[str] = field(default_factory=list)
    human_approval_required: bool = False
    human_approval_received: bool = False
    deterministic_gate_passed: bool = False
    llm_override_prevented: bool = True
    target_stage: str = ""
    requires_human_signoff: bool = False


@dataclass
class StrategyDowngradeSignal:
    signal_type: str = ""
    signal_value: float = 0.0
    threshold: float = 0.0
    signal_detected: bool = False
    signal_timestamp: str = ""
    signal_detail: str = ""


@dataclass
class StrategyLifecyclePolicy:
    strategy_id: str = ""
    strategy_ttl_days: int = DEFAULT_TTL_DAYS
    validation_freshness_days: int = DEFAULT_VALIDATION_FRESHNESS_DAYS
    promotion_expiry_days: int = DEFAULT_PROMOTION_EXPIRY_DAYS
    slippage_drift_threshold: float = DEFAULT_SLIPPAGE_DRIFT_THRESHOLD
    fill_rate_drift_threshold: float = DEFAULT_FILL_RATE_DRIFT_THRESHOLD
    drawdown_breach_threshold: float = DEFAULT_DRAWDOWN_BREACH_THRESHOLD
    net_of_cost_decay_threshold: float = DEFAULT_NET_OF_COST_DECAY_THRESHOLD
    revalidation_required_before_live: bool = True
    human_approval_required_for_live: bool = True
    human_approval_required_for_capital_increase: bool = True
    human_approval_required_for_live_logic_change: bool = True
    llm_cannot_approve_promotion: bool = True
    llm_cannot_set_qty: bool = True
    risk_gate_can_veto_allocation: bool = True
    qty_controlled_by_deterministic_engine: bool = True
    research_only_default_for_new: bool = True
    no_live_order_path: bool = True
    order_execution_allowed_default: bool = False
    market_reality_required: bool = True
    replay_required: bool = True
    risk_gate_replay_required: bool = True
    taiwan_market_constraints_required: bool = True
    tradingview_only_rejected: bool = True
    net_of_cost_required: bool = True


@dataclass
class StrategyLifecycleValidationResult:
    input_id: str = ""
    stage: str = STAGE_R038D
    validation_passed: bool = False
    fail_closed: bool = False
    reason_codes: list[str] = field(default_factory=list)
    strategy_id: str = ""
    strategy_version: str = ""
    current_stage: str = ""
    requested_transition: str = ""
    transition_allowed: bool = False
    promotion_target: str = ""
    downgrade_action: str = ""
    human_approval_required: bool = False
    registry_entry_valid: bool = False
    validation_refs_present: bool = False
    market_reality_required: bool = True
    replay_required: bool = True
    risk_gate_replay_required: bool = True
    no_live_order_path: bool = True
    order_execution_allowed: bool = False
    research_only_default: bool = True
    tradingview_only_rejected: bool = True
    net_of_cost_required: bool = True
    llm_cannot_approve_promotion: bool = True
    llm_cannot_set_qty: bool = True
    risk_gate_can_veto_allocation: bool = True
    taiwan_constraints_required: bool = True
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_id": self.input_id,
            "stage": self.stage,
            "validation_passed": self.validation_passed,
            "fail_closed": self.fail_closed,
            "reason_codes": self.reason_codes,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "current_stage": self.current_stage,
            "requested_transition": self.requested_transition,
            "transition_allowed": self.transition_allowed,
            "promotion_target": self.promotion_target,
            "downgrade_action": self.downgrade_action,
            "human_approval_required": self.human_approval_required,
            "registry_entry_valid": self.registry_entry_valid,
            "validation_refs_present": self.validation_refs_present,
            "market_reality_required": self.market_reality_required,
            "replay_required": self.replay_required,
            "risk_gate_replay_required": self.risk_gate_replay_required,
            "no_live_order_path": self.no_live_order_path,
            "order_execution_allowed": self.order_execution_allowed,
            "research_only_default": self.research_only_default,
            "tradingview_only_rejected": self.tradingview_only_rejected,
            "net_of_cost_required": self.net_of_cost_required,
            "llm_cannot_approve_promotion": self.llm_cannot_approve_promotion,
            "llm_cannot_set_qty": self.llm_cannot_set_qty,
            "risk_gate_can_veto_allocation": self.risk_gate_can_veto_allocation,
            "taiwan_constraints_required": self.taiwan_constraints_required,
            "timestamp": self.timestamp,
        }

    def compute_result_hash(self) -> str:
        d = self.to_dict()
        d.pop("input_id", None)
        d.pop("timestamp", None)
        raw = json.dumps(d, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def validate_strategy_registry_entry(
    entry: StrategyRegistryEntry | None,
) -> list[str]:
    codes: list[str] = []
    if entry is None:
        codes.append("REGISTRY_MISSING_STRATEGY_ID")
        codes.append("REGISTRY_MISSING_STRATEGY_VERSION")
        codes.append("REGISTRY_MISSING_VALIDATION_REFS")
        codes.append("REGISTRY_MISSING_SOURCE_COMMIT")
        codes.append("REGISTRY_MISSING_AUDIT_TRAIL_ID")
        codes.append("REGISTRY_RESEARCH_ONLY_NOT_DEFAULT")
        codes.append("REGISTRY_ORDER_EXECUTION_ALLOWED_TRUE")
        codes.append("REGISTRY_NO_LIVE_ORDER_PATH_FALSE")
        return codes
    if not entry.strategy_id:
        codes.append("REGISTRY_MISSING_STRATEGY_ID")
    if not entry.strategy_version:
        codes.append("REGISTRY_MISSING_STRATEGY_VERSION")
    refs = entry.validation_refs
    if refs is None or not refs.is_complete():
        codes.append("REGISTRY_MISSING_VALIDATION_REFS")
    if not entry.source_commit:
        codes.append("REGISTRY_MISSING_SOURCE_COMMIT")
    if not entry.audit_trace_id:
        codes.append("REGISTRY_MISSING_AUDIT_TRAIL_ID")
    if entry.current_status in ("live_small", "live_normal"):
        codes.append("REGISTRY_STATUS_IMPLIES_LIVE")
    if not entry.research_only_default:
        codes.append("REGISTRY_RESEARCH_ONLY_NOT_DEFAULT")
    if entry.order_execution_allowed:
        codes.append("REGISTRY_ORDER_EXECUTION_ALLOWED_TRUE")
    if not entry.no_live_order_path:
        codes.append("REGISTRY_NO_LIVE_ORDER_PATH_FALSE")
    return codes


def validate_new_strategy_defaults(
    entry: StrategyRegistryEntry | None,
) -> list[str]:
    codes: list[str] = []
    if entry is None:
        codes.append("NEW_STRATEGY_NOT_RESEARCH_ONLY")
        codes.append("NEW_STRATEGY_HAS_REAL_CAPITAL")
        codes.append("NEW_STRATEGY_SELF_ENABLES_LIVE")
        return codes
    if entry.current_stage != StrategyLifecycleStage.RESEARCH_ONLY.value:
        codes.append("NEW_STRATEGY_NOT_RESEARCH_ONLY")
    if entry.real_capital > 0:
        codes.append("NEW_STRATEGY_HAS_REAL_CAPITAL")
    if entry.live_enabled:
        codes.append("NEW_STRATEGY_SELF_ENABLES_LIVE")
    if entry.broker_access:
        codes.append("NEW_STRATEGY_SELF_ENABLES_LIVE")
    return codes


def validate_promotion_readiness(
    request: StrategyPromotionRequest | None,
    policy: StrategyLifecyclePolicy | None = None,
) -> list[str]:
    codes: list[str] = []
    if request is None:
        codes.append("PROMOTION_MISSING_R038A_REF")
        codes.append("PROMOTION_MISSING_R038B_REF")
        codes.append("PROMOTION_MISSING_R038C_REF")
        codes.append("PROMOTION_NET_OF_COST_NOT_POSITIVE")
        codes.append("PROMOTION_REPLAY_NOT_COMPATIBLE")
        codes.append("PROMOTION_RISK_GATE_REPLAY_NOT_COMPATIBLE")
        codes.append("PROMOTION_MARKET_REALITY_NOT_COMPATIBLE")
        codes.append("PROMOTION_TAIWAN_CONSTRAINTS_MISSING")
        codes.append("PROMOTION_TTL_MISSING")
        codes.append("PROMOTION_EXPIRY_MISSING")
        codes.append("PROMOTION_ORDER_EXECUTION_ALLOWED_TRUE")
        return codes
    refs = request.validation_refs
    if refs is None:
        codes.append("PROMOTION_MISSING_R038A_REF")
        codes.append("PROMOTION_MISSING_R038B_REF")
        codes.append("PROMOTION_MISSING_R038C_REF")
        codes.append("PROMOTION_MISSING_VALIDATION_SNAPSHOT")
    else:
        if not refs.r038a_snapshot_ref:
            codes.append("PROMOTION_MISSING_R038A_REF")
        if not refs.r038b_snapshot_ref:
            codes.append("PROMOTION_MISSING_R038B_REF")
        if not refs.r038c_snapshot_ref:
            codes.append("PROMOTION_MISSING_R038C_REF")
        if not refs.validation_snapshot_version:
            codes.append("PROMOTION_MISSING_VALIDATION_SNAPSHOT")
        if refs.validation_expiry_ts:
            try:
                expiry = datetime.fromisoformat(refs.validation_expiry_ts)
                if expiry < datetime.now(timezone.utc):
                    codes.append("PROMOTION_VALIDATION_STALE")
            except Exception:
                codes.append("PROMOTION_VALIDATION_STALE")
        if not refs.all_passed():
            codes.append("PROMOTION_VALIDATION_NOT_ALL_PASSED")
    if not request.net_of_cost_positive:
        codes.append("PROMOTION_NET_OF_COST_NOT_POSITIVE")
    if not request.replay_compatible:
        codes.append("PROMOTION_REPLAY_NOT_COMPATIBLE")
    if not request.risk_gate_replay_compatible:
        codes.append("PROMOTION_RISK_GATE_REPLAY_NOT_COMPATIBLE")
    if not request.market_reality_compatible:
        codes.append("PROMOTION_MARKET_REALITY_NOT_COMPATIBLE")
    if not request.taiwan_constraints_acknowledged:
        codes.append("PROMOTION_TAIWAN_CONSTRAINTS_MISSING")
    if request.is_tradingview_only:
        codes.append("PROMOTION_TRADINGVIEW_ONLY")
    if request.strategy_ttl_days <= 0:
        codes.append("PROMOTION_TTL_MISSING")
    elif request.strategy_ttl_remaining_days <= 0:
        codes.append("PROMOTION_TTL_EXPIRED")
    if not request.promotion_expiry_ts:
        codes.append("PROMOTION_EXPIRY_MISSING")
    else:
        try:
            prom_expiry = datetime.fromisoformat(request.promotion_expiry_ts)
            if prom_expiry < datetime.now(timezone.utc):
                codes.append("PROMOTION_EXPIRY_EXPIRED")
        except Exception:
            codes.append("PROMOTION_EXPIRY_MISSING")
    if not request.no_live_order_path:
        codes.append("PROMOTION_BROKER_LIVE_PATH_PRESENT")
    if request.order_execution_allowed:
        codes.append("PROMOTION_ORDER_EXECUTION_ALLOWED_TRUE")
    if request.llm_approval_present and request.llm_approval_used_as_deterministic:
        codes.append("LLM_APPROVED_PROMOTION")
    if request.llm_approval_present and not request.deterministic_gate_result:
        codes.append("LLM_MISSING_LOCAL_DETERMINISTIC_GATE")
    return codes


def validate_live_promotion_boundary(
    request: StrategyPromotionRequest | None,
) -> list[str]:
    codes: list[str] = []
    if request is None:
        codes.append("PROMOTION_TO_LIVE_MISSING_HUMAN_APPROVAL")
        codes.append("PROMOTION_AUTO_LIVE_APPROVAL")
        codes.append("PROMOTION_AUTO_CAPITAL_INCREASE")
        return codes
    transition = request.requested_transition
    if transition in (
        PromotionTransition.PAPER_TO_LIVE_SMALL.value,
        PromotionTransition.LIVE_SMALL_TO_LIVE_NORMAL.value,
    ):
        if not request.human_approval_required:
            codes.append("PROMOTION_AUTO_LIVE_APPROVAL")
        elif not request.human_approval_received:
            codes.append("PROMOTION_TO_LIVE_MISSING_HUMAN_APPROVAL")
    if transition == PromotionTransition.CAPITAL_INCREASE.value:
        if not request.capital_increase_human_approved:
            codes.append("PROMOTION_CAPITAL_INCREASE_MISSING_HUMAN_APPROVAL")
    if request.live_core_logic_change:
        if not request.live_core_logic_change_human_approved:
            codes.append("PROMOTION_LIVE_CORE_LOGIC_CHANGE_MISSING_HUMAN_APPROVAL")
    return codes


def validate_downgrade_quarantine(
    signals: list[StrategyDowngradeSignal] | None,
    current_stage: str = "",
) -> list[str]:
    codes: list[str] = []
    if signals is None:
        return codes
    for sig in signals:
        if sig.signal_detected:
            if sig.signal_type in (
                DowngradeSignalType.DRAWDOWN_BREACH.value,
                DowngradeSignalType.NET_OF_COST_DECAY.value,
                DowngradeSignalType.MARKET_REALITY_FAILURE.value,
                DowngradeSignalType.VALIDATION_STALE.value,
                DowngradeSignalType.STRATEGY_TTL_EXPIRED.value,
                DowngradeSignalType.PROMOTION_EXPIRED.value,
                DowngradeSignalType.MANUAL_BLOCK.value,
                DowngradeSignalType.GOVERNANCE_BLOCK.value,
                DowngradeSignalType.CONSECUTIVE_LOSS_COOLDOWN.value,
                DowngradeSignalType.REGIME_MISMATCH.value,
            ):
                codes.append("DOWNGRADE_SIGNAL_IGNORED")
                if sig.signal_type == DowngradeSignalType.MARKET_REALITY_FAILURE.value:
                    codes.append("DOWNGRADE_MARKET_REALITY_FAILURE_PROMOTABLE")
                if sig.signal_type == DowngradeSignalType.VALIDATION_STALE.value:
                    codes.append("DOWNGRADE_STALE_STRATEGY_PROMOTABLE")
                if sig.signal_type == DowngradeSignalType.STRATEGY_TTL_EXPIRED.value:
                    codes.append("DOWNGRADE_TTL_EXPIRED_PROMOTABLE")
                if sig.signal_type in (
                    DowngradeSignalType.MANUAL_BLOCK.value,
                    DowngradeSignalType.GOVERNANCE_BLOCK.value,
                ):
                    codes.append("DOWNGRADE_GOVERNANCE_BLOCK_IGNORED")
                if sig.signal_type == DowngradeSignalType.REGIME_MISMATCH.value:
                    codes.append("DOWNGRADE_REGIME_MISMATCH_PROMOTABLE")
            if sig.signal_type == DowngradeSignalType.SLIPPAGE_DRIFT.value:
                if sig.signal_value > sig.threshold > 0:
                    codes.append("DOWNGRADE_SLIPPAGE_DRIFT_OVER_THRESHOLD")
            if sig.signal_type == DowngradeSignalType.FILL_RATE_DRIFT.value:
                if sig.signal_value > sig.threshold > 0:
                    codes.append("DOWNGRADE_FILL_RATE_DRIFT_OVER_THRESHOLD")
    return codes


def validate_strategy_ttl_freshness(
    validation_refs: StrategyValidationEvidenceRef | None,
    policy: StrategyLifecyclePolicy | None = None,
) -> list[str]:
    codes: list[str] = []
    if validation_refs is None:
        codes.append("STRATEGY_MISSING_TTL")
        codes.append("STRATEGY_MISSING_VALIDATION_TIMESTAMP")
        codes.append("STRATEGY_REVALIDATION_BEFORE_LIVE_MISSING")
        return codes
    freshness_days = DEFAULT_VALIDATION_FRESHNESS_DAYS
    if policy is not None:
        freshness_days = policy.validation_freshness_days
    if not validation_refs.validation_snapshot_ts:
        codes.append("STRATEGY_MISSING_VALIDATION_TIMESTAMP")
    else:
        try:
            snap_ts = datetime.fromisoformat(validation_refs.validation_snapshot_ts)
            age = (datetime.now(timezone.utc) - snap_ts).days
            if age > freshness_days:
                codes.append("STRATEGY_EXPIRED_VALIDATION")
        except Exception:
            codes.append("STRATEGY_MISSING_VALIDATION_TIMESTAMP")
    if validation_refs.validation_expiry_ts:
        try:
            exp_ts = datetime.fromisoformat(validation_refs.validation_expiry_ts)
            if exp_ts < datetime.now(timezone.utc):
                codes.append("STRATEGY_EXPIRED_VALIDATION")
        except Exception:
            codes.append("STRATEGY_MISSING_VALIDATION_TIMESTAMP")
    if policy is not None:
        if not policy.revalidation_required_before_live:
            codes.append("STRATEGY_REVALIDATION_BEFORE_LIVE_MISSING")
        if not policy.llm_cannot_approve_promotion:
            codes.append("LLM_APPROVED_PROMOTION")
        if not policy.llm_cannot_set_qty:
            codes.append("ALLOCATION_LLM_CONTROLS_QTY")
        if not policy.risk_gate_can_veto_allocation:
            codes.append("ALLOCATION_RISK_GATE_CANNOT_VETO")
    return codes


def validate_strategy_lifecycle_governance(
    entry: StrategyRegistryEntry | None = None,
    request: StrategyPromotionRequest | None = None,
    signals: list[StrategyDowngradeSignal] | None = None,
    policy: StrategyLifecyclePolicy | None = None,
) -> StrategyLifecycleValidationResult:
    input_id = entry.strategy_id if entry and entry.strategy_id else uuid.uuid4().hex[:16]
    result = StrategyLifecycleValidationResult(
        input_id=input_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    all_reason_codes: list[str] = []

    if policy is not None:
        if policy.human_approval_required_for_live:
            result.human_approval_required = True
        result.market_reality_required = policy.market_reality_required
        result.replay_required = policy.replay_required
        result.risk_gate_replay_required = policy.risk_gate_replay_required
        result.no_live_order_path = policy.no_live_order_path
        result.order_execution_allowed = policy.order_execution_allowed_default
        result.research_only_default = policy.research_only_default_for_new
        result.tradingview_only_rejected = policy.tradingview_only_rejected
        result.net_of_cost_required = policy.net_of_cost_required
        result.llm_cannot_approve_promotion = policy.llm_cannot_approve_promotion
        result.llm_cannot_set_qty = policy.llm_cannot_set_qty
        result.risk_gate_can_veto_allocation = policy.risk_gate_can_veto_allocation

    if entry is not None:
        result.strategy_id = entry.strategy_id
        result.strategy_version = entry.strategy_version
        result.current_stage = entry.current_stage
        result.registry_entry_valid = len(validate_strategy_registry_entry(entry)) == 0

    registry_codes = validate_strategy_registry_entry(entry)
    all_reason_codes.extend(registry_codes)

    if entry is not None:
        new_strategy_codes = validate_new_strategy_defaults(entry)
        all_reason_codes.extend(new_strategy_codes)

    if request is not None:
        result.strategy_id = request.strategy_id
        result.strategy_version = request.strategy_version
        result.current_stage = request.current_stage
        result.requested_transition = request.requested_transition
        refs = request.validation_refs
        if refs is not None:
            result.validation_refs_present = refs.is_complete()
        prom_codes = validate_promotion_readiness(request, policy)
        all_reason_codes.extend(prom_codes)
        live_boundary_codes = validate_live_promotion_boundary(request)
        all_reason_codes.extend(live_boundary_codes)

    downgrade_codes = validate_downgrade_quarantine(signals, entry.current_stage if entry else "")
    all_reason_codes.extend(downgrade_codes)

    ttl_codes = validate_strategy_ttl_freshness(
        entry.validation_refs if entry else None, policy,
    )
    all_reason_codes.extend(ttl_codes)

    has_fail_closed = bool(all_reason_codes)
    result.reason_codes = all_reason_codes
    result.validation_passed = not has_fail_closed
    result.fail_closed = has_fail_closed
    result.transition_allowed = not has_fail_closed
    result.order_execution_allowed = False

    if request is not None and result.transition_allowed:
        result.promotion_target = request.requested_transition

    return result


def run_r038d_strategy_lifecycle(
    entry: StrategyRegistryEntry | None = None,
    request: StrategyPromotionRequest | None = None,
    signals: list[StrategyDowngradeSignal] | None = None,
    policy: StrategyLifecyclePolicy | None = None,
) -> dict[str, Any]:
    result = validate_strategy_lifecycle_governance(entry, request, signals, policy)
    return result.to_dict()
