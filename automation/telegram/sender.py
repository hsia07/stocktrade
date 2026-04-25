"""
Telegram Sender

Minimal Telegram API sender for status reporting.
Only sends status messages; no business logic messages.
Credentials from environment (never stored in files).
"""

import os
import logging
from typing import Optional, Dict, Any

try:
    import urllib.request
    import urllib.error
    import json
except ImportError:
    urllib = None  # type: ignore

logger = logging.getLogger("telegram_sender")


class TelegramSender:
    """Send formatted status messages to Telegram."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
        self.base_url = "https://api.telegram.org/bot{token}"

    def is_configured(self) -> bool:
        """Check if both token and chat_id are present."""
        return bool(self.bot_token) and bool(self.chat_id)

    def send_message(self, text: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
        """
        Send a message to the configured chat.

        Returns dict with:
        - success: bool
        - message_id: int or None
        - error: str or None
        - http_status: int or None
        """
        if not self.is_configured():
            logger.warning("Telegram not configured; skipping send")
            return {"success": False, "message_id": None, "error": "not_configured", "http_status": None}

        if not urllib:
            logger.error("urllib not available; cannot send Telegram message")
            return {"success": False, "message_id": None, "error": "urllib_unavailable", "http_status": None}

        url = f"{self.base_url.format(token=self.bot_token)}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                result = json.loads(body)
                if result.get("ok"):
                    msg_id = result.get("result", {}).get("message_id")
                    logger.info(f"Telegram message sent: message_id={msg_id}")
                    return {"success": True, "message_id": msg_id, "error": None, "http_status": resp.status}
                else:
                    error_desc = result.get("description", "unknown")
                    logger.error(f"Telegram API error: {error_desc}")
                    return {"success": False, "message_id": None, "error": error_desc, "http_status": resp.status}
        except urllib.error.HTTPError as e:
            logger.error(f"Telegram HTTP error: {e.code} {e.reason}")
            return {"success": False, "message_id": None, "error": f"HTTP {e.code}", "http_status": e.code}
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return {"success": False, "message_id": None, "error": str(e), "http_status": None}

    def send_status(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convenience: send a status summary dict.
        summary must contain 'formatted_text' key or will be skipped.
        """
        text = summary.get("formatted_text", "")
        if not text:
            logger.debug("No formatted_text in summary; skipping send")
            return {"success": False, "message_id": None, "error": "no_formatted_text", "http_status": None}
        return self.send_message(text)
