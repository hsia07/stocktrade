import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.features_regimes_strategies import (
    Feature, RegimeInfo, StrategyInfo, StrategyType, StrategyEvaluationResult,
)


def test_feature():
    f = Feature(name="rsi", category="technical", value=0.7, weight=0.5)
    assert f.name == "rsi"
    assert f.value == 0.7


def test_regime_info():
    r = RegimeInfo(regime_id="R001", name="bull_trend", uncertainty=0.2)
    assert r.regime_id == "R001"
    assert r.uncertainty == 0.2


def test_strategy_info():
    s = StrategyInfo(
        strategy_id="S001", name="momentum_5d",
        strategy_type=StrategyType.MOMENTUM, regime="bull", confidence=0.8,
    )
    assert s.strategy_type == StrategyType.MOMENTUM
    assert s.confidence == 0.8


def test_strategy_with_features():
    s = StrategyInfo(
        strategy_id="S001", name="momentum_5d",
        strategy_type=StrategyType.MOMENTUM, regime="bull", confidence=0.8,
        features=[Feature(name="rsi", category="technical", value=0.7)],
    )
    assert len(s.features) == 1


def test_strategy_types():
    assert StrategyType.MOMENTUM.value == "momentum"
    assert StrategyType.MEAN_REVERSION.value == "mean_reversion"
    assert StrategyType.BREAKOUT.value == "breakout"
    assert StrategyType.ARBITRAGE.value == "arbitrage"
    assert len(StrategyType) >= 5


def test_strategy_evaluation_result():
    r = StrategyEvaluationResult(strategy_id="S001", passed=True, confidence=0.8)
    assert r.passed
    assert r.veto_reason == ""


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
