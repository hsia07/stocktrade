import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime, time, timedelta
from modules.market_reality.layer import MarketRealityLayer


class TestR028PriceLimit:
    def test_price_within_limit_passes(self):
        layer = MarketRealityLayer()
        valid, reason = layer.validate_price_limit(105.0, 100.0)
        assert valid is True
        assert "PRICE_WITHIN_LIMIT" in reason

    def test_price_exceeds_limit_up_fails(self):
        layer = MarketRealityLayer()
        valid, reason = layer.validate_price_limit(120.0, 100.0)
        assert valid is False
        assert "PRICE_EXCEEDS_LIMIT_UP" in reason

    def test_price_below_limit_down_fails(self):
        layer = MarketRealityLayer()
        valid, reason = layer.validate_price_limit(80.0, 100.0)
        assert valid is False
        assert "PRICE_BELOW_LIMIT_DOWN" in reason

    def test_price_exactly_at_limit_up_edge_passes(self):
        layer = MarketRealityLayer()
        valid, reason = layer.validate_price_limit(110.0, 100.0)
        assert valid is True

    def test_price_exactly_at_limit_down_edge_passes(self):
        layer = MarketRealityLayer()
        valid, reason = layer.validate_price_limit(90.0, 100.0)
        assert valid is True


class TestR028TradingSession:
    def test_pre_market_auction_detected(self):
        layer = MarketRealityLayer()
        dt = datetime(2026, 5, 18, 8, 45, 0)
        valid, session = layer.validate_trading_session(dt)
        assert valid is True
        assert session == "PRE_MARKET_AUCTION"

    def test_continuous_trading_detected(self):
        layer = MarketRealityLayer()
        dt = datetime(2026, 5, 18, 10, 30, 0)
        valid, session = layer.validate_trading_session(dt)
        assert valid is True
        assert session == "CONTINUOUS_TRADING"

    def test_odd_lot_trading_detected(self):
        layer = MarketRealityLayer()
        dt = datetime(2026, 5, 18, 14, 0, 0)
        valid, session = layer.validate_trading_session(dt)
        assert valid is True
        assert session == "ODD_LOT_TRADING"

    def test_outside_trading_hours_fails(self):
        layer = MarketRealityLayer()
        dt = datetime(2026, 5, 18, 15, 0, 0)
        valid, session = layer.validate_trading_session(dt)
        assert valid is False
        assert session == "OUTSIDE_TRADING_HOURS"


class TestR028TPlus2:
    def test_settlement_date_is_t_plus_2(self):
        layer = MarketRealityLayer()
        trade_date = datetime(2026, 5, 18, 10, 0, 0)
        settlement = layer.calculate_settlement_date(trade_date)
        expected = trade_date + timedelta(days=2)
        assert settlement == expected

    def test_settlement_cycle_reported_in_evaluate(self):
        layer = MarketRealityLayer()
        result = layer.evaluate_order(100.0, 1000, 100.0)
        assert result['constraints']['settlement_cycle'] == "T+2"


class TestR028OddLotBoardLot:
    def test_odd_lot_detected(self):
        layer = MarketRealityLayer()
        assert layer.is_odd_lot(500) is True
        assert layer.is_odd_lot(999) is True

    def test_board_lot_detected(self):
        layer = MarketRealityLayer()
        assert layer.is_odd_lot(1000) is False
        assert layer.is_odd_lot(5000) is False

    def test_evaluate_reports_lot_type_odd(self):
        layer = MarketRealityLayer()
        result = layer.evaluate_order(100.0, 500, 100.0)
        assert result['constraints']['lot_type'] == 'ODD_LOT'

    def test_evaluate_reports_lot_type_round(self):
        layer = MarketRealityLayer()
        result = layer.evaluate_order(100.0, 2000, 100.0)
        assert result['constraints']['lot_type'] == 'ROUND_LOT'


class TestR028Liquidity:
    def test_low_volume_liquidity_fails(self):
        layer = MarketRealityLayer()
        liquid, reason = layer.check_liquidity(500, 100000)
        assert liquid is False
        assert "LIQUIDITY_INSUFFICIENT_LOW_VOLUME" in reason

    def test_large_order_liquidity_fails(self):
        layer = MarketRealityLayer()
        liquid, reason = layer.check_liquidity(10000, 100000)
        assert liquid is False
        assert "LIQUIDITY_INSUFFICIENT_LARGE_ORDER" in reason

    def test_sufficient_liquidity_passes(self):
        layer = MarketRealityLayer()
        liquid, reason = layer.check_liquidity(2000, 100000)
        assert liquid is True
        assert "LIQUIDITY_SUFFICIENT" in reason


class TestR028CostSlippageFillSchema:
    def test_cost_calculation_buy_side_no_tax(self):
        layer = MarketRealityLayer()
        costs = layer.calculate_costs(100.0, 1000, is_sell=False)
        assert costs['transaction_tax'] == 0.0
        assert costs['broker_fee'] > 0
        assert costs['total_cost'] == costs['broker_fee']

    def test_cost_calculation_sell_side_includes_tax(self):
        layer = MarketRealityLayer()
        costs = layer.calculate_costs(100.0, 1000, is_sell=True)
        assert costs['transaction_tax'] > 0
        assert costs['total_cost'] > costs['broker_fee']

    def test_slippage_higher_for_odd_lots(self):
        layer = MarketRealityLayer()
        round_slip = layer.estimate_slippage(100.0, 1000, is_odd_lot=False)
        odd_slip = layer.estimate_slippage(100.0, 1000, is_odd_lot=True)
        assert odd_slip > round_slip

    def test_fill_rate_odd_lot_lower(self):
        layer = MarketRealityLayer()
        round_rate = layer.estimate_fill_rate(1000, is_odd_lot=False)
        odd_rate = layer.estimate_fill_rate(500, is_odd_lot=True)
        assert odd_rate < round_rate


class TestR028EvaluateOrder:
    def _during_trading_hours(self, layer):
        """Patch datetime.now to return a time during continuous trading."""
        from unittest.mock import patch
        import datetime as dt
        fake_now = dt.datetime(2026, 5, 18, 10, 30, 0)
        with patch.object(layer, 'validate_trading_session', return_value=(True, "CONTINUOUS_TRADING")):
            return layer

    def test_evaluate_order_successful(self):
        layer = MarketRealityLayer()
        result = layer.evaluate_order(100.0, 2000, 100.0)
        assert 'costs' in result
        assert 'slippage' in result
        assert 'fill_rate' in result
        assert 'constraints' in result
        assert 'reasons' in result

    def test_evaluate_order_reports_failure_on_price_breach(self):
        layer = MarketRealityLayer()
        result = layer.evaluate_order(120.0, 2000, 100.0)
        assert result['passed'] is False
        reasons = " ".join(result['reasons'])
        assert "PRICE_EXCEEDS_LIMIT_UP" in reasons

    def test_evaluate_order_reports_failure_on_liquidity(self):
        layer = MarketRealityLayer()
        result = layer.evaluate_order(100.0, 500, 100.0)
        assert result['passed'] is False
        reasons = " ".join(result['reasons'])
        assert "LIQUIDITY_INSUFFICIENT" in reasons

    def test_evaluate_order_no_warning_only_pass(self):
        layer = MarketRealityLayer()
        result = layer.evaluate_order(100.0, 2000, 100.0)
        assert result['liquidity_sufficient'] is True

    def test_fail_safe_not_warning_only(self):
        layer = MarketRealityLayer()
        result = layer.evaluate_order(80.0, 500, 100.0)
        assert result['passed'] is False
        assert len(result['reasons']) >= 1
