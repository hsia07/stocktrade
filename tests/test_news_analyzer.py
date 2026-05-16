import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.news_analyzer import NewsAnalyzer, NewsEvent


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


def test_clear():
    a = NewsAnalyzer()
    a.ingest(NewsEvent(event_id="E1", headline="A", source="s", timestamp="2026-01-01T00:00:00"))
    a.clear()
    assert len(a.by_symbol("2330.TW")) == 0


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
