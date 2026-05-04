"""
Telegram Notifier for Phase 2B Governance Chain

Implements pause notifications only (no recovery authorization):
- Sends Telegram alert when auto-pause is triggered
- Notification contains pause reason, duration, manual action required
- Does NOT grant recovery authorization via Telegram
- Mock mode supported (no actual Telegram API calls)
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("telegram_notifier")


class TelegramNotifier:
    """
    Telegram notifier for Phase 2B pause events.
    Only sends alerts and manual takeover notifications, does NOT grant recovery authorization.
    """
    
    def __init__(self, sender=None, enabled: bool = True, mock_mode: bool = True):
        self.sender = sender
        self.enabled = enabled
        self.mock_mode = mock_mode
        self._log = []
    
    def send_pause_notification(self, pause_reason: str, duration_info: Dict[str, Any] = None, 
                                manual_action_required: str = "Use /start to request manual recovery") -> Dict[str, Any]:
        """
        Send Telegram notification for auto-pause event.
        Only alerts and requests manual action, does NOT authorize recovery.
        
        Args:
            pause_reason: One of REASON_* from PauseStateManager
            duration_info: Dict with duration metrics (stall_duration, failure_count, etc.)
            manual_action_required: Instructions for manual recovery
            
        Returns:
            Dict with success, mock, message, log_index
        """
        if not self.enabled:
            return {"success": True, "skipped": True, "message": "notifier disabled"}
        
        # Build notification message
        reason_display = pause_reason.replace("_", " ").title()
        
        msg = f"⚠️ *Auto-Pause Triggered*\n"
        msg += f"Reason: `{reason_display}`\n"
        
        if duration_info:
            if "stall_duration_seconds" in duration_info:
                duration_min = duration_info["stall_duration_seconds"] / 60.0
                msg += f"Stall Duration: `{duration_min:.1f}` minutes\n"
            if "failure_count" in duration_info:
                msg += f"Failure Count: `{duration_info['failure_count']}`\n"
            if "no_new_commit_minutes" in duration_info:
                msg += f"No New Commit: `{duration_info['no_new_commit_minutes']:.1f}` minutes\n"
            if "no_new_rtc_minutes" in duration_info:
                msg += f"No New RETURN_TO_CHATGPT: `{duration_info['no_new_rtc_minutes']:.1f}` minutes\n"
        
        msg += f"\n🔧 *Manual Action Required*\n{manual_action_required}"
        msg += f"\n\n⚠️ *Note*: Telegram notification does NOT grant recovery authorization."
        
        return self._dispatch(msg)
    
    def send_stall_warning(self, current_duration_seconds: float, threshold_seconds: float = 1800) -> Dict[str, Any]:
        """
        Send warning when approaching stall threshold (optional early warning).
        Does NOT trigger pause, only alerts.
        """
        if not self.enabled:
            return {"success": True, "skipped": True, "message": "notifier disabled"}
        
        progress = (current_duration_seconds / threshold_seconds) * 100
        msg = f"⚡ *Stall Warning*\n"
        msg += f"Current Duration: `{current_duration_seconds/60:.1f}` minutes\n"
        msg += f"Threshold: `{threshold_seconds/60:.1f}` minutes\n"
        msg += f"Progress: `{progress:.1f}%`\n"
        msg += f"\nWill trigger auto-pause when threshold is reached."
        
        return self._dispatch(msg)
    
    def send_failure_warning(self, current_count: int, threshold: int = 3) -> Dict[str, Any]:
        """
        Send warning when approaching failure threshold (optional early warning).
        Does NOT trigger pause, only alerts.
        """
        if not self.enabled:
            return {"success": True, "skipped": True, "message": "notifier disabled"}
        
        msg = f"⚡ *Failure Count Warning*\n"
        msg += f"Current Failures: `{current_count}`\n"
        msg += f"Threshold: `{threshold}`\n"
        msg += f"\nWill trigger auto-pause when threshold is reached."
        
        return self._dispatch(msg)
    
    def _dispatch(self, text: str) -> Dict[str, Any]:
        """Send message via sender or mock mode."""
        if self.mock_mode:
            self._log.append(text)
            logger.info(f"Mock Telegram notification: {text[:100]}...")
            return {"success": True, "mock": True, "message": text, "log_index": len(self._log) - 1}
        
        if self.sender and hasattr(self.sender, "send_message"):
            return self.sender.send_message(text)
        
        return {"success": False, "error": "no sender configured"}
    
    def get_log(self) -> list:
        """Return mock log (for testing/verification)."""
        return list(self._log)
    
    def clear_log(self) -> None:
        """Clear mock log."""
        self._log.clear()
