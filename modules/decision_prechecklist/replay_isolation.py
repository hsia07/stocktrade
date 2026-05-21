from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExecutionMode(Enum):
    LIVE = "live"
    REPLAY = "replay"
    SIMULATION = "simulation"
    BACKTEST = "backtest"
    AUDIT = "audit"

    @classmethod
    def _missing_(cls, value: object) -> ExecutionMode | None:
        return None


def validate_mode(value: Any) -> ExecutionMode | None:
    if isinstance(value, ExecutionMode):
        return value
    if isinstance(value, str):
        try:
            return ExecutionMode(value.lower())
        except (ValueError, AttributeError):
            return None
    if value is None:
        return None
    return None


NON_LIVE_MODES = frozenset({
    ExecutionMode.REPLAY,
    ExecutionMode.SIMULATION,
    ExecutionMode.BACKTEST,
    ExecutionMode.AUDIT,
})


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

    @property
    def is_non_live(self) -> bool:
        return self.mode in NON_LIVE_MODES


@dataclass
class IsolationCheckResult:
    allowed: bool
    reason: str = ""
    reason_code: str = ""
    mode: str = ""
    target: str = ""
    isolation_violation_reason: str = ""


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

    def enter_backtest(self) -> IsolationContext:
        ctx = IsolationContext(mode=ExecutionMode.BACKTEST, isolated=True)
        self._context_stack.append(ctx)
        return ctx

    def enter_audit(self) -> IsolationContext:
        ctx = IsolationContext(mode=ExecutionMode.AUDIT, isolated=True)
        self._context_stack.append(ctx)
        return ctx

    def enter_simulation(self) -> IsolationContext:
        ctx = IsolationContext(mode=ExecutionMode.SIMULATION, isolated=True)
        self._context_stack.append(ctx)
        return ctx

    def exit(self) -> None:
        if self._context_stack:
            self._context_stack.pop()

    def _current_mode(self) -> ExecutionMode | None:
        ctx = self.current_context
        if ctx is None:
            return None
        return ctx.mode

    def _blocked_result(self, reason: str, reason_code: str, target: str) -> IsolationCheckResult:
        mode_str = self._current_mode().value if self._current_mode() else "NONE"
        return IsolationCheckResult(
            allowed=False,
            reason=reason,
            reason_code=reason_code,
            mode=mode_str,
            target=target,
            isolation_violation_reason=f"mode={mode_str} target={target} reason={reason_code}",
        )

    def _allowed_result(self, target: str = "") -> IsolationCheckResult:
        mode_str = self._current_mode().value if self._current_mode() else "NONE"
        return IsolationCheckResult(
            allowed=True,
            reason="allowed",
            reason_code="ALLOWED",
            mode=mode_str,
            target=target,
            isolation_violation_reason="",
        )

    def check_store_access(self, store_name: str) -> IsolationCheckResult:
        mode = self._current_mode()
        if mode is None:
            return self._blocked_result(
                "no active context — fail-closed",
                "MODE_CONTEXT_MISSING",
                f"store:{store_name}",
            )
        if mode == ExecutionMode.LIVE:
            return self._allowed_result(target=f"store:{store_name}")
        if store_name in ISOLATED_STORE_NAMES:
            return self._blocked_result(
                f"{mode.value} mode blocked access to live store '{store_name}'. "
                f"Use {mode.value}-isolated store instead.",
                "ISOLATED_STORE_BLOCKED",
                f"store:{store_name}",
            )
        return self._allowed_result(target=f"store:{store_name}")

    def isolate_store_name(self, store_name: str) -> str:
        ctx = self.current_context
        if ctx and ctx.is_non_live and store_name in ISOLATED_STORE_NAMES:
            return f"{ctx.mode.value}_{store_name}"
        return store_name

    def is_in_replay(self) -> bool:
        ctx = self.current_context
        return ctx is not None and ctx.is_replay

    def is_non_live_mode(self) -> bool:
        ctx = self.current_context
        return ctx is not None and ctx.is_non_live

    def assert_can_call_broker(self, target: str = "") -> IsolationCheckResult:
        mode = self._current_mode()
        if mode is None:
            return self._blocked_result(
                "no active context — fail-closed, broker call blocked",
                "BROKER_CALL_MODE_CONTEXT_MISSING",
                f"broker:{target}",
            )
        if mode == ExecutionMode.LIVE:
            return self._allowed_result(target=f"broker:{target}")
        return self._blocked_result(
            f"{mode.value} mode blocked broker API call to '{target}'",
            "BROKER_CALL_BLOCKED_BY_MODE",
            f"broker:{target}",
        )

    def assert_can_place_order(self, target: str = "") -> IsolationCheckResult:
        mode = self._current_mode()
        if mode is None:
            return self._blocked_result(
                "no active context — fail-closed, order placement blocked",
                "ORDER_PLACEMENT_MODE_CONTEXT_MISSING",
                f"order:{target}",
            )
        if mode == ExecutionMode.LIVE:
            return self._allowed_result(target=f"order:{target}")
        return self._blocked_result(
            f"{mode.value} mode blocked order placement for '{target}'",
            "ORDER_PLACEMENT_BLOCKED_BY_MODE",
            f"order:{target}",
        )

    def assert_can_write_runtime_state(self, path: str = "") -> IsolationCheckResult:
        mode = self._current_mode()
        if mode is None:
            return self._blocked_result(
                "no active context — fail-closed, runtime state write blocked",
                "RUNTIME_STATE_WRITE_MODE_CONTEXT_MISSING",
                f"runtime_state:{path}",
            )
        if mode == ExecutionMode.LIVE:
            return self._allowed_result(target=f"runtime_state:{path}")
        return self._blocked_result(
            f"{mode.value} mode blocked runtime state write to '{path}'",
            "RUNTIME_STATE_WRITE_BLOCKED_BY_MODE",
            f"runtime_state:{path}",
        )

    def assert_can_write_live_db(self, table: str = "") -> IsolationCheckResult:
        mode = self._current_mode()
        if mode is None:
            return self._blocked_result(
                "no active context — fail-closed, live DB write blocked",
                "DB_LIVE_WRITE_MODE_CONTEXT_MISSING",
                f"db:{table}",
            )
        if mode == ExecutionMode.LIVE:
            return self._allowed_result(target=f"db:{table}")
        return self._blocked_result(
            f"{mode.value} mode blocked live DB write to '{table}'",
            "DB_LIVE_WRITE_BLOCKED_BY_MODE",
            f"db:{table}",
        )

    def assert_can_write_fill(self, fill_context: str = "") -> IsolationCheckResult:
        mode = self._current_mode()
        if mode is None:
            return self._blocked_result(
                "no active context — fail-closed, fill write blocked",
                "FILL_WRITE_MODE_CONTEXT_MISSING",
                f"fill:{fill_context}",
            )
        if mode == ExecutionMode.LIVE:
            return self._allowed_result(target=f"fill:{fill_context}")
        return self._blocked_result(
            f"{mode.value} mode blocked fill write for '{fill_context}'",
            "FILL_WRITE_BLOCKED_BY_MODE",
            f"fill:{fill_context}",
        )

    def assert_can_start_live_from_replay(self) -> IsolationCheckResult:
        mode = self._current_mode()
        if mode is None:
            return self._blocked_result(
                "no active context — fail-closed, cannot start live from unknown mode",
                "LIVE_START_FROM_UNKNOWN_MODE",
                "live_start",
            )
        if mode == ExecutionMode.LIVE:
            return self._allowed_result(target="live_start")
        return self._blocked_result(
            f"{mode.value} mode cannot start live execution — replay error must not fallback to live",
            "LIVE_START_BLOCKED_BY_NON_LIVE_MODE",
            "live_start",
        )

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
