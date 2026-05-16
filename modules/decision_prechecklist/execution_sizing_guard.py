from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class TaiwanMarketRule(Enum):
    DAY_TRADE_LIMIT = "day_trade_limit"
    POSITION_CAP = "position_cap"
    PRICE_STEP = "price_step"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class TaiwanMarketConstraints:
    symbol: str
    is_taiwan_stock: bool = False
    day_trade_remaining: int = 0
    max_position: int = 0
    current_position: int = 0
    price_step: float = 0.01
    circuit_breaker_active: bool = False
    violated_rules: list[str] = field(default_factory=list)

    def check(self, quantity: int) -> bool:
        self.violated_rules = []
        if not self.is_taiwan_stock:
            return True
        if self.circuit_breaker_active:
            self.violated_rules.append("circuit_breaker")
            return False
        if self.max_position > 0 and self.current_position + quantity > self.max_position:
            self.violated_rules.append("position_cap")
            return False
        if self.day_trade_remaining <= 0 and quantity > 0:
            self.violated_rules.append("day_trade_limit")
            return False
        return True


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
    taiwan_violations: list[str] = field(default_factory=list)


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

    def calculate(self, quantity: int, price: float, risk_budget: float, cash_available: float, liquidity: LiquidityInfo, taiwan: TaiwanMarketConstraints | None = None) -> SizingConstraint:
        max_by_risk = int(risk_budget / max(price, 0.01)) if price > 0 else 0
        max_by_liquidity = int(liquidity.avg_daily_volume * self._max_pct)
        max_by_cash = int(cash_available / max(price, 0.01)) if price > 0 else 0
        final = min(max_by_risk, max_by_liquidity, max_by_cash, quantity)

        taiwan_violations: list[str] = []
        if taiwan is not None:
            if not taiwan.check(final):
                taiwan_violations = list(taiwan.violated_rules)
                final = 0

        veto = "" if final > 0 else "all sizing constraints reduced to zero"
        return SizingConstraint(
            max_qty_by_risk=max_by_risk,
            max_qty_by_liquidity=max_by_liquidity,
            max_qty_by_cash=max_by_cash,
            final_qty=max(0, final),
            veto_reason=veto,
            taiwan_violations=taiwan_violations,
        )
