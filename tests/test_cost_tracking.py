import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from modules.market_reality.cost_tracking import CostTracker


class TestCostTrackerCalculation:
    def test_expected_costs_buy_side_no_tax(self):
        tracker = CostTracker()
        costs = tracker.calculate_expected_costs(100.0, 1000, is_sell=False)
        assert costs['transaction_tax'] == 0.0
        assert costs['broker_fee'] == 100.0 * 1000 * 0.001425
        assert costs['total_cost'] == costs['broker_fee']

    def test_expected_costs_sell_side_tax_included(self):
        tracker = CostTracker()
        costs = tracker.calculate_expected_costs(100.0, 1000, is_sell=True)
        expected_tax = 100.0 * 1000 * 0.001425
        expected_fee = 100.0 * 1000 * 0.001425
        assert costs['transaction_tax'] == pytest.approx(expected_tax)
        assert costs['broker_fee'] == pytest.approx(expected_fee)
        assert costs['total_cost'] == pytest.approx(expected_tax + expected_fee)

    def test_expected_costs_zero_volume(self):
        tracker = CostTracker()
        costs = tracker.calculate_expected_costs(100.0, 0, is_sell=True)
        assert costs['trade_value'] == 0.0
        assert costs['cost_per_share'] == 0.0

    def test_cost_per_share_correct(self):
        tracker = CostTracker()
        costs = tracker.calculate_expected_costs(100.0, 1000, is_sell=True)
        expected_total = 100.0 * 1000 * 0.001425 * 2
        assert costs['cost_per_share'] == pytest.approx(expected_total / 1000)


class TestCostTrackerTracking:
    def test_record_actual_costs_zero_variance(self):
        tracker = CostTracker()
        expected = tracker.calculate_expected_costs(100.0, 1000, is_sell=True)
        variance = tracker.record_actual_costs(expected, expected['total_cost'], expected['transaction_tax'])
        assert variance['variance'] == 0.0
        assert variance['variance_percent'] == 0.0

    def test_record_actual_costs_positive_variance(self):
        tracker = CostTracker()
        expected = tracker.calculate_expected_costs(100.0, 1000, is_sell=True)
        variance = tracker.record_actual_costs(expected, expected['total_cost'] + 50.0, expected['transaction_tax'] + 30.0)
        assert variance['variance'] > 0
        assert variance['variance_percent'] > 0

    def test_record_actual_costs_negative_variance(self):
        tracker = CostTracker()
        expected = tracker.calculate_expected_costs(100.0, 1000, is_sell=True)
        variance = tracker.record_actual_costs(expected, expected['total_cost'] - 20.0, 0.0)
        assert variance['variance'] < 0

    def test_record_appends_to_history(self):
        tracker = CostTracker()
        assert len(tracker.cost_history) == 0
        expected = tracker.calculate_expected_costs(100.0, 1000, is_sell=True)
        tracker.record_actual_costs(expected, expected['total_cost'])
        assert len(tracker.cost_history) == 1
        assert tracker.cost_history[0]['type'] == 'cost_tracking'


class TestCostTrackerSummary:
    def test_empty_summary(self):
        tracker = CostTracker()
        summary = tracker.get_cost_summary()
        assert summary['total_cost'] == 0.0
        assert summary['trade_count'] == 0

    def test_summary_after_multiple_trades(self):
        tracker = CostTracker()
        for i in range(3):
            expected = tracker.calculate_expected_costs(100.0, 1000, is_sell=True)
            tracker.record_actual_costs(expected, expected['total_cost'])
        summary = tracker.get_cost_summary()
        assert summary['total_trades'] == 3
        assert summary['total_cost'] > 0
