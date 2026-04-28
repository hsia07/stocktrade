"""
Telegram Progress Sidecar Adapter

Monitors latest_return_to_chatgpt.txt for changes and converts
changes into TelegramProgressNotifier messages.

This is a sidecar adapter - it does NOT modify the core loop.

Supports:
- Real mode (if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set)
- Mock mode (default if credentials not found)
- Graceful stop via STOP_NOW.flag
"""

import os
import hashlib
import logging
import signal
import time
from pathlib import Path
from typing import Dict, Any, Optional

from automation.control.telegram_progress_notifier import TelegramProgressNotifier


logger = logging.getLogger("telegram_progress_sidecar")

# Stop flag path (same as api_automode_loop.py)
STOP_NOW_FLAG = Path(__file__).parent.parent.parent / "automation" / "control" / "STOP_NOW.flag"


class TelegramProgressSidecar:
    """
    Sidecar adapter that monitors RETURN_TO_CHATGPT report file changes
    and sends progress notifications.

    Supports:
    - Real mode (if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set)
    - Mock mode (default if credentials not found)
    - Graceful stop via STOP_NOW.flag
    """

    def __init__(
        self,
        report_path: str = "automation/control/latest_return_to_chatgpt.txt",
        notifier: Optional[TelegramProgressNotifier] = None,
        enabled: bool = True,
        mock_mode: bool = True
    ):
        self.report_path = Path(report_path)
        self.notifier = notifier or TelegramProgressNotifier(enabled=enabled, mock_mode=mock_mode)
        self.enabled = enabled
        self.mock_mode = mock_mode
        self._last_hash: Optional[str] = None
        self._notified_reply_ids: set = set()
        self._last_state: Dict[str, Any] = {}
        self._running = False
        self._stop_requested = False

        # Setup signal handlers for graceful stop
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            logger.info("Signal handlers registered for SIGINT and SIGTERM")
        except Exception as e:
            logger.warning(f"Failed to register signal handlers: {e}")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        sig_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        logger.info(f"Received {sig_name}, requesting graceful shutdown...")
        self._stop_requested = True

    def _check_stop_now(self) -> bool:
        """Check if STOP_NOW.flag exists."""
        return STOP_NOW_FLAG.exists()

    def _detect_mode(self) -> dict:
        """
        Detect Telegram credentials and return config.
        Returns dict with:
        - mode: 'real' or 'mock'
        - bot_token_present: bool
        - chat_id_present: bool
        """
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        
        config = {
            "mode": "mock",
            "bot_token_present": bool(bot_token),
            "chat_id_present": bool(chat_id),
        }
        
        if bot_token and chat_id:
            config["mode"] = "real"
            logger.info("Telegram credentials found - entering REAL mode")
            logger.info(f"BotToken present: YES (length: {len(bot_token)})")
            logger.info(f"ChatId present: YES")
            # IMPORTANT: Never print actual token to log!
        else:
            logger.info("Telegram credentials NOT found - entering MOCK/LOG mode")
        
        return config

    def run(self, check_interval: float = 2.0):
        """
        Main monitoring loop. Checks for report changes periodically.
        Exits gracefully when stop requested or STOP_NOW.flag is set.
        """
        self._running = True
        self._stop_requested = False
        logger.info(f"Telegram Progress Sidecar started (mode={self.mock_mode})")
        logger.info(f"Monitoring: {self.report_path}")
        logger.info(f"Check interval: {check_interval}s")

        while self._running and not self._stop_requested:
            # Check STOP_NOW.flag
            if self._check_stop_now():
                logger.info("STOP_NOW.flag detected, stopping...")
                break

            try:
                result = self.check_and_notify()
                if result.get("checked"):
                    if result.get("changed"):
                        logger.info(f"Change detected: {result.get('reason', '')}")
                        if result.get("notified"):
                            logger.info(f"Notification sent for round_id={result.get('round_id', '')}")
                else:
                    logger.warning(f"Check failed: {result.get('reason', '')}")
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

            # Sleep with periodic stop checks
            for _ in range(int(check_interval / 0.5)):
                if self._stop_requested or self._check_stop_now():
                    break
                time.sleep(0.5)

        logger.info("Telegram Progress Sidecar stopped")
        self._running = False

    def _compute_hash(self, content: str) -> str:
        """Compute hash of file content for change detection."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _parse_report(self, content: str) -> Dict[str, Any]:
        """
        Parse RETURN_TO_CHATGPT report to extract:
        - round_id
        - status
        - formal_status_code
        - reply_id
        """
        state = {
            "round_id": "unknown",
            "status": "unknown",
            "formal_status_code": "unknown",
            "reply_id": "",
            "raw_content": content
        }
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("round_id:"):
                state["round_id"] = line.split(":", 1)[1].strip()
            elif line.startswith("status:"):
                state["status"] = line.split(":", 1)[1].strip()
            elif line.startswith("formal_status_code:"):
                state["formal_status_code"] = line.split(":", 1)[1].strip()
            elif line.startswith("reply_id:"):
                state["reply_id"] = line.split(":", 1)[1].strip()
        return state

    def check_and_notify(self) -> Dict[str, Any]:
        """
        Check if report file has changed and send notifications if needed.

        Returns dict with:
        - checked: bool
        - changed: bool
        - notified: bool
        - reason: str
        """
        if not self.enabled:
            return {"checked": True, "changed": False, "notified": False, "reason": "sidecar disabled"}

        if not self.report_path.exists():
            logger.debug(f"Report file not found: {self.report_path}")
            return {"checked": True, "changed": False, "notified": False, "reason": "file not found"}

        try:
            content = self.report_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read report file: {e}")
            return {"checked": True, "changed": False, "notified": False, "reason": f"read error: {e}"}

        content_hash = self._compute_hash(content)

        if content_hash == self._last_hash:
            return {"checked": True, "changed": False, "notified": False, "reason": "no change"}

        self._last_hash = content_hash
        state = self._parse_report(content)
        self._last_state = state

        reply_id = state.get("reply_id", "")
        if reply_id and reply_id in self._notified_reply_ids:
            return {"checked": True, "changed": True, "notified": False, "reason": f"duplicate reply_id: {reply_id}"}

        if reply_id:
            self._notified_reply_ids.add(reply_id)

        round_id = state.get("round_id", "unknown")
        status = state.get("status", "unknown")
        formal_code = state.get("formal_status_code", "unknown")

        # Event type mapping based on formal_status_code and status
        # START: formal_status_code contains 'start'/'begin'/'init'
        # PROGRESS: formal_status_code contains 'progress'/'running' or status is 'in_progress'
        # COMPLETE: status == 'completed'
        # ERROR: status == 'failed'/'paused'/'stopped'
        formal_lower = formal_code.lower()

        if status == "completed":
            result = self.notifier.send_complete(round_id)
        elif status == "failed":
            result = self.notifier.send_error(round_id, error=f"status={status}, formal={formal_code}")
        elif status in ("paused", "stopped"):
            result = self.notifier.send_error(round_id, error=f"status={status}, formal={formal_code}")
        elif any(kw in formal_lower for kw in ["start", "begin", "init", "commence"]):
            # START event: explicitly use send_start
            result = self.notifier.send_start(round_id)
        else:
            # PROGRESS event: use send_progress with step info
            result = self.notifier.send_progress(round_id, step="report_update", status=status)

        return {
            "checked": True,
            "changed": True,
            "notified": True,
            "round_id": round_id,
            "status": status,
            "reply_id": reply_id,
            "notify_result": result
        }

    def get_notified_reply_ids(self) -> set:
        """Return set of already-notified reply_ids (for testing)."""
        return self._notified_reply_ids.copy()

    def clear_dedup_cache(self) -> None:
        """Clear deduplication cache (for testing)."""
        self._notified_reply_ids.clear()
