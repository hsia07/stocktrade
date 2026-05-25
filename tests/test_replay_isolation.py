import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.decision_prechecklist.replay_isolation import (
    ReplayIsolationGate,
    ReplayStoreIsolator,
    IsolationContext,
    IsolationCheckResult,
    ExecutionMode,
    ISOLATED_STORE_NAMES,
    NON_LIVE_MODES,
    validate_mode,
)


def test_gate_initialization():
    gate = ReplayIsolationGate()
    assert gate.current_context is None
    assert not gate.is_in_replay()
    assert not gate.is_non_live_mode()


def test_enter_replay():
    gate = ReplayIsolationGate()
    ctx = gate.enter_replay(replay_trace_id="replay-001")
    assert ctx.mode == ExecutionMode.REPLAY
    assert ctx.isolated
    assert ctx.replay_trace_id == "replay-001"
    assert gate.is_in_replay()
    assert gate.is_non_live_mode()


def test_enter_live():
    gate = ReplayIsolationGate()
    ctx = gate.enter_live()
    assert ctx.mode == ExecutionMode.LIVE
    assert ctx.isolated
    assert not gate.is_in_replay()
    assert not gate.is_non_live_mode()


def test_enter_backtest():
    gate = ReplayIsolationGate()
    ctx = gate.enter_backtest()
    assert ctx.mode == ExecutionMode.BACKTEST
    assert ctx.isolated
    assert not gate.is_in_replay()
    assert gate.is_non_live_mode()


def test_enter_audit():
    gate = ReplayIsolationGate()
    ctx = gate.enter_audit()
    assert ctx.mode == ExecutionMode.AUDIT
    assert ctx.isolated
    assert not gate.is_in_replay()
    assert gate.is_non_live_mode()


def test_enter_simulation():
    gate = ReplayIsolationGate()
    ctx = gate.enter_simulation()
    assert ctx.mode == ExecutionMode.SIMULATION
    assert ctx.isolated
    assert not gate.is_in_replay()
    assert gate.is_non_live_mode()


def test_exit():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    assert gate.is_in_replay()
    gate.exit()
    assert gate.current_context is None
    assert not gate.is_non_live_mode()


def test_exit_stack():
    gate = ReplayIsolationGate()
    gate.enter_live()
    gate.enter_replay(replay_trace_id="replay-001")
    assert gate.is_in_replay()
    gate.exit()
    assert not gate.is_in_replay()
    assert gate.current_context is not None
    assert gate.current_context.is_live


def test_check_store_access_live():
    gate = ReplayIsolationGate()
    gate.enter_live()
    for store in ISOLATED_STORE_NAMES:
        result = gate.check_store_access(store)
        assert result.allowed, f"store {store} should be allowed in live mode"
        assert result.reason_code == "ALLOWED"


def test_check_store_access_replay_blocks_isolated():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    for store in ISOLATED_STORE_NAMES:
        result = gate.check_store_access(store)
        assert not result.allowed, f"store {store} should be blocked in replay mode"
        assert "blocked" in result.reason
        assert result.reason_code == "ISOLATED_STORE_BLOCKED"
        assert result.isolation_violation_reason


def test_check_store_access_replay_allows_other():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    result = gate.check_store_access("market_data_cache")
    assert result.allowed
    assert result.reason_code == "ALLOWED"


def test_isolate_store_name_replay():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    isolated = gate.isolate_store_name("trades_log")
    assert isolated == "replay_trades_log"


def test_isolate_store_name_backtest():
    gate = ReplayIsolationGate()
    gate.enter_backtest()
    isolated = gate.isolate_store_name("trades_log")
    assert isolated == "backtest_trades_log"


def test_isolate_store_name_audit():
    gate = ReplayIsolationGate()
    gate.enter_audit()
    isolated = gate.isolate_store_name("trades_log")
    assert isolated == "audit_trades_log"


def test_isolate_store_name_live():
    gate = ReplayIsolationGate()
    gate.enter_live()
    isolated = gate.isolate_store_name("trades_log")
    assert isolated == "trades_log"


def test_isolate_store_name_no_context():
    gate = ReplayIsolationGate()
    isolated = gate.isolate_store_name("trades_log")
    assert isolated == "trades_log"


def test_isolate_store_name_non_isolated():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    isolated = gate.isolate_store_name("market_data_cache")
    assert isolated == "market_data_cache"


def test_isolator_initialization():
    isolator = ReplayStoreIsolator()
    assert isinstance(isolator.gate, ReplayIsolationGate)


def test_isolator_isolate_store():
    isolator = ReplayStoreIsolator()
    isolator.gate.enter_replay(replay_trace_id="replay-001")
    assert isolator.isolate_store("trades_log") == "replay_trades_log"
    assert isolator.isolate_store("market_data") == "market_data"


def test_clear():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    gate.enter_live()
    gate.clear()
    assert gate.current_context is None
    assert not gate.is_non_live_mode()


