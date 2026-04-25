"""R019 SLO / Latency Budget / Stability Tests"""

import unittest
from automation.slo.latency_budget import LatencyBudgetManager, LatencyBudget
from automation.slo.availability_tracker import AvailabilityTracker, AvailabilitySLO
from automation.slo.health_checker import HealthChecker, HealthThreshold


class TestLatencyBudgetManager(unittest.TestCase):
    def setUp(self):
        self.mgr = LatencyBudgetManager()
        self.mgr.register_budget(LatencyBudget("api_call", p50_ms=50, p95_ms=100, p99_ms=200))

    def test_within_budget(self):
        """Measurements within budget should pass."""
        for _ in range(100):
            self.mgr.record("api_call", 30)
        result = self.mgr.check_budget("api_call")
        self.assertEqual(result["status"], "within_budget")

    def test_p95_violation(self):
        """p95 exceeding budget should be flagged."""
        for _ in range(95):
            self.mgr.record("api_call", 30)
        for _ in range(5):
            self.mgr.record("api_call", 150)
        result = self.mgr.check_budget("api_call")
        self.assertEqual(result["status"], "violations")
        self.assertTrue(any("p95" in v for v in result["violations"]))

    def test_p99_violation(self):
        """p99 exceeding budget should be flagged."""
        for _ in range(99):
            self.mgr.record("api_call", 30)
        self.mgr.record("api_call", 250)
        result = self.mgr.check_budget("api_call")
        self.assertEqual(result["status"], "violations")
        self.assertTrue(any("p99" in v for v in result["violations"]))

    def test_no_budget(self):
        """Checking unregistered operation should return no_budget."""
        result = self.mgr.check_budget("unknown")
        self.assertEqual(result["status"], "no_budget")

    def test_percentile_calculation(self):
        """Percentile calculation should be accurate."""
        for i in range(100):
            self.mgr.record("api_call", float(i))
        self.assertEqual(self.mgr.get_percentile("api_call", 50), 50.0)
        self.assertEqual(self.mgr.get_percentile("api_call", 95), 95.0)


class TestAvailabilityTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = AvailabilityTracker()
        self.tracker.register_slo(AvailabilitySLO("order_service", target_success_rate=0.995, target_uptime=0.99))

    def test_meets_slo(self):
        """Success rate above target should meet SLO."""
        for _ in range(995):
            self.tracker.record_result("order_service", True)
        for _ in range(5):
            self.tracker.record_result("order_service", False)
        result = self.tracker.check_slo("order_service")
        self.assertEqual(result["status"], "meets_slo")

    def test_below_slo(self):
        """Success rate below target should breach SLO."""
        for _ in range(900):
            self.tracker.record_result("order_service", True)
        for _ in range(100):
            self.tracker.record_result("order_service", False)
        result = self.tracker.check_slo("order_service")
        self.assertEqual(result["status"], "below_slo")

    def test_no_slo(self):
        """Checking unregistered operation should return no_slo."""
        result = self.tracker.check_slo("unknown")
        self.assertEqual(result["status"], "no_slo")

    def test_no_data(self):
        """Operation with no recorded results should return no_data."""
        result = self.tracker.check_slo("order_service")
        self.assertEqual(result["status"], "no_data")


class TestHealthChecker(unittest.TestCase):
    def setUp(self):
        self.checker = HealthChecker()
        self.checker.register_threshold(HealthThreshold("cpu_usage", healthy_max=50, degraded_max=80))
        self.checker.register_threshold(HealthThreshold("memory_usage", healthy_max=60, degraded_max=85))

    def test_healthy(self):
        """Value within healthy range."""
        self.checker.record_metric("cpu_usage", 30)
        result = self.checker.check_health("cpu_usage")
        self.assertEqual(result["status"], "healthy")

    def test_degraded(self):
        """Value in degraded range."""
        self.checker.record_metric("cpu_usage", 70)
        result = self.checker.check_health("cpu_usage")
        self.assertEqual(result["status"], "degraded")

    def test_unhealthy(self):
        """Value above degraded threshold."""
        self.checker.record_metric("cpu_usage", 95)
        result = self.checker.check_health("cpu_usage")
        self.assertEqual(result["status"], "unhealthy")

    def test_no_data_unhealthy(self):
        """Missing metric should be unhealthy."""
        result = self.checker.check_health("cpu_usage")
        self.assertEqual(result["status"], "unhealthy")

    def test_overall_health_healthy(self):
        """All metrics healthy -> overall healthy."""
        self.checker.record_metric("cpu_usage", 30)
        self.checker.record_metric("memory_usage", 40)
        overall = self.checker.get_overall_health()
        self.assertEqual(overall["overall_status"], "healthy")

    def test_overall_health_degraded(self):
        """One metric degraded -> overall degraded."""
        self.checker.record_metric("cpu_usage", 70)
        self.checker.record_metric("memory_usage", 40)
        overall = self.checker.get_overall_health()
        self.assertEqual(overall["overall_status"], "degraded")

    def test_overall_health_unhealthy(self):
        """One metric unhealthy -> overall unhealthy."""
        self.checker.record_metric("cpu_usage", 95)
        self.checker.record_metric("memory_usage", 40)
        overall = self.checker.get_overall_health()
        self.assertEqual(overall["overall_status"], "unhealthy")


if __name__ == "__main__":
    unittest.main()
