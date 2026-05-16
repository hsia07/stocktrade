import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.event_importance_scorer import EventImportanceScorer
from modules.decision_prechecklist.news_analyzer import NewsEvent


def test_score():
    s = EventImportanceScorer()
    e = NewsEvent(event_id="E1", headline="Earnings", source="s", timestamp="2026-01-01T00:00:00", impact_score=0.8, sentiment=0.5, category="earnings")
    scored = s.score(e)
    assert scored.importance_score > 0
    assert scored.effective_score > 0
    assert scored.ttl_minutes == 1440


def test_expired():
    s = EventImportanceScorer()
    old = NewsEvent(event_id="E1", headline="Old", source="s", timestamp="2020-01-01T00:00:00+00:00", impact_score=0.5, category="earnings")
    scored = s.score(old)
    assert s.is_expired(scored)


def test_not_expired():
    import datetime
    s = EventImportanceScorer()
    fresh = NewsEvent(event_id="E1", headline="Fresh", source="s", timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(), impact_score=0.5, category="earnings")
    scored = s.score(fresh)
    assert not s.is_expired(scored)


if __name__ == "__main__":
    import pytest; import datetime; sys.exit(pytest.main([__file__, "-v"]))
