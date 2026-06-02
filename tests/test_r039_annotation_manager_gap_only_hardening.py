import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
from modules.decision_prechecklist.annotation_review_contract import (
    AnnotationReviewContract,
    AnnotationReviewItem,
    ReviewAuditEntry,
    VALID_REVIEW_STATUSES,
    VALID_TRANSITIONS,
    HARDENED_LABEL_CATEGORIES,
    validate_review_status,
    validate_transition,
    validate_label_category,
    current_scope,
    ui_deferred,
    dashboard_implemented,
    no_fake_ui_claim,
    order_execution_allowed,
    annotation_approval_does_not_enable_trade,
)


def test_contract_initialization():
    c = AnnotationReviewContract()
    assert c is not None
    assert c.item_count() == 0
    assert c.audit_trail_count() == 0


def test_valid_annotation_create():
    c = AnnotationReviewContract()
    item = c.add_item(
        item_id="item-001",
        source_type="trade_log",
        source_ref="log-20260501-001",
        annotation_label="decision_quality",
        reviewer_id="reviewer1",
        reviewer_role="analyst",
        annotation_text="Good entry timing",
    )
    assert item.item_id == "item-001"
    assert item.source_type == "trade_log"
    assert item.source_ref == "log-20260501-001"
    assert item.annotation_label == "decision_quality"
    assert item.review_status == "pending"
    assert item.reviewer_id == "reviewer1"
    assert item.created_at != ""
    assert item.updated_at != ""
    assert c.get_item("item-001") is item


def test_valid_review_approve():
    c = AnnotationReviewContract()
    c.add_item(item_id="item-002", source_type="signal", source_ref="sig-045", annotation_label="signal_type")
    reviewed = c.review_item(item_id="item-002", new_status="approved", reviewer_id="reviewer2", reviewer_role="senior_analyst")
    assert reviewed.review_status == "approved"
    assert reviewed.reviewer_id == "reviewer2"


def test_valid_review_reject_with_reason():
    c = AnnotationReviewContract()
    c.add_item(item_id="item-003", source_type="signal", source_ref="sig-046", annotation_label="risk")
    reviewed = c.review_item(item_id="item-003", new_status="rejected", reviewer_id="reviewer3", reviewer_role="manager", reason_code="false_signal")
    assert reviewed.review_status == "rejected"
    assert reviewed.reason_code == "false_signal"


def test_pending_to_approved():
    c = AnnotationReviewContract()
    c.add_item(item_id="t1", source_type="test", source_ref="t1", annotation_label="edge_assessment")
    c.review_item(item_id="t1", new_status="approved", reviewer_id="r1", reviewer_role="analyst")
    assert c.get_item("t1").review_status == "approved"


def test_pending_to_rejected():
    c = AnnotationReviewContract()
    c.add_item(item_id="t2", source_type="test", source_ref="t2", annotation_label="data_quality")
    c.review_item(item_id="t2", new_status="rejected", reviewer_id="r1", reviewer_role="analyst", reason_code="bad_data")
    assert c.get_item("t2").review_status == "rejected"


def test_pending_to_needs_more_evidence():
    c = AnnotationReviewContract()
    c.add_item(item_id="t3", source_type="test", source_ref="t3", annotation_label="execution_review")
    c.review_item(item_id="t3", new_status="needs_more_evidence", reviewer_id="r1", reviewer_role="analyst", reason_code="insufficient_data")
    assert c.get_item("t3").review_status == "needs_more_evidence"


def test_illegal_transition_fail_closed():
    c = AnnotationReviewContract()
    c.add_item(item_id="t4", source_type="test", source_ref="t4", annotation_label="risk")
    c.review_item(item_id="t4", new_status="approved", reviewer_id="r1", reviewer_role="analyst")
    with pytest.raises(ValueError, match="illegal transition"):
        c.review_item(item_id="t4", new_status="pending", reviewer_id="r1", reviewer_role="analyst")


def test_missing_item_id_fail_closed():
    c = AnnotationReviewContract()
    with pytest.raises(ValueError, match="missing item_id"):
        c.add_item(item_id="", source_type="test", source_ref="ref1", annotation_label="risk")


