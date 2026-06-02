from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone


VALID_REVIEW_STATUSES = frozenset({
    "pending",
    "approved",
    "rejected",
    "needs_more_evidence",
    "blocked",
})


VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"approved", "rejected", "needs_more_evidence", "blocked"},
    "needs_more_evidence": {"pending", "approved", "rejected", "blocked"},
    "approved": set(),
    "rejected": set(),
    "blocked": {"pending"},
}


HARDENED_LABEL_CATEGORIES = frozenset({
    "risk",
    "signal_type",
    "market_regime",
    "outcome",
    "decision_quality",
    "data_quality",
    "edge_assessment",
    "execution_review",
})


SCOPE_LABEL = "backend_contract_only"
UI_DEFERRED = True
DASHBOARD_IMPLEMENTED = False
NO_FAKE_UI_CLAIM = True
ANNOTATION_APPROVAL_DOES_NOT_ENABLE_TRADE = True

current_scope = SCOPE_LABEL
ui_deferred = UI_DEFERRED
dashboard_implemented = DASHBOARD_IMPLEMENTED
no_fake_ui_claim = NO_FAKE_UI_CLAIM
order_execution_allowed = False
annotation_approval_does_not_enable_trade = ANNOTATION_APPROVAL_DOES_NOT_ENABLE_TRADE


@dataclass
class ReviewAuditEntry:
    timestamp: str
    actor_id: str
    actor_role: str
    field: str
    old_value: str | None
    new_value: str | None
    reason_code: str | None
    trace_id: str


@dataclass
class AnnotationReviewItem:
    item_id: str
    source_type: str
    source_ref: str
    annotation_label: str
    review_status: str = "pending"
    reviewer_id: str | None = None
    reviewer_role: str | None = None
    reason_code: str | None = None
    confidence_or_quality_score: float | None = None
    created_at: str = ""
    updated_at: str = ""
    audit_trace_id: str = ""
    annotation_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_review_status(status: str) -> str | None:
    if status not in VALID_REVIEW_STATUSES:
        return f"invalid review status: {status!r}; valid: {sorted(VALID_REVIEW_STATUSES)}"
    return None


def validate_transition(current: str, next_status: str) -> str | None:
    allowed = VALID_TRANSITIONS.get(current)
    if allowed is None:
        return f"unknown current status: {current!r}"
    if next_status not in allowed:
        return (
            f"illegal transition: {current!r} -> {next_status!r}; "
            f"allowed from {current!r}: {sorted(allowed)}"
        )
    return None


def validate_label_category(category: str) -> str | None:
    if category not in HARDENED_LABEL_CATEGORIES:
        return f"invalid label category: {category!r}; valid: {sorted(HARDENED_LABEL_CATEGORIES)}"
    return None


