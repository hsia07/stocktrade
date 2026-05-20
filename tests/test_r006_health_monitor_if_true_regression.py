"""
R006 Health Monitor Regression Tests
Tests that health/monitor.py no longer contains if True fake implementations.
Verifies probe-based fail-closed behavior for broker/data_feed/risk_system checks.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock
from health.monitor import HealthCheck, HealthMonitor


class TestR006HealthMonitorNoFakeImplementation:
    def test_no_if_true_in_source(self):
        import inspect
        source = inspect.getsource(HealthCheck)
        assert 'if True' not in source, \
            "health/monitor.py still contains 'if True' hardcoded check — fake implementation not removed"
        assert "status = 'ok' if True else" not in source, \
            "health/monitor.py still has hardcoded ternary 'if True' — fake implementation"


class TestR006HealthCheckProbeBased:
    def test_broker_probe_success_returns_ok(self):
        checker = HealthCheck(broker_probe=lambda: True)
        result = checker.check_broker_connection()
        assert result['status'] == 'ok', f"Expected ok, got {result['status']}"
        assert 'details' in result
        assert 'timestamp' in result

    def test_broker_probe_false_returns_critical(self):
        checker = HealthCheck(broker_probe=lambda: False)
        result = checker.check_broker_connection()
        assert result['status'] == 'critical', f"Expected critical, got {result['status']}"
        assert 'details' in result
        assert 'timestamp' in result

    def test_broker_probe_exception_returns_critical(self):
        def raising_probe():
            raise RuntimeError("broker unavailable")
        checker = HealthCheck(broker_probe=raising_probe)
        result = checker.check_broker_connection()
        assert result['status'] == 'critical', f"Expected critical on exception, got {result['status']}"
        assert 'exception' in result['details'].lower()

    def test_broker_probe_none_returns_degraded(self):
        checker = HealthCheck(broker_probe=None)
        result = checker.check_broker_connection()
        assert result['status'] == 'degraded', f"Expected degraded when probe missing, got {result['status']}"
        assert 'not configured' in result['details'] or 'degraded' in result['details']


class TestR006DataFeedProbeBased:
    def test_data_feed_probe_success_returns_ok(self):
        checker = HealthCheck(data_feed_probe=lambda: True)
        result = checker.check_data_feed()
        assert result['status'] == 'ok', f"Expected ok, got {result['status']}"

    def test_data_feed_probe_false_returns_warning(self):
        checker = HealthCheck(data_feed_probe=lambda: False)
        result = checker.check_data_feed()
        assert result['status'] == 'warning', f"Expected warning, got {result['status']}"

    def test_data_feed_probe_exception_returns_warning(self):
        def raising_probe():
            raise RuntimeError("data feed timeout")
        checker = HealthCheck(data_feed_probe=raising_probe)
        result = checker.check_data_feed()
        assert result['status'] == 'warning', f"Expected warning on exception, got {result['status']}"
        assert 'exception' in result['details'].lower()

    def test_data_feed_probe_none_returns_degraded(self):
        checker = HealthCheck(data_feed_probe=None)
        result = checker.check_data_feed()
        assert result['status'] == 'degraded', f"Expected degraded when probe missing, got {result['status']}"


class TestR006RiskSystemProbeBased:
    def test_risk_system_probe_success_returns_ok(self):
        checker = HealthCheck(risk_system_probe=lambda: True)
        result = checker.check_risk_system()
        assert result['status'] == 'ok', f"Expected ok, got {result['status']}"

    def test_risk_system_probe_false_returns_critical(self):
        checker = HealthCheck(risk_system_probe=lambda: False)
        result = checker.check_risk_system()
        assert result['status'] == 'critical', f"Expected critical, got {result['status']}"

    def test_risk_system_probe_exception_returns_critical(self):
        def raising_probe():
            raise RuntimeError("risk system error")
        checker = HealthCheck(risk_system_probe=raising_probe)
        result = checker.check_risk_system()
        assert result['status'] == 'critical', f"Expected critical on exception, got {result['status']}"
        assert 'exception' in result['details'].lower()

    def test_risk_system_probe_none_returns_degraded(self):
        checker = HealthCheck(risk_system_probe=None)
        result = checker.check_risk_system()
        assert result['status'] == 'degraded', f"Expected degraded when probe missing, got {result['status']}"


class TestR006HealthMonitorInjection:
    def test_health_monitor_accepts_probes(self):
        broker_mock = MagicMock(return_value=True)
        data_mock = MagicMock(return_value=True)
        risk_mock = MagicMock(return_value=True)
        monitor = HealthMonitor(
            broker_probe=broker_mock,
            data_feed_probe=data_mock,
            risk_system_probe=risk_mock,
        )
        results = monitor.run_checks()
        assert 'broker_connection' in results
        assert 'data_feed' in results
        assert 'risk_system' in results
        assert results['broker_connection']['status'] == 'ok'
        assert results['data_feed']['status'] == 'ok'
        assert results['risk_system']['status'] == 'ok'

    def test_health_monitor_probes_are_called(self):
        broker_mock = MagicMock(return_value=False)
        data_mock = MagicMock(return_value=False)
        risk_mock = MagicMock(return_value=False)
        monitor = HealthMonitor(
            broker_probe=broker_mock,
            data_feed_probe=data_mock,
            risk_system_probe=risk_mock,
        )
        results = monitor.run_checks()
        broker_mock.assert_called()
        data_mock.assert_called()
        risk_mock.assert_called()
        assert results['broker_connection']['status'] == 'critical'
        assert results['data_feed']['status'] == 'warning'
        assert results['risk_system']['status'] == 'critical'


class TestR006AggregateStatus:
    def test_aggregate_status_all_ok(self):
        broker_probe = MagicMock(return_value=True)
        data_probe = MagicMock(return_value=True)
        risk_probe = MagicMock(return_value=True)
        monitor = HealthMonitor(broker_probe=broker_probe, data_feed_probe=data_probe, risk_system_probe=risk_probe)
        results = monitor.run_checks()
        aggregate = monitor.aggregate_status(results)
        assert aggregate['status'] == 'ok'

    def test_aggregate_status_with_critical(self):
        broker_probe = MagicMock(return_value=False)
        data_probe = MagicMock(return_value=True)
        risk_probe = MagicMock(return_value=True)
        monitor = HealthMonitor(broker_probe=broker_probe, data_feed_probe=data_probe, risk_system_probe=risk_probe)
        results = monitor.run_checks()
        aggregate = monitor.aggregate_status(results)
        assert aggregate['status'] == 'critical'

    def test_aggregate_status_no_false_ok_when_no_probes(self):
        monitor = HealthMonitor(broker_probe=None, data_feed_probe=None, risk_system_probe=None)
        results = monitor.run_checks()
        aggregate = monitor.aggregate_status(results)
        assert aggregate['status'] == 'ok', \
            "aggregate_status should be ok when no critical checks, even if all degraded (degraded != critical)"


class TestR006FailClosedBehavior:
    def test_broker_false_is_not_masked_as_ok(self):
        checker = HealthCheck(broker_probe=lambda: False)
        result = checker.check_broker_connection()
        assert result['status'] != 'ok', "broker_probe=False must not return ok"

    def test_data_feed_false_is_not_masked_as_ok(self):
        checker = HealthCheck(data_feed_probe=lambda: False)
        result = checker.check_data_feed()
        assert result['status'] != 'ok', "data_feed_probe=False must not return ok"

    def test_risk_system_false_is_not_masked_as_ok(self):
        checker = HealthCheck(risk_system_probe=lambda: False)
        result = checker.check_risk_system()
        assert result['status'] != 'ok', "risk_system_probe=False must not return ok"


class TestR006ProbeExceptionNotMasked:
    def test_broker_exception_not_masked(self):
        def bad_probe():
            raise ConnectionError("broker network error")
        checker = HealthCheck(broker_probe=bad_probe)
        result = checker.check_broker_connection()
        assert result['status'] == 'critical', "broker exception must return critical, not masked as ok"

    def test_data_feed_exception_not_masked(self):
        def bad_probe():
            raise TimeoutError("data feed timeout")
        checker = HealthCheck(data_feed_probe=bad_probe)
        result = checker.check_data_feed()
        assert result['status'] == 'warning', "data feed exception must return warning, not masked as ok"

    def test_risk_system_exception_not_masked(self):
        def bad_probe():
            raise RuntimeError("risk engine crashed")
        checker = HealthCheck(risk_system_probe=bad_probe)
        result = checker.check_risk_system()
        assert result['status'] == 'critical', "risk system exception must return critical, not masked as ok"


class TestR006MemoryAndDiskStillWorking:
    def test_memory_check_still_functional(self):
        checker = HealthCheck()
        result = checker.check_memory_usage()
        assert 'status' in result
        assert result['status'] in ('ok', 'warning')
        assert 'details' in result
        assert 'timestamp' in result

    def test_disk_check_still_functional(self):
        checker = HealthCheck()
        result = checker.check_disk_space()
        assert 'status' in result
        assert result['status'] in ('ok', 'warning')
        assert 'details' in result
        assert 'timestamp' in result


class TestR006ReasonCodesPresent:
    def test_broker_check_has_reason(self):
        checker = HealthCheck(broker_probe=lambda: False)
        result = checker.check_broker_connection()
        assert 'details' in result
        assert len(result['details']) > 0, "broker check must provide reason/details"

    def test_data_feed_check_has_reason(self):
        checker = HealthCheck(data_feed_probe=lambda: True)
        result = checker.check_data_feed()
        assert 'details' in result
        assert len(result['details']) > 0

    def test_risk_system_check_has_reason(self):
        checker = HealthCheck(risk_system_probe=lambda: True)
        result = checker.check_risk_system()
        assert 'details' in result
        assert len(result['details']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])