import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.conflict_integrator import ConflictIntegrator, SafetyDegrade
from modules.decision_prechecklist.news_analyzer import NewsEvent


def test_no_conflict():
    ci = ConflictIntegrator()
    events = [
        NewsEvent(event_id="E1", headline="Bullish", source="s", timestamp="t", symbols=["AAPL"], sentiment=0.5),
        NewsEvent(event_id="E2", headline="Neutral", source="s", timestamp="t", symbols=["AAPL"], sentiment=0.4),
    ]
    conflicts = ci.detect(events)
    assert len(conflicts) == 0


def test_sentiment_conflict():
    ci = ConflictIntegrator()
    events = [
        NewsEvent(event_id="E1", headline="Very bullish", source="s", timestamp="t", symbols=["AAPL"], sentiment=0.9),
        NewsEvent(event_id="E2", headline="Very bearish", source="s", timestamp="t", symbols=["AAPL"], sentiment=-0.9),
    ]
    conflicts = ci.detect(events)
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "sentiment_conflict"


def test_safety_no_trade():
    ci = ConflictIntegrator()
    events = [
        NewsEvent(event_id="E1", headline="Extreme bullish", source="s", timestamp="t", symbols=["AAPL"], sentiment=1.0, impact_score=0.9),
        NewsEvent(event_id="E2", headline="Extreme bearish", source="s", timestamp="t", symbols=["AAPL"], sentiment=-1.0, impact_score=0.9),
    ]
    conflicts = ci.detect(events)
    assert len(conflicts) == 1
    assert conflicts[0].safety_decision == SafetyDegrade.NO_TRADE


def test_safety_wait_confirmation():
    ci = ConflictIntegrator()
    events = [
        NewsEvent(event_id="E1", headline="Strong bullish", source="s", timestamp="t", symbols=["AAPL"], sentiment=0.9, impact_score=0.9),
        NewsEvent(event_id="E2", headline="Neutral", source="s", timestamp="t", symbols=["AAPL"], sentiment=0.0, impact_score=0.9),
    ]
    conflicts = ci.detect(events)
    assert len(conflicts) == 1
    assert conflicts[0].safety_decision == SafetyDegrade.WAIT_CONFIRMATION


def test_safety_tighten_risk():
    ci = ConflictIntegrator()
    events = [
        NewsEvent(event_id="E1", headline="Slight bullish", source="s", timestamp="t", symbols=["AAPL"], sentiment=0.6, impact_score=0.5),
        NewsEvent(event_id="E2", headline="Slight bearish", source="s", timestamp="t", symbols=["AAPL"], sentiment=-0.1, impact_score=0.5),
    ]
    conflicts = ci.detect(events)
    assert len(conflicts) == 1
    assert conflicts[0].safety_decision == SafetyDegrade.TIGHTEN_RISK


def test_get_active_safety_degrade():
    ci = ConflictIntegrator()
    events = [
        NewsEvent(event_id="E1", headline="Very bullish", source="s", timestamp="t", symbols=["AAPL"], sentiment=0.9),
        NewsEvent(event_id="E2", headline="Very bearish", source="s", timestamp="t", symbols=["AAPL"], sentiment=-0.9),
    ]
    ci.detect(events)
    assert ci.get_active_safety_degrade("AAPL") != SafetyDegrade.NORMAL


def test_resolve():
    ci = ConflictIntegrator()
    events = [
        NewsEvent(event_id="E1", headline="Bullish", source="s", timestamp="t", symbols=["AAPL"], sentiment=0.9),
        NewsEvent(event_id="E2", headline="Bearish", source="s", timestamp="t", symbols=["AAPL"], sentiment=-0.5),
    ]
    conflicts = ci.detect(events)
    ci.resolve(conflicts[0], "use_latest")
    assert conflicts[0].resolution == "use_latest"


def test_get_unresolved():
    ci = ConflictIntegrator()
    events = [
        NewsEvent(event_id="E1", headline="Bullish", source="s", timestamp="t", symbols=["AAPL"], sentiment=0.9),
        NewsEvent(event_id="E2", headline="Bearish", source="s", timestamp="t", symbols=["AAPL"], sentiment=-0.5),
    ]
    ci.detect(events)
    assert len(ci.get_unresolved()) == 1
    ci.resolve_all()
    assert len(ci.get_unresolved()) == 0


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
