import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.execution_sizing_guard import SlippageEstimator, ExecutionSizingGuard, LiquidityInfo, TaiwanMarketConstraints


def test_slippage_estimate():
    est = SlippageEstimator()
    liq = LiquidityInfo(symbol="2330.TW", avg_daily_volume=5000000, spread=0.002, liquidity_score=0.8)
    result = est.estimate(quantity=1000, price=150.0, liquidity=liq)
    assert result.total_slippage > 0
    assert result.liquidity_factor > 0


def test_sizing_guard():
    guard = ExecutionSizingGuard()
    liq = LiquidityInfo(symbol="2330.TW", avg_daily_volume=5000000, spread=0.002, liquidity_score=0.8)
    result = guard.calculate(quantity=1000, price=150.0, risk_budget=50000.0, cash_available=200000.0, liquidity=liq)
    assert result.final_qty > 0
    assert result.final_qty <= 1000


def test_sizing_guard_zero_cash():
    guard = ExecutionSizingGuard()
    liq = LiquidityInfo(symbol="2330.TW", avg_daily_volume=5000000, spread=0.002, liquidity_score=0.8)
    result = guard.calculate(quantity=1000, price=150.0, risk_budget=0.0, cash_available=0.0, liquidity=liq)
    assert result.final_qty == 0
    assert result.veto_reason


def test_sizing_guard_respects_liquidity():
    guard = ExecutionSizingGuard(max_order_pct_of_volume=0.01)
    liq = LiquidityInfo(symbol="LOW", avg_daily_volume=1000, spread=0.01, liquidity_score=0.3)
    result = guard.calculate(quantity=100000, price=10.0, risk_budget=1000000.0, cash_available=1000000.0, liquidity=liq)
    assert result.final_qty <= 10


def test_taiwan_constraints_bypass_non_taiwan():
    tc = TaiwanMarketConstraints(symbol="AAPL", is_taiwan_stock=False)
    assert tc.check(1000) is True
    assert len(tc.violated_rules) == 0


def test_taiwan_circuit_breaker_blocks():
    tc = TaiwanMarketConstraints(symbol="2330.TW", is_taiwan_stock=True, circuit_breaker_active=True, day_trade_remaining=3)
    assert tc.check(100) is False
    assert "circuit_breaker" in tc.violated_rules


def test_taiwan_position_cap():
    tc = TaiwanMarketConstraints(symbol="2330.TW", is_taiwan_stock=True, max_position=1000, current_position=950, day_trade_remaining=3)
    assert tc.check(100) is False
    assert "position_cap" in tc.violated_rules
    assert tc.check(50) is True


def test_taiwan_day_trade_limit():
    tc = TaiwanMarketConstraints(symbol="2330.TW", is_taiwan_stock=True, day_trade_remaining=0, max_position=5000)
    assert tc.check(100) is False
    assert "day_trade_limit" in tc.violated_rules


def test_taiwan_sizing_guard_integration():
    guard = ExecutionSizingGuard()
    liq = LiquidityInfo(symbol="2330.TW", avg_daily_volume=5000000, spread=0.002, liquidity_score=0.8)
    taiwan = TaiwanMarketConstraints(symbol="2330.TW", is_taiwan_stock=True, circuit_breaker_active=True, day_trade_remaining=3)
    result = guard.calculate(quantity=1000, price=150.0, risk_budget=50000.0, cash_available=200000.0, liquidity=liq, taiwan=taiwan)
    assert result.final_qty == 0
    assert "circuit_breaker" in result.taiwan_violations


def test_taiwan_sizing_allows_normal():
    guard = ExecutionSizingGuard()
    liq = LiquidityInfo(symbol="2330.TW", avg_daily_volume=5000000, spread=0.002, liquidity_score=0.8)
    taiwan = TaiwanMarketConstraints(symbol="2330.TW", is_taiwan_stock=True, day_trade_remaining=5, max_position=10000)
    result = guard.calculate(quantity=1000, price=150.0, risk_budget=50000.0, cash_available=200000.0, liquidity=liq, taiwan=taiwan)
    assert result.final_qty > 0