def test_missing_source_ref_fail_closed():
    c = AnnotationReviewContract()
    with pytest.raises(ValueError, match="missing source_ref"):
        c.add_item(item_id="i1", source_type="test", source_ref="", annotation_label="risk")


def test_missing_source_type_fail_closed():
    c = AnnotationReviewContract()
    with pytest.raises(ValueError, match="missing source_type"):
        c.add_item(item_id="i1", source_type="", source_ref="ref1", annotation_label="risk")


def test_invalid_label_fail_closed():
    c = AnnotationReviewContract()
    with pytest.raises(ValueError, match="invalid annotation_label"):
        c.add_item(item_id="i1", source_type="test", source_ref="ref1", annotation_label="nonexistent_label")


def test_missing_reviewer_id_fail_closed():
    c = AnnotationReviewContract()
    c.add_item(item_id="i2", source_type="test", source_ref="r2", annotation_label="risk")
    with pytest.raises(ValueError, match="missing reviewer_id"):
        c.review_item(item_id="i2", new_status="approved", reviewer_id="", reviewer_role="analyst")


def test_missing_reviewer_role_fail_closed():
    c = AnnotationReviewContract()
    c.add_item(item_id="i3", source_type="test", source_ref="r3", annotation_label="risk")
    with pytest.raises(ValueError, match="missing reviewer_role"):
        c.review_item(item_id="i3", new_status="approved", reviewer_id="reviewer1", reviewer_role="")


def test_missing_reason_code_for_reject_fail_closed():
    c = AnnotationReviewContract()
    c.add_item(item_id="i4", source_type="test", source_ref="r4", annotation_label="risk")
    with pytest.raises(ValueError, match="missing reason_code for status='rejected'"):
        c.review_item(item_id="i4", new_status="rejected", reviewer_id="r1", reviewer_role="analyst", reason_code=None)


def test_missing_reason_code_for_blocked_fail_closed():
    c = AnnotationReviewContract()
    c.add_item(item_id="i5", source_type="test", source_ref="r5", annotation_label="risk")
    with pytest.raises(ValueError, match="missing reason_code for status='blocked'"):
        c.review_item(item_id="i5", new_status="blocked", reviewer_id="r1", reviewer_role="analyst", reason_code=None)


def test_audit_trail_append_only():
    c = AnnotationReviewContract()
    c.add_item(item_id="a1", source_type="test", source_ref="s1", annotation_label="data_quality")
    c.review_item(item_id="a1", new_status="approved", reviewer_id="r1", reviewer_role="analyst")
    trail = c.get_audit_trail()
    assert len(trail) == 2  # create + review
    create_entry = trail[0]
    review_entry = trail[1]
    assert create_entry.field == "item_id"
    assert create_entry.new_value == "a1"
    assert review_entry.field == "review_status"
    assert review_entry.old_value == "pending"
    assert review_entry.new_value == "approved"
    assert review_entry.actor_id == "r1"


def test_audit_trail_filter_by_trace_id():
    c = AnnotationReviewContract()
    c.add_item(item_id="a2", source_type="test", source_ref="s2", annotation_label="outcome", audit_trace_id="trace-a2")
    c.review_item(item_id="a2", new_status="rejected", reviewer_id="r2", reviewer_role="manager", reason_code="bad")
    trail = c.get_audit_trail(trace_id="trace-a2")
    assert len(trail) == 2
    for e in trail:
        assert e.trace_id == "trace-a2"


def test_no_broker_live_order_runtime_side_effect():
    c = AnnotationReviewContract()
    assert c.order_execution_allowed is False
    assert c.annotation_approval_does_not_enable_trade is True
    assert c.current_scope == "backend_contract_only"
    c.add_item(item_id="safe1", source_type="test", source_ref="s1", annotation_label="risk")
    c.review_item(item_id="safe1", new_status="approved", reviewer_id="r1", reviewer_role="analyst")
    assert c.order_execution_allowed is False
    assert c.annotation_approval_does_not_enable_trade is True


def test_order_execution_allowed_remains_false():
    assert order_execution_allowed is False


def test_contract_only_status_no_dashboard_claim():
    assert current_scope == "backend_contract_only"
    assert ui_deferred is True
    assert dashboard_implemented is False
    assert no_fake_ui_claim is True


