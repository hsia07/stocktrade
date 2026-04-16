"""
Round 7 Tests: Silence Protection / Abnormal Silence Detection
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta

# Import our modules
from monitoring.silence.detector import SilenceDetector
from monitoring.silence.recovery import SilenceRecovery, SilenceReport


class TestSilenceDetector:
    """Test silence detection functionality"""
    
    def test_detector_initialization(self):
        """SilenceDetector initializes with correct timeout values"""
        detector = SilenceDetector(
            market_data_timeout=30,
            trades_timeout=60,
            heartbeat_timeout=300
        )
        
        assert detector.market_data_timeout == timedelta(seconds=30)
        assert detector.trades_timeout == timedelta(seconds=60)
        assert detector.heartbeat_timeout == timedelta(seconds=300)
    
    def test_update_methods(self):
        """Update methods set timestamps correctly"""
        detector = SilenceDetector()
        
        detector.update_market_data()
        assert detector.last_market_data_update is not None
        
        detector.update_trades()
        assert detector.last_trades_update is not None
        
        detector.update_heartbeat()
        assert detector.last_heartbeat_update is not None
    
    def test_is_silent_with_fresh_data(self):
        """is_silent returns False when data is fresh"""
        detector = SilenceDetector(
            market_data_timeout=30,
            trades_timeout=60,
            heartbeat_timeout=300
        )
        
        detector.update_market_data()
        detector.update_trades()
        detector.update_heartbeat()
        
        assert detector.is_silent() == False
    
    def test_is_silent_with_stale_data(self):
        """is_silent returns True when data is stale"""
        detector = SilenceDetector(
            market_data_timeout=1,  # 1 second timeout for testing
            trades_timeout=60,
            heartbeat_timeout=300
        )
        
        detector.update_market_data()
        time.sleep(1.1)  # Wait for timeout
        
        assert detector.is_silent() == True
    
    def test_get_silence_report(self):
        """get_silence_report returns correct report structure"""
        detector = SilenceDetector()
        detector.update_market_data()
        detector.update_trades()
        
        report = detector.get_silence_report()
        
        assert 'market_data' in report
        assert 'trades' in report
        assert 'heartbeat' in report
        assert isinstance(report['market_data'], float) or report['market_data'] == 'Never updated'
        assert isinstance(report['trades'], float) or report['trades'] == 'Never updated'
    
    def test_reset(self):
        """reset clears all timestamps"""
        detector = SilenceDetector()
        
        detector.update_market_data()
        detector.update_trades()
        detector.update_heartbeat()
        
        detector.reset()
        
        assert detector.last_market_data_update is None
        assert detector.last_trades_update is None
        assert detector.last_heartbeat_update is None


class TestSilenceRecovery:
    """Test silence recovery functionality"""
    
    def test_recovery_initialization(self):
        """SilenceRecovery initializes correctly"""
        recovery = SilenceRecovery()
        
        assert recovery.recovery_history == []
    
    def test_determine_escalation_level(self):
        """Escalation levels determined correctly"""
        recovery = SilenceRecovery()
        
        assert recovery._determine_escalation_level(5) == 1
        assert recovery._determine_escalation_level(20) == 2
        assert recovery._determine_escalation_level(45) == 3
        assert recovery._determine_escalation_level(90) == 4
    
    def test_get_strategy(self):
        """Strategy selected based on escalation level"""
        recovery = SilenceRecovery()
        
        from monitoring.silence.recovery import RecoveryStrategy
        
        assert recovery._get_strategy(1) == RecoveryStrategy.LOG_ALERT
        assert recovery._get_strategy(2) == RecoveryStrategy.NOTIFY_ADMIN
        assert recovery._get_strategy(3) == RecoveryStrategy.SWITCH_TO_OBSERVE
        assert recovery._get_strategy(4) == RecoveryStrategy.PAUSE_TRADING
    
    def test_recovery_history_tracking(self):
        """Recovery actions are tracked in history"""
        recovery = SilenceRecovery()
        
        report = SilenceReport(
            start_time=datetime.now(),
            duration=5
        )
        
        recovery.evaluate_and_recover(report)
        
        assert len(recovery.recovery_history) == 1
        assert 'start_time' in recovery.recovery_history[0]
        assert 'duration' in recovery.recovery_history[0]
        assert 'strategy' in recovery.recovery_history[0]


class TestIntegration:
    """Test integration between detector and recovery"""
    
    def test_silence_triggers_recovery(self):
        """Silence detection can trigger recovery workflow"""
        detector = SilenceDetector(
            market_data_timeout=1,  # Short timeout for testing
            trades_timeout=60,
            heartbeat_timeout=300
        )
        recovery = SilenceRecovery()
        
        # Initial update
        detector.update_market_data()
        
        # Wait for silence
        time.sleep(1.1)
        
        # Check silence
        is_silent = detector.is_silent()
        assert is_silent == True
        
        # Get report and trigger recovery
        if is_silent:
            report = SilenceReport(
                start_time=datetime.now() - timedelta(seconds=5),
                duration=5
            )
            recovery.evaluate_and_recover(report)
        
        assert len(recovery.recovery_history) >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
