from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone


SOURCE_CREDIBILITY_MAP: dict[str, float] = {
    "official": 1.0,
    "reuters": 0.95,
    "bloomberg": 0.95,
    "cnbc": 0.85,
    "yahoo_finance": 0.7,
    "twitter": 0.3,
    "social": 0.25,
    "unknown": 0.5,
}


@dataclass
class NewsEvent:
    event_id: str
    headline: str
    source: str
    timestamp: str
    symbols: list[str] = field(default_factory=list)
    sentiment: float = 0.0
    impact_score: float = 0.5
    category: str = "general"
    body: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def source_credibility(self) -> float:
        return SOURCE_CREDIBILITY_MAP.get(self.source.lower(), SOURCE_CREDIBILITY_MAP["unknown"])

    def age_minutes(self) -> float:
        try:
            return (datetime.now(timezone.utc) - datetime.fromisoformat(self.timestamp)).total_seconds() / 60
        except (ValueError, TypeError):
            return 0.0

    def is_stale(self, max_age_minutes: int = 1440) -> bool:
        return self.age_minutes() > max_age_minutes


@dataclass
class StructuredSignal:
    event_id: str
    symbol: str
    signal_type: str
    direction: str
    confidence: float
    risk_adjustment: str
    recommendation: str
    source: str
    timestamp: str


class NewsAnalyzer:
    def __init__(self):
        self._events: list[NewsEvent] = []
        self._stale_max_age: dict[str, int] = {
            "earnings": 1440,
            "regulatory": 4320,
            "macro": 2880,
            "corporate_action": 720,
            "analyst_rating": 1440,
            "general": 360,
        }

    def ingest(self, event: NewsEvent) -> None:
        self._events.append(event)

    def by_symbol(self, symbol: str) -> list[NewsEvent]:
        return [e for e in self._events if symbol in e.symbols]

    def by_category(self, category: str) -> list[NewsEvent]:
        return [e for e in self._events if e.category == category]

    def recent(self, minutes: int = 60) -> list[NewsEvent]:
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - minutes * 60
        results = []
        for e in self._events:
            try:
                et = datetime.fromisoformat(e.timestamp).timestamp()
                if et >= cutoff:
                    results.append(e)
            except (ValueError, TypeError):
                results.append(e)
        return results

    def high_impact(self, threshold: float = 0.7) -> list[NewsEvent]:
        return [e for e in self._events if e.impact_score >= threshold]

    def get_stale_events(self) -> list[NewsEvent]:
        stale = []
        for e in self._events:
            max_age = self._stale_max_age.get(e.category, 360)
            if e.is_stale(max_age):
                stale.append(e)
        return stale

    def clear_stale(self) -> int:
        before = len(self._events)
        keep = [e for e in self._events if not e.is_stale(self._stale_max_age.get(e.category, 360))]
        self._events = keep
        return before - len(keep)

    def to_signals(self, events: list[NewsEvent] | None = None) -> list[StructuredSignal]:
        src = events if events is not None else self._events
        signals: list[StructuredSignal] = []
        for e in src:
            if e.is_stale(self._stale_max_age.get(e.category, 360)):
                continue
            credibility = e.source_credibility()
            for sym in e.symbols:
                direction = "bullish" if e.sentiment > 0.2 else ("bearish" if e.sentiment < -0.2 else "neutral")
                adj = "tighten_risk" if abs(e.sentiment) > 0.7 else "normal"
                signals.append(StructuredSignal(
                    event_id=e.event_id,
                    symbol=sym,
                    signal_type=e.category,
                    direction=direction,
                    confidence=e.impact_score * credibility,
                    risk_adjustment=adj,
                    recommendation="watch" if abs(e.sentiment) < 0.3 else "no_trade" if abs(e.sentiment) > 0.8 else "observe",
                    source=e.source,
                    timestamp=e.timestamp,
                ))
        return signals

    def clear(self) -> None:
        self._events.clear()
