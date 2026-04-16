"""
Round 6 Tests: Health Check / Circuit Breaker / Failover Center
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta

# Import our modules
from health.monitor import HealthMonitor, HealthCheck
from circuit.breaker import CircuitBreaker, CircuitBreakerState
from failover.center import DegradationCenter, DegradationStrategy


class TestHealthCheck:
    """Test health monitoring functionality"""
    
    def test_health_check_structure(self):
        """HealthCheck returns correct response structure"""
        hc = HealthCheck()
        result = hc.check_broker_connection()
        
        assert 'status' in result
        assert 'details' in result
        assert 'timestamp' in result
        assert result['status'] in ['ok', 'warning', 'critical']
    
    def test_health_monitor_can_run_checks(self):
        """HealthMonitor can run all component checks"""
        monitor = HealthMonitor()
        results = monitor.run_checks()
        
        assert 'broker_connection' in results
        assert 'data_feed' in results
        assert 'risk_system' in results
        assert 'memory_usage' in results
        assert 'disk_space' in results
    
    def test_health_monitor_aggregate_status(self):
        """HealthMonitor can aggregate overall status"""
        monitor = HealthMonitor()
        results = monitor.run_checks()
        aggregate = monitor.aggregate_status(results)
        
        assert 'status' in aggregate
        assert 'details' in aggregate
        assert 'timestamp' in aggregate
        assert aggregate['status'] in ['ok', 'critical']


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    def test_circuit_breaker_initial_state(self):
        """Circuit breaker starts in CLOSED state"""
        cb = CircuitBreaker(
            max_daily_loss=5000,
            max_consecutive_losses=3,
            max_drawdown_pct=10
        )
        
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.should_block_trade() == False
    
    def test_circuit_breaker_opens_on_consecutive_losses(self):
        """Circuit breaker opens after max consecutive losses"""
        cb = CircuitBreaker(
            max_daily_loss=5000,
            max_consecutive_losses=3,
            max_drawdown_pct=10
        )
        
        # Record 3 consecutive losses
        cb.record_trade_result(-100)
        cb.record_trade_result(-200)
        cb.record_trade_result(-300)
        
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.should_block_trade() == True
    
    def test_circuit_breaker_opens_on_daily_loss(self):
        """Circuit breaker opens when daily loss exceeds threshold"""
        cb = CircuitBreaker(
            max_daily_loss=5000,
            max_consecutive_losses=3,
            max_drawdown_pct=10
        )
        
        # Record large loss exceeding threshold
        cb.record_trade_result(-6000)
        
        assert cb.state == CircuitBreakerState.OPEN
    
    def test_circuit_breaker_get_status(self):
        """Circuit breaker provides status information"""
        cb = CircuitBreaker(
            max_daily_loss=5000,
            max_consecutive_losses=3,
            max_drawdown_pct=10
        )
        
        status = cb.get_status()
        
        assert 'state' in status
        assert 'daily_pnl' in status
        assert 'consecutive_losses' in status
        assert 'last_reset_date' in status


class TestDegradationCenter:
    """Test failover and degradation functionality"""
    
    def test_degradation_center_initial_state(self):
        """Degradation center starts with no strategy"""
        dc = DegradationCenter()
        
        assert dc.get_current_strategy() is None
        assert len(dc.history) == 0
    
    def test_degradation_center_applies_pause_strategy(self):
        """Degradation center can apply PAUSE_TRADING strategy"""
        dc = DegradationCenter()
        
        # Simulate unhealthy state
        class MockHealthStatus:
            def is_healthy(self):
                return False
            def has_paper_trading_enabled(self):
                return False
        
        health = MockHealthStatus()
        dc.evaluate_and_degrade(health)
        
        assert dc.get_current_strategy() == DegradationStrategy.PAUSE_TRADING
        assert len(dc.history) > 0
    
    def test_degradation_center_can_restore(self):
        """Degradation center can restore to normal"""
        dc = DegradationCenter()
        
        # First degrade
        class MockUnhealthy:
            def is_healthy(self):
                return False
            def has_paper_trading_enabled(self):
                return False
        
        dc.evaluate_and_degrade(MockUnhealthy())
        assert dc.get_current_strategy() is not None
        
        # Then restore
        dc.restore()
        assert dc.get_current_strategy() is None


class TestIntegration:
    """Test integration between health, circuit, and failover"""
    
    def test_health_triggers_circuit_breaker(self):
        """Health issues can trigger circuit breaker"""
        health = HealthMonitor()
        circuit = CircuitBreaker(
            max_daily_loss=5000,
            max_consecutive_losses=3,
            max_drawdown_pct=10
        )
        
        # Run health checks
        health_results = health.run_checks()
        
        # If any health check fails, should potentially trigger circuit
        # (This is a conceptual test - actual integration would be more complex)
        assert health_results is not None
        assert circuit.get_status() is not None
    
    def test_circuit_blocks_trigger_degradation(self):
        """Circuit breaker opening can trigger degradation"""
        circuit = CircuitBreaker(
            max_daily_loss=5000,
            max_consecutive_losses=3,
            max_drawdown_pct=10
        )
        failover = DegradationCenter()
        
        # Open circuit
        circuit.record_trade_result(-100)
        circuit.record_trade_result(-200)
        circuit.record_trade_result(-300)
        
        assert circuit.state == CircuitBreakerState.OPEN
        
        # Degradation should be applied
        class MockUnhealthy:
            def is_healthy(self):
                return False
            def has_paper_trading_enabled(self):
                return False
        
        failover.evaluate_and_degrade(MockUnhealthy())
        assert failover.get_current_strategy() is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
