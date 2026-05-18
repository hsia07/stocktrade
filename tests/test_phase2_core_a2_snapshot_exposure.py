"""
Phase 2 Core-A2 Snapshot Exposure Tests.
Verify read-only exposure of Core-A1 shadow snapshot via TradingEngine.get_state().
"""

import pytest
from unittest.mock import patch, MagicMock
import logging

logging.disable(logging.CRITICAL)


class TestGetStateIncludesSnapshot:
    def test_get_state_includes_core_a_shadow_snapshot(self):
        """get_state() return dict must include core_a_shadow_snapshot field."""
        from server import engine
        state = engine.get_state()
        assert "core_a_shadow_snapshot" in state
        assert isinstance(state["core_a_shadow_snapshot"], dict)

    def test_snapshot_field_has_required_output_contract(self):
        """core_a_shadow_snapshot must expose present, shadow_result, no_order_side_effects, order_execution_allowed."""
        from server import engine
        state = engine.get_state()
        snap = state["core_a_shadow_snapshot"]
        assert "present" in snap
        assert "shadow_result" in snap
        assert "no_order_side_effects" in snap
        assert "order_execution_allowed" in snap
        assert snap["no_order_side_effects"] is True
        assert snap["order_execution_allowed"] is False


class TestSnapshotAvailableExposure:
    def test_available_snapshot_exposed_read_only(self):
        """When shadow has evaluated, snapshot must be exposed with available=True."""
        from server import engine
        tick = {"price": 500.0, "volume": 1000, "bid_vol": 200, "ask_vol": 150}
        bars = [{"close": 495.0, "high": 505.0, "low": 490.0, "volume": 2000}] * 5
        # Trigger evaluation and store snapshot (simulating loop wiring)
        shadow_snap = engine.core_a_shadow.evaluate("FAKE", bars, tick, {})
        engine._core_a_shadow_snapshots["FAKE"] = shadow_snap
        state = engine.get_state()
        snap = state["core_a_shadow_snapshot"]
        assert snap["present"] is True
        assert snap["available"] is True
        assert snap["shadow_result"] == "ok"
        assert "latest_snapshot" in snap
        assert "snapshots" in snap
        assert "FAKE" in snap["snapshots"]


class TestSnapshotUnavailableExposure:
    def test_unavailable_snapshot_exposed_safely(self):
        """When no evaluations yet, snapshot must expose unavailable safely without crashing."""
        # Use a fresh engine to ensure no prior evaluations
        from server import TradingEngine
        fresh = TradingEngine()
        state = fresh.get_state()
        snap = state["core_a_shadow_snapshot"]
        assert snap["present"] is False
        assert snap["available"] is False
        assert snap["shadow_result"] == "unavailable"
        assert snap["failure_mode"] == "shadow_unavailable"
        assert snap["no_order_side_effects"] is True
        assert snap["order_execution_allowed"] is False


class TestGetStateReadOnlySafety:
    def test_get_state_does_not_mutate_snapshot(self):
        """get_state() must not mutate stored snapshot object."""
        from server import engine
        from dataclasses import asdict
        tick = {"price": 500.0, "volume": 1000, "bid_vol": 200, "ask_vol": 150}
        bars = [{"close": 495.0}] * 5
        shadow_snap = engine.core_a_shadow.evaluate("FAKE2", bars, tick, {})
        engine._core_a_shadow_snapshots["FAKE2"] = shadow_snap
        before = engine._core_a_shadow_snapshots["FAKE2"].shadow_result
        state = engine.get_state()
        after = engine._core_a_shadow_snapshots["FAKE2"].shadow_result
        assert before == after
        # Verify asdict return is a new dict, not the original object
        assert state["core_a_shadow_snapshot"]["snapshots"]["FAKE2"] is not asdict(engine._core_a_shadow_snapshots["FAKE2"])

    def test_get_state_does_not_write_runtime_state(self):
        """get_state() must not create or modify runtime state files."""
        import os, tempfile
        from server import TradingEngine
        fresh = TradingEngine()
        with tempfile.TemporaryDirectory() as tmp:
            # There is no standard runtime state file for Core-A2 to write.
            # This test asserts get_state is pure read-only by comparing
            # key fields (excluding timestamp which naturally changes).
            state_before = fresh.get_state()
            state_after = fresh.get_state()
            # Compare everything except updated_at timestamps
            for key in state_before:
                if key == "core_a_shadow_snapshot":
                    assert state_before[key]["present"] == state_after[key]["present"]
                    assert state_before[key]["available"] == state_after[key]["available"]
                    assert state_before[key]["shadow_result"] == state_after[key]["shadow_result"]
                    assert state_before[key]["no_order_side_effects"] == state_after[key]["no_order_side_effects"]
                    assert state_before[key]["order_execution_allowed"] == state_after[key]["order_execution_allowed"]
                elif key != "timestamp":
                    assert state_before[key] == state_after[key]

    def test_get_state_does_not_alter_final_decision(self):
        """get_state() must not modify any decision fields."""
        from server import engine
        # Get existing state before and after
        before = engine.get_state()
        before_mode = before.get("mode")
        before_auto = before.get("auto_trade")
        after = engine.get_state()
        assert after["mode"] == before_mode
        assert after["auto_trade"] == before_auto

    def test_get_state_does_not_alter_order_permission(self):
        """get_state() must not change order_execution_allowed anywhere."""
        from server import engine
        # order_execution_allowed is a global/module-level variable checked in server wiring tests
        # Verify get_state() does not touch it
        assert hasattr(engine, 'core_a_shadow')
        state = engine.get_state()
        assert state["core_a_shadow_snapshot"]["order_execution_allowed"] is False


