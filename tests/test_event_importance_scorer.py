import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.event_importance_scorer import EventImportanceScorer, RiskTier
from modules.decision_prechecklist.news_analyzer import NewsEvent
import datetime


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
    s = EventImportanceScorer()
    fresh = NewsEvent(event_id="E1", headline="Fresh", source="s", timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(), impact_score=0.5, category="earnings")
    scored = s.score(fresh)
    assert not s.is_expired(scored)


def test_risk_tier_critical():
    s = EventImportanceScorer()
    e = NewsEvent(event_id="E1", headline="Critical reg", source="s", timestamp="2026-01-01T00:00:00", impact_score=0.9, sentiment=0.8, category="regulatory")
    scored = s.score(e)
    assert scored.risk_tier == RiskTier.CRITICAL


def test_risk_tier_high():
    s = EventImportanceScorer()
    e = NewsEvent(event_id="E1", headline="High impact", source="s", timestamp="2026-01-01T00:00:00", impact_score=0.7, sentiment=0.5, category="macro")
    scored = s.score(e)
    assert scored.risk_tier == RiskTier.HIGH


def test_risk_tier_medium():
    s = EventImportanceScorer()
    e = NewsEvent(event_id="E1", headline="Medium", source="s", timestamp="2026-01-01T00:00:00", impact_score=0.4, sentiment=0.0, category="general")
    scored = s.score(e)
    assert scored.risk_tier == RiskTier.MEDIUM


def test_risk_tier_low():
    s = EventImportanceScorer()
    e = NewsEvent(event_id="E1", headline="Low", source="s", timestamp="2026-01-01T00:00:00", impact_score=0.1, sentiment=0.0, category="general")
    scored = s.score(e)
    assert scored.risk_tier == RiskTier.LOW


if __name__ == "__main__":
    import pytest; import datetime; sys.exit(pytest.main([__file__, "-v"]))
