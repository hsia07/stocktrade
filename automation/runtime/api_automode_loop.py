"""
PHASE2 API Automode - C3 Slice 1: Unified Runtime Loop Skeleton

This is a MOCK runtime loop skeleton for the OpenAI + Telegram dual-provider
orchestration system. It contains NO real OpenAI or Telegram API calls.

Slice 1 Acceptance Criteria:
1. Loop runs for >= 60s without crash
2. STOP_NOW.flag causes clean exit within <= 5s
3. No OpenAI/Telegram calls in this slice (mock only)
"""

import os
import sys
import time
import json
import signal
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

# Slice 3 integration: queue available for future message-driven processing
# (imported but not activated in Slice 1/2 loop to preserve core semantics)
try:
    from automation.runtime.queue import MessageQueue
    from automation.runtime.dlq import DLQManager
except ImportError:
    MessageQueue = None
    DLQManager = None

# Slice 4 integration: idempotency and audit trail available for exactly-once
# semantics and message lineage (not activated in mock loop)
try:
    from automation.runtime.idempotency import IdempotencyManager
    from automation.runtime.audit_trail import AuditTrailManager
except ImportError:
    IdempotencyManager = None
    AuditTrailManager = None

# Candidate-pass auto-advance control integration (minimal)
# Available for round orchestration; not activated in idle mock loop
try:
    from automation.control.pause_state import PauseStateManager
    from automation.control.auto_advance import AutoAdvanceController
    from automation.control.status_reporter import StatusReporter
except ImportError:
    PauseStateManager = None
    AutoAdvanceController = None
    StatusReporter = None

# Configuration
REPO_ROOT = Path(__file__).parent.parent.parent
STOP_NOW_FLAG = REPO_ROOT / "automation" / "control" / "STOP_NOW.flag"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
TICK_INTERVAL = 2.0  # seconds between loop ticks
STOP_CHECK_INTERVAL = 0.5  # seconds between STOP_NOW checks during shutdown

# Setup logging
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("api_automode_loop")