class AnnotationReviewContract:
    current_scope = SCOPE_LABEL
    ui_deferred = UI_DEFERRED
    dashboard_implemented = DASHBOARD_IMPLEMENTED
    no_fake_ui_claim = NO_FAKE_UI_CLAIM
    order_execution_allowed = False
    annotation_approval_does_not_enable_trade = ANNOTATION_APPROVAL_DOES_NOT_ENABLE_TRADE

    def __init__(self):
        self._items: dict[str, AnnotationReviewItem] = {}
        self._audit_trail: list[ReviewAuditEntry] = []

    def add_item(
        self,
        item_id: str,
        source_type: str,
        source_ref: str,
        annotation_label: str,
        reviewer_id: str | None = None,
        reviewer_role: str | None = None,
        annotation_text: str = "",
        confidence_or_quality_score: float | None = None,
        audit_trace_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> AnnotationReviewItem:
        errors = self._validate_add(item_id, source_type, source_ref, annotation_label, reviewer_id, reviewer_role)
        if errors:
            msg = "; ".join(errors)
            raise ValueError(f"AnnotationReviewContract add_item fail-closed: {msg}")

        now = _now_iso()
        item = AnnotationReviewItem(
            item_id=item_id,
            source_type=source_type,
            source_ref=source_ref,
            annotation_label=annotation_label,
            reviewer_id=reviewer_id,
            reviewer_role=reviewer_role,
            confidence_or_quality_score=confidence_or_quality_score,
            created_at=now,
            updated_at=now,
            audit_trace_id=audit_trace_id or item_id,
            annotation_text=annotation_text,
            metadata=metadata or {},
        )
        self._items[item_id] = item
        self._append_audit("system", "system", "item_id", None, item_id, "create", audit_trace_id or item_id)
        return item

    def review_item(
        self,
        item_id: str,
        new_status: str,
        reviewer_id: str,
        reviewer_role: str,
        reason_code: str | None = None,
    ) -> AnnotationReviewItem:
        errors = self._validate_review(item_id, new_status, reviewer_id, reviewer_role, reason_code)
        if errors:
            msg = "; ".join(errors)
            raise ValueError(f"AnnotationReviewContract review_item fail-closed: {msg}")

        item = self._items[item_id]
        old_status = item.review_status
        item.review_status = new_status
        item.reviewer_id = reviewer_id
        item.reviewer_role = reviewer_role
        item.reason_code = reason_code
        item.updated_at = _now_iso()

        self._append_audit(
            reviewer_id, reviewer_role, "review_status", old_status, new_status,
            reason_code or "status_change", item.audit_trace_id,
        )
        return item

    def get_item(self, item_id: str) -> AnnotationReviewItem | None:
        return self._items.get(item_id)

    def get_audit_trail(self, trace_id: str | None = None) -> list[ReviewAuditEntry]:
        if trace_id is None:
            return list(self._audit_trail)
        return [e for e in self._audit_trail if e.trace_id == trace_id]

    def pending_items(self) -> list[AnnotationReviewItem]:
        return [i for i in self._items.values() if i.review_status == "pending"]

    def items_by_status(self, status: str) -> list[AnnotationReviewItem]:
        return [i for i in self._items.values() if i.review_status == status]

    def item_count(self) -> int:
        return len(self._items)

    def audit_trail_count(self) -> int:
        return len(self._audit_trail)

    def get_labels(self) -> set[str]:
        return set(HARDENED_LABEL_CATEGORIES)

    def _validate_add(
        self,
        item_id: str,
        source_type: str,
        source_ref: str,
        annotation_label: str,
        reviewer_id: str | None,
        reviewer_role: str | None,
    ) -> list[str]:
        errors: list[str] = []
        if not item_id:
            errors.append("missing item_id")
        if not source_type:
            errors.append("missing source_type")
        if not source_ref:
            errors.append("missing source_ref")
        if not annotation_label:
            errors.append("missing annotation_label")
        if annotation_label not in HARDENED_LABEL_CATEGORIES:
            errors.append(f"invalid annotation_label {annotation_label!r}; valid: {sorted(HARDENED_LABEL_CATEGORIES)}")
        if item_id in self._items:
            errors.append(f"duplicate item_id: {item_id!r}")
        return errors

    def _validate_review(
        self,
        item_id: str,
        new_status: str,
        reviewer_id: str,
        reviewer_role: str,
        reason_code: str | None,
    ) -> list[str]:
        errors: list[str] = []
        if not item_id:
            errors.append("missing item_id")
        if not reviewer_id:
            errors.append("missing reviewer_id")
        if not reviewer_role:
            errors.append("missing reviewer_role")
        if item_id not in self._items:
            errors.append(f"item not found: {item_id!r}")
        else:
            current = self._items[item_id].review_status
            transition_err = validate_transition(current, new_status)
            if transition_err:
                errors.append(transition_err)
        status_err = validate_review_status(new_status)
        if status_err:
            errors.append(status_err)
        if new_status in ("rejected", "blocked") and not reason_code:
            errors.append(f"missing reason_code for status={new_status!r}")
        return errors

    def _append_audit(
        self,
        actor_id: str,
        actor_role: str,
        field: str,
        old_value: str | None,
        new_value: str | None,
        reason_code: str | None,
        trace_id: str,
    ) -> None:
        entry = ReviewAuditEntry(
            timestamp=_now_iso(),
            actor_id=actor_id,
            actor_role=actor_role,
            field=field,
            old_value=old_value,
            new_value=new_value,
            reason_code=reason_code,
            trace_id=trace_id,
        )
        self._audit_trail.append(entry)
