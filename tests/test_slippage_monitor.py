import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from modules.market_reality.slippage_monitor import SlippageMonitor


class TestSlippageMonitorEstimate:
    def test_estimate_expected_slippage_structure(self):
        monitor = SlippageMonitor()
        estimate = monitor.estimate_expected_slippage(100.0, 1000, is_odd_lot=False)
        assert 'expected_slippage' in estimate
        assert 'slippage_percent' in estimate
        assert 'volume_factor' in estimate
        assert 'odd_lot_factor' in estimate
        assert estimate['expected_slippage'] > 0

    def test_odd_lot_higher_slippage(self):
        monitor = SlippageMonitor()
        round_est = monitor.estimate_expected_slippage(100.0, 1000, is_odd_lot=False)
        odd_est = monitor.estimate_expected_slippage(100.0, 999, is_odd_lot=True)
        assert odd_est['odd_lot_factor'] == 1.5
        assert round_est['odd_lot_factor'] == 1.0

    def test_larger_volume_higher_slippage(self):
        monitor = SlippageMonitor()
        small = monitor.estimate_expected_slippage(100.0, 1000, is_odd_lot=False)
        large = monitor.estimate_expected_slippage(100.0, 5000, is_odd_lot=False)
        assert large['expected_slippage'] > small['expected_slippage']

    def test_volume_factor_capped(self):
        monitor = SlippageMonitor()
        est = monitor.estimate_expected_slippage(100.0, 100000, is_odd_lot=False)
        assert est['volume_factor'] == 5.0


class TestSlippageMonitorRecording:
    def test_record_actual_slippage_within_tolerance(self):
        monitor = SlippageMonitor()
        expected = monitor.estimate_expected_slippage(100.0, 1000, is_odd_lot=False)
        actual_price = expected['price'] + expected['expected_slippage']
        record = monitor.record_actual_slippage(expected, actual_price)
        assert record['variance']['within_tolerance'] is True
        assert record['type'] == 'slippage_monitoring'

    def test_record_actual_slippage_exceeds_tolerance(self):
        monitor = SlippageMonitor()
        expected = monitor.estimate_expected_slippage(100.0, 1000, is_odd_lot=False)
        record = monitor.record_actual_slippage(expected, 150.0)
        assert record['variance']['within_tolerance'] is False

    def test_record_appends_to_history(self):
        monitor = SlippageMonitor()
        assert len(monitor.slippage_history) == 0
        expected = monitor.estimate_expected_slippage(100.0, 1000)
        monitor.record_actual_slippage(expected, 100.5)
        assert len(monitor.slippage_history) == 1

    def test_record_with_exact_price_zero_variance(self):
        monitor = SlippageMonitor()
        expected = monitor.estimate_expected_slippage(100.0, 1000)
        record = monitor.record_actual_slippage(expected, 100.0)
        variance = abs(record['variance']['slippage_variance'])
        assert variance == record['expected']['expected_slippage']


class TestSlippageMonitorSummary:
    def test_empty_summary(self):
        monitor = SlippageMonitor()
        summary = monitor.get_slippage_summary()
        assert summary['total_trades'] == 0

    def test_summary_after_multiple_records(self):
        monitor = SlippageMonitor()
        for i in range(5):
            expected = monitor.estimate_expected_slippage(100.0, 1000)
            monitor.record_actual_slippage(expected, 100.5 + i)
        summary = monitor.get_slippage_summary()
        assert summary['total_trades'] == 5
        assert summary['within_tolerance_count'] <= 5


class TestSlippageMonitorSchema:
    def test_get_monitoring_ready_schema(self):
        monitor = SlippageMonitor()
        schema = monitor.get_monitoring_ready_schema()
        assert schema['deterministic_gate_ready'] is True
        assert schema['taiwan_compatible'] is True
        assert schema['monitoring_type'] == 'slippage'
