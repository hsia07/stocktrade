from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SizingResult:
    max_qty: int
    recommended_qty: int
    final_qty: int
    risk_budget_qty: int
    liquidity_qty: int
    portfolio_exposure_qty: int
    strategy_cap_qty: int
    regime_cap_qty: int
    cash_available_qty: int
    passed: bool = False
    veto_reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class PositionSizingEngine:
    def calculate(
        self,
        symbol: str,
        side: str,
        price: float,
        confidence_calibrated: float,
        risk_budget: float,
        current_exposure: float,
        portfolio_value: float,
        strategy_max_pct: float,
        regime_max_pct: float,
        cash_available: float,
        t_plus_2_hold: float,
        avg_daily_volume: int,
        max_pct_of_volume: float,
        max_position_pct_of_portfolio: float,
    ) -> SizingResult:
        risk_budget_qty = int(risk_budget / price) if price > 0 else 0
        liquidity_qty = int(avg_daily_volume * max_pct_of_volume)
        max_position_value = portfolio_value * max_position_pct_of_portfolio
        portfolio_exposure_qty = int(max_position_value / price) if price > 0 else 0
        strategy_cap_qty = int(portfolio_value * strategy_max_pct / price) if price > 0 else 0
        regime_cap_qty = int(portfolio_value * regime_max_pct / price) if price > 0 else 0
        cash_available_qty = int(
            max(0, cash_available - t_plus_2_hold) / price
        ) if price > 0 else 0

        max_qty = min(
            risk_budget_qty,
            liquidity_qty,
            portfolio_exposure_qty,
            strategy_cap_qty,
            regime_cap_qty,
            cash_available_qty,
        )
        if max_qty < 0:
            max_qty = 0

        recommended_qty = int(max_qty * min(1.0, confidence_calibrated * 2.0))
        if recommended_qty < 0:
            recommended_qty = 0

        final_qty = recommended_qty

        result = SizingResult(
            max_qty=max_qty,
            recommended_qty=recommended_qty,
            final_qty=final_qty,
            risk_budget_qty=risk_budget_qty,
            liquidity_qty=liquidity_qty,
            portfolio_exposure_qty=portfolio_exposure_qty,
            strategy_cap_qty=strategy_cap_qty,
            regime_cap_qty=regime_cap_qty,
            cash_available_qty=cash_available_qty,
            details={
                "symbol": symbol,
                "side": side,
                "price": price,
                "confidence_calibrated": confidence_calibrated,
                "risk_budget": risk_budget,
                "current_exposure": current_exposure,
                "portfolio_value": portfolio_value,
                "cash_available": cash_available,
                "t_plus_2_hold": t_plus_2_hold,
            },
        )

        if max_qty == 0:
            result.passed = False
            result.veto_reason = "max_qty=0: all sizing constraints blocked"
        elif recommended_qty == 0:
            result.passed = False
            result.veto_reason = (
                "recommended_qty=0: confidence_calibrated too low for any position"
            )
        else:
            result.passed = True

        return result