def test_taiwan_price_step_invalid():
    tc = TaiwanMarketConstraints(
        symbol="2330.TW", is_taiwan_stock=True, price_step=0.01,
        day_trade_remaining=5, max_position=10000,
    )
    assert tc.check(1000, price=150.01) is True
    assert tc.check(1000, price=150.001) is False
    assert "price_step" in tc.violated_rules


def test_taiwan_suspended_blocks():
    tc = TaiwanMarketConstraints(symbol="2330.TW", is_taiwan_stock=True, is_suspended=True)
    assert tc.check(100) is False
    assert "suspended" in tc.violated_rules


def test_taiwan_disposition_stock_blocks():
    tc = TaiwanMarketConstraints(symbol="2330.TW", is_taiwan_stock=True, is_disposition_stock=True)
    assert tc.check(100) is False
    assert "disposition_stock" in tc.violated_rules


def test_taiwan_collection_auction_blocks():
    tc = TaiwanMarketConstraints(symbol="2330.TW", is_taiwan_stock=True, collection_auction=True)
    assert tc.check(100) is False
    assert "collection_auction" in tc.violated_rules


def test_taiwan_t_plus_2_blocks():
    tc = TaiwanMarketConstraints(symbol="2330.TW", is_taiwan_stock=True, t_plus_2_blocked=True)
    assert tc.check(100) is False
    assert "t_plus_2" in tc.violated_rules


def test_taiwan_near_limit_up_blocks():
    tc = TaiwanMarketConstraints(symbol="2330.TW", is_taiwan_stock=True, near_limit_up=True)
    assert tc.check(100) is False
    assert "near_limit_up" in tc.violated_rules


def test_taiwan_near_limit_down_blocks():
    tc = TaiwanMarketConstraints(symbol="2330.TW", is_taiwan_stock=True, near_limit_down=True)
    assert tc.check(100) is False
    assert "near_limit_down" in tc.violated_rules


def test_taiwan_odd_lot_blocks():
    tc = TaiwanMarketConstraints(symbol="2330.TW", is_taiwan_stock=True, is_odd_lot=True)
    assert tc.check(100) is False
    assert "odd_lot" in tc.violated_rules


def test_taiwan_all_constraints_pass_with_no_violations():
    tc = TaiwanMarketConstraints(
        symbol="2330.TW", is_taiwan_stock=True,
        day_trade_remaining=5, max_position=10000,
        circuit_breaker_active=False, t_plus_2_blocked=False,
        collection_auction=False, is_odd_lot=False,
        near_limit_up=False, near_limit_down=False,
        is_suspended=False, is_disposition_stock=False,
    )
    assert tc.check(100, price=150.00) is True
    assert len(tc.violated_rules) == 0


def test_taiwan_multiple_violations_first_triggers():
    tc = TaiwanMarketConstraints(
        symbol="2330.TW", is_taiwan_stock=True,
        circuit_breaker_active=True, is_suspended=True,
    )
    assert tc.check(100) is False
    assert tc.violated_rules == ["circuit_breaker"]


def test_taiwan_sizing_integration_suspended():
    guard = ExecutionSizingGuard()
    liq = LiquidityInfo(symbol="2330.TW", avg_daily_volume=5000000, spread=0.002, liquidity_score=0.8)
    taiwan = TaiwanMarketConstraints(symbol="2330.TW", is_taiwan_stock=True, is_suspended=True, day_trade_remaining=5, max_position=10000)
    result = guard.calculate(quantity=1000, price=150.0, risk_budget=50000.0, cash_available=200000.0, liquidity=liq, taiwan=taiwan)
    assert result.final_qty == 0
    assert "suspended" in result.taiwan_violations


def test_taiwan_sizing_integration_price_step():
    guard = ExecutionSizingGuard()
    liq = LiquidityInfo(symbol="2330.TW", avg_daily_volume=5000000, spread=0.002, liquidity_score=0.8)
    taiwan = TaiwanMarketConstraints(symbol="2330.TW", is_taiwan_stock=True, day_trade_remaining=5, max_position=10000)
    result = guard.calculate(quantity=1000, price=150.001, risk_budget=50000.0, cash_available=200000.0, liquidity=liq, taiwan=taiwan)
    assert result.final_qty == 0
    assert "price_step" in result.taiwan_violations


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
