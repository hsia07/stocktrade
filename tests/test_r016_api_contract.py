"""
R016 API Contract Tests
Phase 1 API Schema / Data Contract Fixation
Tests that API endpoints and state fields conform to the documented contract.
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server import app, engine
from fastapi.testclient import TestClient

client = TestClient(app)

class TestR016SchemaVersion:
    """R016: schema_version field in get_state()"""
    
    def test_state_contains_schema_version(self):
        state = engine.get_state()
        assert "schema_version" in state
        assert state["schema_version"] == "1.0.0"
    
    def test_api_state_returns_schema_version(self):
        response = client.get("/api/state")
        assert response.status_code == 200
        data = response.json()
        assert "schema_version" in data
        assert data["schema_version"] == "1.0.0"

class TestR016BaselineFieldsStable:
    """R016: Baseline state fields must be stable"""
    
    def test_baseline_fields_present(self):
        state = engine.get_state()
        baseline_fields = [
            "ticks", "agents", "positions", "daily_pnl", "daily_trades",
            "is_halted", "trades_log", "timestamp", "mode", "auto_trade"
        ]
        for field in baseline_fields:
            assert field in state, f"Baseline field '{field}' missing from state"
    
    def test_baseline_field_types(self):
        state = engine.get_state()
        assert isinstance(state["ticks"], dict)
        assert isinstance(state["agents"], dict)
        assert isinstance(state["positions"], dict)
        assert isinstance(state["is_halted"], bool)
        assert isinstance(state["trades_log"], list)
        assert isinstance(state["timestamp"], str)
        assert state["mode"] in ["PAPER", "LIVE"]
        assert isinstance(state["auto_trade"], bool)

class TestR016R006FieldsStable:
    """R016: R006 health/circuit fields must be stable"""
    
    def test_r006_fields_present(self):
        state = engine.get_state()
        assert "health_status" in state
        assert "circuit_breaker" in state
        assert "degradation_strategy" in state

class TestR016R008FieldsStable:
    """R016: R008 mode control fields must be stable"""
    
    def test_r008_fields_present(self):
        state = engine.get_state()
        assert "r008_mode" in state
        assert "mode_allows_trading" in state
        assert "mode_transition_count" in state
    
    def test_r008_mode_values(self):
        state = engine.get_state()
        assert state["r008_mode"].upper() in ["SIM", "OBSERVE", "LIVE", "PAUSE"]
        assert isinstance(state["mode_allows_trading"], bool)
        assert isinstance(state["mode_transition_count"], int)

class TestR016R009FieldsStable:
    """R016: R009 priority fields must be stable"""
    
    def test_r009_fields_present(self):
        state = engine.get_state()
        assert "r009_queue" in state
        assert "r009_alerts" in state
    
    def test_r009_queue_structure(self):
        state = engine.get_state()
        queue = state["r009_queue"]
        assert isinstance(queue, dict)
        if "error" not in queue:
            assert "total_tasks" in queue
            assert isinstance(queue["total_tasks"], int)

class TestR016R011FieldsStable:
    """R016: R011 artifact fields must be stable"""
    
    def test_r011_fields_present(self):
        state = engine.get_state()
        assert "artifact_stats" in state

class TestR016APIEndpointsStable:
    """R016: API endpoints must return stable key sets"""
    
    def test_api_mode_keys(self):
        response = client.get("/api/mode")
        assert response.status_code == 200
        data = response.json()
        assert "mode" in data
        assert "paper_trade" in data
        assert "auto_trade" in data
    
    def test_api_priority_status_keys(self):
        response = client.get("/api/priority_status")
        assert response.status_code == 200
        data = response.json()
        assert "queue" in data
        assert "advisory_only" in data
        assert data["advisory_only"] is True
    
    def test_api_priority_alerts_keys(self):
        response = client.get("/api/priority_alerts")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "advisory_only" in data
        assert data["advisory_only"] is True
    
    def test_api_mode_history_keys(self):
        response = client.get("/api/mode_history")
        assert response.status_code == 200
        data = response.json()
        assert "transitions" in data
        assert "current_mode" in data

class TestR016NoDecisionTracer:
    """R016: Old wrong-topic DecisionTracer must not be present"""
    
    def test_no_decision_tracer_in_engine(self):
        assert not hasattr(engine, 'tracer'), "DecisionTracer must not be present in TradingEngine"
    
    def test_no_decision_tracer_class_imported(self):
        import server as server_module
        assert not hasattr(server_module, 'DecisionTracer'), "DecisionTracer class must not be imported"

class TestR006Regression:
    """R006 integration should not break"""
    
    def test_r006_degradation_center_exists(self):
        assert hasattr(engine, 'degradation_center')
    
    def test_r006_circuit_breaker_exists(self):
        assert hasattr(engine, 'circuit_breaker')
    
    def test_r006_health_monitor_exists(self):
        assert hasattr(engine, 'health_monitor')

class TestR007Regression:
    """R007 integration should not break"""
    
    def test_r007_silence_detector_exists(self):
        assert hasattr(engine, 'silence_detector')

class TestR008Regression:
    """R008 integration should not break"""
    
    def test_r008_mode_controller_exists(self):
        assert hasattr(engine, 'mode_controller')
    
    def test_r008_mode_recorder_exists(self):
        assert hasattr(engine, 'mode_recorder')

class TestR009Regression:
    """R009 integration should not break"""
    
    def test_r009_priority_scheduler_exists(self):
        assert hasattr(engine, 'priority_scheduler')
    
    def test_r009_priority_monitor_exists(self):
        assert hasattr(engine, 'priority_monitor')

class TestR011Regression:
    """R011 integration should not break"""
    
    def test_r011_artifact_manager_exists(self):
        assert hasattr(engine, 'artifact_manager')

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
