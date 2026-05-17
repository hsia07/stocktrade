import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.news_analyzer import NewsAnalyzer, NewsEvent, StructuredSignal


def test_ingest():
    a = NewsAnalyzer()
    e = NewsEvent(event_id="E001", headline="Test", source="news1", timestamp="2026-01-01T00:00:00", symbols=["2330.TW"])
    a.ingest(e)
    assert len(a.by_symbol("2330.TW")) == 1


def test_by_category():
    a = NewsAnalyzer()
    a.ingest(NewsEvent(event_id="E1", headline="A", source="s", timestamp="2026-01-01T00:00:00", category="earnings"))
    a.ingest(NewsEvent(event_id="E2", headline="B", source="s", timestamp="2026-01-01T00:00:00", category="macro"))
    assert len(a.by_category("earnings")) == 1
    assert len(a.by_category("macro")) == 1


def test_high_impact():
    a = NewsAnalyzer()
    a.ingest(NewsEvent(event_id="E1", headline="A", source="s", timestamp="2026-01-01T00:00:00", impact_score=0.9))
    a.ingest(NewsEvent(event_id="E2", headline="B", source="s", timestamp="2026-01-01T00:00:00", impact_score=0.3))
    assert len(a.high_impact(0.7)) == 1


def test_source_credibility():
    official = NewsEvent(event_id="E1", headline="A", source="official", timestamp="2026-01-01T00:00:00")
    social = NewsEvent(event_id="E2", headline="B", source="social", timestamp="2026-01-01T00:00:00")
    unknown = NewsEvent(event_id="E3", headline="C", source="unknown_site", timestamp="2026-01-01T00:00:00")
    assert official.source_credibility() == 1.0
    assert social.source_credibility() == 0.25
    assert unknown.source_credibility() == 0.5


def test_is_stale():
    import datetime
    old = NewsEvent(event_id="E1", headline="Old", source="s", timestamp="2020-01-01T00:00:00+00:00")
    fresh = NewsEvent(event_id="E2", headline="Fresh", source="s", timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat())
    assert old.is_stale(max_age_minutes=360)
    assert not fresh.is_stale(max_age_minutes=360)


def test_get_stale_events():
    import datetime
    a = NewsAnalyzer()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    a.ingest(NewsEvent(event_id="E1", headline="Old", source="s", timestamp="2020-01-01T00:00:00+00:00", category="general"))
    a.ingest(NewsEvent(event_id="E2", headline="Current", source="s", timestamp=now, category="general"))
    stale = a.get_stale_events()
    assert len(stale) == 1
    assert stale[0].event_id == "E1"


def test_clear_stale():
    import datetime
    a = NewsAnalyzer()
    a.ingest(NewsEvent(event_id="E1", headline="Old", source="s", timestamp="2020-01-01T00:00:00+00:00", category="general", symbols=["AAPL"]))
    a.ingest(NewsEvent(event_id="E2", headline="Current", source="s", timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(), category="general", symbols=["AAPL"]))
    removed = a.clear_stale()
    assert removed == 1
    assert len(a.by_symbol("AAPL")) == 1


def test_to_signals():
    a = NewsAnalyzer()
    e = NewsEvent(event_id="E1", headline="AAPL up", source="reuters", timestamp="2026-01-01T00:00:00", symbols=["AAPL"], sentiment=0.6, impact_score=0.8, category="earnings")
    signals = a.to_signals([e])
    assert len(signals) == 1
    assert signals[0].symbol == "AAPL"
    assert signals[0].direction == "bullish"
    assert signals[0].recommendation == "observe"


def test_to_signals_stale_excluded():
    a = NewsAnalyzer()
    e = NewsEvent(event_id="E1", headline="Old news", source="s", timestamp="2020-01-01T00:00:00+00:00", symbols=["AAPL"], sentiment=0.5, category="general")
    signals = a.to_signals([e])
    assert len(signals) == 0


def test_clear():
    a = NewsAnalyzer()
    a.ingest(NewsEvent(event_id="E1", headline="A", source="s", timestamp="2026-01-01T00:00:00"))
    a.clear()
    assert len(a.by_symbol("2330.TW")) == 0


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
