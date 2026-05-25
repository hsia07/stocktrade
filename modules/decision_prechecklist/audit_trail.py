from __future__ import annotations
import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


VALID_SCHEMA_VERSIONS = frozenset({"r032-v1"})
TRADE_ALLOWED_DECISIONS = frozenset({"EXECUTE", "REDUCE_SIZE", "WAIT"})
TRADE_BLOCKED_DECISIONS = frozenset({"BLOCKED", "ABORT", "NO_TRADE"})


@dataclass
class TraceIdentity:
    trace_id: str
    decision_id: str
    session_id: str
    strategy_id: str = ""
    strategy_version: str = ""
    config_version: str = ""
    threshold_version: str = ""
    created_at: str = ""
    decision_ts: str = ""

    @classmethod
    def new(cls, trace_id: str = "", decision_id: str = "", session_id: str = "default",
            strategy_id: str = "", strategy_version: str = "", config_version: str = "",
            threshold_version: str = "") -> "TraceIdentity":
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            trace_id=trace_id or uuid.uuid4().hex[:16],
            decision_id=decision_id or uuid.uuid4().hex[:8],
            session_id=session_id,
            strategy_id=strategy_id,
            strategy_version=strategy_version or "v1",
            config_version=config_version or "v1",
            threshold_version=threshold_version or "v1",
            created_at=now,
            decision_ts=now,
        )


@dataclass
class AIOpinion:
    ai_name: str
    claim: str = ""
    support: bool = False
    reject: bool = False
    veto: bool = False
    veto_reason: str = ""
    confidence: float = 0.0


@dataclass
class DecisionStep:
    step_name: str
    result: str
    detail: str = ""


@dataclass
class DecisionChain:
    final_decision: str = ""
    final_reason_code: str = ""
    event_inputs: list[str] = field(default_factory=list)
    signal_inputs: dict[str, float] = field(default_factory=dict)
    confidence_sources: dict[str, Any] = field(default_factory=dict)
    ai_opinions: list[AIOpinion] = field(default_factory=list)
    steps: list[DecisionStep] = field(default_factory=list)
    local_arbitrator_result: str = ""


@dataclass
class RiskVetoChain:
    risk_snapshot: dict[str, Any] = field(default_factory=dict)
    risk_gate_results: dict[str, str] = field(default_factory=dict)
    veto_reason_codes: list[str] = field(default_factory=list)
    veto_actor: str = ""
    veto_stage: str = ""
    no_trade_reason: str = ""
    reduce_size_reason: str = ""
    wait_confirmation_reason: str = ""

    def has_veto(self) -> bool:
        return any(r == "veto" for r in self.risk_gate_results.values()) or bool(self.veto_reason_codes)


@dataclass
class MarketRealitySnapshot:
    cost_model_version: str = ""
    slippage_model_version: str = ""
    liquidity_score: float = 0.0
    estimated_fill_probability: float = 0.0
    expected_cost: float = 0.0
    expected_slippage: float = 0.0
    expected_net_rr: float = 0.0
    market_session_state: str = ""
    limit_up_down_distance: float = 0.0
    execution_abort_reason: str = ""


@dataclass
class ReplayAuditLink:
    original_trace_id: str
    replay_trace_id: str
    original_record_hash: str
    replay_result_hash: str
    replay_version: str
    replay_timestamp: str
    original_decision: str
    replayed_decision: str
    diff_summary: str
    diff_reason_codes: list[str]
    status: str
    chain_link_id: str


@dataclass
class TaiwanMarketConstraints:
    limit_up_down_pct: float = 10.0
    t2_settlement_aware: bool = False
    auction_session_state: str = ""
    odd_lot_round_lot: str = ""
    halt_disposition_attention: str = ""
    liquidity_insufficiency: str = ""


@dataclass
class OrderFillPnlReview:
    order_intent_id: str = ""
    order_id: str = ""
    fill_id: str = ""
    position_effect: str = ""
    realized_pnl: float = 0.0
    review_id: str = ""
    replay_status: str = ""
    audit_status: str = ""

    def has_any_linkage(self) -> bool:
        return bool(self.order_id or self.fill_id or self.review_id)

    def has_complete_chain(self) -> bool:
        return bool(self.order_id and self.fill_id and self.review_id)


