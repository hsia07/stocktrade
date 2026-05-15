from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NEResult:
    net_edge: float
    expected_net_rr: float
    fill_probability: float
    regime_uncertainty: float
    gross_return: float
    total_costs: float
    total_slippage: float
    risk_premium: float
    passed: bool = False
    veto_reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class NEAEngine:
    def __init__(
        self,
        min_net_edge: float = 0.0,
        min_expected_net_rr: float = 1.0,
        min_fill_probability: float = 0.5,
        max_regime_uncertainty: float = 0.4,
    ):
        self._min_net_edge = min_net_edge
        self._min_expected_net_rr = min_expected_net_rr
        self._min_fill_probability = min_fill_probability
        self._max_regime_uncertainty = max_regime_uncertainty

    def calculate(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: int,
        expected_return: float,
        cost_estimate: float,
        slippage_estimate: float,
        fill_probability: float,
        regime_uncertainty: float,
        risk_free_rate: float = 0.0,
    ) -> NEResult:
        gross_return = expected_return
        total_costs = cost_estimate * quantity
        total_slippage = slippage_estimate * quantity
        risk_premium = max(0.0, regime_uncertainty * expected_return * 0.5)
        net_edge = gross_return - total_costs - total_slippage - risk_premium
        if net_edge != 0:
            expected_net_rr = (gross_return - total_costs - total_slippage) / max(
                abs(net_edge), 1e-10
            )
        else:
            expected_net_rr = 0.0

        result = NEResult(
            net_edge=net_edge,
            expected_net_rr=expected_net_rr,
            fill_probability=fill_probability,
            regime_uncertainty=regime_uncertainty,
            gross_return=gross_return,
            total_costs=total_costs,
            total_slippage=total_slippage,
            risk_premium=risk_premium,
            details={
                "symbol": symbol,
                "side": side,
                "price": price,
                "quantity": quantity,
                "risk_free_rate": risk_free_rate,
            },
        )

        blockers = []
        if net_edge < self._min_net_edge:
            blockers.append(f"net_edge={net_edge:.4f} < min={self._min_net_edge}")
        if expected_net_rr < self._min_expected_net_rr:
            blockers.append(
                f"expected_net_rr={expected_net_rr:.4f} < min={self._min_expected_net_rr}"
            )
        if fill_probability < self._min_fill_probability:
            blockers.append(
                f"fill_probability={fill_probability:.4f} < min={self._min_fill_probability}"
            )
        if regime_uncertainty > self._max_regime_uncertainty:
            blockers.append(
                f"regime_uncertainty={regime_uncertainty:.4f} > max={self._max_regime_uncertainty}"
            )

        if blockers:
            result.passed = False
            result.veto_reason = "; ".join(blockers)
        else:
            result.passed = True

        return result
