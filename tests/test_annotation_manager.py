import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.annotation_manager import AnnotationManager, AnnotationEntry, DataLabel, LABEL_CATEGORIES


def test_manager_initialization():
    m = AnnotationManager()
    assert m is not None


def test_register_label():
    m = AnnotationManager()
    label = DataLabel(label_id="risk_high", name="High Risk", category="risk")
    m.register_label(label)
    assert m.get_label("risk_high") is not None


def test_add_entry():
    m = AnnotationManager()
    entry = m.add_entry(trace_id="trace-001", annotator="reviewer1", annotation="good")
    assert entry.trace_id == "trace-001"
    assert entry.annotator == "reviewer1"


def test_review_entry():
    m = AnnotationManager()
    m.add_entry(trace_id="trace-001", annotator="reviewer1", annotation="good")
    assert m.review_entry("trace-001", "approved") is True
    e = m.get_entry("trace-001")
    assert e.review_status == "approved"


def test_get_pending_entries():
    m = AnnotationManager()
    m.add_entry(trace_id="t1", annotator="a1", annotation="pending")
    m.add_entry(trace_id="t2", annotator="a2", annotation="done")
    m.review_entry("t2", "approved")
    pending = m.get_pending_entries()
    assert len(pending) == 1
    assert pending[0].trace_id == "t1"


def test_review_nonexistent():
    m = AnnotationManager()
    assert m.review_entry("nonexistent", "approved") is False


def test_label_categories():
    assert "risk" in LABEL_CATEGORIES
    assert "signal_type" in LABEL_CATEGORIES
    assert len(LABEL_CATEGORIES) >= 4


def test_annotation_entry_defaults():
    e = AnnotationEntry(trace_id="t1", annotator="a1", annotation="test")
    assert e.tags == []
    assert e.review_status == "pending"
    assert e.timestamp == ""


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
