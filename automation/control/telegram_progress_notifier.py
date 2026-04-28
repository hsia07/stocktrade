"""
Telegram Progress Notifier (Mock Version)

Progress message abstraction layer built on top of TelegramSender.
In mock_mode, does NOT actually send messages; records to internal log.
"""

from typing import List, Dict, Any, Optional


class TelegramProgressNotifier:
    """
    Telegram progress notifier for auto-run construction.

    - mock_mode=True: does NOT call sender.send_message; appends to internal log
    - enabled=False: all methods are no-op
    """

    def __init__(self, sender=None, enabled: bool = True, mock_mode: bool = True):
        self.sender = sender
        self.enabled = enabled
        self.mock_mode = mock_mode
        self._log: List[str] = []

    def _format(self, tag: str, round_id: str, **kwargs) -> str:
        base = f"[AUTO-RUN][{tag}] {round_id}"
        extras = " ".join(f"{k}={v}" for k, v in kwargs.items())
        return f"{base} {extras}".strip()

    def send_start(self, round_id: str) -> Dict[str, Any]:
        if not self.enabled:
            return {"success": True, "skipped": True, "message": "notifier disabled"}
        msg = self._format("START", round_id)
        return self._dispatch(msg)

    def send_progress(self, round_id: str, step: str, status: str) -> Dict[str, Any]:
        if not self.enabled:
            return {"success": True, "skipped": True, "message": "notifier disabled"}
        msg = self._format("PROGRESS", round_id, step=step, status=status)
        return self._dispatch(msg)

    def send_error(self, round_id: str, error: str) -> Dict[str, Any]:
        if not self.enabled:
            return {"success": True, "skipped": True, "message": "notifier disabled"}
        msg = self._format("ERROR", round_id, error=error)
        return self._dispatch(msg)

    def send_complete(self, round_id: str) -> Dict[str, Any]:
        if not self.enabled:
            return {"success": True, "skipped": True, "message": "notifier disabled"}
        msg = self._format("COMPLETE", round_id)
        return self._dispatch(msg)

    def _dispatch(self, text: str) -> Dict[str, Any]:
        if self.mock_mode:
            self._log.append(text)
            return {"success": True, "mock": True, "message": text, "log_index": len(self._log) - 1}
        if self.sender and hasattr(self.sender, "send_message"):
            return self.sender.send_message(text)
        return {"success": False, "error": "no sender configured"}

    def get_log(self) -> List[str]:
        return list(self._log)

    def clear_log(self) -> None:
        self._log.clear()
