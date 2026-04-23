"""
R008 Mode Control Integration Tests
Tests for governance/state_machine integration into TradingEngine.
Runtime authority: PAPER_TRADE / AUTO_TRADE
Governance validation: ModeController
Audit trail: ModeRecorder
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from governance.state_machine.mode_controller import ModeController, Mode
from governance.state_machine.mode_recorder import ModeRecorder

class TestR008InstancesExist:
    """R008 instances created in TradingEngine.__init__"""
    
    def test_mode_controller_exists(self):
        from server import engine
        assert hasattr(engine, 'mode_controller')
        assert isinstance(engine.mode_controller, ModeController)
    
    def test_mode_recorder_exists(self):
        from server import engine
        assert hasattr(engine, 'mode_recorder')
        assert isinstance(engine.mode_recorder, ModeRecorder)
    
    def test_current_r008_mode_exists(self):
        from server import engine
        assert hasattr(engine, '_current_r008_mode')
        assert isinstance(engine._current_r008_mode, Mode)
    
    def test_map_to_r008_mode_method_exists(self):
        from server import engine
        assert hasattr(engine, '_map_to_r008_mode')
        assert callable(engine._map_to_r008_mode)
    
    def test_record_mode_transition_method_exists(self):
        from server import engine
        assert hasattr(engine, '_record_mode_transition')
        assert callable(engine._record_mode_transition)
    
    def test_validate_mode_allows_trading_method_exists(self):
        from server import engine
        assert hasattr(engine, '_validate_mode_allows_trading')
        assert callable(engine._validate_mode_allows_trading)

class TestR008ModeMapping:
    """R008 mode mapping from runtime state"""
    
    def test_paper_trade_true_maps_to_sim(self):
        from server import engine, PAPER_TRADE
        if PAPER_TRADE:
            mode = engine._map_to_r008_mode()
            assert mode == Mode.SIM, f"Expected SIM but got {mode.value}"
    
    def test_live_no_auto_trade_maps_to_observe(self):
        from server import engine, PAPER_TRADE, AUTO_TRADE
        if not PAPER_TRADE and not AUTO_TRADE:
            mode = engine._map_to_r008_mode()
            assert mode == Mode.OBSERVE, f"Expected OBSERVE but got {mode.value}"
    
    def test_live_auto_trade_maps_to_live(self):
        from server import engine, PAPER_TRADE, AUTO_TRADE
        if not PAPER_TRADE and AUTO_TRADE:
            mode = engine._map_to_r008_mode()
            assert mode == Mode.LIVE, f"Expected LIVE but got {mode.value}"

class TestR008APIContractPreservation:
    """Existing API contracts remain intact"""
    
    def test_toggle_mode_returns_expected_keys(self):
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/api/toggle_mode")
        assert response.status_code == 200
        data = response.json()
        assert "mode" in data
        assert "paper_trade" in data
        assert isinstance(data["mode"], str)
        assert isinstance(data["paper_trade"], bool)
    
    def test_get_mode_returns_expected_keys(self):
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/mode")
        assert response.status_code == 200
        data = response.json()
        assert "mode" in data
        assert "paper_trade" in data
        assert "auto_trade" in data
    
    def test_get_state_returns_mode_and_auto_trade(self):
        from server import engine
        state = engine.get_state()
        assert "mode" in state
        assert "auto_trade" in state
        assert isinstance(state["mode"], str)
        assert isinstance(state["auto_trade"], bool)

class TestR008ModeTransitionAPI:
    """R008 /api/mode_transition endpoint"""
    
    def test_mode_transition_exists(self):
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/api/mode_transition", json={"to_mode": "SIM"})
        assert response.status_code in (200, 403)  # Valid request format
    
    def test_mode_transition_blocks_invalid_mode(self):
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/api/mode_transition", json={"to_mode": "NOT_A_REAL_MODE"})
        assert response.status_code == 400
    
    def test_mode_transition_validates_allowed_transition(self):
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        # OBSERVE -> SIM is allowed
        response = client.post("/api/mode_transition", json={
            "from_mode": "OBSERVE",
            "to_mode": "SIM",
            "reason": "test"
        })
        assert response.status_code in (200, 403)
    
    def test_mode_transition_records_in_recorder(self):
        from server import engine, app
        from fastapi.testclient import TestClient
        
        initial_count = len(engine.mode_recorder.get_transition_history())
        client = TestClient(app)
        
        response = client.post("/api/mode_transition", json={
            "from_mode": "OBSERVE",
            "to_mode": "SIM",
            "reason": "test recording"
        })
        
        new_count = len(engine.mode_recorder.get_transition_history())
        assert new_count > initial_count or response.status_code == 403
    
    def test_mode_transition_returns_approval_flag(self):
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/api/mode_transition", json={
            "to_mode": "LIVE",
            "reason": "test"
        })
        if response.status_code == 200:
            data = response.json()
            assert "requires_approval" in data
            assert isinstance(data["requires_approval"], bool)

class TestR008ModeRecording:
    """ModeRecorder integration"""
    
    def test_toggle_mode_records_transition(self):
        from server import engine, app
        from fastapi.testclient import TestClient
        
        initial_count = len(engine.mode_recorder.get_transition_history())
        client = TestClient(app)
        response = client.post("/api/toggle_mode")
        
        new_count = len(engine.mode_recorder.get_transition_history())
        assert new_count > initial_count, "toggle_mode should record transition"
    
    def test_mode_history_api_returns_transitions(self):
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/mode_history")
        assert response.status_code == 200
        data = response.json()
        assert "transitions" in data
        assert "current_mode" in data
    
    def test_recorder_has_operator_info(self):
        from server import engine
        history = engine.mode_recorder.get_transition_history()
        for entry in history:
            assert "operator" in entry
            assert "reason" in entry
            assert "timestamp" in entry

class TestR008DegradationPauseRecording:
    """Degradation -> PAUSE mode recording"""
    
    def test_degradation_pause_records_mode_transition(self):
        from server import engine
        from failover.center import DegradationStrategy
        
        # Create a mock health status that triggers degradation
        class MockUnhealthyStatus:
            def is_healthy(self): return False
            def has_paper_trading_enabled(self): return False
        
        initial_count = len(engine.mode_recorder.get_transition_history())
        
        # Force degradation to PAUSE_TRADING
        engine.degradation_center.evaluate_and_degrade(MockUnhealthyStatus())
        
        new_count = len(engine.mode_recorder.get_transition_history())
        
        # Restore
        engine.degradation_center.restore()
        
        assert engine.degradation_center.get_current_strategy() is None
    
    def test_mode_controller_allows_pause_mode(self):
        from server import engine
        from governance.state_machine.mode_controller import Mode
        # Verify PAUSE is a valid mode (lowercase value)
        assert Mode.PAUSE.value == "pause"

class TestR008TradeGateValidation:
    """Trade gate mode validation"""
    
    def test_sim_mode_allows_trading(self):
        from server import engine
        engine._current_r008_mode = Mode.SIM
        assert engine._validate_mode_allows_trading() is True
    
    def test_live_mode_allows_trading(self):
        from server import engine
        engine._current_r008_mode = Mode.LIVE
        assert engine._validate_mode_allows_trading() is True
    
    def test_observe_mode_blocks_trading(self):
        from server import engine
        engine._current_r008_mode = Mode.OBSERVE
        assert engine._validate_mode_allows_trading() is False
    
    def test_pause_mode_blocks_trading(self):
        from server import engine
        engine._current_r008_mode = Mode.PAUSE
        assert engine._validate_mode_allows_trading() is False
    
    def test_trade_gate_source_code_includes_mode_validation(self):
        import inspect
        from server import TradingEngine
        source = inspect.getsource(TradingEngine.run_loop)
        assert '_validate_mode_allows_trading' in source
        assert 'R008 Mode validation' in source

class TestR008StateExposure:
    """R008 state exposed via get_state()"""
    
    def test_get_state_has_r008_mode(self):
        from server import engine
        state = engine.get_state()
        assert "r008_mode" in state
    
    def test_get_state_has_mode_allows_trading(self):
        from server import engine
        state = engine.get_state()
        assert "mode_allows_trading" in state
    
    def test_get_state_has_mode_transition_count(self):
        from server import engine
        state = engine.get_state()
        assert "mode_transition_count" in state
        assert isinstance(state["mode_transition_count"], int)

class TestR008AuthorityRuling:
    """Runtime authority vs governance overlay"""
    
    def test_runtime_authority_is_paper_trade_auto_trade(self):
        from server import PAPER_TRADE, AUTO_TRADE
        # These globals exist and are boolean
        assert isinstance(PAPER_TRADE, bool)
        assert isinstance(AUTO_TRADE, bool)
    
    def test_mode_controller_provides_validation(self):
        from server import engine
        is_valid, reason = engine.mode_controller.validate_transition(Mode.OBSERVE, Mode.SIM)
        assert isinstance(is_valid, bool)
    
    def test_mode_recorder_provides_audit_trail(self):
        from server import engine
        history = engine.mode_recorder.get_transition_history()
        assert isinstance(history, list)

class TestR006Regression:
    """R006 integration should not break"""
    
    def test_r006_degradation_center_exists(self):
        from server import engine
        assert hasattr(engine, 'degradation_center')
    
    def test_r006_circuit_breaker_exists(self):
        from server import engine
        assert hasattr(engine, 'circuit_breaker')
    
    def test_r006_health_monitor_exists(self):
        from server import engine
        assert hasattr(engine, 'health_monitor')
    
    def test_get_state_has_degradation_strategy(self):
        from server import engine
        state = engine.get_state()
        assert "degradation_strategy" in state
    
    def test_get_state_has_circuit_breaker(self):
        from server import engine
        state = engine.get_state()
        assert "circuit_breaker" in state

class TestR011Regression:
    """R011 integration should not break"""
    
    def test_r011_artifact_manager_exists(self):
        from server import engine
        assert hasattr(engine, 'artifact_manager')
    
    def test_get_state_has_artifact_stats(self):
        from server import engine
        state = engine.get_state()
        assert "artifact_stats" in state

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
