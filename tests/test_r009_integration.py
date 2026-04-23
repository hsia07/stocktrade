"""
R009 Execution Model Integration Tests
Tests for scheduler/priority integration into TradingEngine as advisory overlay.
Execution authority: TradingEngine.run_loop() (unchanged)
PriorityScheduler: Advisory task tracking only
PriorityMonitor: Metrics and alerts only
"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scheduler.priority.scheduler import PriorityScheduler, CommandRouter, Priority, Task, TaskType
from scheduler.priority.monitor import PriorityMonitor

class TestR009InstancesExist:
    """R009 instances created in TradingEngine.__init__"""
    
    def test_priority_scheduler_exists(self):
        from server import engine
        assert hasattr(engine, 'priority_scheduler')
        assert isinstance(engine.priority_scheduler, PriorityScheduler)
    
    def test_priority_monitor_exists(self):
        from server import engine
        assert hasattr(engine, 'priority_monitor')
        assert isinstance(engine.priority_monitor, PriorityMonitor)
    
    def test_command_router_exists(self):
        from server import engine
        assert hasattr(engine, 'command_router')
        assert isinstance(engine.command_router, CommandRouter)
    
    def test_r009_handlers_registered(self):
        from server import engine
        assert TaskType.TRADE_EXECUTION in engine.command_router.handlers
        assert TaskType.RISK_CHECK in engine.command_router.handlers
        assert TaskType.MARKET_DATA in engine.command_router.handlers

class TestR009TaskRecording:
    """R009 task recording in run_loop"""
    
    def test_signal_generates_market_data_task(self):
        from server import engine
        initial_count = engine.priority_scheduler.get_queue_status()['total_tasks']
        # Simulate a signal by calling _record_priority_task directly
        engine._record_priority_task("test-signal", "Test Signal", Priority.HIGH, TaskType.MARKET_DATA)
        new_count = engine.priority_scheduler.get_queue_status()['total_tasks']
        assert new_count > initial_count
    
    def test_trade_generates_trade_execution_task(self):
        from server import engine
        initial_count = engine.priority_scheduler.get_queue_status()['total_tasks']
        engine._record_priority_task("test-trade", "Test Trade", Priority.CRITICAL, TaskType.TRADE_EXECUTION)
        new_count = engine.priority_scheduler.get_queue_status()['total_tasks']
        assert new_count > initial_count
    
    def test_risk_block_generates_risk_check_task(self):
        from server import engine
        initial_count = engine.priority_scheduler.get_queue_status()['total_tasks']
        engine._record_priority_task("test-risk", "Test Risk Block", Priority.HIGH, TaskType.RISK_CHECK)
        new_count = engine.priority_scheduler.get_queue_status()['total_tasks']
        assert new_count > initial_count
    
    def test_degradation_generates_critical_task(self):
        from server import engine
        initial_count = engine.priority_scheduler.get_queue_status()['total_tasks']
        engine._record_priority_task("test-degradation", "Degradation Event", Priority.CRITICAL, TaskType.RISK_CHECK)
        new_count = engine.priority_scheduler.get_queue_status()['total_tasks']
        assert new_count > initial_count

class TestR009APIEndpoints:
    """R009 API endpoints"""
    
    def test_priority_status_exists(self):
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/priority_status")
        assert response.status_code == 200
        data = response.json()
        assert "queue" in data
        assert "advisory_only" in data
        assert data["advisory_only"] is True
    
    def test_priority_alerts_exists(self):
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/priority_alerts")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "advisory_only" in data
        assert data["advisory_only"] is True
    
    def test_priority_status_has_queue_fields(self):
        from server import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/priority_status")
        data = response.json()
        queue = data["queue"]
        assert "total_tasks" in queue
        assert "by_priority" in queue

class TestR009StateExposure:
    """R009 state exposed via get_state()"""
    
    def test_get_state_has_r009_queue(self):
        from server import engine
        state = engine.get_state()
        assert "r009_queue" in state
    
    def test_get_state_has_r009_alerts(self):
        from server import engine
        state = engine.get_state()
        assert "r009_alerts" in state
    
    def test_r009_queue_has_total_tasks(self):
        from server import engine
        state = engine.get_state()
        queue = state["r009_queue"]
        assert "total_tasks" in queue
        assert isinstance(queue["total_tasks"], int)
    
    def test_r009_queue_has_by_priority(self):
        from server import engine
        state = engine.get_state()
        queue = state["r009_queue"]
        assert "by_priority" in queue

class TestR009AuthorityRuling:
    """Execution authority remains with run_loop"""
    
    def test_run_loop_source_code_unchanged(self):
        import inspect
        from server import TradingEngine
        source = inspect.getsource(TradingEngine.run_loop)
        # Verify key execution elements still present
        assert "for sym in WATCH_LIST:" in source
        assert "AUTO_TRADE" in source
        assert "execution.place" in source
    
    def test_scheduler_is_advisory_only(self):
        from server import engine
        # Scheduler should not control execution
        assert hasattr(engine, 'priority_scheduler')
        # The _record_priority_task method should not raise on failure
        try:
            engine._record_priority_task("test", "Test", Priority.HIGH, TaskType.MARKET_DATA)
        except Exception:
            pytest.fail("_record_priority_task should not raise")

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

class TestR007Regression:
    """R007 integration should not break"""
    
    def test_r007_silence_detector_exists(self):
        from server import engine
        assert hasattr(engine, 'silence_detector')
    
    def test_r007_silence_recovery_exists(self):
        from server import engine
        assert hasattr(engine, 'silence_recovery')

class TestR008Regression:
    """R008 integration should not break"""
    
    def test_r008_mode_controller_exists(self):
        from server import engine
        assert hasattr(engine, 'mode_controller')
    
    def test_r008_mode_recorder_exists(self):
        from server import engine
        assert hasattr(engine, 'mode_recorder')
    
    def test_get_state_has_r008_mode(self):
        from server import engine
        state = engine.get_state()
        assert "r008_mode" in state

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
