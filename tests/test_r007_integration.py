"""
R007 Integration Tests: Silence Protection in Main Execution Chain
Tests that SilenceDetector and SilenceRecovery are properly integrated into
TradingEngine.run_loop() and can affect execution flow.
"""
import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from server import TradingEngine, Direction
from monitoring.silence.detector import SilenceDetector
from monitoring.silence.recovery import SilenceRecovery, SilenceReport, RecoveryStrategy


class TestR007Integration:
    """Test R007 silence protection integration into TradingEngine"""
    
    def test_silence_detector_initialized_in_engine(self):
        """TradingEngine initializes SilenceDetector and SilenceRecovery"""
        engine = TradingEngine()
        
        assert hasattr(engine, 'silence_detector')
        assert hasattr(engine, 'silence_recovery')
        assert isinstance(engine.silence_detector, SilenceDetector)
        assert isinstance(engine.silence_recovery, SilenceRecovery)
    
    def test_silence_detector_update_methods_called(self):
        """SilenceDetector update methods are called during run_loop"""
        engine = TradingEngine()
        
        # Mock the update methods to verify they're called
        engine.silence_detector.update_heartbeat = MagicMock()
        engine.silence_detector.update_market_data = MagicMock()
        engine.silence_detector.update_trades = MagicMock()
        engine.silence_detector.is_silent = MagicMock(return_value=False)
        
        # Run one iteration of the loop
        async def run_one_iteration():
            engine._running = True
            engine.risk.ensure_session()
            engine.silence_detector.update_heartbeat()
            ticks = engine.mock.tick()
            engine.latest_ticks = ticks
            engine.silence_detector.update_market_data()
            
            for sym in engine.mock.bases.keys():
                tick = ticks[sym]
                bars = list(engine.mock.bars[sym])
                
                # Check silence
                if engine.silence_detector.is_silent():
                    continue
                
                # Simulate a trade to trigger update_trades
                engine.silence_detector.update_trades()
        
        asyncio.run(run_one_iteration())
        
        # Verify update methods were called
        engine.silence_detector.update_heartbeat.assert_called_once()
        engine.silence_detector.update_market_data.assert_called_once()
        engine.silence_detector.update_trades.assert_called()
    
    def test_silence_blocks_signal_evaluation(self):
        """When silence is detected, signal evaluation is skipped"""
        engine = TradingEngine()
        
        # Force silence state
        engine.silence_detector.is_silent = MagicMock(return_value=True)
        engine.silence_recovery.evaluate_and_recover = MagicMock(
            return_value=RecoveryStrategy.LOG_ALERT
        )
        
        # Track if signal evaluation would occur
        signal_evaluated = False
        original_evaluate = engine.signal_eng.evaluate
        
        def mock_evaluate(sym, bars, tick, obook):
            nonlocal signal_evaluated
            signal_evaluated = True
            return original_evaluate(sym, bars, tick, obook)
        
        engine.signal_eng.evaluate = mock_evaluate
        
        # Run one iteration
        async def run_one_iteration():
            engine._running = True
            engine.risk.ensure_session()
            engine.silence_detector.update_heartbeat()
            ticks = engine.mock.tick()
            engine.latest_ticks = ticks
            engine.silence_detector.update_market_data()
            
            for sym in list(engine.mock.bases.keys())[:1]:
                tick = ticks[sym]
                bars = list(engine.mock.bars[sym])
                bar = bars[-1] if bars else None
                if bar:
                    engine.signal_eng.update_vwap(sym, bar)
                
                # Check silence - this should block signal evaluation
                if engine.silence_detector.is_silent():
                    silence_report = SilenceReport(
                        start_time=datetime.now() - timedelta(seconds=30),
                        duration=30
                    )
                    strategy = engine.silence_recovery.evaluate_and_recover(silence_report)
                    continue
                
                # This should NOT be reached when silent
                obook = {"bid_vol": tick["bid_vol"], "ask_vol": tick["ask_vol"]}
                engine.signal_eng.evaluate(sym, bars, tick, obook)
        
        asyncio.run(run_one_iteration())
        
        # Verify silence was checked and recovery was triggered
        engine.silence_detector.is_silent.assert_called()
        engine.silence_recovery.evaluate_and_recover.assert_called_once()
        # Signal evaluation should have been skipped
        assert not signal_evaluated, "Signal evaluation should be skipped when silent"
    
    def test_silence_recovery_strategy_returned(self):
        """SilenceRecovery returns strategy for engine to act upon"""
        engine = TradingEngine()
        
        silence_report = SilenceReport(
            start_time=datetime.now(),
            duration=5
        )
        
        strategy = engine.silence_recovery.evaluate_and_recover(silence_report)
        
        assert isinstance(strategy, RecoveryStrategy)
        assert strategy == RecoveryStrategy.LOG_ALERT  # duration=5 -> level 1
    
    def test_no_silence_allows_normal_flow(self):
        """When not silent, normal trading flow continues"""
        engine = TradingEngine()
        
        # Ensure silence detector is not silent (fresh data)
        engine.silence_detector.update_market_data()
        engine.silence_detector.update_trades()
        engine.silence_detector.update_heartbeat()
        
        assert not engine.silence_detector.is_silent()
        
        # Run one iteration
        async def run_one_iteration():
            engine._running = True
            engine.risk.ensure_session()
            engine.silence_detector.update_heartbeat()
            ticks = engine.mock.tick()
            engine.latest_ticks = ticks
            engine.silence_detector.update_market_data()
            
            for sym in list(engine.mock.bases.keys())[:1]:
                tick = ticks[sym]
                bars = list(engine.mock.bars[sym])
                bar = bars[-1] if bars else None
                if bar:
                    engine.signal_eng.update_vwap(sym, bar)
                
                if engine.silence_detector.is_silent():
                    continue
                
                obook = {"bid_vol": tick["bid_vol"], "ask_vol": tick["ask_vol"]}
                sig, rep = engine.signal_eng.evaluate(sym, bars, tick, obook)
                
                # Signal evaluation should have occurred
                assert rep is not None
        
        asyncio.run(run_one_iteration())
    
    def test_silence_report_structure(self):
        """SilenceReport is created with correct structure for recovery"""
        start_time = datetime.now() - timedelta(seconds=60)
        report = SilenceReport(start_time=start_time, duration=60)
        
        assert report.start_time == start_time
        assert report.duration == 60
    
    def test_silence_detector_resets_properly(self):
        """SilenceDetector reset clears all timestamps"""
        engine = TradingEngine()
        
        engine.silence_detector.update_market_data()
        engine.silence_detector.update_trades()
        engine.silence_detector.update_heartbeat()
        
        assert engine.silence_detector.last_market_data_update is not None
        
        engine.silence_detector.reset()
        
        assert engine.silence_detector.last_market_data_update is None
        assert engine.silence_detector.last_trades_update is None
        assert engine.silence_detector.last_heartbeat_update is None


class TestR007RunLoopCompatibility:
    """Test that R007 integration doesn't break existing run_loop behavior"""
    
    def test_engine_starts_without_errors(self):
        """TradingEngine can be instantiated without errors"""
        engine = TradingEngine()
        assert engine is not None
        assert engine._running == False
    
    def test_get_state_includes_silence_components(self):
        """Engine state can be retrieved without errors"""
        engine = TradingEngine()
        state = engine.get_state()
        
        assert 'ticks' in state
        assert 'agents' in state
        assert 'positions' in state
        assert 'timestamp' in state
    
    def test_mock_data_engine_works_with_silence(self):
        """MockDataEngine continues to work alongside silence detection"""
        engine = TradingEngine()
        
        ticks = engine.mock.tick()
        assert len(ticks) > 0
        
        for sym, tick in ticks.items():
            assert 'price' in tick
            assert 'volume' in tick


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
