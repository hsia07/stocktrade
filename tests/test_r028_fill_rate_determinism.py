"""
R028: Fill Rate Determinism Tests (填充率确定性测试)
Tests R028 deterministic rework: random.uniform removed from fill-rate paths.

This file tests the deterministic fill-rate/probability rework:
1. layer.py:estimate_fill_rate is now deterministic (no random.uniform)
2. arbitrage_slippage_model.py:_estimate_fill_rate is now deterministic (no random.uniform)
3. Same input repeated calls produce identical output
4. Arbitrage net_profit is deterministic
5. Protection veto is deterministic
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from modules.market_reality.layer import MarketRealityLayer
from modules.market_reality.arbitrage_slippage_model import ArbitrageSlippageModel
from modules.strategy.arbitrage_protection import (
    ArbitrageProtection, ArbitrageOpportunity, ArbitrageType, ProtectionDecision
)
from modules.risk.arbitrage_risk_gate import ArbitrageRiskGate


class TestR028FillRateDeterminism:
    """Test R028 estimate_fill_rate determinism."""

    def test_estimate_fill_rate_repeated_identical_odd_lot(self):
        layer = MarketRealityLayer()
        r1 = layer.estimate_fill_rate(500, is_odd_lot=True)
        r2 = layer.estimate_fill_rate(500, is_odd_lot=True)
        r3 = layer.estimate_fill_rate(500, is_odd_lot=True)
        assert r1 == r2 == r3

    def test_estimate_fill_rate_repeated_identical_board_lot(self):
        layer = MarketRealityLayer()
        r1 = layer.estimate_fill_rate(1000, is_odd_lot=False)
        r2 = layer.estimate_fill_rate(1000, is_odd_lot=False)
        r3 = layer.estimate_fill_rate(1000, is_odd_lot=False)
        assert r1 == r2 == r3

    def test_estimate_fill_rate_repeated_identical_large_volume(self):
        layer = MarketRealityLayer()
        r1 = layer.estimate_fill_rate(15000, is_odd_lot=False)
        r2 = layer.estimate_fill_rate(15000, is_odd_lot=False)
        r3 = layer.estimate_fill_rate(15000, is_odd_lot=False)
        assert r1 == r2 == r3

    def test_estimate_fill_rate_deterministic_values(self):
        layer = MarketRealityLayer()
        assert layer.estimate_fill_rate(500, is_odd_lot=True) == 0.80
        assert layer.estimate_fill_rate(999, is_odd_lot=True) == 0.80
        assert layer.estimate_fill_rate(1000, is_odd_lot=False) == 0.97
        assert layer.estimate_fill_rate(5000, is_odd_lot=False) == 0.97
        assert layer.estimate_fill_rate(10000, is_odd_lot=False) == 0.97
        assert layer.estimate_fill_rate(10001, is_odd_lot=False) == 0.85
        assert layer.estimate_fill_rate(50000, is_odd_lot=False) == 0.85

    def test_estimate_fill_rate_odd_lot_lower_than_board_lot(self):
        layer = MarketRealityLayer()
        odd = layer.estimate_fill_rate(500, is_odd_lot=True)
        board = layer.estimate_fill_rate(1000, is_odd_lot=False)
        assert odd < board

    def test_estimate_fill_rate_large_volume_lower_than_normal(self):
        layer = MarketRealityLayer()
        normal = layer.estimate_fill_rate(1000, is_odd_lot=False)
        large = layer.estimate_fill_rate(15000, is_odd_lot=False)
        assert large < normal


class TestR028ArbitrageFillRateDeterminism:
    """Test arbitrage_slippage_model _estimate_fill_rate determinism."""

    def _make_opp(self, volume):
        return ArbitrageOpportunity(
            arbitrage_type=ArbitrageType.SPOT_FUTURES,
            security_a="2330.TW",
            security_b="TXF.TF",
            gross_profit=10000.0,
            volume=volume,
            price_a=500.0,
            price_b=505.0,
            price_limit_upper=550.0,
            price_limit_lower=450.0,
            settlement_date="2026-05-08"
        )

    def test_estimate_fill_rate_repeated_identical_odd_lot(self):
        model = ArbitrageSlippageModel()
        opp = self._make_opp(500)
        r1 = model._estimate_fill_rate(opp)
        r2 = model._estimate_fill_rate(opp)
        r3 = model._estimate_fill_rate(opp)
        assert r1 == r2 == r3

    def test_estimate_fill_rate_repeated_identical_board_lot(self):
        model = ArbitrageSlippageModel()
        opp = self._make_opp(1000)
        r1 = model._estimate_fill_rate(opp)
        r2 = model._estimate_fill_rate(opp)
        r3 = model._estimate_fill_rate(opp)
        assert r1 == r2 == r3

    def test_estimate_fill_rate_repeated_identical_large_volume(self):
        model = ArbitrageSlippageModel()
        opp = self._make_opp(15000)
        r1 = model._estimate_fill_rate(opp)
        r2 = model._estimate_fill_rate(opp)
        r3 = model._estimate_fill_rate(opp)
        assert r1 == r2 == r3

    def test_estimate_fill_rate_deterministic_values(self):
        model = ArbitrageSlippageModel()
        assert model._estimate_fill_rate(self._make_opp(500)) == 0.80
        assert model._estimate_fill_rate(self._make_opp(999)) == 0.80
        assert model._estimate_fill_rate(self._make_opp(1000)) == 0.97
        assert model._estimate_fill_rate(self._make_opp(5000)) == 0.97
        assert model._estimate_fill_rate(self._make_opp(10000)) == 0.97
        assert model._estimate_fill_rate(self._make_opp(10001)) == 0.85
        assert model._estimate_fill_rate(self._make_opp(50000)) == 0.85


class TestR028ArbitrageNetProfitDeterminism:
    """Test arbitrage net_profit determinism (depends on fill_rate)."""

    def _make_opp(self, volume, gross_profit=10000.0):
        return ArbitrageOpportunity(
            arbitrage_type=ArbitrageType.SPOT_FUTURES,
            security_a="2330.TW",
            security_b="TXF.TF",
            gross_profit=gross_profit,
            volume=volume,
            price_a=500.0,
            price_b=505.0,
            price_limit_upper=550.0,
            price_limit_lower=450.0,
            settlement_date="2026-05-08"
        )

    def test_net_profit_repeated_identical(self):
        model = ArbitrageSlippageModel()
        opp = self._make_opp(5000, gross_profit=10000.0)
        r1 = model.evaluate_arbitrage(opp)
        r2 = model.evaluate_arbitrage(opp)
        r3 = model.evaluate_arbitrage(opp)
        assert r1['net_profit'] == r2['net_profit'] == r3['net_profit']

    def test_fill_rate_repeated_identical(self):
        model = ArbitrageSlippageModel()
        opp = self._make_opp(5000, gross_profit=10000.0)
        r1 = model.evaluate_arbitrage(opp)
        r2 = model.evaluate_arbitrage(opp)
        r3 = model.evaluate_arbitrage(opp)
        assert r1['fill_rate'] == r2['fill_rate'] == r3['fill_rate']

    def test_protection_veto_repeated_identical(self):
        class MockRiskGate:
            def evaluate_arbitrage(self, opp, net_profit):
                return {'passed': True, 'reasons': []}
        model = ArbitrageSlippageModel()
        protection = ArbitrageProtection(MockRiskGate(), model)
        opp = self._make_opp(5000, gross_profit=10000.0)
        r1 = protection.evaluate_opportunity(opp)
        r2 = protection.evaluate_opportunity(opp)
        r3 = protection.evaluate_opportunity(opp)
        assert r1.net_profit_after_costs == r2.net_profit_after_costs == r3.net_profit_after_costs
        assert r1.decision == r2.decision == r3.decision
        assert r1.fill_rate_estimate == r2.fill_rate_estimate == r3.fill_rate_estimate


class TestR028NoRandomInFillPaths:
    """Source scan: no random in fill-rate decision paths."""

    def test_no_random_import_in_layer(self):
        with open("modules/market_reality/layer.py", encoding="utf-8") as f:
            content = f.read()
        assert "import random" not in content
        assert "random.uniform" not in content
        assert "random.random" not in content

    def test_no_random_import_in_arbitrage_slippage(self):
        with open("modules/market_reality/arbitrage_slippage_model.py", encoding="utf-8") as f:
            content = f.read()
        assert "import random" not in content
        assert "random.uniform" not in content
        assert "random.random" not in content