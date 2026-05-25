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


def test_server_v2_check_pre_trade_blocks_replay_mode():
    from server_v2 import engine
    from modules.decision_prechecklist.replay_isolation import ExecutionMode
    engine._replay_isolation_gate.clear()
    engine._replay_isolation_gate.enter_replay("test_trace")
    result = engine.check_pre_trade_isolation("2330.TW", "Buy")
    assert not result.allowed, f"replay mode should block order, got allowed={result.allowed}"
    assert result.reason_code == "ORDER_PLACEMENT_BLOCKED_BY_MODE"
    engine._replay_isolation_gate.clear()


def test_server_v2_check_pre_trade_blocks_backtest_mode():
    from server_v2 import engine
    from modules.decision_prechecklist.replay_isolation import ExecutionMode
    engine._replay_isolation_gate.clear()
    engine._replay_isolation_gate.enter_backtest()
    result = engine.check_pre_trade_isolation("2330.TW", "Sell")
    assert not result.allowed, f"backtest mode should block order, got allowed={result.allowed}"
    assert result.reason_code == "ORDER_PLACEMENT_BLOCKED_BY_MODE"
    engine._replay_isolation_gate.clear()


def test_server_v2_check_pre_trade_blocks_audit_mode():
    from server_v2 import engine
    engine._replay_isolation_gate.clear()
    engine._replay_isolation_gate.enter_audit()
    result = engine.check_pre_trade_isolation("2330.TW", "Buy")
    assert not result.allowed, f"audit mode should block order, got allowed={result.allowed}"
    assert result.reason_code == "ORDER_PLACEMENT_BLOCKED_BY_MODE"
    engine._replay_isolation_gate.clear()


def test_server_v2_check_pre_trade_blocks_simulation_mode():
    from server_v2 import engine
    engine._replay_isolation_gate.clear()
    engine._replay_isolation_gate.enter_simulation()
    result = engine.check_pre_trade_isolation("2330.TW", "Buy")
    assert not result.allowed, f"simulation mode should block order, got allowed={result.allowed}"
    assert result.reason_code == "ORDER_PLACEMENT_BLOCKED_BY_MODE"
    engine._replay_isolation_gate.clear()


def test_server_v2_check_pre_trade_allows_live_mode():
    from server_v2 import engine
    engine._replay_isolation_gate.clear()
    engine._replay_isolation_gate.enter_live()
    result = engine.check_pre_trade_isolation("2330.TW", "Buy")
    assert result.allowed, f"live mode should allow order, got allowed={result.allowed}"
    engine._replay_isolation_gate.clear()


def test_server_v2_check_pre_trade_blocks_no_context():
    from server_v2 import engine
    engine._replay_isolation_gate.clear()
    result = engine.check_pre_trade_isolation("2330.TW", "Buy")
    assert not result.allowed, f"no context should fail-closed, got allowed={result.allowed}"
    assert result.reason_code == "ORDER_PLACEMENT_MODE_CONTEXT_MISSING"


def test_server_v2_check_broker_blocks_replay_mode():
    from server_v2 import engine
    engine._replay_isolation_gate.clear()
    engine._replay_isolation_gate.enter_replay("test_trace_broker")
    result = engine.check_broker_isolation("shioaji")
    assert not result.allowed, f"replay mode should block broker call, got allowed={result.allowed}"
    assert result.reason_code == "BROKER_CALL_BLOCKED_BY_MODE"
    engine._replay_isolation_gate.clear()


def test_server_v2_check_broker_blocks_backtest_mode():
    from server_v2 import engine
    engine._replay_isolation_gate.clear()
    engine._replay_isolation_gate.enter_backtest()
    result = engine.check_broker_isolation("fubon")
    assert not result.allowed, f"backtest mode should block broker call, got allowed={result.allowed}"
    assert result.reason_code == "BROKER_CALL_BLOCKED_BY_MODE"
    engine._replay_isolation_gate.clear()


def test_server_v2_check_broker_allows_live_mode():
    from server_v2 import engine
    engine._replay_isolation_gate.clear()
    engine._replay_isolation_gate.enter_live()
    result = engine.check_broker_isolation("shioaji")
    assert result.allowed, f"live mode should allow broker call, got allowed={result.allowed}"
    engine._replay_isolation_gate.clear()


def test_server_v2_check_broker_blocks_no_context():
    from server_v2 import engine
    engine._replay_isolation_gate.clear()
    result = engine.check_broker_isolation()
    assert not result.allowed, f"no context should fail-closed for broker, got allowed={result.allowed}"
    assert result.reason_code == "BROKER_CALL_MODE_CONTEXT_MISSING"