@dataclass
class DecisionAuditRecord:
    trace_identity: TraceIdentity
    decision_chain: DecisionChain
    risk_veto: RiskVetoChain
    market_reality: MarketRealitySnapshot
    taiwan_constraints: TaiwanMarketConstraints
    order_fill_pnl: OrderFillPnlReview
    schema_version: str = "r032-v1"
    append_only: bool = True
    immutable_after_write: bool = True
    correction_event_id: str = ""
    parent_trace_id: str = ""
    durable_storage_required: bool = True
    replay_compatible: bool = True
    record_hash: str = ""
    previous_record_hash: str = ""
    chain_index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DecisionAuditRecord":
        record = cls(
            trace_identity=TraceIdentity(**data["trace_identity"]),
            decision_chain=DecisionChain(
                event_inputs=data["decision_chain"].get("event_inputs", []),
                signal_inputs=data["decision_chain"].get("signal_inputs", {}),
                confidence_sources=data["decision_chain"].get("confidence_sources", {}),
                ai_opinions=[AIOpinion(**o) for o in data["decision_chain"].get("ai_opinions", [])],
                steps=[DecisionStep(**s) for s in data["decision_chain"].get("steps", [])],
                local_arbitrator_result=data["decision_chain"].get("local_arbitrator_result", ""),
                final_decision=data["decision_chain"].get("final_decision", ""),
                final_reason_code=data["decision_chain"].get("final_reason_code", ""),
            ),
            risk_veto=RiskVetoChain(**data["risk_veto"]),
            market_reality=MarketRealitySnapshot(**data["market_reality"]),
            taiwan_constraints=TaiwanMarketConstraints(**data["taiwan_constraints"]),
            order_fill_pnl=OrderFillPnlReview(**data["order_fill_pnl"]),
        )
        for f in ("schema_version", "append_only", "immutable_after_write",
                   "correction_event_id", "parent_trace_id", "durable_storage_required",
                   "replay_compatible", "record_hash", "previous_record_hash", "chain_index"):
            if f in data:
                setattr(record, f, data[f])
        return record


class DecisionAuditError(ValueError):
    pass


class ImmutableRecordError(PermissionError):
    pass


