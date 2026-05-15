import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.fixed_test_dataset import (
    FIXED_TEST_CASES, FixedTestCase, FixedTestRunResult, make_candidate,
)


def test_fixed_dataset_has_cases():
    assert len(FIXED_TEST_CASES) >= 6


def test_fixed_case_normal_passes():
    cases = [c for c in FIXED_TEST_CASES if c.name == "normal_passes"]
    assert len(cases) == 1
    assert cases[0].expected_passed is True


def test_fixed_case_single_signal_blocked():
    cases = [c for c in FIXED_TEST_CASES if c.name == "single_signal_blocked"]
    assert len(cases) == 1
    assert cases[0].expected_passed is False
    assert cases[0].expected_veto_reason_code == "SINGLE_SIGNAL_DIRECT_TRADE"


def test_fixed_case_event_news_blocked():
    cases = [c for c in FIXED_TEST_CASES if c.name == "event_news_social_blocked"]
    assert len(cases) == 1
    assert cases[0].expected_passed is False


def test_fixed_case_llm_blocked():
    cases = [c for c in FIXED_TEST_CASES if c.name == "llm_source_blocked"]
    assert len(cases) == 1
    assert cases[0].expected_passed is False


def test_fixed_case_taiwan_suspended():
    cases = [c for c in FIXED_TEST_CASES if c.name == "taiwan_suspended_blocked"]
    assert len(cases) == 1
    assert cases[0].candidate.is_suspended is True


def test_fixed_case_non_taiwan():
    cases = [c for c in FIXED_TEST_CASES if c.name == "non_taiwan_stock_passes"]
    assert len(cases) == 1
    assert cases[0].candidate.is_taiwan_stock is False


def test_make_candidate_defaults():
    c = make_candidate()
    assert c.symbol == "2330.TW"
    assert c.side == "buy"
    assert c.confidence_raw == 0.8


def test_make_candidate_overrides():
    c = make_candidate(symbol="2317.TW", confidence_raw=0.5)
    assert c.symbol == "2317.TW"
    assert c.confidence_raw == 0.5


def test_fixed_test_run_result():
    r = FixedTestRunResult(
        test_name="test", passed=True, expected_passed=True,
        actual_passed=True, expected_veto_code=None, actual_veto_code=None,
        matches_expectation=True,
    )
    assert r.matches_expectation


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