def test_server_v2_execution_engineer_place_blocks_replay():
    from server_v2 import engine
    engine._replay_isolation_gate.clear()
    engine._replay_isolation_gate.enter_replay("test_place")
    rec = engine.execution.place("2330", "Buy", 1, 500.0, "test")
    assert rec.get("status") == "blocked", f"replay place should be blocked, got {rec.get('status')}"
    block_reason = rec.get("block_reason", "")
    assert block_reason == "ORDER_PLACEMENT_BLOCKED_BY_MODE", f"expected IsolationGate reason, got {block_reason}"
    engine._replay_isolation_gate.clear()


def test_server_v2_execution_engineer_place_blocks_no_context():
    from server_v2 import engine
    engine._replay_isolation_gate.clear()
    rec = engine.execution.place("2330", "Buy", 1, 500.0, "test")
    assert rec.get("status") == "blocked", f"no-context place should be blocked, got {rec.get('status')}"
    block_reason = rec.get("block_reason", "")
    assert block_reason == "ORDER_PLACEMENT_MODE_CONTEXT_MISSING", f"expected IsolationGate reason, got {block_reason}"


def test_server_v2_execution_engineer_place_still_blocked_by_order_execution_allowed():
    from server_v2 import engine
    from server_v2 import ORDER_EXECUTION_ALLOWED
    engine._replay_isolation_gate.clear()
    engine._replay_isolation_gate.enter_live()
    rec = engine.execution.place("2330", "Buy", 1, 500.0, "test")
    assert rec.get("status") == "blocked", "live context but order_execution_allowed=False should still block"
    block_reason = rec.get("block_reason", "")
    assert block_reason == "order_execution_not_allowed", f"expected order_execution_not_allowed, got {block_reason}"
    engine._replay_isolation_gate.clear()


def test_server_v2_bridge_returns_isolation_gate_result_not_hardcoded():
    from server_v2 import engine
    engine._replay_isolation_gate.clear()
    engine._replay_isolation_gate.enter_replay("bridge_test")
    result = engine.check_pre_trade_isolation("2330.TW", "Buy")
    assert result.mode == "replay", f"expected mode=replay from gate, got mode={result.mode}"
    assert result.target == "order:2330.TW:Buy", f"expected target with order: prefix, got {result.target}"
    engine._replay_isolation_gate.clear()


def test_server_v2_bridge_check_broker_returns_gate_result():
    from server_v2 import engine
    engine._replay_isolation_gate.clear()
    engine._replay_isolation_gate.enter_backtest()
    result = engine.check_broker_isolation("fubon_api")
    assert result.mode == "backtest", f"expected mode=backtest from gate, got mode={result.mode}"
    assert "blocked" in result.reason.lower() or not result.allowed, f"backtest should block broker"
    engine._replay_isolation_gate.clear()


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


# ═══════════════════════════════════════════════════════════════
# II. R033: Comprehensive negative tests
# ═══════════════════════════════════════════════════════════════

def test_replay_attempt_order_placement_blocked():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="neg-order")
    result = gate.assert_can_place_order("2330.TW")
    assert not result.allowed
    assert result.reason_code == "ORDER_PLACEMENT_BLOCKED_BY_MODE"
    gate.clear()


def test_broker_api_call_in_replay_blocked():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="neg-broker")
    result = gate.assert_can_call_broker("fubon_api")
    assert not result.allowed
    assert result.reason_code == "BROKER_CALL_BLOCKED_BY_MODE"
    gate.clear()


def test_original_veto_and_replay_trade_allowed_fails():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="neg-veto")
    original_vetos = [{"gate": "risk", "reason_code": "max_loss_breach", "detail": "10% loss limit"}]
    result = gate.check_veto_replay(original_vetos, replayed_trade_allowed=True)
    assert not result.allowed
    assert result.reason_code == "VETO_REPLAY_MISMATCH"
    gate.clear()


def test_missing_trace_id_fails():
    from modules.decision_prechecklist.decision_comparator import DecisionComparator
    comp = DecisionComparator()
    before = {"trace_id": "", "symbol": "ABC", "side": "buy",
              "candidate_action": "entry", "final_decision": "NO_TRADE"}
    after = {"trace_id": "", "symbol": "ABC", "side": "buy",
             "candidate_action": "entry", "final_decision": "NO_TRADE"}
    report = comp.compare(before, after)
    codes = report.diff_reason_codes
    assert any("missing_trace_id" in c for c in codes)


def test_missing_final_decision_fails():
    from modules.decision_prechecklist.decision_comparator import DecisionComparator
    comp = DecisionComparator()
    before = {"trace_id": "t1", "symbol": "ABC", "side": "buy",
              "candidate_action": "entry", "final_decision": ""}
    after = {"trace_id": "t2", "symbol": "ABC", "side": "buy",
             "candidate_action": "entry", "final_decision": ""}
    report = comp.compare(before, after)
    codes = report.diff_reason_codes
    assert any("missing_final_decision" in c for c in codes)


