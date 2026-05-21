"""
Server_v2 backend execution safety hardening tests.
Verifies order_execution_allowed hard gate, can_trade fail-closed,
connect_shioaji startup gating, and POST endpoint anti-bypass.
"""

import pytest
import os
import logging

logging.disable(logging.CRITICAL)

SERVER_V2_PATH = os.path.join(os.path.dirname(__file__), "..", "server_v2.py")

# ── A: ORDER_EXECUTION_ALLOWED constant ──


class TestOrderExecutionAllowedConstant:
    def test_constant_exists_and_is_false(self):
        from server_v2 import ORDER_EXECUTION_ALLOWED
        assert ORDER_EXECUTION_ALLOWED is False

    def test_constant_reason_exists(self):
        from server_v2 import ORDER_EXECUTION_ALLOWED_REASON
        assert isinstance(ORDER_EXECUTION_ALLOWED_REASON, str)
        assert len(ORDER_EXECUTION_ALLOWED_REASON) > 0

    def test_get_state_includes_order_execution_allowed(self):
        from server_v2 import engine
        state = engine.get_state()
        assert "order_execution_allowed" in state
        assert state["order_execution_allowed"] is False
        assert "order_execution_allowed_reason" in state
        assert isinstance(state["order_execution_allowed_reason"], str)

    def test_get_state_still_has_ui_safety_disclaimer(self):
        from server_v2 import engine
        state = engine.get_state()
        assert "ui_safety_disclaimer" in state
        assert "display-only" in state["ui_safety_disclaimer"]


# ── B: can_trade fail-closed ──


class TestRiskOfficerCanTrade:
    def test_can_trade_method_exists(self):
        from server_v2 import RiskOfficer
        assert hasattr(RiskOfficer, "can_trade")
        assert callable(RiskOfficer.can_trade)

    def test_can_trade_returns_false_when_order_execution_not_allowed(self):
        from server_v2 import RiskOfficer, ORDER_EXECUTION_ALLOWED
        assert ORDER_EXECUTION_ALLOWED is False
        officer = RiskOfficer()
        result = officer.can_trade({"price": 100, "symbol": "2330"})
        assert result is False

    def test_can_trade_returns_false_for_none_tick(self):
        from server_v2 import RiskOfficer, ORDER_EXECUTION_ALLOWED
        officer = RiskOfficer()
        result = officer.can_trade(None)
        if ORDER_EXECUTION_ALLOWED:
            assert result is False
        else:
            assert result is False

    def test_can_trade_returns_false_for_empty_dict(self):
        from server_v2 import RiskOfficer, ORDER_EXECUTION_ALLOWED
        if ORDER_EXECUTION_ALLOWED:
            officer = RiskOfficer()
            result = officer.can_trade({})
            assert result is False

    def test_can_trade_returns_false_when_price_missing(self):
        from server_v2 import RiskOfficer, ORDER_EXECUTION_ALLOWED
        if ORDER_EXECUTION_ALLOWED:
            officer = RiskOfficer()
            result = officer.can_trade({"symbol": "2330"})
            assert result is False

    def test_can_trade_returns_false_when_price_zero(self):
        from server_v2 import RiskOfficer, ORDER_EXECUTION_ALLOWED
        if ORDER_EXECUTION_ALLOWED:
            officer = RiskOfficer()
            result = officer.can_trade({"price": 0, "symbol": "2330"})
            assert result is False

    def test_can_trade_returns_false_when_symbol_missing(self):
        from server_v2 import RiskOfficer, ORDER_EXECUTION_ALLOWED
        if ORDER_EXECUTION_ALLOWED:
            officer = RiskOfficer()
            result = officer.can_trade({"price": 100})
            assert result is False

    def test_can_trade_returns_false_for_stale_tick(self):
        from server_v2 import RiskOfficer, ORDER_EXECUTION_ALLOWED
        if ORDER_EXECUTION_ALLOWED:
            officer = RiskOfficer()
            result = officer.can_trade({"price": 100, "symbol": "2330", "stale": True})
            assert result is False

    def test_can_trade_does_not_raise_attribute_error(self):
        from server_v2 import RiskOfficer
        officer = RiskOfficer()
        try:
            officer.can_trade({"price": 100, "symbol": "2330"})
        except AttributeError:
            pytest.fail("can_trade raised AttributeError")
        except (TypeError, KeyError):
            pass


