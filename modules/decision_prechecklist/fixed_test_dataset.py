from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from modules.decision_prechecklist.checklist import TradeCandidate


@dataclass
class FixedTestCase:
    name: str
    description: str
    candidate: TradeCandidate
    expected_passed: bool
    expected_veto_reason_code: str | None = None


@dataclass
class FixedTestRunResult:
    test_name: str
    passed: bool
    expected_passed: bool
    actual_passed: bool
    expected_veto_code: str | None
    actual_veto_code: str | None
    matches_expectation: bool


FIXED_TEST_CASES: list[FixedTestCase] = []


def register(case: FixedTestCase) -> None:
    FIXED_TEST_CASES.append(case)


def make_candidate(**overrides) -> TradeCandidate:
    params = dict(
        symbol="2330.TW", side="buy", quantity=1000, price=150.0,
        signal_source="strategy_backtest", confidence_raw=0.8,
        strategy="momentum", expected_return=5000.0,
        cost_estimate=0.001, slippage_estimate=0.002, fill_probability=0.95,
        regime_uncertainty=0.1, risk_budget=50000.0, current_exposure=100000.0,
        portfolio_value=1000000.0, cash_available=200000.0, t_plus_2_hold=50000.0,
        avg_daily_volume=5000000, max_pct_of_volume=0.01,
        max_position_pct_of_portfolio=0.05, strategy_max_pct=0.1,
        regime_max_pct=0.15, historical_brier_score=0.2, num_past_decisions=50,
        is_taiwan_stock=True, taiwan_price_limit_pct=0.1,
        is_collection_auction=False, is_odd_lot=False, is_suspended=False,
        is_disposition_stock=False, is_near_limit_up=False,
        is_near_limit_down=False, liquidity_score=0.8,
    )
    params.update(overrides)
    return TradeCandidate(**params)


register(FixedTestCase(
    name="normal_passes", description="Normal valid trade passes all gates",
    candidate=make_candidate(), expected_passed=True,
))
register(FixedTestCase(
    name="single_signal_blocked",
    description="Technical indicator single signal blocked",
    candidate=make_candidate(signal_source="technical_indicator"),
    expected_passed=False, expected_veto_reason_code="SINGLE_SIGNAL_DIRECT_TRADE",
))
register(FixedTestCase(
    name="event_news_social_blocked",
    description="News headline source blocked",
    candidate=make_candidate(signal_source="news_headline"),
    expected_passed=False, expected_veto_reason_code="HIGH_IMPACT_UNCONFIRMED_EVENT",
))
register(FixedTestCase(
    name="llm_source_blocked",
    description="LLM recommendation source blocked",
    candidate=make_candidate(signal_source="llm_recommendation"),
    expected_passed=False, expected_veto_reason_code="LLM_IS_TRADE_CORE",
))
register(FixedTestCase(
    name="taiwan_suspended_blocked",
    description="Taiwan suspended stock blocked",
    candidate=make_candidate(is_suspended=True),
    expected_passed=False, expected_veto_reason_code="TAIWAN_CONSTRAINT",
))
register(FixedTestCase(
    name="taiwan_disposition_blocked",
    description="Taiwan disposition stock blocked",
    candidate=make_candidate(is_disposition_stock=True),
    expected_passed=False, expected_veto_reason_code="TAIWAN_CONSTRAINT",
))
register(FixedTestCase(
    name="taiwan_near_limit_up_blocked",
    description="Taiwan near limit up blocked",
    candidate=make_candidate(is_near_limit_up=True),
    expected_passed=False, expected_veto_reason_code="TAIWAN_CONSTRAINT",
))
register(FixedTestCase(
    name="non_taiwan_stock_passes",
    description="Non-Taiwan stock passes without Taiwan checks",
    candidate=make_candidate(is_taiwan_stock=False),
    expected_passed=True,
))
