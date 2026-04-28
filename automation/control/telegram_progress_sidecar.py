"""
Telegram Progress Sidecar Adapter (Mock Version)

Monitors latest_return_to_chatgpt.txt for changes and converts
changes into TelegramProgressNotifier mock messages.

This is a sidecar adapter - it does NOT modify the core loop.
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from automation.control.telegram_progress_notifier import TelegramProgressNotifier


logger = logging.getLogger("telegram_progress_sidecar")


class TelegramProgressSidecar:
    """
    Sidecar adapter that monitors RETURN_TO_CHATGPT report file changes
    and sends mock progress notifications.
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

        if status == "completed":
            result = self.notifier.send_complete(round_id)
        elif status == "failed":
            result = self.notifier.send_error(round_id, error=f"status={status}, formal={formal_code}")
        elif status in ("paused", "stopped"):
            result = self.notifier.send_error(round_id, error=f"status={status}, formal={formal_code}")
        else:
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
