from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
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

    def check_veto_replay(
        self,
        original_vetos: list[Any],
        replayed_trade_allowed: bool,
    ) -> IsolationCheckResult:
        mode = self._current_mode()
        mode_str = mode.value if mode else "NONE"
        has_veto = bool(original_vetos)
        if has_veto and replayed_trade_allowed:
            return IsolationCheckResult(
                allowed=False,
                reason="original veto present but replay produced trade_allowed=True",
                reason_code="VETO_REPLAY_MISMATCH",
                mode=mode_str,
                target="veto_replay",
                isolation_violation_reason="original veto must not become trade_allowed in replay",
            )
        return IsolationCheckResult(
            allowed=True,
            reason="veto replay consistent",
            reason_code="VETO_REPLAY_CONSISTENT",
            mode=mode_str,
            target="veto_replay",
            isolation_violation_reason="",
        )

    def check_as_of_guard(
        self,
        decision_ts: str = "",
        tradable_ts: str = "",
        source_ts: str = "",
        publish_ts: str = "",
        ingest_ts: str = "",
    ) -> IsolationCheckResult:
        mode = self._current_mode()
        mode_str = mode.value if mode else "NONE"

        def _parse(ts: str) -> datetime | None:
            if not ts:
                return None
            try:
                if ts.endswith("Z"):
                    ts = ts[:-1] + "+00:00"
                return datetime.fromisoformat(ts)
            except (ValueError, TypeError):
                return None

        dt_decision = _parse(decision_ts)
        dt_tradable = _parse(tradable_ts)
        dt_source = _parse(source_ts)
        dt_publish = _parse(publish_ts)
        dt_ingest = _parse(ingest_ts)

        if dt_decision and dt_tradable and dt_decision < dt_tradable:
            return IsolationCheckResult(
                allowed=False,
                reason=f"decision_ts ({decision_ts}) before tradable_ts ({tradable_ts})",
                reason_code="DECISION_TS_BEFORE_TRADABLE_TS",
                mode=mode_str,
                target="as_of_guard",
                isolation_violation_reason="decision timestamp cannot precede tradable timestamp",
            )

        if dt_decision:
            if dt_source and dt_source > dt_decision:
                return IsolationCheckResult(
                    allowed=False,
                    reason=f"source_ts ({source_ts}) after decision_ts ({decision_ts}) — future leak",
                    reason_code="FUTURE_LEAK_SOURCE_AFTER_DECISION",
                    mode=mode_str,
                    target="as_of_guard",
                    isolation_violation_reason="source data timestamp after decision indicates future data leak",
                )
            if dt_publish and dt_publish > dt_decision:
                return IsolationCheckResult(
                    allowed=False,
                    reason=f"publish_ts ({publish_ts}) after decision_ts ({decision_ts}) — future leak",
                    reason_code="FUTURE_LEAK_PUBLISH_AFTER_DECISION",
                    mode=mode_str,
                    target="as_of_guard",
                    isolation_violation_reason="publish timestamp after decision indicates future data leak",
                )
            if dt_ingest and dt_ingest > dt_decision:
                return IsolationCheckResult(
                    allowed=False,
                    reason=f"ingest_ts ({ingest_ts}) after decision_ts ({decision_ts}) — future leak",
                    reason_code="FUTURE_LEAK_INGEST_AFTER_DECISION",
                    mode=mode_str,
                    target="as_of_guard",
                    isolation_violation_reason="ingest timestamp after decision indicates future data leak",
                )

        return IsolationCheckResult(
            allowed=True,
            reason="as-of guard passed",
            reason_code="AS_OF_GUARD_PASSED",
            mode=mode_str,
            target="as_of_guard",
            isolation_violation_reason="",
        )

    def check_replay_live_write(
        self,
        target: str = "",
    ) -> IsolationCheckResult:
        mode = self._current_mode()
        if mode is None:
            return self._blocked_result(
                "no active context — fail-closed, live write blocked",
                "LIVE_WRITE_MODE_CONTEXT_MISSING",
                f"live_write:{target}",
            )
        if mode == ExecutionMode.LIVE:
            return self._allowed_result(target=f"live_write:{target}")
        return self._blocked_result(
            f"{mode.value} mode blocked live write to '{target}'",
            "LIVE_WRITE_BLOCKED_BY_MODE",
            f"live_write:{target}",
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
