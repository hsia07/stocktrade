import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.event_deduplicator import EventDeduplicator
from modules.decision_prechecklist.news_analyzer import NewsEvent


def test_no_duplicate_first_event():
    d = EventDeduplicator()
    e = NewsEvent(event_id="E1", headline="AAPL earnings beat", source="s", timestamp="t", symbols=["AAPL"])
    result = d.check(e)
    assert result is None


def test_detects_duplicate():
    d = EventDeduplicator()
    e1 = NewsEvent(event_id="E1", headline="AAPL earnings beat estimates", source="s", timestamp="t", symbols=["AAPL"])
    e2 = NewsEvent(event_id="E2", headline="AAPL earnings beat estimates", source="s2", timestamp="t2", symbols=["AAPL"])
    d.check(e1)
    d.register(e1)
    result = d.check(e2)
    assert result is not None
    assert result.is_duplicate


def test_different_headlines_not_duplicate():
    d = EventDeduplicator()
    e1 = NewsEvent(event_id="E1", headline="AAPL earnings beat", source="s", timestamp="t", symbols=["AAPL"])
    e2 = NewsEvent(event_id="E2", headline="TSLA stock split announced", source="s", timestamp="t", symbols=["AAPL"])
    d.check(e1)
    d.register(e1)
    result = d.check(e2)
    assert result is None


def test_jaccard_zero():
    d = EventDeduplicator()
    sim = d._jaccard_similarity("", "")
    assert sim == 0.0


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
