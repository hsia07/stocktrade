from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from modules.decision_prechecklist.news_analyzer import NewsEvent


@dataclass
class ConflictRecord:
    event_a: NewsEvent
    event_b: NewsEvent
    conflict_type: str
    resolution: str = "unresolved"


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
                    record = ConflictRecord(
                        event_a=events[i],
                        event_b=events[j],
                        conflict_type="sentiment_conflict",
                    )
                    conflicts.append(record)
                    self._conflicts.append(record)
        return conflicts

    def resolve(self, record: ConflictRecord, resolution: str) -> None:
        record.resolution = resolution

    def get_unresolved(self) -> list[ConflictRecord]:
        return [c for c in self._conflicts if c.resolution == "unresolved"]

    def resolve_all(self, resolution: str = "use_latest") -> int:
        count = 0
        for c in self._conflicts:
            if c.resolution == "unresolved":
                c.resolution = resolution
                count += 1
        return count
