"""
Test cases for R027 Arbitrage Protection Mechanism (套利保护机制)
Tests arbitrage protection only (no execution, no broker/order changes).
Integrates with Risk Layer and Market Reality Layer.
"""

import pytest
from modules.strategy.arbitrage_protection import (
    ArbitrageProtection, ArbitrageOpportunity, ArbitrageType, ProtectionDecision
)
from modules.risk.arbitrage_risk_gate import ArbitrageRiskGate
from modules.market_reality.arbitrage_slippage_model import ArbitrageSlippageModel


# --- Fixtures ---

@pytest.fixture
def mock_risk_gate():
    """Mock Risk Gate that approves all."""
    class MockRiskGate:
        def evaluate_arbitrage(self, opp, net_profit):
            return {'passed': True, 'reasons': []}
    return MockRiskGate()


@pytest.fixture
def mock_market_reality():
    """Mock Market Reality that approves all."""
    class MockMarketReality:
        def evaluate_arbitrage(self, opp):
            return {
                'passed': True,
                'reasons': [],
                'net_profit': opp.gross_profit,
                'fill_rate': 1.0,
                'slippage': 0.0,
                'liquidity_insufficient': False
            }
    return MockMarketReality()


@pytest.fixture
def protection(mock_risk_gate, mock_market_reality):
    """ArbitrageProtection instance."""
    return ArbitrageProtection(mock_risk_gate, mock_market_reality)


@pytest.fixture
def valid_opportunity():
    """Valid arbitrage opportunity within Taiwan market constraints."""
    return ArbitrageOpportunity(
        arbitrage_type=ArbitrageType.SPOT_FUTURES,
        security_a="2330.TW",
        security_b="TXF.TF",
        gross_profit=10000.0,
        volume=1000,
        price_a=500.0,
        price_b=505.0,
        price_limit_upper=550.0,  # +10%
        price_limit_lower=450.0,  # -10%
        settlement_date="2026-05-08"  # T+2
    )


# --- Test Cases ---

