"""
C3 Slice 1 Test: Unified Runtime Loop Skeleton Verification

Tests:
1. Loop runs for >= 60s without crash
2. STOP_NOW.flag causes clean exit within <= 5s
3. No OpenAI/Telegram API calls made
"""

import subprocess
import sys
import time
import os
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
STOP_NOW_FLAG = REPO_ROOT / "automation" / "control" / "STOP_NOW.flag"
METRICS_FILE = REPO_ROOT / "automation" / "runtime" / "slice1_metrics.json"
LOOP_SCRIPT = REPO_ROOT / "automation" / "runtime" / "api_automode_loop.py"

def cleanup():
    """Remove STOP_NOW.flag and metrics file."""
    if STOP_NOW_FLAG.exists():
        STOP_NOW_FLAG.unlink()
    if METRICS_FILE.exists():
        METRICS_FILE.unlink()

def test_1_loop_runs_60s():
    """Test: Loop runs for >= 60s without crash."""
    print("\n[Test 1] Loop runs for >= 60s without crash")
    cleanup()

    proc = subprocess.Popen(
        [sys.executable, str(LOOP_SCRIPT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(REPO_ROOT),
    )

    print(f"  Started loop (PID: {proc.pid})")
    print(f"  Waiting 65s...")

    try:
        proc.wait(timeout=65)
        print(f"  ERROR: Loop exited early with code {proc.returncode}")
        return False
    except subprocess.TimeoutExpired:
        print(f"  Loop still running after 65s (expected)")

    # Clean up
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    stdout, stderr = proc.stdout.read(), proc.stderr.read()
    if "error" in stderr.lower() and "mock" not in stderr.lower():
        print(f"  ERROR: Unexpected error in stderr: {stderr}")
        return False

    print("  PASS: Loop ran for >= 60s without crash")
    return True

def test_2_stop_now_exit_5s():
    """Test: STOP_NOW.flag causes clean exit within <= 5s."""
    print("\n[Test 2] STOP_NOW.flag causes clean exit within <= 5s")
    cleanup()

    proc = subprocess.Popen(
        [sys.executable, str(LOOP_SCRIPT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(REPO_ROOT),
    )

    print(f"  Started loop (PID: {proc.pid})")
    print(f"  Waiting 3s for loop to settle...")
    time.sleep(3)

    print(f"  Creating STOP_NOW.flag...")
    start_time = time.time()
    STOP_NOW_FLAG.write_text("stop", encoding="utf-8")

    try:
        proc.wait(timeout=10)
        elapsed = time.time() - start_time
        print(f"  Loop exited in {elapsed:.2f}s")

        if elapsed <= 5.0:
            print("  PASS: Exit within 5s")
            return True
        else:
            print(f"  FAIL: Exit took {elapsed:.2f}s > 5s")
            return False
    except subprocess.TimeoutExpired:
        print("  FAIL: Loop did not exit within 10s")
        proc.kill()
        proc.wait()
        return False
    finally:
        cleanup()

def test_3_no_real_api_calls():
    """Test: Verify no real OpenAI/Telegram API calls in code."""
    print("\n[Test 3] No real OpenAI/Telegram API calls in slice")

    source = LOOP_SCRIPT.read_text(encoding="utf-8")

    forbidden_patterns = [
        "openai.com",
        "api.openai.com",
        "telegram.org",
        "api.telegram.org",
        "sendMessage",
        "chat.completions",
        "openai.ChatCompletion",
        "bot.send",
    ]

    found = []
    for pattern in forbidden_patterns:
        if pattern in source:
            found.append(pattern)

    if found:
        print(f"  FAIL: Found forbidden patterns: {found}")
        return False

    print("  PASS: No real API call patterns found")
    return True

def main():
    print("=" * 60)
    print("C3 SLICE 1 TEST: Unified Runtime Loop Skeleton")
    print("=" * 60)

    results = {
        "test_1_loop_60s": test_1_loop_runs_60s(),
        "test_2_stop_now_5s": test_2_stop_now_exit_5s(),
        "test_3_no_api_calls": test_3_no_real_api_calls(),
    }

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
