from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExecutionMode(Enum):
    LIVE = "live"
    REPLAY = "replay"
    SIMULATION = "simulation"


@dataclass
class IsolationContext:
    mode: ExecutionMode
    original_trace_id: str = ""
    replay_trace_id: str = ""
    isolated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_live(self) -> bool:
        return self.mode == ExecutionMode.LIVE

    @property
    def is_replay(self) -> bool:
        return self.mode == ExecutionMode.REPLAY


@dataclass
class IsolationCheckResult:
    allowed: bool
    reason: str = ""


ISOLATED_STORE_NAMES = frozenset({
    "trades_log",
    "decision_log",
    "execution_orders",
    "pnl_records",
    "positions",
    "signal_history",
})


class ReplayIsolationGate:
    def __init__(self):
        self._context_stack: list[IsolationContext] = []

    @property
    def current_context(self) -> IsolationContext | None:
        if self._context_stack:
            return self._context_stack[-1]
        return None

    def enter_replay(self, replay_trace_id: str, original_trace_id: str = "") -> IsolationContext:
        ctx = IsolationContext(
            mode=ExecutionMode.REPLAY,
            original_trace_id=original_trace_id,
            replay_trace_id=replay_trace_id,
            isolated=True,
        )
        self._context_stack.append(ctx)
        return ctx

    def enter_live(self) -> IsolationContext:
        ctx = IsolationContext(mode=ExecutionMode.LIVE, isolated=True)
        self._context_stack.append(ctx)
        return ctx

    def exit(self) -> None:
        if self._context_stack:
            self._context_stack.pop()

    def check_store_access(self, store_name: str) -> IsolationCheckResult:
        ctx = self.current_context
        if ctx is None or ctx.is_live:
            return IsolationCheckResult(allowed=True)

        if store_name in ISOLATED_STORE_NAMES:
            return IsolationCheckResult(
                allowed=False,
                reason=(
                    f"replay mode blocked access to live store '{store_name}'. "
                    f"Use replay-isolated store instead."
                ),
            )

        return IsolationCheckResult(allowed=True)

    def isolate_store_name(self, store_name: str) -> str:
        ctx = self.current_context
        if ctx and ctx.is_replay and store_name in ISOLATED_STORE_NAMES:
            return f"replay_{store_name}"
        return store_name

    def is_in_replay(self) -> bool:
        ctx = self.current_context
        return ctx is not None and ctx.is_replay

    def clear(self) -> None:
        self._context_stack.clear()


class ReplayStoreIsolator:
    def __init__(self, gate: ReplayIsolationGate | None = None):
        self._gate = gate or ReplayIsolationGate()

    @property
    def gate(self) -> ReplayIsolationGate:
        return self._gate

    def isolate_store(self, store_name: str) -> str:
        check = self._gate.check_store_access(store_name)
        if not check.allowed:
            return self._gate.isolate_store_name(store_name)
        return store_name
