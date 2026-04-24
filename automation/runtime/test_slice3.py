"""
C3 Slice 3 Test: SQLite Queue + DLQ + Ack/Nack + Restart Recovery

Tests:
A. 1000 messages enqueue < 5 seconds
B. 1000 messages dequeue + ack < 5 seconds
C. ack(message_id) removes from queue
D. nack(message_id, reason) increments retry count
E. message nacked max_retries times moves to DLQ
F. DLQ entry schema: timestamp / provider / correlation_key / failure_reason / original_payload_ref
G. DLQ entries survive process restart
H. pending un-acked messages recoverable after process restart
I. Slice 2 terminal failures can route to DLQ via adapter
J. No idempotency / dedupe / audit trail / compliance reporting
K. No real API calls
"""

import sys
import time
import os
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.runtime.queue import MessageQueue, QueueMessage
from automation.runtime.dlq import DLQManager, DLQEntry
from automation.runtime.dlq_adapter import TerminalFailureToDLQAdapter
from automation.runtime.retry import RetryExhaustedError, ExponentialBackoffRetry, RetryConfig


def get_test_db():
    """Get a temporary test database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def cleanup_db(path):
    """Remove test database."""
    try:
        os.remove(path)
    except OSError:
        pass


def test_1_enqueue_1000_under_5s():
    """Test A: 1000 messages enqueued in < 5 seconds."""
    print("\n[Test 1] Enqueue 1000 messages under 5 seconds")
    db = get_test_db()
    queue = MessageQueue(db)

    start = time.time()
    for i in range(1000):
        queue.enqueue(
            provider="openai",
            payload={"tick": i, "content": f"message_{i}"},
            correlation_key=f"corr_{i}",
        )
    elapsed = time.time() - start

    assert queue.get_pending_count() == 1000, f"Expected 1000 pending, got {queue.get_pending_count()}"
    assert elapsed < 5.0, f"Expected < 5s, got {elapsed:.2f}s"

    print(f"  PASS: Enqueued 1000 messages in {elapsed:.2f}s")
    cleanup_db(db)
    return True


def test_2_dequeue_ack_1000_under_5s():
    """Test B: 1000 messages dequeued and acked in < 5 seconds."""
    print("\n[Test 2] Dequeue + ack 1000 messages under 5 seconds")
    db = get_test_db()
    queue = MessageQueue(db)

    # Enqueue 1000
    message_ids = []
    for i in range(1000):
        mid = queue.enqueue(
            provider="telegram",
            payload={"tick": i},
            correlation_key=f"corr_{i}",
        )
        message_ids.append(mid)

    start = time.time()
    acked = queue.bulk_dequeue_ack(1000)
    elapsed = time.time() - start

    assert acked == 1000, f"Expected 1000 acked, got {acked}"
    assert queue.get_pending_count() == 0, f"Expected 0 pending, got {queue.get_pending_count()}"
    assert elapsed < 5.0, f"Expected < 5s, got {elapsed:.2f}s"

    print(f"  PASS: Dequeued and acked 1000 messages in {elapsed:.2f}s")
    cleanup_db(db)
    return True


def test_3_ack_removes_from_queue():
    """Test C: ack(message_id) removes from queue."""
    print("\n[Test 3] ack removes message from queue")
    db = get_test_db()
    queue = MessageQueue(db)

    mid = queue.enqueue(provider="openai", payload={"test": "ack"})
    assert queue.get_pending_count() == 1

    msg = queue.dequeue()
    assert msg is not None
    assert msg.status == "processing"

    success = queue.ack(msg.id)
    assert success is True

    # Message should no longer be pending or processing
    assert queue.get_pending_count() == 0

    # Verify message status is acked
    retrieved = queue.get_message(msg.id)
    assert retrieved is not None
    assert retrieved.status == "acked"

    print(f"  PASS: ack removed message {msg.id} from active queue")
    cleanup_db(db)
    return True


def test_4_nack_increments_retry_count():
    """Test D: nack increments retry count."""
    print("\n[Test 4] nack increments retry count")
    db = get_test_db()
    queue = MessageQueue(db)

    mid = queue.enqueue(provider="telegram", payload={"test": "nack"})
    msg = queue.dequeue()
    assert msg.retry_count == 0

    result = queue.nack(msg.id, "temporary_error", max_retries=3)
    assert result["status"] == "retry"
    assert result["retry_count"] == 1

    # Message should be back to pending
    assert queue.get_pending_count() == 1

    # Dequeue again and nack
    msg2 = queue.dequeue()
    result2 = queue.nack(msg2.id, "temporary_error_2", max_retries=3)
    assert result2["status"] == "retry"
    assert result2["retry_count"] == 2

    print(f"  PASS: nack incremented retry count correctly")
    cleanup_db(db)
    return True


def test_5_nack_max_retries_moves_to_dlq():
    """Test E: message nacked max_retries times moves to DLQ."""
    print("\n[Test 5] nack max_retries moves message to DLQ")
    db = get_test_db()
    queue = MessageQueue(db)
    dlq = DLQManager(db)

    mid = queue.enqueue(provider="openai", payload={"test": "dlq"}, correlation_key="corr_dlq_001")

    # Nack 3 times (max_retries=3 means 3 total attempts)
    for i in range(3):
        msg = queue.dequeue()
        result = queue.nack(msg.id, f"failure_{i+1}", max_retries=3)
        if i < 2:
            assert result["status"] == "retry"
        else:
            assert result["status"] == "dlq"

    # Message should be in DLQ status in queue table
    retrieved = queue.get_message(mid)
    assert retrieved is not None
    assert retrieved.status == "dlq"

    print(f"  PASS: Message moved to DLQ after max retries")
    cleanup_db(db)
    return True


def test_6_dlq_schema_complete():
    """Test F: DLQ entry schema contains required fields."""
    print("\n[Test 6] DLQ entry schema completeness")
    db = get_test_db()
    dlq = DLQManager(db)

    entry_id = dlq.add_entry(
        provider="telegram",
        correlation_key="corr_schema_test",
        failure_reason="mock_failure_reason",
        original_payload_ref="payload_ref_001",
        payload_snapshot={"attempts": 3, "error": "test"},
    )

    entry = dlq.get_entry(entry_id)
    assert entry is not None
    assert hasattr(entry, "timestamp") and entry.timestamp > 0
    assert entry.provider == "telegram"
    assert entry.correlation_key == "corr_schema_test"
    assert entry.failure_reason == "mock_failure_reason"
    assert entry.original_payload_ref == "payload_ref_001"
    assert entry.payload_snapshot == {"attempts": 3, "error": "test"}

    print(f"  PASS: DLQ schema complete: {entry}")
    cleanup_db(db)
    return True


def test_7_dlq_survives_restart():
    """Test G: DLQ entries survive process restart."""
    print("\n[Test 7] DLQ entries survive process restart")
    db = get_test_db()

    # Phase 1: Create DLQ entries
    dlq1 = DLQManager(db)
    entry_id = dlq1.add_entry(
        provider="openai",
        correlation_key="corr_restart",
        failure_reason="restart_test",
        original_payload_ref="ref_restart",
    )
    count_before = dlq1.get_count()
    assert count_before == 1
    dlq1.close()

    # Phase 2: Simulate restart by creating new instance
    dlq2 = DLQManager(db)
    count_after = dlq2.get_count()
    assert count_after == 1, f"Expected 1 DLQ entry after restart, got {count_after}"

    entry = dlq2.get_entry(entry_id)
    assert entry is not None
    assert entry.provider == "openai"

    print(f"  PASS: DLQ survived restart ({count_after} entries)")
    cleanup_db(db)
    return True


def test_8_pending_recovery_after_restart():
    """Test H: pending un-acked messages recoverable after restart."""
    print("\n[Test 8] Pending message recovery after restart")
    db = get_test_db()

    # Phase 1: Enqueue messages, dequeue one but don't ack
    queue1 = MessageQueue(db)
    mid1 = queue1.enqueue(provider="openai", payload={"msg": 1})
    mid2 = queue1.enqueue(provider="telegram", payload={"msg": 2})

    msg = queue1.dequeue()  # This message is now 'processing'
    assert msg is not None
    assert msg.status == "processing"
    queue1.close()

    # Phase 2: Simulate restart
    queue2 = MessageQueue(db)
    recovered = queue2.recover_pending()
    assert len(recovered) >= 1, f"Expected at least 1 recovered message, got {len(recovered)}"

    # The dequeued (but un-acked) message should be back to pending
    pending_count = queue2.get_pending_count()
    assert pending_count >= 1, f"Expected at least 1 pending after recovery, got {pending_count}"

    print(f"  PASS: Recovered {len(recovered)} pending messages after restart")
    cleanup_db(db)
    return True


def test_9_slice2_terminal_failure_to_dlq_adapter():
    """Test I: Slice 2 terminal failures route to DLQ via adapter."""
    print("\n[Test 9] Slice 2 terminal failure → DLQ adapter")
    db = get_test_db()
    dlq = DLQManager(db)
    adapter = TerminalFailureToDLQAdapter(dlq)

    # Simulate Slice 2 terminal failure
    error = RetryExhaustedError(
        provider="openai",
        attempts=3,
        last_error="Mock OpenAI terminal failure",
    )

    entry_id = adapter.route(error, correlation_key="slice2_test_001")
    assert entry_id is not None

    entry = dlq.get_entry(entry_id)
    assert entry is not None
    assert entry.provider == "openai"
    assert entry.failure_reason == "Mock OpenAI terminal failure"
    assert entry.correlation_key == "slice2_test_001"
    assert entry.original_payload_ref == "slice2_test_001"
    assert entry.payload_snapshot["attempts"] == 3

    # Test with dict (execute_safe output)
    terminal_dict = {
        "status": "terminal_failure",
        "provider": "telegram",
        "attempts": 3,
        "last_error": "Mock Telegram terminal failure",
    }
    entry_id2 = adapter.route_dict(terminal_dict, correlation_key="slice2_test_002")
    entry2 = dlq.get_entry(entry_id2)
    assert entry2.provider == "telegram"
    assert entry2.failure_reason == "Mock Telegram terminal failure"

    print(f"  PASS: Slice 2 terminal failures routed to DLQ successfully")
    cleanup_db(db)
    return True


def test_10_no_idempotency_dedupe_audit_compliance():
    """Test J: No idempotency / dedupe / audit trail / compliance reporting in source."""
    print("\n[Test 10] No forbidden Slice 4 patterns in Slice 3 source")

    source_files = [
        Path(__file__).parent / "queue.py",
        Path(__file__).parent / "dlq.py",
        Path(__file__).parent / "dlq_adapter.py",
    ]

    forbidden = [
        "idempotency_key", "idempotency cache", "dedupe", "deduplication",
        "audit_trail", "audit trail", "compliance_report", "compliance reporting",
    ]

    found = []
    for src_file in source_files:
        lines = src_file.read_text(encoding="utf-8").splitlines()
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue
            # Track docstring state
            if '"""' in stripped or "'''" in stripped:
                # Toggle docstring state
                count_triple = stripped.count('"""') + stripped.count("'''")
                if count_triple % 2 == 1:
                    in_docstring = not in_docstring
                continue
            if in_docstring:
                continue
            lower_line = stripped.lower()
            for pattern in forbidden:
                if pattern.lower() in lower_line:
                    found.append(f"{src_file.name}: {pattern}")

    if found:
        print(f"  FAIL: Found forbidden patterns: {found}")
        return False

    print(f"  PASS: No idempotency / dedupe / audit trail / compliance reporting in Slice 3")
    return True


