import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.auto_regression_check import AutoRegressionChecker, RegressionSuiteResult
from modules.decision_prechecklist.fixed_test_dataset import FIXED_TEST_CASES, FixedTestCase, make_candidate


def test_checker_initialization():
    c = AutoRegressionChecker()
    assert c is not None


def test_checker_runs_all_cases():
    c = AutoRegressionChecker()
    result = c.run(FIXED_TEST_CASES)
    assert result.total >= 6
    assert result.matched + result.mismatched == result.total


def test_checker_known_result():
    c = AutoRegressionChecker()
    result = c.run()
    normal = [r for r in result.results if r.test_name == "normal_passes"]
    assert len(normal) == 1
    assert normal[0].passed is True
    assert normal[0].matches_expectation


def test_checker_detects_mismatch():
    c = AutoRegressionChecker()
    bad_case = FixedTestCase(
        name="should_fail_but_passes",
        description="test",
        candidate=make_candidate(),
        expected_passed=False,
    )
    result = c.run([bad_case])
    assert result.mismatched == 1


def test_regression_suite_result():
    r = RegressionSuiteResult(total=5, matched=5, mismatched=0, summary="all pass")
    assert r.matched == 5
    assert r.mismatched == 0


def test_checker_run_empty_list():
    c = AutoRegressionChecker()
    result = c.run([])
    assert result.total == 0
    assert result.matched == 0


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