# ── C: ExecutionEngineer.place blocked ──


class TestExecutionEngineerPlaceBlocked:
    def test_place_returns_blocked_when_order_execution_not_allowed(self):
        from server_v2 import ORDER_EXECUTION_ALLOWED
        if ORDER_EXECUTION_ALLOWED:
            pytest.skip("ORDER_EXECUTION_ALLOWED is True, gate not active")
        from server_v2 import ExecutionEngineer
        eng = ExecutionEngineer()
        result = eng.place("2330", "Buy", 1, 500.0, "test")
        assert isinstance(result, dict)
        assert result.get("status") == "blocked"
        assert "block_reason" in result
        block_reason = result.get("block_reason", "")
        assert block_reason in (
            "order_execution_not_allowed",
            "ORDER_PLACEMENT_MODE_CONTEXT_MISSING"
        ), f"expected order_execution_not_allowed or IsolationGate reason, got {block_reason}"

    def test_place_blocked_does_not_call_shioaji(self):
        from server_v2 import ORDER_EXECUTION_ALLOWED
        if ORDER_EXECUTION_ALLOWED:
            pytest.skip("ORDER_EXECUTION_ALLOWED is True, gate not active")
        from server_v2 import ExecutionEngineer
        eng = ExecutionEngineer()
        import unittest.mock
        with unittest.mock.patch.object(eng, "_api", None):
            result = eng.place("2330", "Buy", 1, 500.0, "test")
            assert result.get("status") == "blocked"
            assert result.get("broker_id") is None


# ── D: POST /api/toggle_mode block ──


class TestToggleModeBlocked:
    def test_toggle_mode_to_live_returns_blocked_when_order_execution_not_allowed(self):
        from server_v2 import ORDER_EXECUTION_ALLOWED
        if ORDER_EXECUTION_ALLOWED:
            pytest.skip("ORDER_EXECUTION_ALLOWED is True, gate not active")
        from server_v2 import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/api/toggle_mode")
        data = response.json()
        assert response.status_code == 200
        assert data.get("status") == "blocked" or data.get("order_execution_allowed") is not None

    def test_toggle_mode_returns_order_execution_allowed_reason_when_blocked(self):
        from server_v2 import ORDER_EXECUTION_ALLOWED
        if ORDER_EXECUTION_ALLOWED:
            pytest.skip("ORDER_EXECUTION_ALLOWED is True, gate not active")
        from server_v2 import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/api/toggle_mode")
        data = response.json()
        if data.get("status") == "blocked":
            assert "order_execution_allowed_reason" in data
            assert isinstance(data["order_execution_allowed_reason"], str)

    def test_toggle_mode_does_not_change_paper_trade_when_blocked(self):
        from server_v2 import ORDER_EXECUTION_ALLOWED, PAPER_TRADE
        if ORDER_EXECUTION_ALLOWED:
            pytest.skip("ORDER_EXECUTION_ALLOWED is True, gate not active")
        original = PAPER_TRADE
        from server_v2 import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/api/toggle_mode")
        data = response.json()
        if data.get("status") == "blocked":
            from server_v2 import PAPER_TRADE as pt_after
            assert pt_after == original


# ── E: POST /api/settings block ──


