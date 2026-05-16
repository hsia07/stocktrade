from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone
from modules.decision_prechecklist.news_analyzer import NewsEvent


STALE_MAX_AGE_MINUTES: dict[str, int] = {
    "earnings": 1440,
    "regulatory": 4320,
    "macro": 2880,
    "corporate_action": 720,
    "analyst_rating": 1440,
    "general": 360,
}


@dataclass
class DedupResult:
    original: NewsEvent
    duplicate: NewsEvent
    similarity: float
    is_duplicate: bool


@dataclass
class StaleCheckResult:
    event: NewsEvent
    is_stale: bool
    age_minutes: float
    max_age_minutes: int
    action: str


class EventDeduplicator:
    def __init__(self, headline_similarity_threshold: float = 0.8):
        self._threshold = headline_similarity_threshold
        self._seen_headlines: dict[str, list[NewsEvent]] = {}

    def check(self, event: NewsEvent) -> DedupResult | None:
        key = event.symbols[0] if event.symbols else "_global"
        if key not in self._seen_headlines:
            self._seen_headlines[key] = []
            return None

        for existing in self._seen_headlines[key]:
            sim = self._jaccard_similarity(existing.headline, event.headline)
            if sim >= self._threshold:
                return DedupResult(
                    original=existing,
                    duplicate=event,
                    similarity=sim,
                    is_duplicate=True,
                )
        return None

    def register(self, event: NewsEvent) -> None:
        key = event.symbols[0] if event.symbols else "_global"
        if key not in self._seen_headlines:
            self._seen_headlines[key] = []
        self._seen_headlines[key].append(event)

    def check_stale(self, event: NewsEvent) -> StaleCheckResult:
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(event.timestamp)).total_seconds() / 60
        except (ValueError, TypeError):
            age = 0.0
        max_age = STALE_MAX_AGE_MINUTES.get(event.category, 360)
        stale = age > max_age
        return StaleCheckResult(
            event=event,
            is_stale=stale,
            age_minutes=age,
            max_age_minutes=max_age,
            action="reject" if stale else "accept",
        )

    def filter_stale(self, events: list[NewsEvent]) -> tuple[list[NewsEvent], list[NewsEvent]]:
        fresh: list[NewsEvent] = []
        stale: list[NewsEvent] = []
        for e in events:
            result = self.check_stale(e)
            if result.is_stale:
                stale.append(e)
            else:
                fresh.append(e)
        return fresh, stale

    def dedup_and_filter(self, event: NewsEvent) -> DedupResult | StaleCheckResult | None:
        stale_result = self.check_stale(event)
        if stale_result.is_stale:
            return stale_result
        dup_result = self.check(event)
        if dup_result is None:
            self.register(event)
        return dup_result

    def _jaccard_similarity(self, a: str, b: str) -> float:
        set_a = set(a.lower().split())
        set_b = set(b.lower().split())
        if not set_a or not set_b:
            return 0.0
        inter = len(set_a & set_b)
        union = len(set_a | set_b)
        return inter / union if union > 0 else 0.0
