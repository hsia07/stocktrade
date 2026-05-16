from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SlippageEstimate:
    expected_slippage: float
    liquidity_factor: float
    volatility_factor: float
    total_slippage: float


@dataclass
class LiquidityInfo:
    symbol: str
    avg_daily_volume: int
    spread: float
    liquidity_score: float


@dataclass
class SizingConstraint:
    max_qty_by_risk: int
    max_qty_by_liquidity: int
    max_qty_by_cash: int
    final_qty: int
    veto_reason: str = ""


class SlippageEstimator:
    def estimate(self, quantity: int, price: float, liquidity: LiquidityInfo) -> SlippageEstimate:
        base_slippage = liquidity.spread / 2.0
        share_of_volume = quantity / max(liquidity.avg_daily_volume, 1)
        volume_slippage = share_of_volume * 0.01
        liquidity_factor = 1.0 / max(liquidity.liquidity_score, 0.01)
        vol_factor = 1.0
        total = base_slippage + volume_slippage
        total = total * liquidity_factor * vol_factor
        return SlippageEstimate(
            expected_slippage=base_slippage + volume_slippage,
            liquidity_factor=liquidity_factor,
            volatility_factor=vol_factor,
            total_slippage=total,
        )


class ExecutionSizingGuard:
    def __init__(self, max_order_pct_of_volume: float = 0.01):
        self._max_pct = max_order_pct_of_volume

    def calculate(self, quantity: int, price: float, risk_budget: float, cash_available: float, liquidity: LiquidityInfo) -> SizingConstraint:
        max_by_risk = int(risk_budget / max(price, 0.01)) if price > 0 else 0
        max_by_liquidity = int(liquidity.avg_daily_volume * self._max_pct)
        max_by_cash = int(cash_available / max(price, 0.01)) if price > 0 else 0
        final = min(max_by_risk, max_by_liquidity, max_by_cash, quantity)
        veto = "" if final > 0 else "all sizing constraints reduced to zero"
        return SizingConstraint(
            max_qty_by_risk=max_by_risk,
            max_qty_by_liquidity=max_by_liquidity,
            max_qty_by_cash=max_by_cash,
            final_qty=max(0, final),
            veto_reason=veto,
        )
