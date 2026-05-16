from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from modules.decision_prechecklist.news_analyzer import NewsEvent


@dataclass
class DedupResult:
    original: NewsEvent
    duplicate: NewsEvent
    similarity: float
    is_duplicate: bool


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

    def _jaccard_similarity(self, a: str, b: str) -> float:
        set_a = set(a.lower().split())
        set_b = set(b.lower().split())
        if not set_a or not set_b:
            return 0.0
        inter = len(set_a & set_b)
        union = len(set_a | set_b)
        return inter / union if union > 0 else 0.0
