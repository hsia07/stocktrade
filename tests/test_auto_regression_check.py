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


def test_checker_detects_veto_code_mismatch():
    c = AutoRegressionChecker()
    case = FixedTestCase(
        name="veto_code_mismatch",
        description="expected veto code differs from actual",
        candidate=make_candidate(is_suspended=True),
        expected_passed=False,
        expected_veto_reason_code="WRONG_CODE",
    )
    result = c.run([case])
    assert result.mismatched == 1
    assert result.results[0].matches_expectation is False
    assert result.results[0].expected_veto_code == "WRONG_CODE"


def test_checker_detects_opposite_direction():
    c = AutoRegressionChecker()
    case = FixedTestCase(
        name="opposite_direction",
        description="actual passes but expected fails",
        candidate=make_candidate(),
        expected_passed=False,
    )
    result = c.run([case])
    assert result.mismatched == 1
    assert result.results[0].expected_passed is False
    assert result.results[0].actual_passed is True
    assert result.results[0].matches_expectation is False


def test_fixed_test_cases_non_empty_and_known_names():
    assert len(FIXED_TEST_CASES) >= 7
    names = {c.name for c in FIXED_TEST_CASES}
    assert "normal_passes" in names
    assert "single_signal_blocked" in names
    assert "taiwan_suspended_blocked" in names


def test_serializable_report():
    c = AutoRegressionChecker()
    result = c.run()
    d = result.to_dict()
    assert isinstance(d, dict)
    assert "total" in d
    assert "matched" in d
    assert "mismatched" in d


def test_version_diff_report():
    c = AutoRegressionChecker()
    report = c.run().as_report()
    assert isinstance(report, dict)
    assert report["suite_name"] == "R037_regression_full"
    assert "mismatch_items" in report
    assert "all_results" in report
    for item in report["all_results"]:
        assert "test_name" in item
        assert "matches_expectation" in item


def test_smoke_mode():
    c = AutoRegressionChecker()
    result = c.run(mode="smoke")
    assert result is not None
    assert result.suite_name == "R037_regression_smoke"


def test_run_smoke_method():
    c = AutoRegressionChecker()
    result = c.run_smoke()
    assert result is not None
    assert result.suite_name == "R037_regression_smoke"


def test_extreme_scenario_filtered_in_smoke():
    c = AutoRegressionChecker()
    extreme = FixedTestCase(
        name="extreme_volatility",
        description="extreme scenario with high volatility",
        candidate=make_candidate(), expected_passed=True,
    )
    normal = FixedTestCase(
        name="normal_case",
        description="normal scenario",
        candidate=make_candidate(), expected_passed=True,
    )
    full_result = c.run([extreme, normal], mode="full")
    assert full_result.total == 2
    smoke_result = c.run([extreme, normal], mode="smoke")
    assert smoke_result.total == 1


def test_strategy_parameter_update_contract():
    c = AutoRegressionChecker()
    contract = c.check_strategy_parameter_update(make_candidate())
    assert isinstance(contract, dict)
    assert contract["contract"] == "strategy_parameter_update_regression_check"
    assert "status" in contract
    assert "note" in contract


def test_ai_weight_update_contract():
    c = AutoRegressionChecker()
    contract = c.check_ai_weight_update(make_candidate())
    assert isinstance(contract, dict)
    assert contract["contract"] == "ai_weight_update_regression_check"
    assert "status" in contract
    assert "note" in contract


def test_observable_output_has_stable_keys():
    c = AutoRegressionChecker()
    report = c.run().as_report()
    expected_keys = {"suite_name", "total", "matched", "mismatched", "passed", "summary", "mismatch_items", "all_results"}
    assert expected_keys.issubset(report.keys())


def test_no_broker_live_order_pollution():
    import ast
    with open("modules/decision_prechecklist/auto_regression_check.py") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            else:
                names = [f"{node.module}.{a.name}" for a in node.names]
            for name in names:
                for term in ["broker", "server_v2", "index_v2", "websocket", "socket"]:
                    assert term not in name.lower(), f"forbidden import '{name}' contains '{term}'"


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
