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
        assert isinstance(report['market_data'], float) or report['market_data'] is None
        assert isinstance(report['trades'], float) or report['trades'] is None
    
    def test_reset_then_is_silent(self):
        """After reset(), is_silent() must return True (fail-closed)"""
        detector = SilenceDetector()
        detector.update_market_data()
        detector.update_trades()
        detector.update_heartbeat()
        assert detector.last_market_data_update is not None
        detector.reset()
        assert detector.is_silent() == True

    def test_all_timestamps_none_is_silent(self):
        """All timestamps None → is_silent() must return True (fail-closed)"""
        detector = SilenceDetector(
            market_data_timeout=30,
            trades_timeout=60,
            heartbeat_timeout=300
        )
        assert detector.last_market_data_update is None
        assert detector.last_trades_update is None
        assert detector.last_heartbeat_update is None
        assert detector.is_silent() == True

    def test_market_data_none_trades_heartbeat_fresh(self):
        """market_data=None, trades+heartbeat fresh → is_silent() must return True"""
        detector = SilenceDetector(
            market_data_timeout=30,
            trades_timeout=60,
            heartbeat_timeout=300
        )
        detector.last_market_data_update = None
        detector.update_trades()
        detector.update_heartbeat()
        assert detector.is_silent() == True

    def test_trades_none_others_fresh(self):
        """trades=None, market_data+heartbeat fresh → is_silent() must return True"""
        detector = SilenceDetector(
            market_data_timeout=30,
            trades_timeout=60,
            heartbeat_timeout=300
        )
        detector.update_market_data()
        detector.last_trades_update = None
        detector.update_heartbeat()
        assert detector.is_silent() == True

    def test_heartbeat_none_others_fresh(self):
        """heartbeat=None, market_data+trades fresh → is_silent() must return True"""
        detector = SilenceDetector(
            market_data_timeout=30,
            trades_timeout=60,
            heartbeat_timeout=300
        )
        detector.update_market_data()
        detector.update_trades()
        detector.last_heartbeat_update = None
        assert detector.is_silent() == True

    def test_malformed_timestamp_is_silent(self):
        """Malformed/non-datetime timestamp → is_silent() must return True (fail-closed)"""
        detector = SilenceDetector(
            market_data_timeout=30,
            trades_timeout=60,
            heartbeat_timeout=300
        )
        detector.last_market_data_update = "not-a-datetime"
        detector.update_trades()
        detector.update_heartbeat()
        assert detector.is_silent() == True

        detector2 = SilenceDetector(market_data_timeout=30, trades_timeout=60, heartbeat_timeout=300)
        detector2.last_market_data_update = 12345
        detector2.update_trades()
        detector2.update_heartbeat()
        assert detector2.is_silent() == True

    def test_mixed_stale_and_none(self):
        """One channel stale, another None → is_silent() must return True"""
        detector = SilenceDetector(
            market_data_timeout=1,
            trades_timeout=60,
            heartbeat_timeout=300
        )
        detector.update_market_data()
        time.sleep(1.1)
        detector.last_trades_update = None
        detector.update_heartbeat()
        assert detector.is_silent() == True

    def test_expired_market_data_is_silent(self):
        """market_data expired, others fresh → is_silent() returns True"""
        detector = SilenceDetector(
            market_data_timeout=1,
            trades_timeout=60,
            heartbeat_timeout=300
        )
        detector.update_market_data()
        time.sleep(1.1)
        detector.update_trades()
        detector.update_heartbeat()
        assert detector.is_silent() == True

    def test_expired_trades_is_silent(self):
        """trades expired, others fresh → is_silent() returns True"""
        detector = SilenceDetector(
            market_data_timeout=30,
            trades_timeout=1,
            heartbeat_timeout=300
        )
        detector.update_market_data()
        detector.update_trades()
        time.sleep(1.1)
        detector.update_heartbeat()
        assert detector.is_silent() == True

    def test_expired_heartbeat_is_silent(self):
        """heartbeat expired, others fresh → is_silent() returns True"""
        detector = SilenceDetector(
            market_data_timeout=30,
            trades_timeout=60,
            heartbeat_timeout=1
        )
        detector.update_market_data()
        detector.update_trades()
        detector.update_heartbeat()
        time.sleep(1.1)
        assert detector.is_silent() == True

    def test_get_silence_report_all_none(self):
        """get_silence_report() with all None → all fields None (no mixed types)"""
        detector = SilenceDetector()
        detector.last_market_data_update = None
        detector.last_trades_update = None
        detector.last_heartbeat_update = None
        report = detector.get_silence_report()
        assert report['market_data'] is None
        assert report['trades'] is None
        assert report['heartbeat'] is None

    def test_get_silence_report_malformed_timestamp(self):
        """get_silence_report() with malformed timestamp → None (not exception)"""
        detector = SilenceDetector()
        detector.last_market_data_update = "bad-value"
        detector.update_trades()
        detector.update_heartbeat()
        report = detector.get_silence_report()
        assert report['market_data'] is None
        assert report['trades'] is not None

    def test_silence_report_consistent_types(self):
        """get_silence_report() returns consistent types when all timestamps valid"""
        detector = SilenceDetector()
        detector.update_market_data()
        detector.update_trades()
        detector.update_heartbeat()
        report = detector.get_silence_report()
        assert isinstance(report['market_data'], float)
        assert isinstance(report['trades'], float)
        assert isinstance(report['heartbeat'], float)


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
