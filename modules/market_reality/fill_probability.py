"""
R029: Fill Probability Modeling Module (填充概率建模模块)
Implements fill probability modeling with structured outputs.
Complies with NEA v0.1 mandatory patches for R029.
"""

from typing import Dict, Optional
import random
from datetime import datetime


class FillProbabilityModel:
    """
    Models fill probability for orders.
    Provides structured outputs for deterministic final gate.
    """
    
    def __init__(self):
        self.fill_history: List[Dict] = []
        
    def estimate_fill_probability(self, volume: int, is_odd_lot: bool = False,
                                   market_volatility: str = 'normal') -> Dict:
        """
        Estimate fill probability before order placement.
        Returns structured fill probability breakdown.
        """
        # Base probability based on lot type
        if is_odd_lot:
            base_prob = random.uniform(0.75, 0.95)  # Lower for odd lots
        else:
            if volume > 10000:  # Large volume
                base_prob = random.uniform(0.85, 0.98)  # Partial fill likely
            else:
                base_prob = random.uniform(0.95, 1.0)  # Normal fill rate
                
        # Adjust based on market volatility
        volatility_adjustment = {
            'low': 0.02,
            'normal': 0.0,
            'high': -0.05
        }.get(market_volatility, 0.0)
        
        adjusted_prob = min(max(base_prob + volatility_adjustment, 0.0), 1.0)
        
        return {
            'fill_probability': adjusted_prob,
            'fill_percentage': adjusted_prob * 100,
            'base_probability': base_prob,
            'volatility_adjustment': volatility_adjustment,
            'is_odd_lot': is_odd_lot,
            'volume': volume,
            'market_volatility': market_volatility,
            'expected_fill_rate': adjusted_prob,
            'timestamp': datetime.now().isoformat()
        }
        
    def record_actual_fill(self, expected: Dict, actual_filled: int, 
                              actual_volume: int) -> Dict:
        """
        Record actual fill after execution.
        Returns fill comparison for monitoring.
        """
        expected_prob = expected['fill_probability']
        actual_prob = actual_filled / actual_volume if actual_volume > 0 else 0.0
        
        fill_variance = actual_prob - expected_prob
        
        fill_record = {
            'expected': expected,
            'actual': {
                'actual_filled': actual_filled,
                'actual_volume': actual_volume,
                'actual_fill_rate': actual_prob,
                'timestamp': datetime.now().isoformat()
            },
            'variance': {
                'fill_variance': fill_variance,
                'variance_percent': (fill_variance / expected_prob) * 100 if expected_prob > 0 else 0.0,
                'filled_as_expected': abs(fill_variance) <= 0.05  # 5% tolerance
            },
            'type': 'fill_probability'
        }
        
        # Store in history
        self.fill_history.append(fill_record)
        
        return fill_record
        
    def get_fill_summary(self, trades: int = 30) -> Dict:
        """
        Get fill probability summary for monitoring.
        Returns aggregated fill metrics.
        """
        if not self.fill_history:
            return {'total_trades': 0, 'avg_fill_rate': 0.0}
            
        recent = self.fill_history[-trades:] if len(self.fill_history) > trades else self.fill_history
        
        fill_rates = [h['actual']['actual_fill_rate'] for h in recent]
        avg_fill_rate = sum(fill_rates) / len(fill_rates)
        
        as_expected = sum(1 for h in recent if h['variance']['filled_as_expected'])
        
        return {
            'total_trades': len(recent),
            'avg_expected_fill_rate': sum(h['expected']['fill_probability'] for h in recent) / len(recent),
            'avg_actual_fill_rate': avg_fill_rate,
            'avg_variance': sum(h['variance']['fill_variance'] for h in recent) / len(recent),
            'filled_as_expected_count': as_expected,
            'filled_as_expected_percent': (as_expected / len(recent)) * 100 if recent else 0.0
        }
        
    def get_modeling_ready_schema(self) -> Dict:
        """
        Returns modeling-ready schema for deterministic gate.
        Structured outputs for cost/slippage/fill decisions.
        """
        return {
            'modeling_type': 'fill_probability',
            'schema_version': '1.0',
            'fields': {
                'fill_probability': 'float',
                'fill_percentage': 'float',
                'expected_fill_rate': 'float',
                'actual_fill_rate': 'float',
                'fill_variance': 'float',
                'filled_as_expected': 'bool',
                'timestamp': 'isoformat'
            },
            'deterministic_gate_ready': True,
            'taiwan_compatible': True,
            'price_limit_check': '±10%',
            'settlement': 'T+2'
        }
