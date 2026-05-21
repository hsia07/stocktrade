import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from modules.decision_prechecklist.replay_isolation import (
    ReplayIsolationGate,
    ReplayStoreIsolator,
    IsolationCheckResult,
    ExecutionMode,
    validate_mode,
)


# ═══════════════════════════════════════════════════════════════
# A. Missing / Unknown / Malformed mode fail-closed
# ═══════════════════════════════════════════════════════════════

def test_no_context_order_placement_blocked():
    gate = ReplayIsolationGate()
    assert gate.current_context is None
    result = gate.assert_can_place_order(target="2330.TW:Buy")
    assert not result.allowed
    assert result.reason_code == "ORDER_PLACEMENT_MODE_CONTEXT_MISSING"
    assert result.isolation_violation_reason


def test_no_context_broker_call_blocked():
    gate = ReplayIsolationGate()
    result = gate.assert_can_call_broker(target="shioaji")
    assert not result.allowed
    assert result.reason_code == "BROKER_CALL_MODE_CONTEXT_MISSING"


def test_no_context_runtime_write_blocked():
    gate = ReplayIsolationGate()
    result = gate.assert_can_write_runtime_state(path="positions")
    assert not result.allowed
    assert result.reason_code == "RUNTIME_STATE_WRITE_MODE_CONTEXT_MISSING"


def test_no_context_db_write_blocked():
    gate = ReplayIsolationGate()
    result = gate.assert_can_write_live_db(table="trades_log")
    assert not result.allowed
    assert result.reason_code == "DB_LIVE_WRITE_MODE_CONTEXT_MISSING"


def test_no_context_fill_write_blocked():
    gate = ReplayIsolationGate()
    result = gate.assert_can_write_fill(fill_context="FILL-001")
    assert not result.allowed
    assert result.reason_code == "FILL_WRITE_MODE_CONTEXT_MISSING"


def test_no_context_live_start_blocked():
    gate = ReplayIsolationGate()
    result = gate.assert_can_start_live_from_replay()
    assert not result.allowed
    assert result.reason_code == "LIVE_START_FROM_UNKNOWN_MODE"


def test_no_context_store_access_blocked():
    gate = ReplayIsolationGate()
    result = gate.check_store_access("trades_log")
    assert not result.allowed
    assert result.reason_code == "MODE_CONTEXT_MISSING"


def test_validate_mode_rejects_invalid():
    assert validate_mode("INVALID") is None
    assert validate_mode("") is None
    assert validate_mode(None) is None
    assert validate_mode(123) is None
    assert validate_mode([]) is None


def test_execution_mode_missing_returns_none():
    try:
        m = ExecutionMode("nonexistent")
        assert m is None
    except ValueError:
        pass


# ═══════════════════════════════════════════════════════════════
# B. Replay / Backtest / Audit / Simulation mode guards
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("mode_name,enter_method,kwargs", [
    ("replay", "enter_replay", {"replay_trace_id": "t1"}),
    ("backtest", "enter_backtest", {}),
    ("audit", "enter_audit", {}),
    ("simulation", "enter_simulation", {}),
])
def test_all_non_live_modes_block_broker_call(mode_name, enter_method, kwargs):
    gate = ReplayIsolationGate()
    getattr(gate, enter_method)(**kwargs)
    result = gate.assert_can_call_broker(target="shioaji")
    assert not result.allowed, f"{mode_name} should block broker call"
    assert result.reason_code == "BROKER_CALL_BLOCKED_BY_MODE"


@pytest.mark.parametrize("mode_name,enter_method,kwargs", [
    ("replay", "enter_replay", {"replay_trace_id": "t1"}),
    ("backtest", "enter_backtest", {}),
    ("audit", "enter_audit", {}),
    ("simulation", "enter_simulation", {}),
])
def test_all_non_live_modes_block_order_placement(mode_name, enter_method, kwargs):
    gate = ReplayIsolationGate()
    getattr(gate, enter_method)(**kwargs)
    result = gate.assert_can_place_order(target="2330.TW:Buy")
    assert not result.allowed, f"{mode_name} should block order placement"
    assert result.reason_code == "ORDER_PLACEMENT_BLOCKED_BY_MODE"


@pytest.mark.parametrize("mode_name,enter_method,kwargs", [
    ("replay", "enter_replay", {"replay_trace_id": "t1"}),
    ("backtest", "enter_backtest", {}),
    ("audit", "enter_audit", {}),
    ("simulation", "enter_simulation", {}),
])
def test_all_non_live_modes_block_runtime_write(mode_name, enter_method, kwargs):
    gate = ReplayIsolationGate()
    getattr(gate, enter_method)(**kwargs)
    result = gate.assert_can_write_runtime_state(path="positions")
    assert not result.allowed, f"{mode_name} should block runtime write"
    assert result.reason_code == "RUNTIME_STATE_WRITE_BLOCKED_BY_MODE"