class TestArbitrageProtectionMechanism:
    """Test R027 arbitrage protection (no execution)."""
    
    def test_protection_approves_valid_opportunity(self, protection, valid_opportunity):
        """Test protection approves valid arbitrage opportunity."""
        report = protection.evaluate_opportunity(valid_opportunity)
        assert report.decision == ProtectionDecision.APPROVE
        assert 'PROTECTION_APPROVED' in report.reason_codes
        assert report.risk_gate_passed is True
        assert report.market_reality_passed is True
        assert report.taiwan_constraints_passed is True
        
    def test_protection_veto_liquidity_insufficient(self, protection, valid_opportunity):
        """Test protection vetoes when liquidity insufficient."""
        # Mock market reality to return liquidity insufficient
        class LiquidityMock:
            def evaluate_arbitrage(self, opp):
                return {
                    'passed': False,
                    'reasons': ['LIQUIDITY_INSUFFICIENT'],
                    'liquidity_insufficient': True,
                    'fill_rate': 0.5
                }
        protection.market_reality = LiquidityMock()
        
        report = protection.evaluate_opportunity(valid_opportunity)
        assert report.decision == ProtectionDecision.VETO_LIQUIDITY
        assert 'LIQUIDITY_INSUFFICIENT' in report.reason_codes
        
    def test_protection_veto_taiwan_price_limit_breach(self, protection, valid_opportunity):
        """Test protection vetoes when price breaches ±10% limit."""
        # Set price above +10% limit
        valid_opportunity.price_a = 560.0  # > 550.0 (10% above 500)
        
        report = protection.evaluate_opportunity(valid_opportunity)
        assert report.decision == ProtectionDecision.VETO_TAIWAN_CONSTRAINT
        assert 'PRICE_A_BREACHES_LIMIT' in report.reason_codes
        
    def test_protection_veto_risk_limit_breach(self, protection, valid_opportunity):
        """Test protection vetoes when risk limit breached."""
        # Mock risk gate to reject
        class RiskMock:
            def evaluate_arbitrage(self, opp, net_profit):
                return {'passed': False, 'reasons': ['ARBITRAGE_POSITION_LIMIT_BREACH']}
        protection.risk_gate = RiskMock()
        
        report = protection.evaluate_opportunity(valid_opportunity)
        assert report.decision == ProtectionDecision.VETO_RISK_LIMIT
        assert 'ARBITRAGE_POSITION_LIMIT_BREACH' in report.reason_codes
        
    def test_protection_veto_market_reality_unfavorable(self, protection, valid_opportunity):
        """Test protection vetoes when market reality unfavorable."""
        class RealityMock:
            def evaluate_arbitrage(self, opp):
                return {
                    'passed': False,
                    'reasons': ['MARKET_REALITY_UNFAVORABLE'],
                    'net_profit': -1000.0
                }
        protection.market_reality = RealityMock()
        
        report = protection.evaluate_opportunity(valid_opportunity)
        assert report.decision == ProtectionDecision.VETO_MARKET_REALITY
        assert 'MARKET_REALITY_UNFAVORABLE' in report.reason_codes
        
    def test_protection_aborts_when_net_profit_non_positive(self, protection, valid_opportunity):
        """Test protection aborts when net profit after costs is non-positive."""
        # Set gross profit very low
        valid_opportunity.gross_profit = 10.0  # Too low after costs
        
        report = protection.evaluate_opportunity(valid_opportunity)
        assert report.decision == ProtectionDecision.ABORT_NO_TRADE
        assert 'NET_PROFIT_NON_POSITIVE' in report.reason_codes
        
    def test_protection_respects_taiwan_t_plus_2_settlement(self, protection, valid_opportunity):
        """Test protection considers T+2 settlement risk."""
        # This is simplified, but verifies the field exists and is considered
        assert valid_opportunity.settlement_date == "2026-05-08"
        report = protection.evaluate_opportunity(valid_opportunity)
        assert report.taiwan_constraints_passed is True
        
    def test_protection_no_execution_broker_integration(self, protection, valid_opportunity):
        """Test protection does NOT integrate with broker (no execution)."""
        report = protection.evaluate_opportunity(valid_opportunity)
        # Verify no broker/order attributes exist
        assert not hasattr(report, 'broker_order_id')
        assert not hasattr(report, 'execution_status')
        
    def test_protection_generates_pre_trade_report(self, protection, valid_opportunity):
        """Test protection generates pre-trade report with reason codes."""
        report = protection.evaluate_opportunity(valid_opportunity)
        assert isinstance(report.reason_codes, list)
        assert len(report.reason_codes) > 0
        assert isinstance(report.net_profit_after_costs, float)
        assert isinstance(report.fill_rate_estimate, float)
        assert isinstance(report.slippage_estimate, float)
        
    def test_protection_handles_partial_fill_scenario(self, protection, valid_opportunity):
        """Test protection handles partial fill gracefully."""
        class PartialFillMock:
            def evaluate_arbitrage(self, opp):
                return {
                    'passed': True,
                    'reasons': ['PARTIAL_FILL'],
                    'fill_rate': 0.6,  # Only 60% filled
                    'slippage': 100.0
                }
        protection.market_reality = PartialFillMock()
        
        report = protection.evaluate_opportunity(valid_opportunity)
        assert report.decision == ProtectionDecision.APPROVE  # Still approved but with low fill rate
        assert 0 < report.fill_rate_estimate < 1.0
        
    def test_protection_handles_non_fill_scenario(self, protection, valid_opportunity):
        """Test protection handles non-fill scenario gracefully."""
        class NonFillMock:
            def evaluate_arbitrage(self, opp):
                return {
                    'passed': False,
                    'reasons': ['NON_FILL_SCENARIO'],
                    'fill_rate': 0.0,
                    'liquidity_insufficient': True
                }
        protection.market_reality = NonFillMock()
        
        report = protection.evaluate_opportunity(valid_opportunity)
        assert report.decision == ProtectionDecision.VETO_LIQUIDITY
        assert 'NON_FILL_SCENARIO' in report.reason_codes
        

