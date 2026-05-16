import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.execution_sizing_guard import SlippageEstimator, ExecutionSizingGuard, LiquidityInfo


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


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