def test_11_no_real_api_calls():
    """Test K: No real API call patterns in Slice 3 source."""
    print("\n[Test 11] No real API call patterns in source")

    source_files = [
        Path(__file__).parent / "queue.py",
        Path(__file__).parent / "dlq.py",
        Path(__file__).parent / "dlq_adapter.py",
    ]

    forbidden = ["openai.com", "api.openai.com", "telegram.org", "api.telegram.org", "sendMessage", "chat.completions"]
    found = []
    for src_file in source_files:
        content = src_file.read_text(encoding="utf-8")
        for pattern in forbidden:
            if pattern in content:
                found.append(f"{src_file.name}: {pattern}")

    if found:
        print(f"  FAIL: Found forbidden patterns: {found}")
        return False

    print(f"  PASS: No real API call patterns found")
    return True


def main():
    print("=" * 60)
    print("C3 SLICE 3 TEST: SQLite Queue + DLQ + Ack/Nack + Recovery")
    print("=" * 60)

    tests = [
        ("test_1_enqueue_1000_under_5s", test_1_enqueue_1000_under_5s),
        ("test_2_dequeue_ack_1000_under_5s", test_2_dequeue_ack_1000_under_5s),
        ("test_3_ack_removes_from_queue", test_3_ack_removes_from_queue),
        ("test_4_nack_increments_retry_count", test_4_nack_increments_retry_count),
        ("test_5_nack_max_retries_moves_to_dlq", test_5_nack_max_retries_moves_to_dlq),
        ("test_6_dlq_schema_complete", test_6_dlq_schema_complete),
        ("test_7_dlq_survives_restart", test_7_dlq_survives_restart),
        ("test_8_pending_recovery_after_restart", test_8_pending_recovery_after_restart),
        ("test_9_slice2_terminal_failure_to_dlq_adapter", test_9_slice2_terminal_failure_to_dlq_adapter),
        ("test_10_no_idempotency_dedupe_audit_compliance", test_10_no_idempotency_dedupe_audit_compliance),
        ("test_11_no_real_api_calls", test_11_no_real_api_calls),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            results[name] = test_fn()
        except Exception as e:
            print(f"  FAIL: Exception: {e}")
            results[name] = False

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")

    all_pass = all(results.values())
    print("=" * 60)
    print(f"OVERALL: {'ALL PASS' if all_pass else 'SOME FAILED'}")
    print("=" * 60)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
