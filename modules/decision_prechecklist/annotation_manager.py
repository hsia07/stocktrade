from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone


@dataclass
class AnnotationEntry:
    trace_id: str
    annotator: str
    annotation: str
    tags: list[str] = field(default_factory=list)
    timestamp: str = ""
    review_status: str = "pending"


@dataclass
class ReviewQueue:
    entries: list[AnnotationEntry] = field(default_factory=list)

    def add(self, entry: AnnotationEntry) -> None:
        self.entries.append(entry)

    def pending(self) -> list[AnnotationEntry]:
        return [e for e in self.entries if e.review_status == "pending"]

    def reviewed(self) -> list[AnnotationEntry]:
        return [e for e in self.entries if e.review_status != "pending"]


@dataclass
class DataLabel:
    label_id: str
    name: str
    category: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


LABEL_CATEGORIES = frozenset({
    "risk",
    "signal_type",
    "market_regime",
    "outcome",
    "decision_quality",
})


class AnnotationManager:
    def __init__(self):
        self._labels: dict[str, DataLabel] = {}
        self._entries: list[AnnotationEntry] = []

    def register_label(self, label: DataLabel) -> None:
        self._labels[label.label_id] = label

    def get_label(self, label_id: str) -> DataLabel | None:
        return self._labels.get(label_id)

    def add_entry(self, trace_id: str, annotator: str, annotation: str, tags: list[str] | None = None) -> AnnotationEntry:
        entry = AnnotationEntry(
            trace_id=trace_id,
            annotator=annotator,
            annotation=annotation,
            tags=tags or [],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._entries.append(entry)
        return entry

    def review_entry(self, trace_id: str, status: str) -> bool:
        for e in self._entries:
            if e.trace_id == trace_id:
                e.review_status = status
                return True
        return False

    def get_pending_entries(self) -> list[AnnotationEntry]:
        return [e for e in self._entries if e.review_status == "pending"]

    def get_entry(self, trace_id: str) -> AnnotationEntry | None:
        for e in self._entries:
            if e.trace_id == trace_id:
                return e
        return None
