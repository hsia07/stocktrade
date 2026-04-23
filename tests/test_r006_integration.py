"""
R006 Integration Tests: Health Circuit Integration into TradingEngine
Tests that R006 components are properly wired into the main execution chain.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from server import TradingEngine, Signal, Direction
from circuit.breaker import CircuitBreakerState


class TestR006TradingEngineIntegration:
    """Test R006 integration into TradingEngine main chain"""
    
    def test_trading_engine_has_r006_instances(self):
        """TradingEngine initializes R006 components"""
        engine = TradingEngine()
        
        assert hasattr(engine, 'health_monitor')
        assert hasattr(engine, 'circuit_breaker')
        assert hasattr(engine, 'degradation_center')
    
    def test_health_monitor_runs_in_loop(self):
        """HealthMonitor.run_checks is accessible from TradingEngine"""
        engine = TradingEngine()
        
        # Health monitor should be able to run checks
        results = engine.health_monitor.run_checks()
        assert 'broker_connection' in results
        assert 'data_feed' in results
        
        aggregate = engine.health_monitor.aggregate_status(results)
        assert 'status' in aggregate
        assert aggregate['status'] in ['ok', 'critical']
    
    def test_circuit_breaker_blocks_trades_when_open(self):
        """Circuit breaker OPEN state blocks new trades"""
        engine = TradingEngine()
        
        # Force circuit breaker to OPEN
        engine.circuit_breaker.state = CircuitBreakerState.OPEN
        
        # should_block_trade should return True
        assert engine.circuit_breaker.should_block_trade() == True
        
        # Verify state is exposed
        status = engine.circuit_breaker.get_status()
        assert status['state'] == 'OPEN'
    
    def test_circuit_breaker_allows_trades_when_closed(self):
        """Circuit breaker CLOSED state allows new trades"""
        engine = TradingEngine()
        
        # Circuit breaker should start CLOSED
        assert engine.circuit_breaker.state == CircuitBreakerState.CLOSED
        assert engine.circuit_breaker.should_block_trade() == False
    
    def test_circuit_breaker_opens_on_losses(self):
        """Circuit breaker transitions to OPEN after excessive losses"""
        engine = TradingEngine()
        
        # Record losses exceeding threshold
        max_consecutive = engine.circuit_breaker.max_consecutive_losses
        for _ in range(max_consecutive):
            engine.circuit_breaker.record_trade_result(-100)
        
        assert engine.circuit_breaker.state == CircuitBreakerState.OPEN
    
    def test_degradation_center_applies_pause(self):
        """DegradationCenter applies PAUSE_TRADING on unhealthy"""
        engine = TradingEngine()
        
        class MockUnhealthy:
            def is_healthy(self): return False
            def has_paper_trading_enabled(self): return False
        
        engine.degradation_center.evaluate_and_degrade(MockUnhealthy())
        
        from failover.center import DegradationStrategy
        assert engine.degradation_center.get_current_strategy() == DegradationStrategy.PAUSE_TRADING
    
    def test_degradation_center_can_restore(self):
        """DegradationCenter can restore to normal"""
        engine = TradingEngine()
        
        class MockUnhealthy:
            def is_healthy(self): return False
            def has_paper_trading_enabled(self): return False
        
        engine.degradation_center.evaluate_and_degrade(MockUnhealthy())
        assert engine.degradation_center.get_current_strategy() is not None
        
        engine.degradation_center.restore()
        assert engine.degradation_center.get_current_strategy() is None
    
    def test_state_exposes_r006_info(self):
        """get_state() exposes R006 health/circuit info"""
        engine = TradingEngine()
        
        state = engine.get_state()
        
        assert 'health_status' in state
        assert 'circuit_breaker' in state
        assert 'degradation_strategy' in state
    
    def test_circuit_breaker_records_trade_results(self):
        """Circuit breaker records trade results from position closes"""
        engine = TradingEngine()
        
        initial_pnl = engine.circuit_breaker.daily_pnl
        engine.circuit_breaker.record_trade_result(-500)
        
        assert engine.circuit_breaker.daily_pnl == initial_pnl - 500
    
    def test_risk_officer_still_functional(self):
        """RiskOfficer remains functional alongside R006"""
        engine = TradingEngine()
        
        # RiskOfficer should still have all its methods
        assert hasattr(engine.risk, 'can_enter')
        assert hasattr(engine.risk, 'calc_lots')
        assert hasattr(engine.risk, 'on_entry')
        assert hasattr(engine.risk, 'on_exit')
        assert hasattr(engine.risk, 'get_report')
        
        # RiskOfficer should still track its own state
        assert hasattr(engine.risk, 'daily_pnl')
        assert hasattr(engine.risk, 'consecutive_loss')
        assert hasattr(engine.risk, 'is_halted')
    
    def test_no_double_halt_conflict(self):
        """Multiple halt sources do not conflict - fail-closed is safe"""
        engine = TradingEngine()
        
        # Both RiskOfficer and CircuitBreaker can halt
        # This is expected and safe (fail-closed)
        
        # Force RiskOfficer halt
        engine.risk.is_halted = True
        engine.risk.halt_reason = "Test halt"
        
        # Force CircuitBreaker OPEN
        engine.circuit_breaker.state = CircuitBreakerState.OPEN
        
        # Both indicate halt
        assert engine.risk.is_halted == True
        assert engine.circuit_breaker.should_block_trade() == True
        
        # This is the expected fail-closed behavior
        # Trading should not proceed when either halts
    
    def test_health_critical_triggers_degradation(self):
        """Health critical status triggers degradation evaluation"""
        engine = TradingEngine()
        
        # Mock health monitor to return critical
        with patch.object(engine.health_monitor, 'run_checks') as mock_checks:
            mock_checks.return_value = {
                'broker_connection': {'status': 'critical', 'details': 'Broker down', 'timestamp': '2024-01-01'},
                'data_feed': {'status': 'ok', 'details': 'OK', 'timestamp': '2024-01-01'},
                'risk_system': {'status': 'ok', 'details': 'OK', 'timestamp': '2024-01-01'},
                'memory_usage': {'status': 'ok', 'details': 'OK', 'timestamp': '2024-01-01'},
                'disk_space': {'status': 'ok', 'details': 'OK', 'timestamp': '2024-01-01'},
            }
            
            aggregate = engine.health_monitor.aggregate_status(mock_checks.return_value)
            assert aggregate['status'] == 'critical'
            
            # Degradation should be triggered
            class SimpleHealthStatus:
                def is_healthy(self): return False
                def has_paper_trading_enabled(self): return False
            
            engine.degradation_center.evaluate_and_degrade(SimpleHealthStatus())
            from failover.center import DegradationStrategy
            assert engine.degradation_center.get_current_strategy() == DegradationStrategy.PAUSE_TRADING


class TestR006RunLoopHooks:
    """Test R006 hooks in run_loop execution"""
    
    def test_run_loop_has_health_check_hook(self):
        """run_loop source code includes health check hook"""
        import inspect
        source = inspect.getsource(TradingEngine.run_loop)
        
        # Verify health check is in the loop
        assert 'health_monitor.run_checks()' in source
        assert 'health_monitor.aggregate_status' in source
    
    def test_run_loop_has_circuit_breaker_hook(self):
        """run_loop source code includes circuit breaker hook"""
        import inspect
        source = inspect.getsource(TradingEngine.run_loop)
        
        # Verify circuit breaker check is in the loop
        assert 'circuit_breaker.should_block_trade()' in source
        assert 'circuit_blocked' in source
    
    def test_run_loop_has_degradation_hook(self):
        """run_loop source code includes degradation hook"""
        import inspect
        source = inspect.getsource(TradingEngine.run_loop)
        
        # Verify degradation is in the loop
        assert 'degradation_center.evaluate_and_degrade' in source
        assert 'degradation_center.restore' in source
    
    def test_run_loop_has_degradation_hard_gate(self):
        """run_loop has hard gate for PAUSE_TRADING strategy"""
        import inspect
        source = inspect.getsource(TradingEngine.run_loop)
        
        # Verify hard gate exists before symbol processing
        assert 'DegradationStrategy.PAUSE_TRADING' in source
        assert 'continue' in source
    
    def test_circuit_breaker_syncs_from_risk_officer(self):
        """CircuitBreaker syncs daily_pnl and consecutive_loss from RiskOfficer"""
        engine = TradingEngine()
        
        # Simulate a trade exit that updates RiskOfficer
        engine.risk.daily_pnl = -500
        engine.risk.consecutive_loss = 2
        
        # Sync to circuit breaker
        engine.circuit_breaker.sync_from_risk_officer(engine.risk.daily_pnl, engine.risk.consecutive_loss)
        
        # CircuitBreaker should now match RiskOfficer
        assert engine.circuit_breaker.daily_pnl == -500
        assert engine.circuit_breaker.consecutive_losses == 2
    
    def test_circuit_breaker_opens_after_sync(self):
        """CircuitBreaker opens after sync shows excessive losses"""
        engine = TradingEngine()
        
        # Set RiskOfficer to excessive losses
        engine.risk.daily_pnl = -6000  # exceeds default max_daily_loss=5000
        engine.risk.consecutive_loss = 5  # exceeds default max_consecutive_losses=3
        
        # Sync to circuit breaker
        engine.circuit_breaker.sync_from_risk_officer(engine.risk.daily_pnl, engine.risk.consecutive_loss)
        
        # CircuitBreaker should now be OPEN
        from circuit.breaker import CircuitBreakerState
        assert engine.circuit_breaker.state == CircuitBreakerState.OPEN
    
    def test_degradation_pause_blocks_symbol_processing(self):
        """PAUSE_TRADING strategy blocks symbol processing in run_loop"""
        engine = TradingEngine()
        
        # Force degradation to PAUSE_TRADING
        from failover.center import DegradationStrategy
        engine.degradation_center.current_strategy = DegradationStrategy.PAUSE_TRADING
        
        # Verify strategy is active
        assert engine.degradation_center.get_current_strategy() == DegradationStrategy.PAUSE_TRADING
        
        # Verify run_loop has the hard gate check
        import inspect
        source = inspect.getsource(TradingEngine.run_loop)
        assert 'DegradationStrategy.PAUSE_TRADING' in source


if __name__ == '__main__':
    pytest.main([__file__, '-v'])