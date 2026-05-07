"""
R029: Cost Tracking Module (成本追踪模块)
Implements explicit transaction cost tracking for Taiwan market.
Tracks: transaction tax, broker fees, expected vs actual costs.
Complies with NEA v0.1 mandatory patches for R029.
"""

from typing import Dict, List, Optional
from datetime import datetime


class CostTracker:
    """
    Tracks all transaction costs with Taiwan market specifics.
    Transaction tax: 0.1425% on sell side only.
    Broker fees: configurable rate (default 0.1425%).
    """
    
    def __init__(self, broker_fee_rate: float = 0.001425):
        self.broker_fee_rate = broker_fee_rate
        self.transaction_tax_rate = 0.001425  # Taiwan securities transaction tax
        
        # Cost history for monitoring
        self.cost_history: List[Dict] = []
        
    def calculate_expected_costs(self, price: float, volume: int, 
                                is_sell: bool = True) -> Dict:
        """
        Calculate expected costs before execution.
        Returns structured cost breakdown.
        """
        trade_value = price * volume
        
        transaction_tax = 0.0
        if is_sell:
            transaction_tax = trade_value * self.transaction_tax_rate
            
        broker_fee = trade_value * self.broker_fee_rate
        total_cost = transaction_tax + broker_fee
        
        cost_breakdown = {
            'trade_value': trade_value,
            'transaction_tax': transaction_tax,
            'broker_fee': broker_fee,
            'total_cost': total_cost,
            'cost_per_share': total_cost / volume if volume > 0 else 0.0,
            'is_sell': is_sell,
            'timestamp': datetime.now().isoformat()
        }
        
        return cost_breakdown
        
    def record_actual_costs(self, expected: Dict, actual_cost: float, 
                           actual_tax: float = 0.0) -> Dict:
        """
        Record actual costs after execution.
        Returns cost comparison for monitoring.
        """
        variance = {
            'expected_total': expected['total_cost'],
            'actual_total': actual_cost,
            'variance': actual_cost - expected['total_cost'],
            'variance_percent': ((actual_cost - expected['total_cost']) / 
                                 expected['total_cost'] * 100) if expected['total_cost'] > 0 else 0.0,
            'expected_tax': expected.get('transaction_tax', 0.0),
            'actual_tax': actual_tax,
            'expected_fee': expected.get('broker_fee', 0.0),
            'timestamp': datetime.now().isoformat()
        }
        
        # Store in history
        self.cost_history.append({
            'expected': expected,
            'actual': variance,
            'type': 'cost_tracking'
        })
        
        return variance
        
    def get_cost_summary(self, days: int = 30) -> Dict:
        """
        Get cost summary for monitoring.
        Returns aggregated cost metrics.
        """
        if not self.cost_history:
            return {'total_cost': 0.0, 'trade_count': 0}
            
        recent_costs = self.cost_history[-days:] if len(self.cost_history) > days else self.cost_history
        
        total_tax = sum(h['actual']['actual_tax'] for h in recent_costs)
        total_fee = sum(h['expected']['broker_fee'] for h in recent_costs)
        total_trades = len(recent_costs)
        
        return {
            'total_trades': total_trades,
            'total_transaction_tax': total_tax,
            'total_broker_fee': total_fee,
            'total_cost': total_tax + total_fee,
            'avg_cost_per_trade': (total_tax + total_fee) / total_trades if total_trades > 0 else 0.0
        }