@pytest.mark.parametrize("mode_name,enter_method,kwargs", [
    ("replay", "enter_replay", {"replay_trace_id": "t1"}),
    ("backtest", "enter_backtest", {}),
    ("audit", "enter_audit", {}),
    ("simulation", "enter_simulation", {}),
])
def test_all_non_live_modes_block_db_write(mode_name, enter_method, kwargs):
    gate = ReplayIsolationGate()
    getattr(gate, enter_method)(**kwargs)
    result = gate.assert_can_write_live_db(table="execution_orders")
    assert not result.allowed, f"{mode_name} should block db write"
    assert result.reason_code == "DB_LIVE_WRITE_BLOCKED_BY_MODE"


@pytest.mark.parametrize("mode_name,enter_method,kwargs", [
    ("replay", "enter_replay", {"replay_trace_id": "t1"}),
    ("backtest", "enter_backtest", {}),
    ("audit", "enter_audit", {}),
    ("simulation", "enter_simulation", {}),
])
def test_all_non_live_modes_block_fill_write(mode_name, enter_method, kwargs):
    gate = ReplayIsolationGate()
    getattr(gate, enter_method)(**kwargs)
    result = gate.assert_can_write_fill(fill_context="FILL-001")
    assert not result.allowed, f"{mode_name} should block fill write"
    assert result.reason_code == "FILL_WRITE_BLOCKED_BY_MODE"


@pytest.mark.parametrize("mode_name,enter_method,kwargs", [
    ("replay", "enter_replay", {"replay_trace_id": "t1"}),
    ("backtest", "enter_backtest", {}),
    ("audit", "enter_audit", {}),
    ("simulation", "enter_simulation", {}),
])
def test_all_non_live_modes_block_live_start(mode_name, enter_method, kwargs):
    gate = ReplayIsolationGate()
    getattr(gate, enter_method)(**kwargs)
    result = gate.assert_can_start_live_from_replay()
    assert not result.allowed, f"{mode_name} should block live start"
    assert result.reason_code == "LIVE_START_BLOCKED_BY_NON_LIVE_MODE"


# ═══════════════════════════════════════════════════════════════
# C. Live mode respects guards (allowed)
# ═══════════════════════════════════════════════════════════════

def test_live_mode_allows_broker_call():
    gate = ReplayIsolationGate()
    gate.enter_live()
    result = gate.assert_can_call_broker(target="shioaji")
    assert result.allowed
    assert result.reason_code == "ALLOWED"


def test_live_mode_allows_order_placement():
    gate = ReplayIsolationGate()
    gate.enter_live()
    result = gate.assert_can_place_order(target="2330.TW:Buy")
    assert result.allowed


def test_live_mode_allows_runtime_write():
    gate = ReplayIsolationGate()
    gate.enter_live()
    result = gate.assert_can_write_runtime_state(path="positions")
    assert result.allowed


def test_live_mode_allows_db_write():
    gate = ReplayIsolationGate()
    gate.enter_live()
    result = gate.assert_can_write_live_db(table="trades_log")
    assert result.allowed


def test_live_mode_allows_fill_write():
    gate = ReplayIsolationGate()
    gate.enter_live()
    result = gate.assert_can_write_fill(fill_context="FILL-001")
    assert result.allowed


def test_live_mode_allows_live_start():
    gate = ReplayIsolationGate()
    gate.enter_live()
    result = gate.assert_can_start_live_from_replay()
    assert result.allowed


# ═══════════════════════════════════════════════════════════════
# D. IsolationCheckResult has reason_code / block_reason
# ═══════════════════════════════════════════════════════════════

def test_isolation_result_all_fields():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="t1")
    result = gate.assert_can_place_order(target="2330.TW:Buy")
    assert hasattr(result, "allowed")
    assert hasattr(result, "reason")
    assert hasattr(result, "reason_code")
    assert hasattr(result, "mode")
    assert hasattr(result, "target")
    assert hasattr(result, "isolation_violation_reason")
    assert result.mode == "replay"
    assert result.target == "order:2330.TW:Buy"


def test_isolation_result_reason_code_present():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="t1")
    for result in [
        gate.assert_can_call_broker(target="x"),
        gate.assert_can_place_order(target="x"),
        gate.assert_can_write_runtime_state(path="x"),
        gate.assert_can_write_live_db(table="x"),
        gate.assert_can_write_fill(fill_context="x"),
        gate.assert_can_start_live_from_replay(),
    ]:
        assert result.reason_code and not result.allowed, f"missing reason_code for {result}"