def test_valid_review_statuses():
    assert "pending" in VALID_REVIEW_STATUSES
    assert "approved" in VALID_REVIEW_STATUSES
    assert "rejected" in VALID_REVIEW_STATUSES
    assert "needs_more_evidence" in VALID_REVIEW_STATUSES
    assert "blocked" in VALID_REVIEW_STATUSES


def test_valid_transitions():
    assert VALID_TRANSITIONS["pending"] == {"approved", "rejected", "needs_more_evidence", "blocked"}
    assert VALID_TRANSITIONS["approved"] == set()
    assert VALID_TRANSITIONS["rejected"] == set()
    assert VALID_TRANSITIONS["blocked"] == {"pending"}
    assert VALID_TRANSITIONS["needs_more_evidence"] == {"pending", "approved", "rejected", "blocked"}


def test_validate_review_status():
    assert validate_review_status("pending") is None
    assert validate_review_status("invalid") is not None


def test_validate_transition():
    assert validate_transition("pending", "approved") is None
    assert validate_transition("approved", "pending") is not None


def test_validate_label_category():
    assert validate_label_category("risk") is None
    assert validate_label_category("invalid") is not None


def test_blocked_item_can_return_to_pending():
    c = AnnotationReviewContract()
    c.add_item(item_id="b1", source_type="test", source_ref="r1", annotation_label="risk")
    c.review_item(item_id="b1", new_status="blocked", reviewer_id="r1", reviewer_role="analyst", reason_code="needs_clarification")
    assert c.get_item("b1").review_status == "blocked"
    c.review_item(item_id="b1", new_status="pending", reviewer_id="r2", reviewer_role="senior_analyst", reason_code="clarified")
    assert c.get_item("b1").review_status == "pending"


def test_needs_more_evidence_can_approve():
    c = AnnotationReviewContract()
    c.add_item(item_id="n1", source_type="test", source_ref="r1", annotation_label="execution_review")
    c.review_item(item_id="n1", new_status="needs_more_evidence", reviewer_id="r1", reviewer_role="analyst", reason_code="insufficient")
    c.review_item(item_id="n1", new_status="approved", reviewer_id="r2", reviewer_role="senior_analyst", reason_code="additional_data_ok")
    assert c.get_item("n1").review_status == "approved"


def test_pending_items():
    c = AnnotationReviewContract()
    c.add_item(item_id="p1", source_type="test", source_ref="r1", annotation_label="risk")
    c.add_item(item_id="p2", source_type="test", source_ref="r2", annotation_label="risk")
    c.review_item(item_id="p2", new_status="approved", reviewer_id="r1", reviewer_role="analyst")
    pending = c.pending_items()
    assert len(pending) == 1
    assert pending[0].item_id == "p1"


def test_items_by_status():
    c = AnnotationReviewContract()
    c.add_item(item_id="s1", source_type="test", source_ref="r1", annotation_label="data_quality")
    c.review_item(item_id="s1", new_status="needs_more_evidence", reviewer_id="r1", reviewer_role="analyst", reason_code="unclear")
    items = c.items_by_status("needs_more_evidence")
    assert len(items) == 1
    assert items[0].item_id == "s1"


def test_duplicate_item_id_fail_closed():
    c = AnnotationReviewContract()
    c.add_item(item_id="dup1", source_type="test", source_ref="r1", annotation_label="risk")
    with pytest.raises(ValueError, match="duplicate item_id"):
        c.add_item(item_id="dup1", source_type="test", source_ref="r2", annotation_label="risk")


def test_hardened_label_categories():
    assert "risk" in HARDENED_LABEL_CATEGORIES
    assert "data_quality" in HARDENED_LABEL_CATEGORIES
    assert "edge_assessment" in HARDENED_LABEL_CATEGORIES
    assert "execution_review" in HARDENED_LABEL_CATEGORIES


def test_get_labels():
    c = AnnotationReviewContract()
    labels = c.get_labels()
    assert "risk" in labels
    assert "data_quality" in labels
    assert len(labels) >= 6


def test_review_nonexistent_item_fail_closed():
    c = AnnotationReviewContract()
    with pytest.raises(ValueError, match="item not found"):
        c.review_item(item_id="nonexistent", new_status="approved", reviewer_id="r1", reviewer_role="analyst")


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
