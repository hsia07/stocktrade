from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from enum import Enum
from datetime import datetime, timezone
from modules.decision_prechecklist.news_analyzer import NewsEvent


class RiskTier(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ImportanceScoredEvent:
    event: NewsEvent
    importance_score: float
    time_decay_factor: float
    effective_score: float
    ttl_minutes: int
    risk_tier: RiskTier = RiskTier.MEDIUM


class EventImportanceScorer:
    def __init__(self):
        self._ttl_map: dict[str, int] = {
            "earnings": 1440,
            "regulatory": 4320,
            "macro": 2880,
            "corporate_action": 720,
            "analyst_rating": 1440,
            "general": 360,
        }

    def score(self, event: NewsEvent) -> ImportanceScoredEvent:
        base = event.impact_score
        if event.sentiment != 0:
            base = base * (1.0 + abs(event.sentiment) * 0.5)
        base = min(1.0, base)

        ttl = self._ttl_map.get(event.category, 360)
        try:
            age_minutes = (datetime.now(timezone.utc) - datetime.fromisoformat(event.timestamp)).total_seconds() / 60
        except (ValueError, TypeError):
            age_minutes = 0
        decay = max(0.1, 1.0 - (age_minutes / ttl)) if ttl > 0 else 0.1

        effective = base * decay
        risk_tier = self._determine_risk_tier(effective, event.category)

        return ImportanceScoredEvent(
            event=event,
            importance_score=base,
            time_decay_factor=decay,
            effective_score=effective,
            ttl_minutes=ttl,
            risk_tier=risk_tier,
        )

    def _determine_risk_tier(self, effective_score: float, category: str) -> RiskTier:
        if effective_score >= 0.8 and category in ("regulatory", "earnings"):
            return RiskTier.CRITICAL
        if effective_score >= 0.6:
            return RiskTier.HIGH
        if effective_score >= 0.3:
            return RiskTier.MEDIUM
        return RiskTier.LOW

    def is_expired(self, scored: ImportanceScoredEvent) -> bool:
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(scored.event.timestamp)).total_seconds() / 60
        except (ValueError, TypeError):
            age = 0
        return age > scored.ttl_minutes
