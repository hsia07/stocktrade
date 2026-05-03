"""
API Auto-Mode Loop (Phase 2B Runtime Implementation)

Implements Phase 2B auto-pause trigger rules:
- consecutive_failure_count >= 3 can trigger auto pause (standalone)
- stuck_duration >= 30min can trigger auto pause (standalone)
- no_new_commit >= 60min AND no_new_RETURN_TO_CHATGPT >= 45min can trigger auto pause (combination only)
- no_new_phase_transition >= 90min only as auxiliary signal (cannot trigger alone)
"""

import logging
from typing import Dict, Any, Optional
import time

from automation.control.pause_state import PauseStateManager

logger = logging.getLogger("api_automode_loop")


class APIAutoModeLoop:
    """Phase 2B runtime: auto-pause trigger logic for API automode loop."""
    
    # Phase 2B trigger thresholds
    _CONSECUTIVE_FAILURE_THRESHOLD = 3
    _STUCK_DURATION_THRESHOLD_SECONDS = 30 * 60  # 30 minutes
    _NO_NEW_COMMIT_THRESHOLD_SECONDS = 60 * 60  # 60 minutes
    _NO_NEW_RTC_THRESHOLD_SECONDS = 45 * 60  # 45 minutes
    _NO_NEW_PHASE_TRANSITION_THRESHOLD_SECONDS = 90 * 60  # 90 minutes (auxiliary only)
    
    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.pause_manager = PauseStateManager(self.repo_root)
        
        # Phase 2B state tracking
        self._consecutive_failure_count = 0
        self._stuck_start_time = None
        self._last_commit_time = None
        self._last_rtc_time = None
        self._last_phase_transition_time = None
        self._no_new_commit_start_time = None
        self._no_new_rtc_start_time = None
        self._no_new_phase_transition_start_time = None
    
    def record_failure(self) -> None:
        """Record a failure and check if should trigger auto-pause."""
        self._consecutive_failure_count += 1
        logger.warning(f"Failure recorded. Consecutive count: {self._consecutive_failure_count}")
        
        if self._consecutive_failure_count >= self._CONSECUTIVE_FAILURE_THRESHOLD:
            self._trigger_auto_pause(
                reason=self.pause_manager.REASON_FAILURE,
                extra_data={"failure_count": self._consecutive_failure_count}
            )
    
    def record_success(self) -> None:
        """Reset failure count on success."""
        if self._consecutive_failure_count > 0:
            logger.info(f"Success recorded. Resetting failure count from {self._consecutive_failure_count}")
            self._consecutive_failure_count = 0
    
    def check_stall(self, current_time: float = None) -> None:
        """
        Check if system is stuck (no progress).
        Call this periodically to track stall duration.
        """
        if current_time is None:
            current_time = time.time()
        
        # If we're making progress, reset stall
        if self._is_progress_made():
            if self._stuck_start_time is not None:
                logger.info("Progress detected, resetting stall timer")
                self._stuck_start_time = None
            return
        
        # No progress being made
        if self._stuck_start_time is None:
            self._stuck_start_time = current_time
            logger.info("Stall detected, starting timer")
        else:
            stuck_duration = current_time - self._stuck_start_time
            if stuck_duration >= self._STUCK_DURATION_THRESHOLD_SECONDS:
                self._trigger_auto_pause(
                    reason=self.pause_manager.REASON_STALL,
                    extra_data={"stall_duration_seconds": stuck_duration}
                )
    
    def check_no_new_commit_rtc(self, commit_time: float = None, rtc_time: float = None) -> None:
        """
        Check if no new commit AND no new RETURN_TO_CHATGPT combination trigger.
        Both conditions must be met for combination trigger.
        """
        current_time = time.time()
        
        # Check no new commit
        if commit_time is None:
            commit_time = self._get_last_commit_time()
        if commit_time is not None:
            no_new_commit_duration = current_time - commit_time
            if no_new_commit_duration >= self._NO_NEW_COMMIT_THRESHOLD_SECONDS:
                if self._no_new_commit_start_time is None:
                    self._no_new_commit_start_time = current_time
            else:
                self._no_new_commit_start_time = None
        
        # Check no new RETURN_TO_CHATGPT
        if rtc_time is None:
            rtc_time = self._get_last_rtc_time()
        if rtc_time is not None:
            no_new_rtc_duration = current_time - rtc_time
            if no_new_rtc_duration >= self._NO_NEW_RTC_THRESHOLD_SECONDS:
                if self._no_new_rtc_start_time is None:
                    self._no_new_rtc_start_time = current_time
            else:
                self._no_new_rtc_start_time = None
        
        # Combination trigger: both conditions met
        if (self._no_new_commit_start_time is not None and 
            self._no_new_rtc_start_time is not None):
            # Both timers started, check which is the limiting factor
            no_new_commit_elapsed = current_time - self._no_new_commit_start_time
            no_new_rtc_elapsed = current_time - self._no_new_rtc_start_time
            
            if (no_new_commit_elapsed >= self._NO_NEW_COMMIT_THRESHOLD_SECONDS and 
                no_new_rtc_elapsed >= self._NO_NEW_RTC_THRESHOLD_SECONDS):
                self._trigger_auto_pause(
                    reason=self.pause_manager.REASON_NO_NEW_COMMIT_RTC,
                    extra_data={
                        "no_new_commit_minutes": no_new_commit_elapsed / 60,
                        "no_new_rtc_minutes": no_new_rtc_elapsed / 60
                    }
                )
    
    def check_no_new_phase_transition(self, phase_transition_time: float = None) -> None:
        """
        Check no new phase transition (auxiliary signal only, cannot trigger alone).
        This is only recorded as auxiliary information, not a standalone trigger.
        """
        current_time = time.time()
        
        if phase_transition_time is None:
            phase_transition_time = self._get_last_phase_transition_time()
        
        if phase_transition_time is not None:
            no_new_phase_duration = current_time - phase_transition_time
            if no_new_phase_duration >= self._NO_NEW_PHASE_TRANSITION_THRESHOLD_SECONDS:
                if self._no_new_phase_transition_start_time is None:
                    self._no_new_phase_transition_start_time = current_time
                    logger.info(f"No new phase transition for {no_new_phase_duration/60:.1f} minutes (auxiliary signal only)")
    
    def manual_start_request(self) -> Dict[str, Any]:
        """
        /start semantics: only a request for manual recovery.
        Does NOT directly resume. Must run pre-resume checks first.
        """
        if not self.pause_manager.is_paused():
            return {"can_resume": False, "reason": "Not paused", "requires_pre_resume": False}
        
        # Run pre-resume checks
        pre_resume = self.pause_manager.pre_resume_checks(
            authorized_scope=[
                self.pause_manager.REASON_FAILURE,
                self.pause_manager.REASON_STALL,
                self.pause_manager.REASON_NO_NEW_COMMIT_RTC,
                self.pause_manager.REASON_NO_PHASE_TRANSITION,
                self.pause_manager.REASON_MANUAL
            ]
        )
        
        if not pre_resume["can_resume"]:
            return {
                "can_resume": False,
                "reason": f"Pre-resume checks failed: {pre_resume['reason']}",
                "failed_checks": pre_resume["failed_checks"],
                "requires_pre_resume": True
            }
        
        return {
            "can_resume": True,
            "reason": "Pre-resume checks passed. Manual authorization required to resume.",
            "requires_pre_resume": True,
            "pre_resume_result": pre_resume
        }
    
    def _is_progress_made(self) -> bool:
        """Check if system is making progress (override in subclass or use hooks)."""
        # Default: check if there are recent state changes, commits, etc.
        # This should be customized based on actual progress indicators
        try:
            state_path = self.repo_root / "automation" / "control" / "state.runtime.json"
            if state_path.exists():
                import os
                mtime = state_path.stat().st_mtime
                if time.time() - mtime < 300:  # 5 minutes
                    return True
        except Exception:
            pass
        return False
    
    def _get_last_commit_time(self) -> Optional[float]:
        """Get last commit time (simplified - should use git log in real impl)."""
        return self._last_commit_time
    
    def _get_last_rtc_time(self) -> Optional[float]:
        """Get last RETURN_TO_CHATGPT time (simplified)."""
        return self._last_rtc_time
    
    def _get_last_phase_transition_time(self) -> Optional[float]:
        """Get last phase transition time (simplified)."""
        return self._last_phase_transition_time
    
    def _trigger_auto_pause(self, reason: str, extra_data: Dict[str, Any] = None) -> None:
        """Trigger auto-pause with given reason and extra data."""
        logger.warning(f"Auto-pause triggered! Reason: {reason}")
        
        # Send Telegram notification
        try:
            from automation.control.telegram_notifier import TelegramNotifier
            notifier = TelegramNotifier(mock_mode=True)  # Default mock mode
            notifier.send_pause_notification(
                pause_reason=reason,
                duration_info=extra_data,
                manual_action_required="Use /start to request manual recovery. Pre-resume checks will run."
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
        
        # Set pause with checkpoint
        checkpoint_data = {
            "pause_reason": reason,
            "triggered_at": time.time(),
            **(extra_data or {})
        }
        self.pause_manager.set_pause(reason=reason, checkpoint_data=checkpoint_data)
