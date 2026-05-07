"""
R029: Slippage Monitoring Module (滑点监控模块)
Implements slippage monitoring with expected vs actual comparison.
Complies with NEA v0.1 mandatory patches for R029.
"""

from typing import Dict, List, Optional
from datetime import datetime


class SlippageMonitor:
    """
    Monitors slippage with expected vs actual comparison.
    Provides structured outputs for deterministic final gate.
    """
    
    def __init__(self):
        self.slippage_history: List[Dict] = []
        self.monitoring_enabled = True
        
    def estimate_expected_slippage(self, price: float, volume: int, 
                                  is_odd_lot: bool = False) -> Dict:
        """
        Estimate expected slippage before execution.
        Returns structured slippage breakdown.
        """
        base_slippage_percent = 0.001  # 0.1% base
        
        # Volume factor: larger volume → higher slippage
        volume_factor = min(volume / 1000, 5.0)
        
        # Odd lot penalty: higher slippage for odd lots
        odd_lot_factor = 1.5 if is_odd_lot else 1.0
        
        slippage_percent = base_slippage_percent * volume_factor * odd_lot_factor
        expected_slippage = price * slippage_percent
        
        return {
            'expected_slippage': expected_slippage,
            'slippage_percent': slippage_percent * 100,
            'base_percent': base_slippage_percent * 100,
            'volume_factor': volume_factor,
            'odd_lot_factor': odd_lot_factor,
            'price': price,
            'volume': volume,
            'is_odd_lot': is_odd_lot,
            'timestamp': datetime.now().isoformat()
        }
        
    def record_actual_slippage(self, expected: Dict, actual_price: float) -> Dict:
        """
        Record actual slippage after execution.
        Returns slippage comparison for monitoring.
        """
        expected_slippage = expected['expected_slippage']
        expected_price = expected['price']
        
        # Calculate actual slippage
        actual_slippage = abs(actual_price - expected_price)
        actual_slippage_percent = (actual_slippage / expected_price) * 100 if expected_price > 0 else 0.0
        
        # Variance
        slippage_variance = actual_slippage - expected_slippage
        variance_percent = ((actual_slippage - expected_slippage) / 
                             expected_slippage * 100) if expected_slippage > 0 else 0.0
        
        monitoring_record = {
            'expected': expected,
            'actual': {
                'actual_price': actual_price,
                'actual_slippage': actual_slippage,
                'actual_slippage_percent': actual_slippage_percent,
                'timestamp': datetime.now().isoformat()
            },
            'variance': {
                'slippage_variance': slippage_variance,
                'variance_percent': variance_percent,
                'within_tolerance': abs(variance_percent) <= 10.0  # 10% tolerance
            },
            'type': 'slippage_monitoring'
        }
        
        # Store in history
        self.slippage_history.append(monitoring_record)
        
        return monitoring_record
        
    def get_slippage_summary(self, trades: int = 30) -> Dict:
        """
        Get slippage summary for monitoring.
        Returns aggregated slippage metrics.
        """
        if not self.slippage_history:
            return {'total_trades': 0, 'avg_variance': 0.0}
            
        recent = self.slippage_history[-trades:] if len(self.slippage_history) > trades else self.slippage_history
        
        variances = [h['variance']['slippage_variance'] for h in recent]
        avg_variance = sum(variances) / len(variances)
        
        within_tolerance = sum(1 for h in recent if h['variance']['within_tolerance'])
        
        return {
            'total_trades': len(recent),
            'avg_expected_slippage': sum(h['expected']['expected_slippage'] for h in recent) / len(recent),
            'avg_actual_slippage': sum(h['actual']['actual_slippage'] for h in recent) / len(recent),
            'avg_variance': avg_variance,
            'within_tolerance_count': within_tolerance,
            'within_tolerance_percent': (within_tolerance / len(recent)) * 100 if recent else 0.0
        }
        
    def get_monitoring_ready_schema(self) -> Dict:
        """
        Returns monitoring-ready schema for deterministic gate.
        Structured outputs for cost/slippage/fill decisions.
        """
        return {
            'monitoring_type': 'slippage',
            'schema_version': '1.0',
            'fields': {
                'expected_slippage': 'float',
                'actual_slippage': 'float',
                'variance': 'float',
                'variance_percent': 'float',
                'within_tolerance': 'bool',
                'timestamp': 'isoformat'
            },
            'deterministic_gate_ready': True,
            'taiwan_compatible': True,
            'price_limit_check': '±10%',
            'settlement': 'T+2'
        }
