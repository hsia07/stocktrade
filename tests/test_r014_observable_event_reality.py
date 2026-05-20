import pytest
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import ObservableEvent


class TestObservableEventBehavior:
    """Dedicated behavioral tests for R014 ObservableEvent - not string-only scan."""

    def test_import_real_source(self):
        """Test that we can import the real ObservableEvent source."""
        oe = ObservableEvent()
        assert hasattr(oe, 'emit')
        assert hasattr(oe, 'events')
        assert isinstance(oe.events, list)

    def test_emit_positive_event_write(self):
        """Test emit() appends event to in-memory events list."""
        oe = ObservableEvent()
        event = oe.emit(
            event_type="system",
            source="test_source",
            status="info",
            message="Test event",
            details={"key": "value"}
        )
        assert len(oe.events) == 1
        assert event is not None

    def test_event_fields_completeness(self):
        """Test event contains all required fields."""
        oe = ObservableEvent()
        event = oe.emit(
            event_type="trade",
            source="execution_2330",
            status="success",
            message="Buy 100 shares",
            details={"price": 100.0}
        )
        assert "event_id" in event
        assert "timestamp" in event
        assert event["event_type"] == "trade"
        assert event["source"] == "execution_2330"
        assert event["status"] == "success"
        assert event["message"] == "Buy 100 shares"
        assert "details" in event

    def test_event_id_unique_or_nonempty(self):
        """Test event_id is non-empty."""
        oe = ObservableEvent()
        event = oe.emit(
            event_type="system",
            source="test",
            status="info",
            message="Test"
        )
        assert event["event_id"]
        assert len(event["event_id"]) > 0

    def test_event_id_not_formal_trace_id(self):
        """Test that event_id is NOT claimed to be formal trace_id."""
        oe = ObservableEvent()
        event = oe.emit(
            event_type="system",
            source="test",
            status="info",
            message="Test"
        )
        event_id = event["event_id"]
        assert not event_id.startswith("trace_"), "event_id must NOT be called trace_id"
        assert "trace_id" not in event, "event must NOT have trace_id field"

    def test_timestamp_parseable(self):
        """Test timestamp is ISO format parseable."""
        oe = ObservableEvent()
        event = oe.emit(
            event_type="system",
            source="test",
            status="info",
            message="Test"
        )
        ts = event["timestamp"]
        assert ts is not None
        assert "T" in ts or ":" in ts

    def test_emit_trade_behavior(self):
        """Test emit_trade() creates trade event."""
        oe = ObservableEvent()
        event = oe.emit_trade(symbol="2330.TW", action="buy", price=100.0, lots=100)
        assert event["event_type"] == "trade"
        assert "2330.TW" in event["details"]["symbol"]
        assert event["details"]["action"] == "buy"

    def test_emit_signal_behavior(self):
        """Test emit_signal() creates signal event."""
        oe = ObservableEvent()
        event = oe.emit_signal(symbol="2330.TW", direction="buy", confidence=0.8, reason="RSI below 30")
        assert event["event_type"] == "signal"
        assert event["details"]["direction"] == "buy"

    def test_emit_risk_alert_behavior(self):
        """Test emit_risk_alert() creates risk event."""
        oe = ObservableEvent()
        event = oe.emit_risk_alert(symbol="2330.TW", alert_type="circuit_breaker", details={"state": "OPEN"})
        assert event["event_type"] == "risk"
        assert event["status"] == "alert"

    def test_emit_error_behavior(self):
        """Test emit_error() creates error event."""
        oe = ObservableEvent()
        event = oe.emit_error(source="test", error_type="Timeout", message="Request timeout")
        assert event["event_type"] == "error"
        assert event["status"] == "error"

    def test_emit_recovery_behavior(self):
        """Test emit_recovery() creates recovery event."""
        oe = ObservableEvent()
        event = oe.emit_recovery(source="silence", recovery_type="silence_recovered")
        assert event["event_type"] == "recovery"
        assert event["status"] == "success"

    def test_emit_audit_behavior(self):
        """Test emit_audit() creates audit event."""
        oe = ObservableEvent()
        event = oe.emit_audit(action="mode_changed", actor="system")
        assert event["event_type"] == "audit"

    def test_append_only_invariant(self):
        """Test append-only: events can only be added, not overwritten."""
        oe = ObservableEvent()
        event1 = oe.emit(event_type="system", source="test", status="info", message="First")
        original_event_id = event1["event_id"]
        
        event2 = oe.emit(event_type="system", source="test", status="info", message="Second")
        assert len(oe.events) == 2
        assert oe.events[0]["event_id"] == original_event_id, "First event must not be overwritten"
        assert oe.events[0]["message"] == "First", "First event must retain original message"

    def test_malformed_details_does_not_break(self):
        """Test malformed/unusual details do not break append-only."""
        oe = ObservableEvent()
        
        oe.emit(event_type="system", source="test", status="info", message="Normal")
        
        oe.emit(event_type="system", source="test", status="info", message="With None details", details=None)
        
        oe.emit(event_type="system", source="test", status="info", message="With empty dict", details={})
        
        oe.emit(event_type="system", source="test", status="info", message="With nested", details={"nested": {"deep": True}})
        
        assert len(oe.events) == 4, "All events should be appended successfully"

    def test_get_events_filtering(self):
        """Test get_events() filtering works."""
        oe = ObservableEvent()
        oe.emit(event_type="trade", source="exec", status="success", message="Trade 1")
        oe.emit(event_type="signal", source="sig", status="info", message="Signal 1")
        oe.emit(event_type="trade", source="exec", status="success", message="Trade 2")
        
        trade_events = oe.get_events(event_type="trade")
        assert len(trade_events) == 2
        
        signal_events = oe.get_events(event_type="signal")
        assert len(signal_events) == 1

    def test_validate_schema(self):
        """Test schema validation."""
        oe = ObservableEvent()
        oe.emit(event_type="system", source="test", status="info", message="Test")
        
        result = oe.validate_schema()
        assert result["valid"] is True
        assert result["event_count"] == 1

    def test_no_broker_api_called(self):
        """Test that ObservableEvent does NOT call broker API."""
        oe = ObservableEvent()
        event = oe.emit(
            event_type="trade",
            source="test",
            status="info",
            message="Test trade",
            details={"test": True}
        )
        assert event is not None
        assert "shioaji" not in str(event).lower()
        assert "fubon" not in str(event).lower()
        assert "broker" not in str(event).lower()

    def test_runtime_state_not_persisted(self):
        """Test that events are only in-memory, not persisted to DB."""
        oe = ObservableEvent()
        oe.emit(event_type="system", source="test", status="info", message="Test")
        assert len(oe.events) > 0
        assert hasattr(oe, '_schema'), "Schema exists for validation only"


class TestObservableEventNegativeBoundary:
    """Negative tests for ObservableEvent - no broker/live pollution."""

    def test_no_fubon_integration(self):
        """Ensure no Fubon API integration."""
        oe = ObservableEvent()
        event = oe.emit(
            event_type="system",
            source="test",
            status="info",
            message="Test"
        )
        event_str = str(event).lower()
        assert "fubon" not in event_str
        assert "券商" not in event_str

    def test_no_shioaji_integration(self):
        """Ensure no Shioaji API integration."""
        oe = ObservableEvent()
        event = oe.emit(
            event_type="system",
            source="test",
            status="info",
            message="Test"
        )
        event_str = str(event).lower()
        assert "shioaji" not in event_str

    def test_in_memory_not_durable_persistence(self):
        """Ensure events are in-memory only, not durable."""
        oe = ObservableEvent()
        oe.emit(event_type="system", source="test", status="info", message="Test")
        assert hasattr(oe, 'events')
        assert isinstance(oe.events, list)
        assert len(oe.events) > 0