import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.conflict_integrator import ConflictIntegrator, ConflictRecord
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


def test_resolve():
    ci = ConflictIntegrator()
    events = [
        NewsEvent(event_id="E1", headline="Bullish", source="s", timestamp="t", symbols=["AAPL"], sentiment=0.9),
        NewsEvent(event_id="E2", headline="Bearish", source="s", timestamp="t", symbols=["AAPL"], sentiment=-0.9),
    ]
    conflicts = ci.detect(events)
    ci.resolve(conflicts[0], "use_latest")
    assert conflicts[0].resolution == "use_latest"


def test_get_unresolved():
    ci = ConflictIntegrator()
    events = [
        NewsEvent(event_id="E1", headline="Bullish", source="s", timestamp="t", symbols=["AAPL"], sentiment=0.9),
        NewsEvent(event_id="E2", headline="Bearish", source="s", timestamp="t", symbols=["AAPL"], sentiment=-0.9),
    ]
    ci.detect(events)
    assert len(ci.get_unresolved()) == 1


def test_resolve_all():
    ci = ConflictIntegrator()
    events = [
        NewsEvent(event_id="E1", headline="Bullish", source="s", timestamp="t", symbols=["AAPL"], sentiment=0.9),
        NewsEvent(event_id="E2", headline="Bearish", source="s", timestamp="t", symbols=["AAPL"], sentiment=-0.9),
        NewsEvent(event_id="E3", headline="Very bullish", source="s", timestamp="t", symbols=["TSLA"], sentiment=0.8),
        NewsEvent(event_id="E4", headline="Very bearish", source="s", timestamp="t", symbols=["TSLA"], sentiment=-0.8),
    ]
    ci.detect(events)
    resolved = ci.resolve_all("ignore_bearish")
    assert resolved == 2
    assert len(ci.get_unresolved()) == 0


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
