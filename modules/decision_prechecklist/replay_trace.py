from __future__ import annotations
import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


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
