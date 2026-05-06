"""
R027: Arbitrage Risk Gate (套利风险门控)
Integrates with deterministic Risk Layer / Final Gate.
Ensures arbitrage protection cannot bypass risk checks.

Taiwan Market Constraints:
- ±10% price limit
- T+2 settlement
- Liquidity insufficient → veto
"""

from typing import Dict, List
from modules.strategy.arbitrage_protection import ArbitrageOpportunity, ArbitrageProtectionReport


class ArbitrageRiskGate:
    """
    Deterministic Risk Layer / Final Gate for arbitrage.
    Must NOT be bypassed by arbitrage protection mechanism.
    """
    
    def __init__(self, position_limit: float, exposure_limit: float, loss_limit: float):
        self.position_limit = position_limit
        self.exposure_limit = exposure_limit
        self.loss_limit = loss_limit
        # Taiwan market: T+2 settlement risk
        self.settlement_days = 2
        # ±10% price limit
        self.price_limit_percent = 0.10
        
    def evaluate_arbitrage(self, opportunity: ArbitrageOpportunity, net_profit: float) -> Dict:
        """
        Evaluate arbitrage against Risk Layer.
        Returns: {'passed': bool, 'reasons': List[str]}
        """
        reasons = []
        passed = True
        
        # 1. Position limit check
        if not self._check_position_limit(opportunity):
            reasons.append('ARBITRAGE_POSITION_LIMIT_BREACH')
            passed = False
            
        # 2. Exposure limit check
        if not self._check_exposure_limit(opportunity, net_profit):
            reasons.append('ARBITRAGE_EXPOSURE_LIMIT_BREACH')
            passed = False
            
        # 3. Loss limit check
        if not self._check_loss_limit(opportunity, net_profit):
            reasons.append('ARBITRAGE_LOSS_LIMIT_BREACH')
            passed = False
            
        # 4. Taiwan market: price limit check (±10%)
        if not self._check_price_limit(opportunity):
            reasons.append('ARBITRAGE_PRICE_LIMIT_BREACH')
            passed = False
            
        # 5. T+2 settlement risk: check if we can hold position for 2 days
        if not self._check_settlement_risk(opportunity):
            reasons.append('ARBITRAGE_SETTLEMENT_RISK')
            passed = False
            
        # 6. Portfolio risk: arbitrage must not increase overall risk exposure
        if not self._check_portfolio_risk(opportunity, net_profit):
            reasons.append('ARBITRAGE_PORTFOLIO_RISK_INCREASE')
            passed = False
            
        return {'passed': passed, 'reasons': reasons}
        
    def _check_position_limit(self, opportunity: ArbitrageOpportunity) -> bool:
        """Check if arbitrage would breach position limit."""
        # Simplified: in real implementation, would check current position + new arbitrage
        return True  # Placeholder
        
    def _check_exposure_limit(self, opportunity: ArbitrageOpportunity, net_profit: float) -> bool:
        """Check if arbitrage exposure (gross profit) exceeds limit."""
        return abs(net_profit) <= self.exposure_limit
        
    def _check_loss_limit(self, opportunity: ArbitrageOpportunity, net_profit: float) -> bool:
        """Check if arbitrage could cause loss beyond limit."""
        # If net_profit is negative, check against loss limit
        if net_profit < 0:
            return abs(net_profit) <= self.loss_limit
        return True
        
    def _check_price_limit(self, opportunity: ArbitrageOpportunity) -> bool:
        """Taiwan market: check prices within ±10% limit."""
        if not (opportunity.price_limit_lower <= opportunity.price_a <= opportunity.price_limit_upper):
            return False
        if not (opportunity.price_limit_lower <= opportunity.price_b <= opportunity.price_limit_upper):
            return False
        return True
        
    def _check_settlement_risk(self, opportunity: ArbitrageOpportunity) -> bool:
        """T+2 settlement: check if we can hold for 2 business days."""
        # Simplified: would check market risk over 2-day holding period
        return True  # Placeholder
        
    def _check_portfolio_risk(self, opportunity: ArbitrageOpportunity, net_profit: float) -> bool:
        """Check arbitrage doesn't increase overall portfolio risk."""
        # Simplified: would check VaR, CVaR, etc.
        return True  # Placeholder