class AuditTrailChain:
    def __init__(self, chain_id: str | None = None):
        self._chain_id = chain_id or uuid.uuid4().hex[:16]
        self._records: list[DecisionAuditRecord] = []
        self._last_hash = ""

    @property
    def chain_id(self) -> str:
        return self._chain_id

    @property
    def records(self) -> list[DecisionAuditRecord]:
        return list(self._records)

    @property
    def last_hash(self) -> str:
        return self._last_hash

    @property
    def record_count(self) -> int:
        return len(self._records)

    @staticmethod
    def _compute_record_hash(record: DecisionAuditRecord) -> str:
        payload = {
            "trace_id": record.trace_identity.trace_id,
            "decision_id": record.trace_identity.decision_id,
            "final_decision": record.decision_chain.final_decision,
            "final_reason_code": record.decision_chain.final_reason_code,
            "schema_version": record.schema_version,
            "previous_record_hash": record.previous_record_hash,
            "chain_index": record.chain_index,
            "veto_count": len(record.risk_veto.veto_reason_codes),
            "timestamp": record.trace_identity.decision_ts,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _check_required_fields(record: DecisionAuditRecord) -> list[str]:
        errors = []
        if not record.trace_identity.trace_id:
            errors.append("missing_trace_id")
        if not record.trace_identity.decision_id:
            errors.append("missing_decision_id")
        if not record.decision_chain.final_decision:
            errors.append("missing_final_decision")
        if not record.decision_chain.final_reason_code:
            errors.append("missing_final_reason_code")
        return errors

    @staticmethod
    def _check_veto_invariant(record: DecisionAuditRecord) -> list[str]:
        errors = []
        if record.risk_veto.has_veto():
            if record.decision_chain.final_decision == "EXECUTE":
                errors.append("veto_trade_allowed_conflict")
        return errors

    @staticmethod
    def _check_raw_confidence_guard(record: DecisionAuditRecord) -> list[str]:
        errors = []
        cs = record.decision_chain.confidence_sources
        raw = cs.get("raw_confidence", None) if isinstance(cs, dict) else None
        if raw is not None and raw >= 0.95 and record.decision_chain.final_decision == "EXECUTE":
            has_chain_steps = bool(record.decision_chain.steps)
            has_risk_gates = bool(record.risk_veto.risk_gate_results)
            has_ai_opinions = bool(record.decision_chain.ai_opinions)
            if not has_chain_steps and not has_risk_gates and not has_ai_opinions:
                errors.append("raw_confidence_direct_trade_approval")
        return errors

    @staticmethod
    def _check_llm_approval_guard(record: DecisionAuditRecord) -> list[str]:
        errors = []
        for opinion in record.decision_chain.ai_opinions:
            if opinion.veto and record.decision_chain.final_decision == "EXECUTE":
                errors.append(f"llm_veto_ignored:{opinion.ai_name}")
        return errors

    @staticmethod
    def _check_schema_version(record: DecisionAuditRecord) -> list[str]:
        errors = []
        if record.schema_version not in VALID_SCHEMA_VERSIONS:
            errors.append(f"invalid_schema_version:{record.schema_version}")
        return errors

    @staticmethod
    def _check_missing_risk_snapshot(record: DecisionAuditRecord) -> list[str]:
        errors = []
        if not record.risk_veto.risk_snapshot:
            if record.decision_chain.final_decision:
                errors.append("missing_risk_snapshot_for_nonempty_decision")
        return errors

    @staticmethod
    def _check_taiwan_placeholders(record: DecisionAuditRecord) -> list[str]:
        errors = []
        tc = record.taiwan_constraints
        if tc.limit_up_down_pct <= 0:
            errors.append("taiwan_limit_up_down_missing")
        if not tc.auction_session_state:
            errors.append("taiwan_auction_session_missing")
        if not tc.odd_lot_round_lot:
            errors.append("taiwan_odd_lot_round_lot_missing")
        if not tc.halt_disposition_attention:
            errors.append("taiwan_halt_disposition_attention_missing")
        if not tc.liquidity_insufficiency:
            errors.append("taiwan_liquidity_insufficiency_missing")
        return errors

    @staticmethod
    def _check_market_reality_placeholders(record: DecisionAuditRecord) -> list[str]:
        errors = []
        mr = record.market_reality
        if not mr.cost_model_version:
            errors.append("cost_model_version_missing")
        if not mr.slippage_model_version:
            errors.append("slippage_model_version_missing")
        if not mr.market_session_state:
            errors.append("market_session_state_missing")
        return errors

    @staticmethod
    def _check_order_fill_pnl_linkage(record: DecisionAuditRecord) -> list[str]:
        errors = []
        ofp = record.order_fill_pnl
        if ofp.has_any_linkage() and not ofp.has_complete_chain():
            errors.append("order_fill_pnl_partial_linkage_no_complete_chain")
        return errors

    def validate_record(self, record: DecisionAuditRecord) -> list[str]:
        all_errors: list[str] = []
        all_errors.extend(self._check_required_fields(record))
        all_errors.extend(self._check_veto_invariant(record))
        all_errors.extend(self._check_raw_confidence_guard(record))
        all_errors.extend(self._check_llm_approval_guard(record))
        all_errors.extend(self._check_schema_version(record))
        all_errors.extend(self._check_missing_risk_snapshot(record))
        all_errors.extend(self._check_taiwan_placeholders(record))
        all_errors.extend(self._check_market_reality_placeholders(record))
        all_errors.extend(self._check_order_fill_pnl_linkage(record))
        return all_errors

    def is_valid(self, record: DecisionAuditRecord) -> bool:
        return len(self.validate_record(record)) == 0

    def append(self, record: DecisionAuditRecord) -> DecisionAuditRecord:
        errors = self.validate_record(record)
        if errors:
            raise DecisionAuditError(f"Record validation failed: {', '.join(errors)}")
        record.chain_index = len(self._records)
        record.previous_record_hash = self._last_hash
        record.record_hash = self._compute_record_hash(record)
        self._records.append(record)
        self._last_hash = record.record_hash
        return record

    def append_correction(self, original_record: DecisionAuditRecord,
                          corrected_record: DecisionAuditRecord) -> DecisionAuditRecord:
        if original_record.immutable_after_write:
            raise ImmutableRecordError(
                "Cannot mutate an immutable append-only record. "
                "Use append_correction (creates new record linked to original)."
            )
        corrected_record.parent_trace_id = original_record.trace_identity.trace_id
        corrected_record.correction_event_id = original_record.trace_identity.decision_id
        return self.append(corrected_record)

    def verify_integrity(self) -> bool:
        previous = ""
        for i, rec in enumerate(self._records):
            expected = self._compute_record_hash(rec)
            if rec.record_hash != expected:
                return False
            if rec.previous_record_hash != previous:
                return False
            previous = rec.record_hash
        return True

    def verify_integrity_detailed(self) -> dict[str, Any]:
        previous = ""
        for i, rec in enumerate(self._records):
            expected = self._compute_record_hash(rec)
            if rec.record_hash != expected:
                return {"valid": False, "broken_at": i, "reason": "hash_mismatch", "total": len(self._records)}
            if rec.previous_record_hash != previous:
                return {"valid": False, "broken_at": i, "reason": "chain_break", "total": len(self._records)}
            previous = rec.record_hash
        return {"valid": True, "broken_at": -1, "reason": "", "total": len(self._records)}

    def export_jsonl(self) -> str:
        lines = [json.dumps(rec.to_dict(), ensure_ascii=False) for rec in self._records]
        return "\n".join(lines)

    def import_jsonl(self, jsonl: str) -> None:
        self._records = []
        self._last_hash = ""
        for line in jsonl.strip().split("\n"):
            if not line.strip():
                continue
            data = json.loads(line)
            rec = DecisionAuditRecord.from_dict(data)
            self._records.append(rec)
        if self._records:
            self._last_hash = self._records[-1].record_hash

    def replay(self, jsonl: str) -> list[DecisionAuditRecord]:
        self.import_jsonl(jsonl)
        return list(self._records)

    def clear(self) -> None:
        self._records = []
        self._last_hash = ""

    def get_by_trace_id(self, trace_id: str) -> list[DecisionAuditRecord]:
        return [r for r in self._records if r.trace_identity.trace_id == trace_id]

    def get_by_decision_id(self, decision_id: str) -> DecisionAuditRecord | None:
        for r in self._records:
            if r.trace_identity.decision_id == decision_id:
                return r
        return None

    def link_replay_result(
        self,
        replay_result_dict: dict[str, Any],
        original_record: DecisionAuditRecord | None = None,
    ) -> ReplayAuditLink:
        trace_id = replay_result_dict.get("trace_id", "")
        original_rec = original_record
        if original_rec is None:
            match = self.get_by_trace_id(trace_id)
            original_rec = match[0] if match else None

        link = ReplayAuditLink(
            original_trace_id=trace_id,
            replay_trace_id="",
            original_record_hash=replay_result_dict.get("original_record_hash", ""),
            replay_result_hash="",
            replay_version=replay_result_dict.get("replay_version", "r033-v1"),
            replay_timestamp=replay_result_dict.get("replay_timestamp", ""),
            original_decision=replay_result_dict.get("original_decision", ""),
            replayed_decision=replay_result_dict.get("replayed_decision", ""),
            diff_summary=replay_result_dict.get("diff_summary", ""),
            diff_reason_codes=replay_result_dict.get("diff_reason_codes", []),
            status="replay_linked",
            chain_link_id=f"{self._chain_id}-R{len(self._records):04d}",
        )
        return link


def create_decision_audit_record(
    trace_id: str = "",
    decision_id: str = "",
    session_id: str = "default",
    strategy_id: str = "",
    final_decision: str = "",
    final_reason_code: str = "",
    raw_confidence: float | None = None,
    ai_opinions: list[dict[str, Any]] | None = None,
    risk_gate_results: dict[str, str] | None = None,
    veto_reason_codes: list[str] | None = None,
    risk_snapshot: dict[str, Any] | None = None,
    market_session_state: str = "",
    auction_session_state: str = "continuous",
    limit_up_down_distance: float = 0.0,
    halt_disposition_attention: str = "none",
    liquidity_insufficiency: str = "none",
    order_id: str = "",
    fill_id: str = "",
    review_id: str = "",
) -> DecisionAuditRecord:
    tid = TraceIdentity.new(
        trace_id=trace_id,
        decision_id=decision_id,
        session_id=session_id,
        strategy_id=strategy_id,
    )
    opinions = [AIOpinion(**o) for o in (ai_opinions or [])]
    chain = DecisionChain(
        final_decision=final_decision,
        final_reason_code=final_reason_code,
        confidence_sources={"raw_confidence": raw_confidence} if raw_confidence is not None else {},
        ai_opinions=opinions,
    )
    rvc = RiskVetoChain(
        risk_snapshot=risk_snapshot or {},
        risk_gate_results=risk_gate_results or {},
        veto_reason_codes=veto_reason_codes or [],
    )
    mr = MarketRealitySnapshot(
        cost_model_version="r032-v1",
        slippage_model_version="r032-v1",
        market_session_state=market_session_state,
        limit_up_down_distance=limit_up_down_distance,
    )
    tc = TaiwanMarketConstraints(
        limit_up_down_pct=10.0,
        auction_session_state=auction_session_state,
        odd_lot_round_lot="round_lot" if auction_session_state != "odd_lot" else "odd_lot",
        halt_disposition_attention=halt_disposition_attention,
        liquidity_insufficiency=liquidity_insufficiency,
    )
    ofp = OrderFillPnlReview(
        order_id=order_id,
        fill_id=fill_id,
        review_id=review_id,
    )
    return DecisionAuditRecord(
        trace_identity=tid,
        decision_chain=chain,
        risk_veto=rvc,
        market_reality=mr,
        taiwan_constraints=tc,
        order_fill_pnl=ofp,
    )


def reject_mutation_or_overwrite(record: DecisionAuditRecord) -> bool:
    if record.immutable_after_write and record.append_only:
        raise ImmutableRecordError(
            "Cannot mutate immutable append-only record. "
            "Use AuditTrailChain.append_correction() to create a linked correction."
        )
    return True