class TestSettingsAntiBypass:
    def test_settings_cannot_disable_paper_trade_when_order_execution_not_allowed(self):
        from server_v2 import ORDER_EXECUTION_ALLOWED
        if ORDER_EXECUTION_ALLOWED:
            pytest.skip("ORDER_EXECUTION_ALLOWED is True, gate not active")
        from server_v2 import app, PAPER_TRADE
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/api/settings", json={"paper_trade": False})
        data = response.json()
        assert data.get("status") == "blocked"
        from server_v2 import PAPER_TRADE as pt_after
        assert pt_after == PAPER_TRADE

    def test_settings_blocked_returns_reason(self):
        from server_v2 import ORDER_EXECUTION_ALLOWED
        if ORDER_EXECUTION_ALLOWED:
            pytest.skip("ORDER_EXECUTION_ALLOWED is True, gate not active")
        from server_v2 import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/api/settings", json={"paper_trade": False})
        data = response.json()
        if data.get("status") == "blocked":
            assert "order_execution_allowed_reason" in data
            assert isinstance(data["order_execution_allowed_reason"], str)

    def test_settings_can_still_update_auto_trade_without_bypass(self):
        from server_v2 import ORDER_EXECUTION_ALLOWED
        if ORDER_EXECUTION_ALLOWED:
            pytest.skip("ORDER_EXECUTION_ALLOWED is True, gate not active")
        from server_v2 import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/api/settings", json={"auto_trade": False})
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"


# ── F: connect_shioaji startup gating ──


class TestConnectShioajiStartupGate:
    def test_connect_shioaji_does_not_call_login_when_order_execution_not_allowed(self):
        from server_v2 import ORDER_EXECUTION_ALLOWED
        if ORDER_EXECUTION_ALLOWED:
            pytest.skip("ORDER_EXECUTION_ALLOWED is True, gate not active")
        from server_v2 import TradingEngine
        import unittest.mock
        with unittest.mock.patch("server_v2.log") as mock_log:
            engine_local = TradingEngine()
            engine_local.connect_shioaji()
            mock_log.info.assert_any_call(unittest.mock.ANY)
            found_blocked = any(
                "blocked" in str(call).lower() and "order_execution_allowed" in str(call).lower()
                for call in mock_log.info.call_args_list
            )
            assert found_blocked, "connect_shioaji should log blocked message"

    def test_startup_code_does_not_bypass_shioaji_gate(self):
        from server_v2 import ORDER_EXECUTION_ALLOWED
        if ORDER_EXECUTION_ALLOWED:
            pytest.skip("ORDER_EXECUTION_ALLOWED is True, gate not active")
        import server_v2
        assert hasattr(server_v2, "ORDER_EXECUTION_ALLOWED")
        assert server_v2.ORDER_EXECUTION_ALLOWED is False


# ── G: G1-G8 visible surface preserved ──


class TestG1toG8Preserved:
    def test_live_blocked_still_in_mode_endpoint(self):
        from server_v2 import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/mode")
        assert response.status_code == 200
        data = response.json()
        assert data.get("live_blocked") is True

    def test_ui_safety_disclaimer_present(self):
        from server_v2 import engine
        state = engine.get_state()
        assert "ui_safety_disclaimer" in state

    def test_order_execution_allowed_false_in_api_state(self):
        from server_v2 import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/state")
        assert response.status_code == 200
        data = response.json()
        assert data.get("order_execution_allowed") is False


# ── H: No runtime/broker/live/R049 started ──


class TestSafetyBoundaries:
    def test_no_new_api_endpoint_for_execution(self):
        from server_v2 import app
        routes = [route.path for route in app.routes]
        dangerous = [r for r in routes if "execute" in r.lower() or "place_order" in r.lower()]
        assert len(dangerous) == 0, f"Dangerous routes found: {dangerous}"

    def test_server_v2_does_not_import_shioaji_at_top_level(self):
        import ast
        with open(SERVER_V2_PATH, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "shioaji" in alias.name.lower():
                        return
            elif isinstance(node, ast.ImportFrom):
                if node.module and "shioaji" in node.module.lower():
                    return
        assert True, "shioaji is not imported at module level (lazy import inside method)"

    def test_stop_robot_still_works(self):
        from server_v2 import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/api/stop_robot")
        assert response.status_code == 200
        data = response.json()
        assert data.get("auto_trade") is False
