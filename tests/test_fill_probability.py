import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from modules.market_reality.fill_probability import FillProbabilityModel


class TestFillProbabilityEstimate:
    def test_normal_lot_normal_volatility(self):
        model = FillProbabilityModel()
        result = model.estimate_fill_probability(1000, is_odd_lot=False, market_volatility='normal')
        assert 0.0 < result['fill_probability'] <= 1.0
        assert result['market_volatility'] == 'normal'

    def test_odd_lot_lower_probability(self):
        model = FillProbabilityModel()
        normal = model.estimate_fill_probability(1000, is_odd_lot=False)
        odd = model.estimate_fill_probability(500, is_odd_lot=True)
        assert odd['fill_probability'] < normal['fill_probability']

    def test_high_volatility_reduces_probability(self):
        model = FillProbabilityModel()
        normal = model.estimate_fill_probability(1000, is_odd_lot=False, market_volatility='normal')
        high = model.estimate_fill_probability(1000, is_odd_lot=False, market_volatility='high')
        assert high['fill_probability'] < normal['fill_probability']

    def test_low_volatility_increases_probability(self):
        model = FillProbabilityModel()
        low = model.estimate_fill_probability(1000, is_odd_lot=False, market_volatility='low')
        assert low['volatility_adjustment'] == 0.02

    def test_large_volume_reduces_probability(self):
        model = FillProbabilityModel()
        normal = model.estimate_fill_probability(1000, is_odd_lot=False)
        large = model.estimate_fill_probability(20000, is_odd_lot=False)
        assert large['fill_probability'] < normal['fill_probability']

    def test_estimate_returns_all_required_fields(self):
        model = FillProbabilityModel()
        result = model.estimate_fill_probability(1000)
        assert 'fill_probability' in result
        assert 'fill_percentage' in result
        assert 'base_probability' in result
        assert 'volatility_adjustment' in result
        assert 'expected_fill_rate' in result
        assert result['expected_fill_rate'] == result['fill_probability']

    def test_probability_clamped(self):
        model = FillProbabilityModel()
        result = model.estimate_fill_probability(1000, is_odd_lot=False, market_volatility='low')
        assert 0.0 <= result['fill_probability'] <= 1.0

    def test_same_input_repeated_result_identical(self):
        """Deterministic: same input must produce identical fill_probability."""
        model = FillProbabilityModel()
        result1 = model.estimate_fill_probability(1000, is_odd_lot=False, market_volatility='normal')
        result2 = model.estimate_fill_probability(1000, is_odd_lot=False, market_volatility='normal')
        assert result1['fill_probability'] == result2['fill_probability']
        assert result1['base_probability'] == result2['base_probability']

    def test_large_volume_always_less_than_normal(self):
        """Deterministic: large volume must always have lower fill probability."""
        model = FillProbabilityModel()
        normal = model.estimate_fill_probability(1000, is_odd_lot=False)
        large = model.estimate_fill_probability(20000, is_odd_lot=False)
        assert large['fill_probability'] < normal['fill_probability']
        # Explicit deterministic values
        assert normal['base_probability'] == 0.97
        assert large['base_probability'] == 0.90

    def test_high_volatility_always_reduces(self):
        """Deterministic: high volatility must always reduce fill probability."""
        model = FillProbabilityModel()
        normal = model.estimate_fill_probability(1000, is_odd_lot=False, market_volatility='normal')
        high = model.estimate_fill_probability(1000, is_odd_lot=False, market_volatility='high')
        assert high['fill_probability'] < normal['fill_probability']

    def test_low_volatility_always_increases(self):
        """Deterministic: low volatility must always increase fill probability."""
        model = FillProbabilityModel()
        normal = model.estimate_fill_probability(1000, is_odd_lot=False, market_volatility='normal')
        low = model.estimate_fill_probability(1000, is_odd_lot=False, market_volatility='low')
        assert low['fill_probability'] > normal['fill_probability']

    def test_odd_lot_always_lower_than_board_lot(self):
        """Deterministic: odd lot must always have lower fill probability."""
        model = FillProbabilityModel()
        board = model.estimate_fill_probability(1000, is_odd_lot=False)
        odd = model.estimate_fill_probability(500, is_odd_lot=True)
        assert odd['fill_probability'] < board['fill_probability']
        assert odd['base_probability'] == 0.85


class TestFillProbabilityRecording:
    def test_record_actual_fill_exact_match(self):
        model = FillProbabilityModel()
        expected = model.estimate_fill_probability(1000, is_odd_lot=False)
        expected_prob = expected['fill_probability']
        actual_filled = int(1000 * expected_prob)
        record = model.record_actual_fill(expected, actual_filled, 1000)
        assert abs(record['variance']['fill_variance']) <= 0.05
        assert record['variance']['filled_as_expected'] is True

    def test_record_actual_fill_underperforms(self):
        model = FillProbabilityModel()
        expected = model.estimate_fill_probability(1000, is_odd_lot=False)
        record = model.record_actual_fill(expected, 100, 1000)
        assert record['variance']['fill_variance'] < 0
        assert record['variance']['filled_as_expected'] is False

    def test_record_appends_to_history(self):
        model = FillProbabilityModel()
        assert len(model.fill_history) == 0
        expected = model.estimate_fill_probability(1000)
        model.record_actual_fill(expected, 1000, 1000)
        assert len(model.fill_history) == 1


class TestFillProbabilitySummary:
    def test_empty_summary(self):
        model = FillProbabilityModel()
        summary = model.get_fill_summary()
        assert summary['total_trades'] == 0

    def test_summary_after_multiple_records(self):
        model = FillProbabilityModel()
        for i in range(4):
            expected = model.estimate_fill_probability(1000)
            model.record_actual_fill(expected, int(1000 * expected['fill_probability']), 1000)
        summary = model.get_fill_summary()
        assert summary['total_trades'] == 4
