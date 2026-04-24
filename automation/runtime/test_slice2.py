"""
C3 Slice 2 Test: Retry with Exponential Backoff

Tests:
A. OpenAI mock fail 2x then success (cumulative backoff >= 3s)
B. Telegram mock fail 2x then success (cumulative backoff >= 3s)
C. OpenAI mock fail 3x then terminal failure result
D. Telegram mock fail 3x then terminal failure result
E. max_retries configurable
F. base_delay_seconds configurable
G. optional jitter policy
H. No real API calls
I. No durable queue / DLQ / idempotency / audit trail
"""

import sys
import time
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.runtime.retry import (
    ExponentialBackoffRetry,
    RetryConfig,
    RetryExhaustedError,
)


def test_1_openai_mock_fail_twice_then_success():
    """Test A: OpenAI mock fails 2x, succeeds on 3rd. Cumulative backoff >= 3s."""
    print("\n[Test 1] OpenAI mock fail 2x then success")
    call_count = [0]

    def mock_openai():
        call_count[0] += 1
        if call_count[0] <= 2:
            raise Exception(f"OpenAI mock error #{call_count[0]}")
        return "openai_success"

    config = RetryConfig(max_retries=3, base_delay_seconds=1.0, jitter=False)
    retry = ExponentialBackoffRetry(config)

    start = time.time()
    result = retry.execute(mock_openai, provider="openai")
    elapsed = time.time() - start

    assert result["status"] == "success", f"Expected success, got {result}"
    assert result["result"] == "openai_success"
    assert result["attempts"] == 3, f"Expected 3 attempts, got {result['attempts']}"
    assert call_count[0] == 3

    # Backoff: attempt 0 delay = 1s, attempt 1 delay = 2s, total >= 3s
    assert elapsed >= 3.0, f"Expected >= 3s backoff, got {elapsed:.2f}s"

    print(f"  PASS: Success after 3 attempts, backoff = {elapsed:.2f}s")
    return True


def test_2_telegram_mock_fail_twice_then_success():
    """Test B: Telegram mock fails 2x, succeeds on 3rd. Cumulative backoff >= 3s."""
    print("\n[Test 2] Telegram mock fail 2x then success")
    call_count = [0]

    def mock_telegram():
        call_count[0] += 1
        if call_count[0] <= 2:
            raise Exception(f"Telegram mock error #{call_count[0]}")
        return "telegram_success"

    config = RetryConfig(max_retries=3, base_delay_seconds=1.0, jitter=False)
    retry = ExponentialBackoffRetry(config)

    start = time.time()
    result = retry.execute(mock_telegram, provider="telegram")
    elapsed = time.time() - start

    assert result["status"] == "success"
    assert result["result"] == "telegram_success"
    assert result["attempts"] == 3
    assert elapsed >= 3.0, f"Expected >= 3s backoff, got {elapsed:.2f}s"

    print(f"  PASS: Success after 3 attempts, backoff = {elapsed:.2f}s")
    return True


def test_3_openai_terminal_failure():
    """Test C: OpenAI mock fails 3x, returns terminal failure result."""
    print("\n[Test 3] OpenAI terminal failure after 3 failures")
    call_count = [0]

    def mock_openai():
        call_count[0] += 1
        raise Exception(f"OpenAI terminal error #{call_count[0]}")

    config = RetryConfig(max_retries=3, base_delay_seconds=0.5, jitter=False)
    retry = ExponentialBackoffRetry(config)

    try:
        retry.execute(mock_openai, provider="openai")
        print("  FAIL: Should have raised RetryExhaustedError")
        return False
    except RetryExhaustedError as e:
        assert e.provider == "openai"
        assert e.attempts == 4  # initial + 3 retries
        error_dict = e.to_dict()
        assert error_dict["status"] == "terminal_failure"
        assert error_dict["provider"] == "openai"
        assert error_dict["attempts"] == 4
        assert "OpenAI terminal error #4" in error_dict["last_error"]
        print(f"  PASS: Terminal failure raised correctly: {error_dict}")
        return True


def test_4_telegram_terminal_failure():
    """Test D: Telegram mock fails 3x, returns terminal failure result."""
    print("\n[Test 4] Telegram terminal failure after 3 failures")
    call_count = [0]

    def mock_telegram():
        call_count[0] += 1
        raise Exception(f"Telegram terminal error #{call_count[0]}")

    config = RetryConfig(max_retries=3, base_delay_seconds=0.5, jitter=False)
    retry = ExponentialBackoffRetry(config)

    # Test execute_safe which returns dict instead of raising
    result = retry.execute_safe(mock_telegram, provider="telegram")

    assert result["status"] == "terminal_failure"
    assert result["provider"] == "telegram"
    assert result["attempts"] == 4
    assert "Telegram terminal error #4" in result["last_error"]
    print(f"  PASS: Terminal failure dict returned correctly: {result}")
    return True


