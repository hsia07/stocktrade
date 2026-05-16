import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.event_deduplicator import EventDeduplicator, StaleCheckResult
from modules.decision_prechecklist.news_analyzer import NewsEvent
import datetime


def test_no_duplicate_first_event():
    d = EventDeduplicator()
    e = NewsEvent(event_id="E1", headline="AAPL beats earnings", source="s", timestamp="t", symbols=["AAPL"])
    result = d.check(e)
    assert result is None
    d.register(e)


def test_detects_duplicate():
    d = EventDeduplicator(headline_similarity_threshold=0.5)
    e1 = NewsEvent(event_id="E1", headline="AAPL beats earnings", source="s", timestamp="t", symbols=["AAPL"])
    e2 = NewsEvent(event_id="E2", headline="AAPL beats earnings Q1", source="s", timestamp="t", symbols=["AAPL"])
    d.register(e1)
    result = d.check(e2)
    assert result is not None
    assert result.is_duplicate


def test_different_headlines_not_duplicate():
    d = EventDeduplicator()
    e1 = NewsEvent(event_id="E1", headline="AAPL beats earnings", source="s", timestamp="t", symbols=["AAPL"])
    e2 = NewsEvent(event_id="E2", headline="TSLA stock drops", source="s", timestamp="t", symbols=["TSLA"])
    d.register(e1)
    result = d.check(e2)
    assert result is None


def test_jaccard_zero():
    d = EventDeduplicator()
    sim = d._jaccard_similarity("", "")
    assert sim == 0.0


def test_check_stale_detects_old():
    d = EventDeduplicator()
    old = NewsEvent(event_id="E1", headline="Old", source="s", timestamp="2020-01-01T00:00:00+00:00", category="general")
    result = d.check_stale(old)
    assert result.is_stale
    assert result.action == "reject"


def test_check_stale_accepts_fresh():
    d = EventDeduplicator()
    fresh = NewsEvent(event_id="E1", headline="Fresh", source="s", timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(), category="general")
    result = d.check_stale(fresh)
    assert not result.is_stale
    assert result.action == "accept"


def test_filter_stale():
    d = EventDeduplicator()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    events = [
        NewsEvent(event_id="E1", headline="Old", source="s", timestamp="2020-01-01T00:00:00+00:00", category="general"),
        NewsEvent(event_id="E2", headline="Fresh", source="s", timestamp=now, category="general"),
    ]
    fresh, stale = d.filter_stale(events)
    assert len(stale) == 1
    assert len(fresh) == 1


def test_dedup_and_filter_stale():
    d = EventDeduplicator()
    old = NewsEvent(event_id="E1", headline="Old", source="s", timestamp="2020-01-01T00:00:00+00:00", category="general", symbols=["AAPL"])
    result = d.dedup_and_filter(old)
    assert isinstance(result, StaleCheckResult)
    assert result.is_stale


def test_dedup_and_filter_dedup():
    d = EventDeduplicator(headline_similarity_threshold=0.5)
    e1 = NewsEvent(event_id="E1", headline="AAPL up", source="s", timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(), category="general", symbols=["AAPL"])
    e2 = NewsEvent(event_id="E2", headline="AAPL up a lot", source="s", timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(), category="general", symbols=["AAPL"])
    d.dedup_and_filter(e1)
    result = d.dedup_and_filter(e2)
    assert result is not None
    assert hasattr(result, "is_duplicate") and result.is_duplicate


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
