"""
R029: Tests for Cost Tracking, Slippage Monitoring, Fill Probability Modeling.
Verifies NEA v0.1 mandatory patches for R029.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from market_reality.cost_tracking import CostTracker
from market_reality.slippage_monitor import SlippageMonitor
from market_reality.fill_probability import FillProbabilityModel
from market_reality.integration import MarketRealityIntegration


def test_cost_tracker():
    """Test R029: Cost tracking functionality."""
    tracker = CostTracker()
    
    # Test 1: Sell order costs
    costs = tracker.calculate_expected_costs(price=100.0, volume=1000, is_sell=True)
    assert costs['transaction_tax'] == 100000 * 0.001425  # 142.5
    assert costs['broker_fee'] == 100000 * 0.001425  # 142.5
    assert costs['total_cost'] == 285.0
    print("PASS: test_cost_tracker 1 - sell order costs")
    
    # Test 2: Buy order costs (no transaction tax)
    costs = tracker.calculate_expected_costs(price=100.0, volume=1000, is_sell=False)
    assert costs['transaction_tax'] == 0.0
    assert costs['broker_fee'] == 142.5
    print("PASS: test_cost_tracker 2 - buy order costs")
    
    # Test 3: Cost breakdown structure
    costs = tracker.calculate_expected_costs(price=50.0, volume=500, is_sell=True)
    assert 'trade_value' in costs
    assert 'transaction_tax' in costs
    assert 'broker_fee' in costs
    assert 'total_cost' in costs
    assert 'cost_per_share' in costs
    print("PASS: test_cost_tracker 3 - cost breakdown structure")
    

def test_slippage_monitor():
    """Test R029: Slippage monitoring functionality."""
    monitor = SlippageMonitor()
    
    # Test 1: Expected slippage estimation
    expected = monitor.estimate_expected_slippage(price=100.0, volume=1000, is_odd_lot=False)
    assert 'expected_slippage' in expected
    assert 'slippage_percent' in expected
    assert expected['expected_slippage'] > 0
    print("PASS: test_slippage_monitor 1 - expected slippage")
    
    # Test 2: Odd lot penalty
    odd_lot = monitor.estimate_expected_slippage(price=100.0, volume=500, is_odd_lot=True)
    round_lot = monitor.estimate_expected_slippage(price=100.0, volume=1000, is_odd_lot=False)
    assert odd_lot['odd_lot_factor'] == 1.5
    assert round_lot['odd_lot_factor'] == 1.0
    print("PASS: test_slippage_monitor 2 - odd lot penalty")
    
    # Test 3: Monitoring-ready schema
    schema = monitor.get_monitoring_ready_schema()
    assert schema['deterministic_gate_ready'] == True
    assert schema['taiwan_compatible'] == True
    assert 'expected_slippage' in schema['fields']
    print("PASS: test_slippage_monitor 3 - monitoring schema")
    

def test_fill_probability_model():
    """Test R029: Fill probability modeling functionality."""
    model = FillProbabilityModel()
    
    # Test 1: Fill probability estimation
    fill = model.estimate_fill_probability(volume=1000, is_odd_lot=False, market_volatility='normal')
    assert 'fill_probability' in fill
    assert 0.0 <= fill['fill_probability'] <= 1.0
    print("PASS: test_fill_probability_model 1 - fill probability")
    
    # Test 2: Odd lot fill rate
    odd_fill = model.estimate_fill_probability(volume=500, is_odd_lot=True)
    round_fill = model.estimate_fill_probability(volume=1000, is_odd_lot=False)
    assert odd_fill['is_odd_lot'] == True
    assert round_fill['is_odd_lot'] == False
    print("PASS: test_fill_probability_model 2 - odd lot fill")
    
    # Test 3: Modeling-ready schema
    schema = model.get_modeling_ready_schema()
    assert schema['deterministic_gate_ready'] == True
    assert 'fill_probability' in schema['fields']
    assert schema['taiwan_compatible'] == True
    print("PASS: test_fill_probability_model 3 - modeling schema")
    

def test_integration():
    """Test R029: Integration with R028 Market Reality Layer."""
    integration = MarketRealityIntegration()
    
    # Test 1: Comprehensive order evaluation
    result = integration.evaluate_order_with_tracking(
        price=105.0, volume=1000, reference_price=100.0,
        avg_daily_volume=100000, is_sell=True
    )
    assert result['deterministic_gate_ready'] == True
    assert 'costs' in result
    assert 'slippage' in result
    assert 'fill' in result
    assert result['taiwan_compliance']['all_constraints_enforced'] == True
    print("PASS: test_integration 1 - comprehensive evaluation")
    
    # Test 2: Taiwan market constraints preserved
    assert result['constraints']['price_limit']['passed'] == True
    assert result['constraints']['settlement_cycle'] == 'T+2'
    print("PASS: test_integration 2 - Taiwan constraints")
    
    # Test 3: Monitoring summary
    summary = integration.get_monitoring_summary()
    assert 'cost_summary' in summary
    assert 'slippage_summary' in summary
    assert 'fill_summary' in summary
    assert summary['deterministic_gate']['ready'] == True
    print("PASS: test_integration 3 - monitoring summary")
    

def test_taiwan_market_compatibility():
    """Test R029: Taiwan market compatibility with R028."""
    integration = MarketRealityIntegration()
    
    # Test 1: Price limit ±10%
    result = integration.evaluate_order_with_tracking(
        price=111.0, volume=1000, reference_price=100.0
    )
    assert result['constraints']['price_limit']['passed'] == False
    assert 'PRICE_EXCEEDS_LIMIT_UP' in str(result['reasons'])
    print("PASS: test_taiwan_market_compatibility 1 - price limit enforcement")
    
    # Test 2: Odd lot detection
    result = integration.evaluate_order_with_tracking(
        price=100.0, volume=500, reference_price=100.0
    )
    assert result['constraints']['lot_type'] == 'ODD_LOT'
    print("PASS: test_taiwan_market_compatibility 2 - odd lot detection")
    
    # Test 3: T+2 settlement
    assert result['constraints']['settlement_cycle'] == 'T+2'
    print("PASS: test_taiwan_market_compatibility 3 - T+2 settlement")
    

if __name__ == '__main__':
    print("=== R029 Test Suite ===")
    print("Testing NEA v0.1 mandatory patches for R029...")
    print()
    
    test_cost_tracker()
    test_slippage_monitor()
    test_fill_probability_model()
    test_integration()
    test_taiwan_market_compatibility()
    
    print()
    print("=== All R029 tests passed ===")