def test_isolation_context_properties():
    ctx = IsolationContext(mode=ExecutionMode.REPLAY, isolated=True)
    assert ctx.is_replay
    assert not ctx.is_live
    assert ctx.is_non_live
    ctx_live = IsolationContext(mode=ExecutionMode.LIVE, isolated=True)
    assert ctx_live.is_live
    assert not ctx_live.is_replay
    assert not ctx_live.is_non_live
    ctx_bt = IsolationContext(mode=ExecutionMode.BACKTEST, isolated=True)
    assert ctx_bt.is_non_live
    assert not ctx_bt.is_live
    ctx_au = IsolationContext(mode=ExecutionMode.AUDIT, isolated=True)
    assert ctx_au.is_non_live
    assert not ctx_au.is_live
    ctx_sim = IsolationContext(mode=ExecutionMode.SIMULATION, isolated=True)
    assert ctx_sim.is_non_live
    assert not ctx_sim.is_live


def test_isolation_check_result():
    result = IsolationCheckResult(allowed=False, reason="blocked", reason_code="BLOCKED")
    assert not result.allowed
    assert result.reason == "blocked"
    assert result.reason_code == "BLOCKED"


def test_enter_replay_with_original():
    gate = ReplayIsolationGate()
    ctx = gate.enter_replay(replay_trace_id="replay-002", original_trace_id="live-001")
    assert ctx.original_trace_id == "live-001"
    assert ctx.replay_trace_id == "replay-002"


def test_validate_mode():
    assert validate_mode(ExecutionMode.LIVE) == ExecutionMode.LIVE
    assert validate_mode(ExecutionMode.REPLAY) == ExecutionMode.REPLAY
    assert validate_mode("live") == ExecutionMode.LIVE
    assert validate_mode("replay") == ExecutionMode.REPLAY
    assert validate_mode("backtest") == ExecutionMode.BACKTEST
    assert validate_mode("audit") == ExecutionMode.AUDIT
    assert validate_mode("simulation") == ExecutionMode.SIMULATION
    assert validate_mode("UNKNOWN") is None
    assert validate_mode("") is None
    assert validate_mode(None) is None
    assert validate_mode(123) is None


def test_non_live_modes():
    assert ExecutionMode.REPLAY in NON_LIVE_MODES
    assert ExecutionMode.SIMULATION in NON_LIVE_MODES
    assert ExecutionMode.BACKTEST in NON_LIVE_MODES
    assert ExecutionMode.AUDIT in NON_LIVE_MODES
    assert ExecutionMode.LIVE not in NON_LIVE_MODES


def test_assert_can_place_order_replay_blocked():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    result = gate.assert_can_place_order(target="2330.TW:Buy")
    assert not result.allowed
    assert result.reason_code == "ORDER_PLACEMENT_BLOCKED_BY_MODE"
    assert "replay" in result.reason
    assert result.mode == "replay"
    assert result.target == "order:2330.TW:Buy"
    assert result.isolation_violation_reason


def test_assert_can_place_order_backtest_blocked():
    gate = ReplayIsolationGate()
    gate.enter_backtest()
    result = gate.assert_can_place_order(target="2330.TW:Sell")
    assert not result.allowed
    assert result.reason_code == "ORDER_PLACEMENT_BLOCKED_BY_MODE"


def test_assert_can_place_order_audit_blocked():
    gate = ReplayIsolationGate()
    gate.enter_audit()
    result = gate.assert_can_place_order(target="2330.TW:Buy")
    assert not result.allowed


def test_assert_can_place_order_simulation_blocked():
    gate = ReplayIsolationGate()
    gate.enter_simulation()
    result = gate.assert_can_place_order(target="2330.TW:Buy")
    assert not result.allowed


def test_assert_can_place_order_live_allowed():
    gate = ReplayIsolationGate()
    gate.enter_live()
    result = gate.assert_can_place_order(target="2330.TW:Buy")
    assert result.allowed
    assert result.reason_code == "ALLOWED"


def test_assert_can_call_broker_blocked():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    result = gate.assert_can_call_broker(target="shioaji")
    assert not result.allowed
    assert result.reason_code == "BROKER_CALL_BLOCKED_BY_MODE"
    assert result.mode == "replay"


def test_assert_can_call_broker_live_allowed():
    gate = ReplayIsolationGate()
    gate.enter_live()
    result = gate.assert_can_call_broker(target="shioaji")
    assert result.allowed


def test_assert_can_write_runtime_state_blocked():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    result = gate.assert_can_write_runtime_state(path="positions")
    assert not result.allowed
    assert result.reason_code == "RUNTIME_STATE_WRITE_BLOCKED_BY_MODE"


def test_assert_can_write_runtime_state_live_allowed():
    gate = ReplayIsolationGate()
    gate.enter_live()
    result = gate.assert_can_write_runtime_state(path="positions")
    assert result.allowed


def test_assert_can_write_live_db_blocked():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    result = gate.assert_can_write_live_db(table="trades_log")
    assert not result.allowed
    assert result.reason_code == "DB_LIVE_WRITE_BLOCKED_BY_MODE"


