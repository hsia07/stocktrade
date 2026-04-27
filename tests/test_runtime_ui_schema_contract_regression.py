"""
Runtime UI Schema Contract Anti-Regression Tests
Tests to prevent runtime UI schema contract repairs from being silently reverted.
"""
import pytest, sys, os, re, ast
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server_v2 import app, engine
from fastapi.testclient import TestClient

client = TestClient(app)


class TestModeConstantGuard:
    """Guard against bare MODE_* constants being used in runtime instance methods"""

    @pytest.fixture
    def server_source(self):
        with open("server_v2.py", encoding="utf-8") as f:
            return f.read()

    def test_no_bare_mode_sims_in_instance_methods(self, server_source):
        """Verify instance methods use self.MODE_* not bare MODE_SIM"""
        tree = ast.parse(server_source)
        violations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                if func_name in ("sync_mode_with_state", "enter_sim_mode", "exit_sim_mode", "get_state"):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Name) and child.id == "MODE_SIM":
                            violations.append(f"{func_name}: line {child.lineno}")

        assert not violations, f"Bare MODE_SIM found in: {violations}"

    def test_no_bare_mode_pause_in_instance_methods(self, server_source):
        """Verify instance methods use self.MODE_* not bare MODE_PAUSE"""
        tree = ast.parse(server_source)
        violations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                if func_name in ("sync_mode_with_state", "enter_sim_mode", "exit_sim_mode", "get_state"):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Name) and child.id == "MODE_PAUSE":
                            violations.append(f"{func_name}: line {child.lineno}")

        assert not violations, f"Bare MODE_PAUSE found in: {violations}"

    def test_no_bare_mode_recovery_in_instance_methods(self, server_source):
        """Verify instance methods use self.MODE_* not bare MODE_RECOVERY"""
        tree = ast.parse(server_source)
        violations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                if func_name in ("sync_mode_with_state", "enter_sim_mode", "exit_sim_mode", "get_state"):
                    for child in ast.walk(node):
                        if isinstance(child, ast.Name) and child.id == "MODE_RECOVERY":
                            violations.append(f"{func_name}: line {child.lineno}")

        assert not violations, f"Bare MODE_RECOVERY found in: {violations}"

    def test_mode_constants_are_class_attributes(self, server_source):
        """Verify MODE_* are defined as class attributes"""
        tree = ast.parse(server_source)

        mode_constants = {"MODE_SIM", "MODE_PAUSE", "MODE_RECOVERY", "MODE_OBSERVE", "MODE_PAPER", "MODE_LIVE"}
        class_attrs = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "TradingEngine":
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id in mode_constants:
                                class_attrs.add(target.id)

        assert class_attrs >= mode_constants, f"Missing MODE_* class attrs: {mode_constants - class_attrs}"


class TestAPIStateSchemaGuard:
    """Guard against API state schema regression"""

    def test_api_state_returns_200(self):
        response = client.get("/api/state")
        assert response.status_code == 200

    def test_api_state_has_schema_version(self):
        state = engine.get_state()
        assert "schema_version" in state, "schema_version missing"
        assert state["schema_version"] == "1.0.0"

    def test_api_state_has_required_core_ticks(self):
        state = engine.get_state()
        assert "ticks" in state, " REQUIRED_CORE 'ticks' missing"

    def test_api_state_has_required_core_positions(self):
        state = engine.get_state()
        assert "positions" in state, "REQUIRED_CORE 'positions' missing"

    def test_api_state_has_required_core_trades_log(self):
        state = engine.get_state()
        assert "trades_log" in state, "REQUIRED_CORE 'trades_log' missing"

    def test_api_state_has_required_core_execution_orders(self):
        state = engine.get_state()
        assert "execution_orders" in state, "REQUIRED_CORE 'execution_orders' missing"

    def test_api_state_has_required_core_sources(self):
        state = engine.get_state()
        assert "sources" in state, "REQUIRED_CORE 'sources' missing"

    def test_api_state_has_required_core_source_info(self):
        state = engine.get_state()
        assert "source_info" in state, "REQUIRED_CORE 'source_info' missing"

    def test_api_state_has_required_core_backtest(self):
        state = engine.get_state()
        assert "backtest" in state, "REQUIRED_CORE 'backtest' missing"

    def test_api_state_has_required_core_signal_history(self):
        state = engine.get_state()
        assert "signal_history" in state, "REQUIRED_CORE 'signal_history' missing"

    def test_api_state_has_required_core_mode(self):
        state = engine.get_state()
        assert "mode" in state, "REQUIRED_CORE 'mode' missing"


class TestFrontendPartialPayloadGuard:
    """Guard against frontend partial payload regression"""

    @pytest.fixture
    def frontend_source(self):
        with open("index_v2.html", encoding="utf-8") as f:
            return f.read()

    def test_render_preserves_schema_version_check(self, frontend_source):
        """Verify render(d) still validates schema_version"""
        assert 'd.schema_version' in frontend_source, "render() must check schema_version"

    def test_render_preserves_required_core_check(self, frontend_source):
        """Verify render(d) still validates REQUIRED_CORE"""
        assert 'coreMissing' in frontend_source or 'REQUIRED_CORE' in frontend_source, "render() must check REQUIRED_CORE"

    def test_websocket_guard_exists(self, frontend_source):
        """Verify WebSocket onmessage has payload guard"""
        assert 'ws.onmessage' in frontend_source

        pattern = r'if\s*\(\s*data\.schema_version\s*&&\s*data\.ticks\s*\)'
        assert re.search(pattern, frontend_source), "WebSocket must guard full state payload"

    def test_no_direct_render_on_partial_payload(self, frontend_source):
        """Verify partial payload does NOT directly call render() without guard"""
        import re
        pattern = r'ws\.onmessage[^{]*{[^}]*render\('
        matches = re.findall(pattern, frontend_source, re.DOTALL)
        for m in matches:
            if "data.schema_version" not in m and "data.ticks" not in m:
                pytest.fail(f"render() called without full payload guard: {m[:50]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])