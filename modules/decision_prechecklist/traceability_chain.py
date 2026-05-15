from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class TraceabilityLink:
    link_id: str
    trace_id: str
    symbol: str
    side: str
    final_decision: str
    timestamp: str
    previous_link_hash: str
    link_hash: str
    chain_index: int
    total_steps: int
    veto_count: int
    details: dict[str, Any] = field(default_factory=dict)
    order_ref: str = ""
    fill_ref: str = ""
    pnl_ref: str = ""

    def verify_hash(self) -> bool:
        computed = self._compute_hash(ignore_hash=True)
        return computed == self.link_hash

    def _compute_hash(self, ignore_hash: bool = False) -> str:
        payload = {
            "link_id": self.link_id,
            "trace_id": self.trace_id,
            "symbol": self.symbol,
            "side": self.side,
            "final_decision": self.final_decision,
            "timestamp": self.timestamp,
            "previous_link_hash": self.previous_link_hash,
            "chain_index": self.chain_index,
            "total_steps": self.total_steps,
            "veto_count": self.veto_count,
            "order_ref": self.order_ref,
            "fill_ref": self.fill_ref,
            "pnl_ref": self.pnl_ref,
            "details": self.details,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


@dataclass
class ChainVerificationResult:
    valid: bool
    total_links: int
    broken_at: int
    errors: list[str] = field(default_factory=list)


class TraceabilityChain:
    def __init__(self, chain_id: str | None = None):
        self._chain_id = chain_id or uuid_str()
        self._links: list[TraceabilityLink] = []
        self._last_hash = ""

    @property
    def chain_id(self) -> str:
        return self._chain_id

    @property
    def links(self) -> list[TraceabilityLink]:
        return list(self._links)

    @property
    def last_hash(self) -> str:
        return self._last_hash

    def add_link(
        self,
        trace_id: str,
        symbol: str,
        side: str,
        final_decision: str,
        total_steps: int,
        veto_count: int,
        timestamp: str | None = None,
        order_ref: str = "",
        fill_ref: str = "",
        pnl_ref: str = "",
        details: dict[str, Any] | None = None,
    ) -> TraceabilityLink:
        chain_index = len(self._links)
        link_id = f"{self._chain_id}-L{chain_index:04d}"
        ts = timestamp or datetime.now(timezone.utc).isoformat()

        link = TraceabilityLink(
            link_id=link_id,
            trace_id=trace_id,
            symbol=symbol,
            side=side,
            final_decision=final_decision,
            timestamp=ts,
            previous_link_hash=self._last_hash,
            link_hash="",
            chain_index=chain_index,
            total_steps=total_steps,
            veto_count=veto_count,
            order_ref=order_ref,
            fill_ref=fill_ref,
            pnl_ref=pnl_ref,
            details=details or {},
        )

        link.link_hash = link._compute_hash()
        self._links.append(link)
        self._last_hash = link.link_hash
        return link

    def verify_chain(self) -> ChainVerificationResult:
        errors: list[str] = []
        previous = ""

        for i, link in enumerate(self._links):
            if link.previous_link_hash != previous:
                errors.append(
                    f"link[{i}] hash chain broken: "
                    f"expected prev={previous[:16]}..., "
                    f"got {link.previous_link_hash[:16]}..."
                )
                return ChainVerificationResult(
                    valid=False, total_links=len(self._links), broken_at=i, errors=errors
                )
            if not link.verify_hash():
                errors.append(
                    f"link[{i}] self-hash invalid: "
                    f"computed != stored"
                )
                return ChainVerificationResult(
                    valid=False, total_links=len(self._links), broken_at=i, errors=errors
                )
            previous = link.link_hash

        return ChainVerificationResult(
            valid=True, total_links=len(self._links), broken_at=-1, errors=[]
        )

    def export_jsonl(self) -> str:
        lines = [json.dumps(asdict(link), ensure_ascii=False) for link in self._links]
        return "\n".join(lines)

    def import_jsonl(self, jsonl: str) -> None:
        self._links = []
        self._last_hash = ""
        for line in jsonl.strip().split("\n"):
            if not line.strip():
                continue
            data = json.loads(line)
            self._links.append(TraceabilityLink(**data))
        if self._links:
            self._last_hash = self._links[-1].link_hash

    def clear(self) -> None:
        self._links = []
        self._last_hash = ""


def uuid_str() -> str:
    import uuid
    return uuid.uuid4().hex[:16]
