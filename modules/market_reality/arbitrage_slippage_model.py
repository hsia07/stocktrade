"""
R027: Market Reality - Arbitrage Slippage Model (市场现实-套利滑价模型)
Integrates with Market Reality Layer for arbitrage.
Handles cost, slippage, fill rate, partial fill, non-fill scenarios.

Taiwan Market Realities:
- 集合竞价: 08:30-09:00 (pre-market auction)
- 盘中交易: 09:00-13:30 (continuous trading)
- 零股交易: 13:40-14:30 (odd lots, different pricing)
- 流动性不足: wide bid/ask spread, low volume
"""

from typing import Dict
import random


class ArbitrageSlippageModel:
    """
    Market Reality Layer for arbitrage.
    Models cost, slippage, fill rate, partial fill, non-fill.
    """
    
    def __init__(self):
        # Taiwan market trading sessions
        self.pre_market_auction = ("08:30", "09:00")
        self.continuous_trading = ("09:00", "13:30")
        self.odd_lot_trading = ("13:40", "14:30")
        # Costs
        self.transaction_tax_rate = 0.001425  # Taiwan securities transaction tax
        self.broker_fee_rate = 0.001425  # Simplified broker fee
        
    def evaluate_arbitrage(self, opportunity: 'ArbitrageOpportunity') -> Dict:
        """
        Evaluate arbitrage against Market Reality Layer.
        Returns: {'passed': bool, 'reasons': List[str], 'net_profit': float,
                  'fill_rate': float, 'slippage': float, 'liquidity_insufficient': bool}
        """
        reasons = []
        passed = True
        
        # 1. Calculate costs (transaction tax + fees)
        costs = self._calculate_costs(opportunity)
        
        # 2. Estimate slippage based on Taiwan market reality
        slippage = self._estimate_slippage(opportunity)
        
        # 3. Estimate fill rate (may not fill 100%)
        fill_rate = self._estimate_fill_rate(opportunity)
        
        # 4. Check liquidity
        liquidity_insufficient = self._check_liquidity(opportunity)
        if liquidity_insufficient:
            reasons.append('LIQUIDITY_INSUFFICIENT')
            passed = False
            
        # 5. Calculate net profit after costs and slippage
        # Note: gross_profit is before costs and slippage
        net_profit = opportunity.gross_profit - costs - slippage
        
        # 6. Adjust for partial fill
        if fill_rate < 1.0:
            net_profit = net_profit * fill_rate
            reasons.append('PARTIAL_FILL')
            
        # 7. Check if arbitrage is in valid trading session
        if not self._check_trading_session(opportunity):
            reasons.append('INVALID_TRADING_SESSION')
            passed = False
            
        # 8. Check zero lot vs whole lot differences
        if self._is_odd_lot(opportunity):
            reasons.append('ODD_LOT_ARBITRAGE')
            # Odd lot pricing may differ from whole lot
            
        return {
            'passed': passed,
            'reasons': reasons,
            'net_profit': net_profit,
            'fill_rate': fill_rate,
            'slippage': slippage,
            'liquidity_insufficient': liquidity_insufficient,
            'costs': costs
        }
        
    def _calculate_costs(self, opportunity: 'ArbitrageOpportunity') -> float:
        """Calculate total costs: transaction tax + fees."""
        # Transaction tax (Taiwan: 0.1425% on sell side)
        tax = abs(opportunity.price_a * opportunity.volume) * self.transaction_tax_rate
        # Broker fees (simplified)
        fees = abs(opportunity.price_a * opportunity.volume) * self.broker_fee_rate
        return tax + fees
        
    def _estimate_slippage(self, opportunity: 'ArbitrageOpportunity') -> float:
        """
        Estimate slippage based on Taiwan market reality.
        Higher volume → higher slippage.
        Lower liquidity → higher slippage.
        """
        # Simplified model: 0.1% to 1% depending on volume and liquidity
        base_slippage_percent = 0.001  # 0.1%
        # Adjust based on volume (larger volume → higher slippage)
        volume_factor = min(opportunity.volume / 1000, 5.0)  # Cap at 5x
        slippage_percent = base_slippage_percent * volume_factor
        return opportunity.gross_profit * slippage_percent
        
    def _estimate_fill_rate(self, opportunity: 'ArbitrageOpportunity') -> float:
        """
        Estimate fill rate probability.
        May not fill 100% of intended arbitrage volume.
        """
        # Simplified: 90% to 100% fill rate
        # In reality, depends on order book depth, market volatility, etc.
        return random.uniform(0.90, 1.0)
        
    def _check_liquidity(self, opportunity: 'ArbitrageOpportunity') -> bool:
        """
        Check if liquidity is sufficient for arbitrage.
        Wide bid/ask spread or low volume → liquidity insufficient.
        """
        # Simplified: check if volume is above threshold
        min_volume_threshold = 1000  # Minimum volume for arbitrage
        return opportunity.volume >= min_volume_threshold
        
    def _check_trading_session(self, opportunity: 'ArbitrageOpportunity') -> bool:
        """
        Check if arbitrage is in valid Taiwan market trading session.
        - 集合竞价: 08:30-09:00
        - 盘中交易: 09:00-13:30
        - 零股交易: 13:40-14:30
        """
        # Simplified: assume all arbitrage happens during continuous trading
        return True
        
    def _is_odd_lot(self, opportunity: 'ArbitrageOpportunity') -> bool:
        """Check if arbitrage involves odd lots (零股)."""
        # Taiwan: odd lots < 1000 shares
        return opportunity.volume < 1000