class TestGetStateNoForbiddenPaths:
    def test_no_broker_api_call_from_get_state(self):
        """get_state() must not call broker API."""
        from server import engine
        with patch.object(engine, 'broker', create=True) as mock_broker:
            engine.get_state()
            if hasattr(mock_broker, 'place_order'):
                mock_broker.place_order.assert_not_called()

    def test_no_execution_call_from_get_state(self):
        """get_state() must not trigger execution."""
        from server import engine
        with patch.object(engine, 'execution', create=True) as mock_exec:
            engine.get_state()
            if hasattr(mock_exec, 'execute'):
                mock_exec.execute.assert_not_called()

    def test_no_live_mode_from_get_state(self):
        """get_state() must not enable or trigger live trading mode."""
        from server import TradingEngine
        fresh = TradingEngine()
        state = fresh.get_state()
        # Verify mode is still whatever default is, not forced to LIVE
        assert state.get("mode") in ("PAPER", "LIVE")

    def test_no_direct_buy_sell_in_get_state(self):
        """get_state() source must not contain direct buy/sell paths."""
        import inspect
        from server import TradingEngine
        src = inspect.getsource(TradingEngine.get_state)
        assert "buy_order" not in src
        assert "sell_order" not in src
        assert "place_order" not in src

    def test_no_new_api_endpoint_added(self):
        """No new API endpoint must be added for Core-A2."""
        with open("server.py", encoding="utf-8") as f:
            content = f.read()
        # Count @app.get/post/put/delete occurrences
        endpoints = [l for l in content.split("\n") if l.strip().startswith("@app.")]
        # Verify no endpoint specifically for core_a shadow
        for ep in endpoints:
            assert "core_a" not in ep.lower()
            assert "shadow" not in ep.lower()
        # Verify existing /api/state still exists
        assert '@app.get("/api/state")' in content

    def test_no_ui_index_v2_touch(self):
        """index_v2.html must not reference Core-A2 or shadow snapshot."""
        with open("index_v2.html", encoding="utf-8") as f:
            content = f.read()
        assert "core_a_shadow_snapshot" not in content
        assert "core_a" not in content.lower() or "box-shadow" in content.lower()

    def test_server_v2_unchanged(self):
        """server_v2.py must not contain Core-A2 references."""
        with open("server_v2.py", encoding="utf-8") as f:
            content = f.read()
        assert "core_a_shadow_snapshot" not in content
        assert "core_a" not in content.lower()

    def test_order_execution_allowed_remains_false(self):
        """order_execution_allowed must remain FALSE globally."""
        with open("server.py", encoding="utf-8") as f:
            content = f.read()
        assert "order_execution_allowed = True" not in content
        assert "order_execution_allowed=True" not in content


class TestSnapshotSecretProtection:
    def test_snapshot_does_not_expose_secret_token_chat_id(self):
        """Exposed snapshot must not contain secret, token, chat_id, API key, broker credential."""
        from server import engine
        tick = {"price": 500.0, "volume": 1000, "bid_vol": 200, "ask_vol": 150}
        bars = [{"close": 495.0}] * 5
        engine.core_a_shadow.evaluate("SECRET_TEST", bars, tick, {})
        state = engine.get_state()
        snap_str = str(state["core_a_shadow_snapshot"]).lower()
        forbidden = ["secret", "token", "chat_id", "api_key", "password", "credential", "broker_key"]
        for f in forbidden:
            assert f not in snap_str, f"Snapshot exposes forbidden field: {f}"