def test_assert_can_write_live_db_live_allowed():
    gate = ReplayIsolationGate()
    gate.enter_live()
    result = gate.assert_can_write_live_db(table="trades_log")
    assert result.allowed


def test_assert_can_write_fill_blocked():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    result = gate.assert_can_write_fill(fill_context="FILL-001")
    assert not result.allowed
    assert result.reason_code == "FILL_WRITE_BLOCKED_BY_MODE"


def test_assert_can_write_fill_live_allowed():
    gate = ReplayIsolationGate()
    gate.enter_live()
    result = gate.assert_can_write_fill(fill_context="FILL-001")
    assert result.allowed


def test_assert_can_start_live_from_replay_blocked():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    result = gate.assert_can_start_live_from_replay()
    assert not result.allowed
    assert result.reason_code == "LIVE_START_BLOCKED_BY_NON_LIVE_MODE"


def test_assert_can_start_live_from_live_allowed():
    gate = ReplayIsolationGate()
    gate.enter_live()
    result = gate.assert_can_start_live_from_replay()
    assert result.allowed


# ── R033: veto replay enforcement ──

def test_check_veto_replay_blocks_trade_allowed():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="r1")
    original_vetos = [{"gate": "risk", "reason_code": "max_loss", "detail": "stop"}]
    result = gate.check_veto_replay(original_vetos, replayed_trade_allowed=True)
    assert not result.allowed
    assert result.reason_code == "VETO_REPLAY_MISMATCH"


def test_check_veto_replay_allows_consistent_veto():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="r1")
    original_vetos = [{"gate": "risk", "reason_code": "max_loss", "detail": "stop"}]
    result = gate.check_veto_replay(original_vetos, replayed_trade_allowed=False)
    assert result.allowed
    assert result.reason_code == "VETO_REPLAY_CONSISTENT"


def test_check_veto_replay_no_veto_allows_trade():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="r1")
    result = gate.check_veto_replay([], replayed_trade_allowed=True)
    assert result.allowed


def test_check_veto_replay_no_context_returns_mode_none():
    gate = ReplayIsolationGate()
    result = gate.check_veto_replay([], replayed_trade_allowed=False)
    assert result.mode == "NONE"


# ── R033: as-of guard ──

def test_as_of_guard_decision_ts_before_tradable_ts():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="r1")
    result = gate.check_as_of_guard(
        decision_ts="2025-01-01T09:00:00",
        tradable_ts="2025-01-01T10:00:00",
    )
    assert not result.allowed
    assert result.reason_code == "DECISION_TS_BEFORE_TRADABLE_TS"


def test_as_of_guard_future_leak_source_after_decision():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="r1")
    result = gate.check_as_of_guard(
        decision_ts="2025-01-01T09:00:00",
        source_ts="2025-01-01T10:00:00",
    )
    assert not result.allowed
    assert "FUTURE_LEAK" in result.reason_code


def test_as_of_guard_future_leak_publish_after_decision():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="r1")
    result = gate.check_as_of_guard(
        decision_ts="2025-01-01T09:00:00",
        publish_ts="2025-01-01T10:00:00",
    )
    assert not result.allowed
    assert "FUTURE_LEAK" in result.reason_code


def test_as_of_guard_future_leak_ingest_after_decision():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="r1")
    result = gate.check_as_of_guard(
        decision_ts="2025-01-01T09:00:00",
        ingest_ts="2025-01-01T10:00:00",
    )
    assert not result.allowed
    assert "FUTURE_LEAK" in result.reason_code


def test_as_of_guard_passes_valid_timestamps():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="r1")
    result = gate.check_as_of_guard(
        decision_ts="2025-01-01T10:00:00",
        tradable_ts="2025-01-01T09:00:00",
        source_ts="2025-01-01T08:00:00",
        publish_ts="2025-01-01T08:30:00",
        ingest_ts="2025-01-01T08:45:00",
    )
    assert result.allowed
    assert result.reason_code == "AS_OF_GUARD_PASSED"


def test_as_of_guard_empty_timestamps_passes():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="r1")
    result = gate.check_as_of_guard()
    assert result.allowed


def test_as_of_guard_no_context():
    gate = ReplayIsolationGate()
    result = gate.check_as_of_guard(
        decision_ts="2025-01-01T09:00:00",
        tradable_ts="2025-01-01T10:00:00",
    )
    assert not result.allowed
    assert result.reason_code == "DECISION_TS_BEFORE_TRADABLE_TS"


# ── R033: replay live write blocking ──

def test_check_replay_live_write_blocked():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="r1")
    result = gate.check_replay_live_write(target="live_state")
    assert not result.allowed
    assert "LIVE_WRITE" in result.reason_code


def test_check_replay_live_write_allowed_in_live():
    gate = ReplayIsolationGate()
    gate.enter_live()
    result = gate.check_replay_live_write(target="live_state")
    assert result.allowed


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
