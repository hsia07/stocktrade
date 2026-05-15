from __future__ import annotations
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
