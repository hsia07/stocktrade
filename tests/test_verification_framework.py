import sys, os, random; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.verification_framework import (
    VerificationRunner, VerificationCheck, VerificationSuiteResult,
    StressTestEngine, StressTestScenario, StressTestResult,
)


def test_runner_initialization():
    r = VerificationRunner()
    assert r is not None


def test_runner_add_and_run():
    r = VerificationRunner()
    r.add_check("always_true", lambda: (True, "ok"))
    r.add_check("always_false", lambda: (False, "fail"))
    result = r.run_all()
    assert result.total_checks == 2
    assert result.passed_checks == 1
    assert result.failed_checks == 1
    assert not result.all_passed


def test_runner_all_pass():
    r = VerificationRunner()
    for i in range(5):
        r.add_check(f"check_{i}", lambda: (True, "ok"))
    result = r.run_all()
    assert result.all_passed
    assert result.passed_checks == 5


def test_runner_exception_handling():
    r = VerificationRunner()
    def _raise():
        raise ValueError("boom")
        return True, ""
    r.add_check("bad_check", _raise)
    result = r.run_all()
    assert result.failed_checks == 1
    assert "boom" in result.checks[0].detail


def test_verification_suite_result_properties():
    result = VerificationSuiteResult(total_checks=10, passed_checks=8, failed_checks=2)
    assert not result.all_passed
    result2 = VerificationSuiteResult(total_checks=5, passed_checks=5, failed_checks=0)
    assert result2.all_passed


def test_verification_check():
    c = VerificationCheck(name="test", passed=True, detail="ok", duration_ms=1.5)
    assert c.name == "test"
    assert c.passed


def test_stress_test_engine():
    engine = StressTestEngine()
    scenario = StressTestScenario(
        name="test_scenario",
        generate=lambda: {"value": random.random()},
        verify=lambda x: x["value"] >= 0,
        count=50,
    )
    engine.add_scenario(scenario)
    results = engine.run_all()
    assert len(results) == 1
    assert results[0].total == 50
    assert results[0].passed == 50
    assert results[0].pass_rate == 1.0


def test_stress_test_with_failures():
    engine = StressTestEngine()
    scenario = StressTestScenario(
        name="partial_fail",
        generate=lambda: random.random(),
        verify=lambda x: x > 0.3,
        count=100,
    )
    result = engine.run_scenario(scenario)
    assert result.total == 100
    assert result.passed < 100
    assert result.pass_rate < 1.0


def test_stress_test_exception_handling():
    engine = StressTestEngine()
    calls = [0]
    def _gen():
        calls[0] += 1
        if calls[0] % 2 == 0:
            raise ValueError("err")
        return 1
    scenario = StressTestScenario(
        name="exception_test",
        generate=_gen,
        verify=lambda x: x > 0,
        count=10,
    )
    result = engine.run_scenario(scenario)
    assert result.total == 10
    assert result.failed == 5


def test_stress_test_metrics():
    engine = StressTestEngine()
    scenario = StressTestScenario(
        name="metrics",
        generate=lambda: 1,
        verify=lambda x: True,
        count=20,
    )
    result = engine.run_scenario(scenario)
    assert result.avg_duration_ms >= 0
    assert result.max_duration_ms >= result.min_duration_ms
    assert result.scenario_name == "metrics"


def test_runner_with_empty_checks():
    r = VerificationRunner()
    result = r.run_all()
    assert result.total_checks == 0
    assert result.all_passed


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