def test_decision_ts_before_tradable_ts_fails():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="neg-asof")
    result = gate.check_as_of_guard(
        decision_ts="2025-01-01T09:00:00",
        tradable_ts="2025-01-01T10:00:00",
    )
    assert not result.allowed
    assert result.reason_code == "DECISION_TS_BEFORE_TRADABLE_TS"
    gate.clear()


def test_future_leak_source_after_decision_fails():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="neg-leak")
    result = gate.check_as_of_guard(
        decision_ts="2025-01-01T09:00:00",
        source_ts="2025-01-01T10:00:00",
    )
    assert not result.allowed
    assert "FUTURE_LEAK" in result.reason_code
    gate.clear()


def test_audit_record_mutation_attempt_blocked():
    from modules.decision_prechecklist.audit_trail import (
        ImmutableRecordError, reject_mutation_or_overwrite, create_decision_audit_record
    )
    record = create_decision_audit_record(
        trace_id="mut-test",
        final_decision="NO_TRADE",
        final_reason_code="no_signal",
    )
    record.immutable_after_write = True
    record.append_only = True
    with pytest.raises(ImmutableRecordError):
        reject_mutation_or_overwrite(record)


def test_replay_live_write_attempt_blocked():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="neg-livewrite")
    result = gate.check_replay_live_write(target="live_state")
    assert not result.allowed
    assert "LIVE_WRITE" in result.reason_code
    gate.clear()


def test_replay_runtime_write_attempt_blocked():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="neg-runtime")
    result = gate.assert_can_write_runtime_state("live_cache")
    assert not result.allowed
    assert "RUNTIME_STATE_WRITE" in result.reason_code
    gate.clear()


# ═══════════════════════════════════════════════════════════════
# III. R033: Edge tests — no-trade, veto-only, partial placeholders
# ═══════════════════════════════════════════════════════════════

def test_replay_no_trade_record_safe():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="edge-no-trade")
    result = gate.assert_can_place_order("2330.TW")
    assert not result.allowed
    gate.clear()


def test_replay_veto_only_record():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="edge-veto-only")
    vetos = [{"gate": "risk", "reason_code": "rule_based", "detail": "no_trade_day"}]
    result = gate.check_veto_replay(vetos, replayed_trade_allowed=False)
    assert result.allowed
    gate.clear()


def test_replay_market_reality_placeholder_present():
    from modules.decision_prechecklist.decision_comparator import DecisionComparator
    comp = DecisionComparator()
    before = {"trace_id": "t1", "symbol": "ABC", "side": "buy",
              "candidate_action": "entry", "final_decision": "NO_TRADE"}
    after = dict(before)
    mr = {
        "cost_model_version": "r032-v1",
        "slippage_model_version": "r032-v1",
        "liquidity_score": 0.5,
        "estimated_fill_probability": 0.9,
        "expected_cost": 0.001,
        "expected_slippage": 0.0005,
        "expected_net_rr": -0.001,
        "market_session_state": "continuous",
        "limit_up_down_distance": 9.5,
    }
    report = comp.compare(before, after,
                          market_reality_before=mr,
                          market_reality_after=mr)
    assert len(report.market_reality_diffs) == 0  # identical placeholders ok


def test_replay_taiwan_constraint_placeholder_present():
    tc = {
        "limit_up_down_pct": 10.0,
        "t2_settlement_aware": True,
        "auction_session_state": "continuous",
        "odd_lot_round_lot": "round_lot",
        "halt_disposition_attention": "none",
        "liquidity_insufficiency": "none",
    }
    assert tc["limit_up_down_pct"] == 10.0
    assert tc["odd_lot_round_lot"] in ("round_lot", "odd_lot")
    assert tc["halt_disposition_attention"] in ("none", "halt", "attention", "disposition")


def test_replay_market_reality_missing_fields_incomplete():
    from modules.decision_prechecklist.decision_comparator import DecisionComparator
    comp = DecisionComparator()
    before = {"trace_id": "t1", "symbol": "ABC", "side": "buy",
              "candidate_action": "entry", "final_decision": "NO_TRADE"}
    after = dict(before)
    mr_partial = {"cost_model_version": "v1"}
    report = comp.compare(before, after,
                          market_reality_before=mr_partial,
                          market_reality_after=mr_partial)
    # Partial market reality not treated as violation by comparator
    assert len(report.market_reality_diffs) == 0  # identical partials
    # But audit trail validation would flag it
    from modules.decision_prechecklist.audit_trail import AuditTrailChain, create_decision_audit_record
    chain = AuditTrailChain()
    record = create_decision_audit_record(
        trace_id="partial-mr",
        final_decision="NO_TRADE",
        final_reason_code="no_signal",
        market_session_state="",
    )
    record.market_reality.cost_model_version = ""
    errors = chain.validate_record(record)
    assert any("cost_model_version_missing" in e for e in errors)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
