from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from enum import Enum
from modules.decision_prechecklist.news_analyzer import NewsEvent


class SafetyDegrade(Enum):
    NORMAL = "normal"
    TIGHTEN_RISK = "tighten_risk"
    WAIT_CONFIRMATION = "wait_confirmation"
    NO_TRADE = "no_trade"


@dataclass
class ConflictRecord:
    event_a: NewsEvent
    event_b: NewsEvent
    conflict_type: str
    resolution: str = "unresolved"
    safety_decision: SafetyDegrade = SafetyDegrade.NORMAL


class ConflictIntegrator:
    def __init__(self):
        self._conflicts: list[ConflictRecord] = []

    def detect(self, events: list[NewsEvent]) -> list[ConflictRecord]:
        conflicts: list[ConflictRecord] = []
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                shared = set(events[i].symbols) & set(events[j].symbols)
                if not shared:
                    continue
                if abs(events[i].sentiment - events[j].sentiment) > 0.5:
                    safety = self._decide_safety(events[i], events[j])
                    record = ConflictRecord(
                        event_a=events[i],
                        event_b=events[j],
                        conflict_type="sentiment_conflict",
                        safety_decision=safety,
                    )
                    conflicts.append(record)
                    self._conflicts.append(record)
        return conflicts

    def _decide_safety(self, a: NewsEvent, b: NewsEvent) -> SafetyDegrade:
        diff = abs(a.sentiment - b.sentiment)
        max_impact = max(a.impact_score, b.impact_score)
        if diff > 1.2 and max_impact > 0.7:
            return SafetyDegrade.NO_TRADE
        if diff > 0.8 or max_impact > 0.8:
            return SafetyDegrade.WAIT_CONFIRMATION
        if diff > 0.5 or max_impact > 0.6:
            return SafetyDegrade.TIGHTEN_RISK
        return SafetyDegrade.NORMAL

    def resolve(self, record: ConflictRecord, resolution: str) -> None:
        record.resolution = resolution
        if resolution == "no_trade":
            record.safety_decision = SafetyDegrade.NO_TRADE
        elif resolution == "wait_confirmation":
            record.safety_decision = SafetyDegrade.WAIT_CONFIRMATION
        elif resolution in ("tighten_risk", "ignore_bearish"):
            record.safety_decision = SafetyDegrade.TIGHTEN_RISK
        elif resolution in ("use_latest", "use_majority"):
            record.safety_decision = SafetyDegrade.NORMAL

    def get_unresolved(self) -> list[ConflictRecord]:
        return [c for c in self._conflicts if c.resolution == "unresolved"]

    def get_active_safety_degrade(self, symbol: str) -> SafetyDegrade:
        worst = SafetyDegrade.NORMAL
        for c in self._conflicts:
            if c.resolution != "unresolved":
                continue
            shared = symbol in c.event_a.symbols or symbol in c.event_b.symbols
            if not shared:
                continue
            order = [SafetyDegrade.NORMAL, SafetyDegrade.TIGHTEN_RISK, SafetyDegrade.WAIT_CONFIRMATION, SafetyDegrade.NO_TRADE]
            if order.index(c.safety_decision) > order.index(worst):
                worst = c.safety_decision
        return worst

    def resolve_all(self, resolution: str = "use_latest") -> int:
        count = 0
        for c in self._conflicts:
            if c.resolution == "unresolved":
                self.resolve(c, resolution)
                count += 1
        return count