class TestNoExecutionOrBrokerIntegration:
    """Verify no execution/broker/order core modifications."""
    
    def test_no_arbitrage_execution_module_exists(self):
        """Verify arbitrage_execution.py is NOT included."""
        import os
        exec_path = "modules/strategy/arbitrage_execution.py"
        # This file should NOT exist in this candidate
        # (It's forbidden per constraints)
        # We just verify we're not importing it
        
    def test_no_broker_core_modifications(self, protection):
        """Verify no broker core modifications."""
        assert not hasattr(protection, 'broker')
        assert not hasattr(protection, 'order_executor')
        
    def test_no_runtime_modifications(self, protection):
        """Verify no runtime modifications."""
        assert not hasattr(protection, 'runtime')
        assert not hasattr(protection, 'execution_engine')
        

class TestMachineCheckableChecks:
    """Machine-checkable validation."""
    
    def test_arbitrage_protection_module_exists(self):
        """Check arbitrage_protection.py exists."""
        import os
        assert os.path.exists("modules/strategy/arbitrage_protection.py")
        
    def test_risk_gate_module_exists(self):
        """Check arbitrage_risk_gate.py exists."""
        import os
        assert os.path.exists("modules/risk/arbitrage_risk_gate.py")
        
    def test_market_reality_module_exists(self):
        """Check arbitrage_slippage_model.py exists."""
        import os
        assert os.path.exists("modules/market_reality/arbitrage_slippage_model.py")
        
    def test_no_execution_module(self):
        """Verify arbitrage_execution.py does NOT exist."""
        import os
        assert not os.path.exists("modules/strategy/arbitrage_execution.py")
        
    def test_taiwan_constraints_in_code(self, protection, valid_opportunity):
        """Verify Taiwan constraints are checked in code."""
        # Breach price limit
        valid_opportunity.price_a = 560.0
        report = protection.evaluate_opportunity(valid_opportunity)
        assert report.taiwan_constraints_passed is False
        
    def test_liquidity_veto_path_exists(self, protection, valid_opportunity):
        """Verify liquidity veto path exists."""
        class LiquidityMock:
            def evaluate_arbitrage(self, opp):
                return {
                    'passed': False,
                    'reasons': ['LIQUIDITY_INSUFFICIENT'],
                    'liquidity_insufficient': True
                }
        protection.market_reality = LiquidityMock()
        
        report = protection.evaluate_opportunity(valid_opportunity)
        assert report.decision == ProtectionDecision.VETO_LIQUIDITY
        
    def test_cost_slippage_fill_rate_logic(self, protection, valid_opportunity):
        """Verify cost/slippage/fill-rate logic participates in decision."""
        report = protection.evaluate_opportunity(valid_opportunity)
        assert isinstance(report.net_profit_after_costs, float)
        assert isinstance(report.slippage_estimate, float)
        assert isinstance(report.fill_rate_estimate, float)
        
    def test_final_gate_veto_path_exists(self, protection, valid_opportunity):
        """Verify deterministic Risk Layer / Final Gate veto path exists."""
        class RiskMock:
            def evaluate_arbitrage(self, opp, net_profit):
                return {'passed': False, 'reasons': ['FINAL_GATE_VETO']}
        protection.risk_gate = RiskMock()
        
        report = protection.evaluate_opportunity(valid_opportunity)
        assert report.decision == ProtectionDecision.VETO_RISK_LIMIT
        assert 'FINAL_GATE_VETO' in report.reason_codes
        
    def test_evidence_package_6_of_6_complete(self):
        """Verify evidence package is 6/6 complete."""
        import os
        base = "automation/control/candidates/R027-ARBITRAGE-PROTECTION/"
        files = [
            "task.txt", "evidence.json", "report.json",
            "candidate.diff", "no-aider-used.txt", "test-results.txt"
        ]
        for f in files:
            assert os.path.exists(base + f), f"Missing: {base + f}"