def test_5_configurable_max_retries():
    """Test E: max_retries configurable (default 3, min 1, max 10)."""
    print("\n[Test 5] Configurable max_retries")

    # Default
    config = RetryConfig()
    assert config.max_retries == 3

    # Custom
    config = RetryConfig(max_retries=1)
    assert config.max_retries == 1

    config = RetryConfig(max_retries=10)
    assert config.max_retries == 10

    # Boundary
    try:
        RetryConfig(max_retries=0)
        print("  FAIL: Should have raised ValueError for max_retries=0")
        return False
    except ValueError:
        pass

    try:
        RetryConfig(max_retries=11)
        print("  FAIL: Should have raised ValueError for max_retries=11")
        return False
    except ValueError:
        pass

    print("  PASS: max_retries configurable and validated")
    return True


def test_6_configurable_base_delay():
    """Test F: base_delay_seconds configurable (default 1.0)."""
    print("\n[Test 6] Configurable base_delay_seconds")

    config = RetryConfig()
    assert config.base_delay_seconds == 1.0

    config = RetryConfig(base_delay_seconds=2.0)
    assert config.base_delay_seconds == 2.0

    try:
        RetryConfig(base_delay_seconds=0.1)
        print("  FAIL: Should have raised ValueError for base_delay=0.1")
        return False
    except ValueError:
        pass

    try:
        RetryConfig(base_delay_seconds=61.0)
        print("  FAIL: Should have raised ValueError for base_delay=61.0")
        return False
    except ValueError:
        pass

    print("  PASS: base_delay_seconds configurable and validated")
    return True


def test_7_jitter_policy():
    """Test G: Optional jitter policy."""
    print("\n[Test 7] Optional jitter policy")

    config = RetryConfig(jitter=True, jitter_factor=0.5)
    retry = ExponentialBackoffRetry(config)

    # Measure multiple delays to show variance
    delays = []
    for attempt in range(5):
        delay = retry._calculate_delay(attempt)
        delays.append(delay)

    base_delay = 1.0 * (2 ** 0)  # For attempt 0, base = 1.0
    # With jitter_factor 0.5, delay should be in [0.5, 1.5]
    assert 0.5 <= delays[0] <= 1.5, f"Jittered delay out of range: {delays[0]}"

    print(f"  PASS: Jitter delays: {[f'{d:.2f}' for d in delays[:3]]}...")
    return True


def test_8_no_real_api_calls():
    """Test H: No real API call patterns in retry.py source."""
    print("\n[Test 8] No real API call patterns in source")

    import os

    source_path = Path(__file__).parent / "retry.py"
    source = source_path.read_text(encoding="utf-8")

    forbidden = ["openai.com", "api.openai.com", "telegram.org", "api.telegram.org", "sendMessage", "chat.completions"]
    found = [f for f in forbidden if f in source]

    if found:
        print(f"  FAIL: Found forbidden patterns: {found}")
        return False

    print("  PASS: No real API call patterns found")
    return True


def test_9_no_durable_queue():
    """Test I: No durable queue / DLQ / idempotency / audit trail implementation."""
    print("\n[Test 9] No durable queue / DLQ / idempotency / audit trail")

    source_path = Path(__file__).parent / "retry.py"
    source_lines = source_path.read_text(encoding="utf-8").splitlines()

    # Only check code lines (not comments/docstrings)
    import re
    code_lines = []
    for line in source_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
            code_lines.append(stripped)

    # Check for actual implementation patterns (not docstring mentions)
    forbidden_implementations = [
        "import sqlite3", "import redis", "sqlite3.connect", "redis.Redis",
        "class DLQ", "def dlq", "dead_letter_queue", "idempotency_key",
        "dedupe", "audit_log_file", "queue.put", "queue.get"
    ]

    found = []
    for pattern in forbidden_implementations:
        for line in code_lines:
            if pattern.lower() in line.lower():
                found.append(pattern)
                break

    if found:
        print(f"  FAIL: Found forbidden implementation patterns: {found}")
        return False

    print("  PASS: No durable queue / DLQ / idempotency / audit trail implementation")
    return True


def main():
    print("=" * 60)
    print("C3 SLICE 2 TEST: Retry with Exponential Backoff")
    print("=" * 60)

    tests = [
        ("test_1_openai_mock_fail_twice_then_success", test_1_openai_mock_fail_twice_then_success),
        ("test_2_telegram_mock_fail_twice_then_success", test_2_telegram_mock_fail_twice_then_success),
        ("test_3_openai_terminal_failure", test_3_openai_terminal_failure),
        ("test_4_telegram_terminal_failure", test_4_telegram_terminal_failure),
        ("test_5_configurable_max_retries", test_5_configurable_max_retries),
        ("test_6_configurable_base_delay", test_6_configurable_base_delay),
        ("test_7_jitter_policy", test_7_jitter_policy),
        ("test_8_no_real_api_calls", test_8_no_real_api_calls),
        ("test_9_no_durable_queue", test_9_no_durable_queue),
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
