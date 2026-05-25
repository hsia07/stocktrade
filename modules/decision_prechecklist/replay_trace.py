from __future__ import annotations
import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DiffReasonCode(str, Enum):
    DECISION_CHANGED = "decision_changed"
    VETO_IGNORED_IN_REPLAY = "veto_ignored_in_replay"
    VETO_ADDED_IN_REPLAY = "veto_added_in_replay"
    VETO_REMOVED_IN_REPLAY = "veto_removed_in_replay"
    MARKET_REALITY_SNAPSHOT_CHANGED = "market_reality_snapshot_changed"
    MARKET_REALITY_SNAPSHOT_MISSING = "market_reality_snapshot_missing"
    TAIWAN_CONSTRAINTS_CHANGED = "taiwan_constraints_changed"
    TAIWAN_CONSTRAINTS_MISSING = "taiwan_constraints_missing"
    CONFIDENCE_RAW_USED_AS_TRADE_SIGNAL = "confidence_raw_used_as_trade_signal"
    CONFIDENCE_CALIBRATION_CHANGED = "confidence_calibration_changed"
    AS_OF_VIOLATION = "as_of_violation"
    FUTURE_LEAK_DETECTED = "future_leak_detected"
    DECISION_TS_BEFORE_TRADABLE_TS = "decision_ts_before_tradable_ts"
    STALE_DATA_DETECTED = "stale_data_detected"
    FIELD_CHANGED = "field_changed"
    STEP_ADDED = "step_added"
    STEP_REMOVED = "step_removed"
    STEP_CHANGED = "step_changed"
    AI_OPINION_CHANGED = "ai_opinion_changed"
    AI_OPINION_VETO_IGNORED = "ai_opinion_veto_ignored"
    RISK_SNAPSHOT_CHANGED = "risk_snapshot_changed"
    MISSING_TRACE_ID = "missing_trace_id"
    MISSING_FINAL_DECISION = "missing_final_decision"
    MISSING_MARKET_REALITY_SNAPSHOT = "missing_market_reality_snapshot"
    ORDER_EXECUTION_ATTEMPTED = "order_execution_attempted"
    BROKER_CALL_ATTEMPTED = "broker_call_attempted"
    LIVE_STATE_WRITE_ATTEMPTED = "live_state_write_attempted"
    REPLAY_OUTPUT_NOT_APPEND_ONLY = "replay_output_not_append_only"


@dataclass
class VetoRecord:
    gate: str
    reason_code: str
    detail: str


@dataclass
class DecisionStep:
    step_name: str
    result: str
    detail: str


@dataclass
class ReplayTrace:
    trace_id: str
    symbol: str
    side: str
    candidate_action: str
    timestamp: str
    decision_chain: list[DecisionStep] = field(default_factory=list)
    risk_snapshot: dict[str, Any] = field(default_factory=dict)
    market_reality_snapshot: dict[str, Any] = field(default_factory=dict)
    threshold_config_version: str = ""
    final_decision: str = ""
    vetoes: list[VetoRecord] = field(default_factory=list)
    order_ref: str = ""
    fill_ref: str = ""
    pnl_ref: str = ""
    previous_trace_hash: str = ""
    chain_link_id: str = ""

    @classmethod
    def new(cls, symbol: str, side: str, candidate_action: str) -> ReplayTrace:
        return cls(
            trace_id=uuid.uuid4().hex[:16],
            symbol=symbol,
            side=side,
            candidate_action=candidate_action,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def add_step(self, step_name: str, result: str, detail: str = "") -> None:
        self.decision_chain.append(DecisionStep(step_name, result, detail))

    def add_veto(self, gate: str, reason_code: str, detail: str) -> None:
        self.vetoes.append(VetoRecord(gate, reason_code, detail))

    def finalize(self, decision: str) -> None:
        self.final_decision = decision

    def compute_trace_hash(self) -> str:
        payload = {
            "trace_id": self.trace_id,
            "symbol": self.symbol,
            "side": self.side,
            "candidate_action": self.candidate_action,
            "timestamp": self.timestamp,
            "final_decision": self.final_decision,
            "previous_trace_hash": self.previous_trace_hash,
            "chain_link_id": self.chain_link_id,
            "order_ref": self.order_ref,
            "fill_ref": self.fill_ref,
            "pnl_ref": self.pnl_ref,
            "vetoes": [asdict(v) for v in self.vetoes],
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReplayResult:
    trace_id: str
    original_record_hash: str
    replay_version: str
    replay_timestamp: str
    original_decision: str
    replayed_decision: str
    diff_summary: str
    diff_reason_codes: list[str]
    has_veto_replay_mismatch: bool
    has_as_of_violation: bool
    has_future_leak: bool
    confidence_labels: dict[str, str]
    market_reality_snapshot: dict[str, Any]
    taiwan_constraints: dict[str, Any]
    as_of_fields: dict[str, str]
    previous_replay_hash: str
    chain_link_id: str

    def compute_replay_hash(self) -> str:
        payload = {
            "trace_id": self.trace_id,
            "original_record_hash": self.original_record_hash,
            "original_decision": self.original_decision,
            "replayed_decision": self.replayed_decision,
            "diff_summary": self.diff_summary,
            "diff_reason_codes": sorted(self.diff_reason_codes),
            "replay_version": self.replay_version,
            "replay_timestamp": self.replay_timestamp,
            "has_veto_replay_mismatch": self.has_veto_replay_mismatch,
            "has_as_of_violation": self.has_as_of_violation,
            "has_future_leak": self.has_future_leak,
            "previous_replay_hash": self.previous_replay_hash,
            "chain_link_id": self.chain_link_id,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
