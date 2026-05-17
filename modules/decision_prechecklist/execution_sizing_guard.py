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
    t_plus_2_blocked: bool = False
    collection_auction: bool = False
    is_odd_lot: bool = False
    near_limit_up: bool = False
    near_limit_down: bool = False
    is_suspended: bool = False
    is_disposition_stock: bool = False
    violated_rules: list[str] = field(default_factory=list)

    def check(self, quantity: int, price: float | None = None) -> bool:
        self.violated_rules = []
        if not self.is_taiwan_stock:
            return True
        if self.circuit_breaker_active:
            self.violated_rules.append("circuit_breaker")
            return False
        if self.is_suspended:
            self.violated_rules.append("suspended")
            return False
        if self.is_disposition_stock:
            self.violated_rules.append("disposition_stock")
            return False
        if self.collection_auction:
            self.violated_rules.append("collection_auction")
            return False
        if self.t_plus_2_blocked:
            self.violated_rules.append("t_plus_2")
            return False
        if self.near_limit_up:
            self.violated_rules.append("near_limit_up")
            return False
        if self.near_limit_down:
            self.violated_rules.append("near_limit_down")
            return False
        if self.is_odd_lot:
            self.violated_rules.append("odd_lot")
            return False
        if price is not None and self.price_step > 0:
            remainder = price % self.price_step
            if remainder > 1e-9 and abs(remainder - self.price_step) > 1e-9:
                self.violated_rules.append("price_step")
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
    veto_reason: str = ""


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
    def estimate(self, quantity: int, price: float, liquidity: LiquidityInfo, max_allowed_slippage: float = 0.05) -> SlippageEstimate:
        base_slippage = liquidity.spread / 2.0
        share_of_volume = quantity / max(liquidity.avg_daily_volume, 1)
        volume_slippage = share_of_volume * 0.01
        liquidity_factor = 1.0 / max(liquidity.liquidity_score, 0.01)
        vol_factor = 1.0
        total = base_slippage + volume_slippage
        total = total * liquidity_factor * vol_factor
        veto = "slippage_excessive" if total > max_allowed_slippage else ""
        return SlippageEstimate(
            expected_slippage=base_slippage + volume_slippage,
            liquidity_factor=liquidity_factor,
            volatility_factor=vol_factor,
            total_slippage=total,
            veto_reason=veto,
        )


class ExecutionSizingGuard:
    def __init__(self, max_order_pct_of_volume: float = 0.01, max_allowed_slippage: float = 0.05):
        self._max_pct = max_order_pct_of_volume
        self._max_slippage = max_allowed_slippage

    def calculate(self, quantity: int, price: float, risk_budget: float, cash_available: float, liquidity: LiquidityInfo, taiwan: TaiwanMarketConstraints | None = None) -> SizingConstraint:
        max_by_risk = int(risk_budget / max(price, 0.01)) if price > 0 else 0
        max_by_liquidity = int(liquidity.avg_daily_volume * self._max_pct)
        max_by_cash = int(cash_available / max(price, 0.01)) if price > 0 else 0
        final = min(max_by_risk, max_by_liquidity, max_by_cash, quantity)

        taiwan_violations: list[str] = []
        if taiwan is not None:
            if not taiwan.check(final, price=price):
                taiwan_violations = list(taiwan.violated_rules)
                final = 0

        slippage_excessive = False
        if final > 0:
            slippage_est = SlippageEstimator().estimate(final, price, liquidity, self._max_slippage)
            if slippage_est.veto_reason:
                slippage_excessive = True
                final = 0

        veto = ""
        if final == 0:
            if taiwan_violations:
                pass
            elif slippage_excessive:
                veto = "slippage_excessive"
            elif max_by_cash == 0:
                veto = "cash_insufficient"
            elif max_by_risk == 0:
                veto = "risk_budget_exhausted"
            elif max_by_liquidity == 0:
                veto = "liquidity_insufficient"
            else:
                parts = []
                if max_by_liquidity < quantity:
                    parts.append("liquidity_insufficient")
                if max_by_cash < quantity:
                    parts.append("cash_insufficient")
                if max_by_risk < quantity:
                    parts.append("risk_budget_exhausted")
                veto = ";".join(parts) if parts else "all_sizing_reduced_to_zero"
        elif final < quantity:
            parts = []
            if max_by_liquidity < quantity:
                parts.append("liquidity_insufficient")
            if max_by_cash < quantity:
                parts.append("cash_insufficient")
            if max_by_risk < quantity:
                parts.append("risk_budget_exhausted")
            veto = ";".join(parts)

        return SizingConstraint(
            max_qty_by_risk=max_by_risk,
            max_qty_by_liquidity=max_by_liquidity,
            max_qty_by_cash=max_by_cash,
            final_qty=max(0, final),
            veto_reason=veto,
            taiwan_violations=taiwan_violations,
        )
