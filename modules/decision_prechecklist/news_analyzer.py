from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone


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


class NewsAnalyzer:
    def __init__(self):
        self._events: list[NewsEvent] = []

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

    def clear(self) -> None:
        self._events.clear()