# ═══════════════════════════════════════════════════════════════
# E. Store isolation behavior with new modes
# ═══════════════════════════════════════════════════════════════

def test_backtest_store_access_blocked():
    gate = ReplayIsolationGate()
    gate.enter_backtest()
    for store in ["trades_log", "execution_orders", "pnl_records", "positions", "decision_log", "signal_history"]:
        result = gate.check_store_access(store)
        assert not result.allowed
        assert result.reason_code == "ISOLATED_STORE_BLOCKED"


def test_audit_store_access_blocked():
    gate = ReplayIsolationGate()
    gate.enter_audit()
    for store in ["trades_log", "execution_orders", "pnl_records", "positions", "decision_log", "signal_history"]:
        result = gate.check_store_access(store)
        assert not result.allowed
        assert result.reason_code == "ISOLATED_STORE_BLOCKED"


def test_simulation_store_access_blocked():
    gate = ReplayIsolationGate()
    gate.enter_simulation()
    for store in ["trades_log", "execution_orders", "pnl_records", "positions", "decision_log", "signal_history"]:
        result = gate.check_store_access(store)
        assert not result.allowed
        assert result.reason_code == "ISOLATED_STORE_BLOCKED"


def test_non_isolated_store_allowed_in_non_live():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="t1")
    result = gate.check_store_access("market_data_cache")
    assert result.allowed


# ═══════════════════════════════════════════════════════════════
# F. Mutation-style: removing the guard should fail tests
# ═══════════════════════════════════════════════════════════════

def test_mutation_guard_removal_broker_block_would_fail():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="t1")
    result = gate.assert_can_call_broker(target="shioaji")
    assert not result.allowed
    assert result.reason_code == "BROKER_CALL_BLOCKED_BY_MODE"


def test_mutation_guard_removal_order_block_would_fail():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="t1")
    with_non_live = gate.assert_can_place_order(target="2330.TW:Buy")
    assert not with_non_live.allowed
    gate.exit()
    gate.enter_live()
    with_live = gate.assert_can_place_order(target="2330.TW:Buy")
    assert with_live.allowed
    assert with_non_live.reason_code != with_live.reason_code


# ═══════════════════════════════════════════════════════════════
# G. ReplayStoreIsolator works with all modes
# ═══════════════════════════════════════════════════════════════

def test_isolator_backtest():
    isolator = ReplayStoreIsolator()
    isolator.gate.enter_backtest()
    assert isolator.isolate_store("trades_log") == "backtest_trades_log"
    assert isolator.isolate_store("market_data") == "market_data"


def test_isolator_audit():
    isolator = ReplayStoreIsolator()
    isolator.gate.enter_audit()
    assert isolator.isolate_store("trades_log") == "audit_trades_log"


def test_isolator_simulation():
    isolator = ReplayStoreIsolator()
    isolator.gate.enter_simulation()
    assert isolator.isolate_store("trades_log") == "simulation_trades_log"


# ═══════════════════════════════════════════════════════════════
# H. Server_v2 integration: check_pre_trade_isolation
# ═══════════════════════════════════════════════════════════════

def test_server_v2_imports_replay_isolation():
    from modules.decision_prechecklist.replay_isolation import (
        ReplayIsolationGate, ExecutionMode, IsolationCheckResult,
    )
    gate = ReplayIsolationGate()
    assert isinstance(gate, ReplayIsolationGate)


def test_server_v2_trading_engine_has_isolation_gate():
    from server_v2 import engine
    assert hasattr(engine, "_replay_isolation_gate")
    assert hasattr(engine, "check_pre_trade_isolation")
    assert hasattr(engine, "check_broker_isolation")


def test_server_v2_engine_resolve_execution_mode():
    from server_v2 import engine
    mode = engine._resolve_execution_mode()
    assert mode in set(ExecutionMode)


def test_server_v2_engine_check_pre_trade():
    from server_v2 import engine
    result = engine.check_pre_trade_isolation("2330.TW", "Buy")
    assert isinstance(result, IsolationCheckResult)
    assert hasattr(result, "allowed")
    assert hasattr(result, "reason_code")
    assert hasattr(result, "mode")


# ═══════════════════════════════════════════════════════════════
# I. No real broker / live API called
# ═══════════════════════════════════════════════════════════════

def test_no_broker_import_in_isolation_module():
    import modules.decision_prechecklist.replay_isolation as ri
    with open(ri.__file__, encoding="utf-8", errors="replace") as f:
        source = f.read()
    assert "shioaji" not in source.lower()
    assert "fubon" not in source.lower()
    assert "import shioaji" not in source.lower()
    assert "import fubon" not in source.lower()
    assert "def place_order" not in source
    assert "_api.place_order" not in source
    assert "broker" not in source.lower() or "assert_can_call_broker" in source


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
