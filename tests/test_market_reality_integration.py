import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch
import pytest
from modules.market_reality.integration import MarketRealityIntegration


def _patch_session(integration):
    """Mock the layer's trading session to return a valid session."""
    patcher = patch.object(integration.layer, 'validate_trading_session',
                           return_value=(True, "CONTINUOUS_TRADING"))
    patcher.start()
    return patcher


class TestMarketRealityIntegrationEvaluation:
    def test_integration_evaluate_order_passes(self):
        integration = MarketRealityIntegration()
        patcher = _patch_session(integration)
        try:
            result = integration.evaluate_order_with_tracking(100.0, 2000, 100.0)
            assert result['passed'] is True
        finally:
            patcher.stop()
        assert 'costs' in result
        assert 'slippage' in result
        assert 'fill' in result
        assert 'constraints' in result
        assert 'reasons' in result

    def test_integration_reports_cost_breakdown(self):
        integration = MarketRealityIntegration()
        patcher = _patch_session(integration)
        try:
            result = integration.evaluate_order_with_tracking(100.0, 2000, 100.0, is_sell=True)
        finally:
            patcher.stop()
        costs = result['costs']
        assert 'expected' in costs
        assert costs['tracking_enabled'] is True
        assert costs['expected']['total_cost'] > 0

    def test_integration_reports_slippage(self):
        integration = MarketRealityIntegration()
        patcher = _patch_session(integration)
        try:
            result = integration.evaluate_order_with_tracking(100.0, 2000, 100.0)
        finally:
            patcher.stop()
        slippage = result['slippage']
        assert 'expected' in slippage
        assert slippage['monitoring_enabled'] is True
        assert slippage['expected']['expected_slippage'] > 0

    def test_integration_reports_fill_probability(self):
        integration = MarketRealityIntegration()
        patcher = _patch_session(integration)
        try:
            result = integration.evaluate_order_with_tracking(100.0, 2000, 100.0)
        finally:
            patcher.stop()
        fill = result['fill']
        assert 'expected' in fill
        assert fill['modeling_enabled'] is True
        assert 0 < fill['expected']['fill_probability'] <= 1.0

    def test_integration_reports_taiwan_compliance(self):
        integration = MarketRealityIntegration()
        patcher = _patch_session(integration)
        try:
            result = integration.evaluate_order_with_tracking(100.0, 2000, 100.0)
        finally:
            patcher.stop()
        taiwan = result['taiwan_compliance']
        assert taiwan['price_limit'] == '±10%'
        assert taiwan['settlement'] == 'T+2'
        assert taiwan['all_constraints_enforced'] is True

    def test_integration_reports_price_breach(self):
        integration = MarketRealityIntegration()
        patcher = _patch_session(integration)
        try:
            result = integration.evaluate_order_with_tracking(120.0, 2000, 100.0)
        finally:
            patcher.stop()
        assert result['passed'] is False
        assert any("PRICE" in r for r in result['reasons'])

    def test_integration_no_warning_only_pass(self):
        integration = MarketRealityIntegration()
        patcher = _patch_session(integration)
        try:
            result = integration.evaluate_order_with_tracking(100.0, 2000, 100.0)
        finally:
            patcher.stop()
        assert result['passed'] is True
        assert result['deterministic_gate_ready'] is True


class TestMarketRealityIntegrationRecording:
    def test_record_actual_execution_structure(self):
        integration = MarketRealityIntegration()
        patcher = _patch_session(integration)
        try:
            evaluation = integration.evaluate_order_with_tracking(100.0, 2000, 100.0)
        finally:
            patcher.stop()
        record = integration.record_actual_execution(
            evaluation, 100.5, 2000, 2000, evaluation['costs']['expected']['total_cost']
        )
        assert 'comparisons' in record
        assert 'cost_variance' in record['comparisons']
        assert 'slippage_variance' in record['comparisons']
        assert 'fill_variance' in record['comparisons']

    def test_record_actual_execution_appends_tracking(self):
        integration = MarketRealityIntegration()
        patcher = _patch_session(integration)
        try:
            evaluation = integration.evaluate_order_with_tracking(100.0, 2000, 100.0)
        finally:
            patcher.stop()
        integration.record_actual_execution(
            evaluation, 100.5, 2000, 2000, evaluation['costs']['expected']['total_cost']
        )
        summary = integration.get_monitoring_summary()
        assert summary['cost_summary']['total_trades'] >= 1


class TestMarketRealityIntegrationSummary:
    def test_monitoring_summary_structure(self):
        integration = MarketRealityIntegration()
        summary = integration.get_monitoring_summary()
        assert 'cost_summary' in summary
        assert 'slippage_summary' in summary
        assert 'fill_summary' in summary
        assert 'taiwan_market' in summary
        assert 'deterministic_gate' in summary
        assert summary['deterministic_gate']['ready'] is True
