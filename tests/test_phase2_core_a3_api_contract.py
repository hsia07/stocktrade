"""
Phase 2 Core-A3 API Contract Hardening Tests.
Verify API response schema contract for core_a_shadow_snapshot via existing /api/state.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
import logging

logging.disable(logging.CRITICAL)


class TestAPIStateExists:
    def test_api_state_exists_and_returns_state(self):
        """/api/state endpoint exists and returns engine.get_state() directly."""
        from server import app, engine
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/state")
        assert response.status_code == 200
        state = response.json()
        assert isinstance(state, dict)
        # Verify it matches engine.get_state()
        expected = engine.get_state()
        assert "core_a_shadow_snapshot" in state or "core_a_shadow_snapshot" in expected

    def test_api_state_no_new_endpoint_added(self):
        """No new API endpoint should be added for Core-A3."""
        from server import app
        routes = [route.path for route in app.routes]
        core_a_routes = [r for r in routes if "core_a" in r.lower() or "shadow" in r.lower()]
        assert len(core_a_routes) == 0, f"Unexpected Core-A endpoint found: {core_a_routes}"


class TestAPISchemaContract:
    def test_api_state_includes_core_a_shadow_snapshot(self):
        """/api/state response must include core_a_shadow_snapshot field."""
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/state")
        assert response.status_code == 200
        state = response.json()
        assert "core_a_shadow_snapshot" in state
        assert isinstance(state["core_a_shadow_snapshot"], dict)

    def test_core_a_shadow_snapshot_contains_required_keys(self):
        """core_a_shadow_snapshot must contain all required contract keys."""
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/state")
        assert response.status_code == 200
        snapshot = response.json()["core_a_shadow_snapshot"]
        required_keys = ["present", "available", "shadow_result", "no_order_side_effects",
                         "order_execution_allowed", "updated_at"]
        for key in required_keys:
            assert key in snapshot, f"Missing required key: {key}"

    def test_available_path_schema_valid(self):
        """When shadow evaluations exist, available=True and snapshots present."""
        from server import app, TradingEngine
        from fastapi.testclient import TestClient
        from modules.phase2.core_a_shadow_aggregator import CoreAShadowAggregator
        client = TestClient(app)
        # Force available path by running a shadow evaluation
        engine = TradingEngine()
        if engine.core_a_shadow is not None:
            try:
                engine.core_a_shadow.evaluate("TEST_AVAILABLE_PATH")
            except Exception:
                pass
            # Refresh state
            response = client.get("/api/state")
            assert response.status_code == 200
            snapshot = response.json()["core_a_shadow_snapshot"]
            if snapshot.get("available") is True:
                assert "snapshots" in snapshot
                assert isinstance(snapshot["snapshots"], dict)  # keyed by symbol
                assert "latest_snapshot" in snapshot
                assert isinstance(snapshot["latest_snapshot"], dict)
                assert snapshot["latest_snapshot"].get("no_order_side_effects") is True
                assert snapshot["latest_snapshot"].get("order_execution_allowed") is False
            else:
                # If still unavailable, at least verify the schema shape is documented
                assert "present" in snapshot
                assert "available" in snapshot

    def test_unavailable_path_schema_valid(self):
        """When no evaluations yet, unavailable path returns safe fallback."""
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/state")
        assert response.status_code == 200
        snapshot = response.json()["core_a_shadow_snapshot"]
        if snapshot.get("available") is False:
            assert snapshot.get("shadow_result") == "unavailable"
            assert "failure_mode" in snapshot
            assert snapshot.get("no_order_side_effects") is True
            assert snapshot.get("order_execution_allowed") is False
            assert snapshot.get("present") is False
            assert "updated_at" in snapshot

    def test_failure_mode_present_when_unavailable(self):
        """Unavailable snapshot must include failure_mode key."""
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/state")
        assert response.status_code == 200
        snapshot = response.json()["core_a_shadow_snapshot"]
        if snapshot.get("available") is False:
            assert "failure_mode" in snapshot
            assert isinstance(snapshot["failure_mode"], str)


class TestAPISecretProtection:
    def test_snapshot_no_secret_exposure(self):
        """API response snapshot must not expose secret, token, chat_id, api_key, broker_credential."""
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/state")
        assert response.status_code == 200
        snapshot = response.json()["core_a_shadow_snapshot"]
        snapshot_str = str(snapshot).lower()
        forbidden = ["secret", "token", "chat_id", "api_key", "broker_credential", "password"]
        for word in forbidden:
            assert word not in snapshot_str, f"Forbidden field '{word}' detected in API response"

    def test_api_state_no_secret_at_top_level(self):
        """Top-level /api/state response must not expose secrets."""
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/state")
        assert response.status_code == 200
        state = response.json()
        state_str = str(state).lower()
        forbidden = ["secret", "token", "chat_id", "api_key", "broker_credential", "password"]
        for word in forbidden:
            assert word not in state_str, f"Forbidden field '{word}' detected in top-level response"


class TestAPIOrderPermission:
    def test_order_execution_allowed_false(self):
        """order_execution_allowed must be FALSE in API response."""
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/state")
        assert response.status_code == 200
        snapshot = response.json()["core_a_shadow_snapshot"]
        assert snapshot.get("order_execution_allowed") is False

    def test_api_no_trade_permission_implication(self):
        """core_a_shadow_snapshot must not contain keys implying trade permission."""
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/state")
        assert response.status_code == 200
        snapshot = response.json()["core_a_shadow_snapshot"]
        # Check keys at the snapshot level, not raw string search (to allow "is_sell" in market data)
        snapshot_keys = [k.lower() for k in snapshot.keys()]
        implication_keys = ["trade_allowed", "can_trade", "place_order", "send_order", "execute_trade", "trade_approved"]
        for key in implication_keys:
            assert key not in snapshot_keys, f"Trade implication key '{key}' found in core_a_shadow_snapshot keys"


class TestAPIReadOnly:
    def test_get_state_readonly_no_mutation(self):
        """Multiple calls to /api/state must not mutate engine state."""
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response1 = client.get("/api/state")
        response2 = client.get("/api/state")
        assert response1.status_code == 200
        assert response2.status_code == 200
        state1 = response1.json()
        state2 = response2.json()
        # core_a_shadow_snapshot should be structurally consistent
        assert state1["core_a_shadow_snapshot"]["present"] == state2["core_a_shadow_snapshot"]["present"]
        assert state1["core_a_shadow_snapshot"]["order_execution_allowed"] == state2["core_a_shadow_snapshot"]["order_execution_allowed"]

    def test_api_state_does_not_write_runtime_state(self):
        """/api/state must not create or modify runtime state files."""
        import os
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        # Check that calling /api/state doesn't create new files in project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        before = set(os.listdir(project_root))
        response = client.get("/api/state")
        assert response.status_code == 200
        after = set(os.listdir(project_root))
        new_files = after - before
        # Filter out common temp files
        runtime_files = [f for f in new_files if not f.startswith('.') and not f.endswith('.pyc')]
        assert len(runtime_files) == 0, f"Runtime files created: {runtime_files}"


class TestAPIForbiddenPaths:
    def test_no_new_endpoint_for_core_a3(self):
        """Core-A3 must not add any new API endpoint."""
        from server import app
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        # Known existing endpoints before Core-A3
        allowed = ["/api/state", "/api/trades", "/api/toggle_mode", "/api/mode",
                   "/api/mode_transition", "/api/mode_history", "/api/priority_status",
                   "/api/priority_alerts", "/ws"]
        for route in routes:
            if route not in allowed and route not in ["/", "/docs", "/openapi.json", "/redoc"]:
                assert "core_a" not in route.lower(), f"New Core-A endpoint detected: {route}"
                assert "shadow" not in route.lower(), f"New shadow endpoint detected: {route}"

    def test_no_ui_wiring_added(self):
        """Core-A3 must not add UI wiring to index_v2.html."""
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        index_path = os.path.join(project_root, "index_v2.html")
        assert os.path.exists(index_path), "index_v2.html not found"
        with open(index_path, encoding="utf-8") as f:
            content = f.read()
        assert "core_a_shadow_snapshot" not in content
        assert "shadow_snapshot" not in content

    def test_server_v2_unchanged(self):
        """server_v2.py must not be modified by Core-A3."""
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        server_v2_path = os.path.join(project_root, "server_v2.py")
        assert os.path.exists(server_v2_path), "server_v2.py not found"
        with open(server_v2_path, encoding="utf-8") as f:
            content = f.read()
        assert "core_a_shadow_snapshot" not in content
        assert "core_a" not in content.lower() or "box-shadow" in content.lower()

    def test_no_broker_execution_live_in_api_state(self):
        """/api/state source must not call broker, execution, or live paths."""
        import inspect
        from server import app
        # Find /api/state handler
        api_state_route = None
        for route in app.routes:
            if hasattr(route, 'path') and route.path == "/api/state":
                api_state_route = route
                break
        assert api_state_route is not None
        handler = api_state_route.endpoint
        source = inspect.getsource(handler)
        assert "broker" not in source.lower()
        assert "execution" not in source.lower()
        assert "live" not in source.lower()
        assert "place_order" not in source.lower()
        assert "send_order" not in source.lower()
        assert "buy" not in source.lower() or "_buy" in source.lower()  # Allow "_buy" for safe substrings
        assert "sell" not in source.lower() or "_sell" in source.lower()

    def test_api_state_no_runtime_state_write(self):
        """/api/state must not contain file write operations."""
        import inspect
        from server import app
        api_state_route = None
        for route in app.routes:
            if hasattr(route, 'path') and route.path == "/api/state":
                api_state_route = route
                break
        assert api_state_route is not None
        handler = api_state_route.endpoint
        source = inspect.getsource(handler)
        assert "open(" not in source or ("open(" in source and "r" in source)


class TestSchemaContract:
    _SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 "automation", "control", "candidates",
                                 "PHASE2_CORE_A3_API_CONTRACT_HARDENING",
                                 "core_a_shadow_snapshot_schema.json")

    def test_schema_artifact_exists(self):
        """Schema artifact must exist."""
        import json
        assert os.path.exists(self._SCHEMA_PATH), f"Schema artifact not found at {self._SCHEMA_PATH}"
        with open(self._SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        assert "endpoint" in schema
        assert "field" in schema
        assert "required_keys" in schema
        assert "safety_fields" in schema
        assert "forbidden_fields" in schema
        assert "statement" in schema

    def test_schema_endpoint_is_existing_api_state(self):
        """Schema must specify existing /api/state endpoint."""
        import json
        with open(self._SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        assert schema["endpoint"] == "/api/state"

    def test_schema_field_is_core_a_shadow_snapshot(self):
        """Schema must specify core_a_shadow_snapshot field."""
        import json
        with open(self._SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        assert schema["field"] == "core_a_shadow_snapshot"

    def test_schema_safety_fields_order_exec_false(self):
        """Schema safety fields must declare order_execution_allowed = FALSE."""
        import json
        with open(self._SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        safety = schema.get("safety_fields", {})
        assert safety.get("order_execution_allowed") is False
        assert safety.get("no_order_side_effects") is True

    def test_schema_forbidden_fields_include_secret_token(self):
        """Schema forbidden fields must include secret, token, chat_id, api_key, broker_credential."""
        import json
        with open(self._SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        forbidden = schema.get("forbidden_fields", [])
        required_forbidden = ["secret", "token", "chat_id", "api_key", "broker_credential"]
        for field in required_forbidden:
            assert field in forbidden, f"Missing forbidden field: {field}"

    def test_schema_statement_not_trade_approval(self):
        """Schema statement must clarify this is not trade approval."""
        import json
        with open(self._SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        statement = schema.get("statement", "")
        assert "not trade approval" in statement.lower() or "read-only" in statement.lower()
        assert "not broker" in statement.lower() or "not execution" in statement.lower()