class AutomodeRuntimeLoop:
    """Mock unified runtime loop skeleton for dual-provider orchestration."""

    def __init__(self):
        self._running = False
        self._shutdown_requested = False
        self._tick_count = 0
        self._start_time: Optional[float] = None
        self._stop_time: Optional[float] = None
        self._metrics: Dict[str, Any] = {
            "ticks": 0,
            "mock_work_items": 0,
            "mock_dispatches": 0,
            "errors": 0,
            "start_time": None,
            "stop_time": None,
        }
        # Slice 3: queue and DLQ available for integration in later slices
        self._queue = MessageQueue() if MessageQueue else None
        self._dlq = DLQManager() if DLQManager else None
        # Slice 4: idempotency and audit trail available for exactly-once semantics
        self._idempotency = IdempotencyManager() if IdempotencyManager else None
        self._audit_trail = AuditTrailManager() if AuditTrailManager else None
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Register SIGINT and SIGTERM for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        logger.info("Signal handlers registered for SIGINT and SIGTERM")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        sig_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        logger.info(f"Received {sig_name}, requesting graceful shutdown...")
        self._shutdown_requested = True

    def _check_stop_now(self) -> bool:
        """Check if STOP_NOW.flag exists."""
        return STOP_NOW_FLAG.exists()

    def _check_pause(self) -> bool:
        """Check if PAUSE.flag exists (candidate-pass auto-advance control)."""
        if PauseStateManager:
            paused = PauseStateManager(REPO_ROOT).is_paused()
            if paused:
                logger.info("PAUSE.flag detected (auto-advance control)")
            return paused
        return False

    def _log_control_state(self):
        """Log auto-advance control layer status."""
        if PauseStateManager and AutoAdvanceController and StatusReporter:
            logger.info("Auto-advance control layer: ACTIVE")
            logger.info("Pause state: %s", "PAUSED" if self._check_pause() else "RUNNING")
        else:
            logger.debug("Auto-advance control layer: not loaded")

    def _mock_generate_work_item(self) -> Optional[Dict[str, Any]]:
        """Mock: Generate a work item (NO OpenAI call)."""
        self._tick_count += 1
        work_item = {
            "tick": self._tick_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": "mock_openai",
            "status": "mock_generated",
            "content_hash": f"mock_hash_{self._tick_count}",
        }
        logger.debug(f"Mock work item generated: tick={self._tick_count}")
        return work_item

    def _mock_dispatch(self, work_item: Dict[str, Any]) -> bool:
        """Mock: Dispatch work item (NO Telegram call)."""
        logger.debug(
            f"Mock dispatch: tick={work_item['tick']}, provider=mock_telegram"
        )
        return True

    def _process_tick(self):
        """Process one loop tick."""
        try:
            # Check STOP_NOW before processing
            if self._check_stop_now():
                logger.info("STOP_NOW.flag detected, initiating clean shutdown")
                self._shutdown_requested = True
                return

            # Mock work generation
            work_item = self._mock_generate_work_item()
            if work_item:
                self._metrics["mock_work_items"] += 1

                # Mock dispatch
                success = self._mock_dispatch(work_item)
                if success:
                    self._metrics["mock_dispatches"] += 1

            self._metrics["ticks"] = self._tick_count

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Error in tick {self._tick_count}: {e}")

    def start(self):
        """Start the runtime loop."""
        self._start_time = time.time()
        self._running = True
        self._metrics["start_time"] = datetime.now(timezone.utc).isoformat()

        logger.info("=" * 60)
        logger.info("API AUTOMODE RUNTIME LOOP - SLICE 1 (MOCK)")
        logger.info("=" * 60)
        logger.info(f"STOP_NOW flag path: {STOP_NOW_FLAG}")
        logger.info(f"Tick interval: {TICK_INTERVAL}s")
        logger.info("NO REAL OpenAI/Telegram calls in this slice")
        logger.info("=" * 60)
        self._log_control_state()
        logger.info("=" * 60)
        logger.info("Loop started")

        try:
            while self._running and not self._shutdown_requested:
                self._process_tick()

                if self._shutdown_requested:
                    break

                # Sleep with periodic STOP_NOW checks
                slept = 0.0
                while slept < TICK_INTERVAL and not self._shutdown_requested:
                    time.sleep(STOP_CHECK_INTERVAL)
                    slept += STOP_CHECK_INTERVAL
                    if self._check_stop_now():
                        logger.info("STOP_NOW.flag detected during sleep")
                        self._shutdown_requested = True
                        break

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received")
            self._shutdown_requested = True

        finally:
            self._shutdown()

    def _shutdown(self):
        """Perform graceful shutdown."""
        self._running = False
        self._stop_time = time.time()
        self._metrics["stop_time"] = datetime.now(timezone.utc).isoformat()

        runtime = 0.0
        if self._start_time:
            runtime = self._stop_time - self._start_time

        logger.info("=" * 60)
        logger.info("SHUTDOWN COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total runtime: {runtime:.2f}s")
        logger.info(f"Total ticks: {self._tick_count}")
        logger.info(f"Mock work items: {self._metrics['mock_work_items']}")
        logger.info(f"Mock dispatches: {self._metrics['mock_dispatches']}")
        logger.info(f"Errors: {self._metrics['errors']}")
        logger.info("=" * 60)

        # Write metrics to file for test verification
        metrics_file = REPO_ROOT / "automation" / "runtime" / "slice1_metrics.json"
        try:
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(self._metrics, f, indent=2)
            logger.info(f"Metrics written to {metrics_file}")
        except Exception as e:
            logger.error(f"Failed to write metrics: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Return current metrics."""
        return self._metrics.copy()


def main():
    """Entry point for the runtime loop."""
    loop = AutomodeRuntimeLoop()
    loop.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
