"""
Telegram Notifier for Phase 2B Governance Chain

Implements pause notifications only (no recovery authorization):
- Sends Telegram alert when auto-pause is triggered
- Notification contains pause reason, duration, manual action required
- Does NOT grant recovery authorization via Telegram
- Mock mode supported (no actual Telegram API calls)
- Phase 2B: dedup/rate-limit/fingerprint to prevent notification spam
- Phase 2B: dedup failure does NOT block pause (fail-closed)
"""

import logging
import time
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("telegram_notifier")


class TelegramNotifier:
    """
    Telegram notifier for Phase 2B pause events.
    Only sends alerts and manual takeover notifications, does NOT grant recovery authorization.
    Phase 2B: includes dedup/fingerprint to prevent duplicate spam.
    """
    
    # Dedup window: same fingerprint within this window (seconds) is suppressed
    DEDUP_WINDOW_SECONDS = 300  # 5 minutes
    # Max dedup entries to track (LRU-like)
    MAX_DEDUP_ENTRIES = 20
    
    def __init__(self, sender=None, enabled: bool = True, mock_mode: bool = True):
        self.sender = sender
        self.enabled = enabled
        self.mock_mode = mock_mode
        self._log = []
        # Dedup state: {fingerprint: timestamp}
        self._dedup_history: Dict[str, float] = {}
    
    def send_pause_notification(self, pause_reason: str, duration_info: Dict[str, Any] = None, 
                                manual_action_required: str = "Use /start to request manual recovery",
                                sub_reason: str = "") -> Dict[str, Any]:
        """
        Send Telegram notification for auto-pause event.
        Only alerts and requests manual action, does NOT authorize recovery.
        Phase 2B: dedup via fingerprint (reason + sub_reason).
        
        Args:
            pause_reason: One of REASON_* from PauseStateManager
            duration_info: Dict with duration metrics (stall_duration, failure_count, etc.)
            manual_action_required: Instructions for manual recovery
            sub_reason: Optional sub-category for usage exhaustion
            
        Returns:
            Dict with success, mock, message, log_index
        """
        if not self.enabled:
            return {"success": True, "skipped": True, "message": "notifier disabled"}
        
        # Dedup check (fail-closed: dedup failure does NOT block pause)
        try:
            extra = str(duration_info or "")
            fingerprint = self._make_fingerprint(pause_reason, sub_reason, extra)
            if self._is_duplicate(fingerprint):
                return {"success": True, "dedup": True, "message": "duplicate suppressed"}
        except Exception as e:
            logger.warning(f"Dedup check failed (non-blocking): {e}")
        
        # Build notification message
        reason_display = pause_reason.replace("_", " ").title()
        
        msg = f"⚠️ *Auto-Pause Triggered*\n"
        msg += f"Reason: `{reason_display}`\n"
        if sub_reason:
            msg += f"Sub-Reason: `{sub_reason}`\n"
        
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
        msg += f"\n⚠️ *Manual /start required*: resume requires `/start` + pre-resume checks."
        
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
    
    def send_usage_exhausted_notification(self, sub_reason: str = "", extra: str = "") -> Dict[str, Any]:
        """
        Send notification when task budget / API usage is exhausted.
        Phase 2B: includes sub_reason in notification and dedup fingerprint.
        """
        if not self.enabled:
            return {"success": True, "skipped": True, "message": "notifier disabled"}
        
        # Dedup check (fail-closed: dedup failure does NOT block pause)
        try:
            fingerprint = self._make_fingerprint("usage_exhausted", sub_reason, extra)
            if self._is_duplicate(fingerprint):
                return {"success": True, "dedup": True, "message": "duplicate suppressed"}
        except Exception as e:
            logger.warning(f"Dedup check failed (non-blocking): {e}")
        
        reason_line = f"Category: `{sub_reason}`\n" if sub_reason else ""
        msg = (
            "\u26a0\ufe0f *Usage Exhausted*\n"
            f"\n{reason_line}"
            "Task budget or API usage limit reached.\n"
            "Auto-advance is paused until the budget resets or override is granted.\n"
            "\n"
            "*Prohibited:* auto-retry, auto-model-switch, auto-key-switch, auto-continue.\n"
            "\n"
            "🔧 *Manual Action Required:*\n"
            "1. Resolve the usage issue (recharge, quota reset, model restore).\n"
            "2. Use `/start` to request manual recovery.\n"
            "3. Pre-resume checks will validate readiness before resume."
        )
        return self._dispatch(msg)

    def send_blocked_notification(self, reason: str = "") -> Dict[str, Any]:
        """
        Send notification when auto-advance is blocked.
        """
        if not self.enabled:
            return {"success": True, "skipped": True, "message": "notifier disabled"}
        msg = "\u26d4 *Blocked*\n\nAuto-advance cannot proceed."
        if reason:
            msg += f"\nReason: {reason}"
        return self._dispatch(msg)

    def send_awaiting_instruction_notification(self) -> Dict[str, Any]:
        """
        Send notification when system awaits a manual instruction.
        """
        if not self.enabled:
            return {"success": True, "skipped": True, "message": "notifier disabled"}
        msg = (
            "\u23f3 *Awaiting Instruction*\n"
            "\n"
            "The system is waiting for a manual decision before it can proceed."
        )
        return self._dispatch(msg)

    def send_undefined_round_blocked_notification(self) -> Dict[str, Any]:
        """
        Send notification when an undefined round blocks auto-advance.
        """
        if not self.enabled:
            return {"success": True, "skipped": True, "message": "notifier disabled"}
        msg = (
            "\U0001f6ab *Undefined Round Blocked*\n"
            "\n"
            "An undefined-round condition has blocked auto-advance.\n"
            "Manual review and resolution required before proceeding."
        )
        return self._dispatch(msg)

    def _make_fingerprint(self, reason: str, sub_reason: str = "", extra: str = "") -> str:
        """Create a deterministic fingerprint for dedup (no secrets included)."""
        raw = f"{reason}|{sub_reason}|{extra}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _is_duplicate(self, fingerprint: str) -> bool:
        """Check if fingerprint was sent within dedup window."""
        now = time.time()
        last_sent = self._dedup_history.get(fingerprint)
        if last_sent and (now - last_sent) < self.DEDUP_WINDOW_SECONDS:
            logger.info(f"Dedup: suppressing duplicate notification (fingerprint={fingerprint}, last={last_sent:.0f})")
            return True
        # Prune stale entries when near capacity
        if len(self._dedup_history) >= self.MAX_DEDUP_ENTRIES:
            cutoff = now - self.DEDUP_WINDOW_SECONDS
            stale = [k for k, v in self._dedup_history.items() if v < cutoff]
            for k in stale:
                del self._dedup_history[k]
        self._dedup_history[fingerprint] = now
        return False

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
