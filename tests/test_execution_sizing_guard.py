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


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
