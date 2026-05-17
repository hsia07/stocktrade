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
)


def test_gate_initialization():
    gate = ReplayIsolationGate()
    assert gate.current_context is None
    assert not gate.is_in_replay()


def test_enter_replay():
    gate = ReplayIsolationGate()
    ctx = gate.enter_replay(replay_trace_id="replay-001")
    assert ctx.mode == ExecutionMode.REPLAY
    assert ctx.isolated
    assert ctx.replay_trace_id == "replay-001"
    assert gate.is_in_replay()


def test_enter_live():
    gate = ReplayIsolationGate()
    ctx = gate.enter_live()
    assert ctx.mode == ExecutionMode.LIVE
    assert ctx.isolated
    assert not gate.is_in_replay()


def test_exit():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    assert gate.is_in_replay()
    gate.exit()
    assert gate.current_context is None


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


def test_check_store_access_replay_blocks_isolated():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    for store in ISOLATED_STORE_NAMES:
        result = gate.check_store_access(store)
        assert not result.allowed, f"store {store} should be blocked in replay mode"
        assert "replay mode blocked" in result.reason


def test_check_store_access_replay_allows_other():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    result = gate.check_store_access("market_data_cache")
    assert result.allowed


def test_isolate_store_name_replay():
    gate = ReplayIsolationGate()
    gate.enter_replay(replay_trace_id="replay-001")
    isolated = gate.isolate_store_name("trades_log")
    assert isolated == "replay_trades_log"


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


def test_isolation_context_properties():
    ctx = IsolationContext(mode=ExecutionMode.REPLAY, isolated=True)
    assert ctx.is_replay
    assert not ctx.is_live
    ctx_live = IsolationContext(mode=ExecutionMode.LIVE, isolated=True)
    assert ctx_live.is_live
    assert not ctx_live.is_replay


def test_isolation_check_result():
    result = IsolationCheckResult(allowed=False, reason="blocked")
    assert not result.allowed
    assert result.reason == "blocked"


def test_enter_replay_with_original():
    gate = ReplayIsolationGate()
    ctx = gate.enter_replay(replay_trace_id="replay-002", original_trace_id="live-001")
    assert ctx.original_trace_id == "live-001"
    assert ctx.replay_trace_id == "replay-002"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
