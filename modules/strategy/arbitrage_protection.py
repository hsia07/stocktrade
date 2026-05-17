"""
R027: Arbitrage Protection Mechanism (套利保护机制)
Authoritative Topic: 套利 / 套利保护机制 (from 161轮正式重编主题总表_唯一基准版_v2.md)

This module provides arbitrage opportunity safety checks and protection decisions.
It does NOT execute trades (no broker/order integration).
It integrates with Risk Layer / Final Gate for deterministic veto.

Taiwan Market Constraints:
- 涨跌幅限制: ±10%
- T+2 交割
- 集合竞价: 08:30-09:00
- 盘中交易: 09:00-13:30
- 零股交易: 13:40-14:30 (different lot size)
- 流动性不足 veto
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class ArbitrageType(Enum):
    SPOT_FUTURES = "spot_futures"
    ETF_UNDERLYING = "etf_underlying"
    CONVERTIBLE_BOND = "convertible_bond"


class ProtectionDecision(Enum):
    APPROVE = "approve"
    VETO_LIQUIDITY = "veto_liquidity"
    VETO_RISK_LIMIT = "veto_risk_limit"
    VETO_MARKET_REALITY = "veto_market_reality"
    VETO_TAIWAN_CONSTRAINT = "veto_taiwan_constraint"
    ABORT_NO_TRADE = "abort_no_trade"


@dataclass
class ArbitrageOpportunity:
    arbitrage_type: ArbitrageType
    security_a: str
    security_b: str
    gross_profit: float
    volume: int
    price_a: float
    price_b: float
    # Taiwan market: prices must stay within ±10% limit
    price_limit_upper: float
    price_limit_lower: float
    # T+2 settlement risk
    settlement_date: str  # T+2 from trade date


@dataclass
class ArbitrageProtectionReport:
    opportunity: ArbitrageOpportunity
    decision: ProtectionDecision
    reason_codes: List[str]
    net_profit_after_costs: float
    fill_rate_estimate: float
    slippage_estimate: float
    risk_gate_passed: bool
    market_reality_passed: bool
    taiwan_constraints_passed: bool


class ArbitrageProtection:
    """
    R027 Arbitrage Protection Mechanism.
    Protection-first: only safety checks, no execution.
    """
    
    def __init__(self, risk_gate, market_reality_model):
        self.risk_gate = risk_gate
        self.market_reality = market_reality_model
        # Taiwan market constraints
        self.price_limit_percent = 0.10  # ±10%
        self.settlement_days = 2  # T+2
        
    def evaluate_opportunity(self, opportunity: ArbitrageOpportunity) -> ArbitrageProtectionReport:
        """
        Evaluate arbitrage opportunity safety.
        Returns protection decision (approve/veto/abort).
        """
        reason_codes = []
        
        # 1. Taiwan market constraints check
        taiwan_check = self._check_taiwan_constraints(opportunity)
        if not taiwan_check['passed']:
            return ArbitrageProtectionReport(
                opportunity=opportunity,
                decision=ProtectionDecision.VETO_TAIWAN_CONSTRAINT,
                reason_codes=taiwan_check['reasons'],
                net_profit_after_costs=0.0,
                fill_rate_estimate=0.0,
                slippage_estimate=0.0,
                risk_gate_passed=False,
                market_reality_passed=False,
                taiwan_constraints_passed=False
            )
            
        # 2. Market Reality Layer integration
        reality_result = self.market_reality.evaluate_arbitrage(opportunity)
        if not reality_result['passed']:
            reason_codes.extend(reality_result['reasons'])
            if reality_result.get('liquidity_insufficient', False):
                return ArbitrageProtectionReport(
                    opportunity=opportunity,
                    decision=ProtectionDecision.VETO_LIQUIDITY,
                    reason_codes=reason_codes,
                    net_profit_after_costs=reality_result.get('net_profit', 0.0),
                    fill_rate_estimate=reality_result.get('fill_rate', 0.0),
                    slippage_estimate=reality_result.get('slippage', 0.0),
                    risk_gate_passed=False,
                    market_reality_passed=False,
                    taiwan_constraints_passed=True
                )
            return ArbitrageProtectionReport(
                opportunity=opportunity,
                decision=ProtectionDecision.VETO_MARKET_REALITY,
                reason_codes=reason_codes,
                net_profit_after_costs=reality_result.get('net_profit', 0.0),
                fill_rate_estimate=reality_result.get('fill_rate', 0.0),
                slippage_estimate=reality_result.get('slippage', 0.0),
                risk_gate_passed=False,
                market_reality_passed=False,
                taiwan_constraints_passed=True
            )
            
        # 3. Gross-to-net: subtract costs (fees, tax, slippage)
        costs = self._calculate_total_costs(opportunity)
        net_profit = opportunity.gross_profit - costs
        if net_profit <= 0:
            reason_codes.append('NET_PROFIT_NON_POSITIVE')
            return ArbitrageProtectionReport(
                opportunity=opportunity,
                decision=ProtectionDecision.ABORT_NO_TRADE,
                reason_codes=reason_codes,
                net_profit_after_costs=net_profit,
                fill_rate_estimate=reality_result.get('fill_rate', 0.0),
                slippage_estimate=reality_result.get('slippage', 0.0),
                risk_gate_passed=False,
                market_reality_passed=True,
                taiwan_constraints_passed=True
            )
            
        # 4. Liquidity veto check
        if reality_result.get('liquidity_insufficient', False):
            reason_codes.append('LIQUIDITY_INSUFFICIENT')
            return ArbitrageProtectionReport(
                opportunity=opportunity,
                decision=ProtectionDecision.VETO_LIQUIDITY,
                reason_codes=reason_codes,
                net_profit_after_costs=net_profit,
                fill_rate_estimate=reality_result.get('fill_rate', 0.0),
                slippage_estimate=reality_result.get('slippage', 0.0),
                risk_gate_passed=False,
                market_reality_passed=True,
                taiwan_constraints_passed=True
            )
            
        # 5. Deterministic Risk Layer / Final Gate integration
        risk_result = self.risk_gate.evaluate_arbitrage(opportunity, net_profit)
        if not risk_result['passed']:
            reason_codes.extend(risk_result['reasons'])
            return ArbitrageProtectionReport(
                opportunity=opportunity,
                decision=ProtectionDecision.VETO_RISK_LIMIT,
                reason_codes=reason_codes,
                net_profit_after_costs=net_profit,
                fill_rate_estimate=reality_result.get('fill_rate', 0.0),
                slippage_estimate=reality_result.get('slippage', 0.0),
                risk_gate_passed=False,
                market_reality_passed=True,
                taiwan_constraints_passed=True
            )
            
        # 6. Protection approved (NOT execution, just approval)
        reason_codes.append('PROTECTION_APPROVED')
        return ArbitrageProtectionReport(
            opportunity=opportunity,
            decision=ProtectionDecision.APPROVE,
            reason_codes=reason_codes,
            net_profit_after_costs=net_profit,
            fill_rate_estimate=reality_result.get('fill_rate', 1.0),
            slippage_estimate=reality_result.get('slippage', 0.0),
            risk_gate_passed=True,
            market_reality_passed=True,
            taiwan_constraints_passed=True
        )
        
    def _check_taiwan_constraints(self, opportunity: ArbitrageOpportunity) -> dict:
        """Check Taiwan market specific constraints."""
        reasons = []
        passed = True
        
        # ±10% price limit check
        if not (opportunity.price_limit_lower <= opportunity.price_a <= opportunity.price_limit_upper):
            reasons.append('PRICE_A_BREACHES_LIMIT')
            passed = False
        if not (opportunity.price_limit_lower <= opportunity.price_b <= opportunity.price_limit_upper):
            reasons.append('PRICE_B_BREACHES_LIMIT')
            passed = False
            
        # T+2 settlement: check if settlement date is valid (simplified)
        # In real implementation, would check business days
        
        return {'passed': passed, 'reasons': reasons}
        
    def _calculate_total_costs(self, opportunity: ArbitrageOpportunity) -> float:
        """Calculate total costs: fees + tax + slippage."""
        # Simplified: 0.1425% transaction tax + fees + slippage
        tax_rate = 0.001425  # Taiwan securities transaction tax
        tax = abs(opportunity.price_a * opportunity.volume) * tax_rate
        # Add fees and slippage (from market reality model)
        fees = 0  # Would come from broker model
        slippage = 0  # Would come from market reality model
        return tax + fees + slippage
