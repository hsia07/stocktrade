"""
Pause State Manager

Implements Telegram /pause semantics:
- /pause creates PAUSE.flag in automation/control/
- Safe stop happens AFTER current round completes, BEFORE next dispatch
- Never interrupts atomic steps
- Readable from truth source / control state
- Supports multiple pause reasons: manual, usage_exhausted, connection_failure, stall, no_new_commit_rtc
- Saves checkpoint on pause for recovery
- Phase 2B: sub-category detection for usage exhaustion (insufficient_balance, api_quota, model_unavailable, source_unavailable)
- Phase 2B: pre-resume checks include RTC validity/freshness + pause reason resolution
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger("pause_state")

class PauseStateManager:
    """Manage pause state via PAUSE.flag."""
    
    PAUSE_FLAG_NAME = "PAUSE.flag"
    CHECKPOINT_PATH = "automation/control/checkpoint.json"
    
    # Pause reasons - Phase 2B governance chain
    REASON_MANUAL = "manual_pause_requested"
    REASON_FAILURE = "paused_after_failure"  # consecutive_failure_count >= 3
    REASON_STALL = "auto_paused_by_stall"  # stuck_duration >= 30min
    REASON_NO_NEW_COMMIT_RTC = "auto_paused_by_no_new_commit_rtc"  # no_new_commit>=60min + no_new_rtc>=45min
    REASON_NO_PHASE_TRANSITION = "auto_paused_by_no_phase_transition"  # no_new_phase_transition>=90min (auxiliary only)
    REASON_USAGE = "paused_by_usage"  # Phase 2B, OpenCode usage exhausted/unavailable
    
    # Phase 2B usage exhaustion sub-reasons
    USAGE_SUB_INSUFFICIENT_BALANCE = "insufficient_balance"
    USAGE_SUB_API_QUOTA_EXHAUSTED = "api_quota_exhausted"
    USAGE_SUB_MODEL_UNAVAILABLE = "model_unavailable"
    USAGE_SUB_SOURCE_UNAVAILABLE = "usage_source_unavailable"
    USAGE_SUB_UNKNOWN = "unknown_usage_exhaustion"
    
    USAGE_SUB_REASONS = [
        USAGE_SUB_INSUFFICIENT_BALANCE,
        USAGE_SUB_API_QUOTA_EXHAUSTED,
        USAGE_SUB_MODEL_UNAVAILABLE,
        USAGE_SUB_SOURCE_UNAVAILABLE,
        USAGE_SUB_UNKNOWN,
    ]
    
    # Sentinel paths for auto-detection (relative to repo_root)
    USAGE_SENTINEL_INSUFFICIENT_BALANCE = "automation/control/sentinels/usage_insufficient_balance.sentinel"
    USAGE_SENTINEL_API_QUOTA = "automation/control/sentinels/usage_api_quota.sentinel"
    USAGE_SENTINEL_MODEL_UNAVAILABLE = "automation/control/sentinels/usage_model_unavailable.sentinel"
    USAGE_SENTINEL_SOURCE_UNAVAILABLE = "automation/control/sentinels/usage_source_unavailable.sentinel"
    USAGE_SENTINEL_GENERIC = "automation/control/sentinels/usage_exhausted.sentinel"
    
    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.pause_flag = self.repo_root / "automation" / "control" / self.PAUSE_FLAG_NAME
        self.checkpoint_path = self.repo_root / self.CHECKPOINT_PATH

    def is_paused(self) -> bool:
        """Check if PAUSE.flag exists."""
        return self.pause_flag.exists()

    def detect_usage_sub_reason(self) -> Optional[str]:
        """
        Auto-detect usage exhaustion sub-category by checking sentinel files.
        Returns sub_reason string or None if no sentinel found.
        Follows classification priority: insufficient_balance > api_quota > model_unavailable > source_unavailable > generic.
        """
        sentinel_map = [
            (self.repo_root / self.USAGE_SENTINEL_INSUFFICIENT_BALANCE, self.USAGE_SUB_INSUFFICIENT_BALANCE),
            (self.repo_root / self.USAGE_SENTINEL_API_QUOTA, self.USAGE_SUB_API_QUOTA_EXHAUSTED),
            (self.repo_root / self.USAGE_SENTINEL_MODEL_UNAVAILABLE, self.USAGE_SUB_MODEL_UNAVAILABLE),
            (self.repo_root / self.USAGE_SENTINEL_SOURCE_UNAVAILABLE, self.USAGE_SUB_SOURCE_UNAVAILABLE),
            (self.repo_root / self.USAGE_SENTINEL_GENERIC, self.USAGE_SUB_UNKNOWN),
        ]
        for sentinel_path, sub_reason in sentinel_map:
            if sentinel_path.exists():
                return sub_reason
        return None

    def classify_usage_exhaustion(self, extra_data: Dict[str, Any] = None) -> str:
        """
        Classify usage exhaustion into sub-category.
        Checks sentinel files first, then falls back to extra_data hints, then unknown.
        Fail-closed: any unrecognized usage exhaustion is mapped to USAGE_SUB_UNKNOWN.
        """
        sentinel_result = self.detect_usage_sub_reason()
        if sentinel_result:
            return sentinel_result
        if extra_data:
            hint = extra_data.get("usage_sub_reason", "")
            if hint in self.USAGE_SUB_REASONS:
                return hint
        return self.USAGE_SUB_UNKNOWN

    def set_pause(self, reason: str = "", checkpoint_data: Dict[str, Any] = None,
                  sub_reason: str = "") -> bool:
        """
        Create PAUSE.flag and save checkpoint.
        If reason is REASON_USAGE and no sub_reason provided, auto-classify.
        """
        try:
            if reason == self.REASON_USAGE and not sub_reason:
                sub_reason = self.classify_usage_exhaustion(checkpoint_data)
            content = f"paused_at=auto\nreason={reason}\n"
            if sub_reason:
                content += f"sub_reason={sub_reason}\n"
            self.pause_flag.write_text(content, encoding="utf-8")
            logger.info(f"PAUSE.flag created: {reason} sub_reason={sub_reason}")
            if checkpoint_data:
                self._save_checkpoint(checkpoint_data)
            return True
        except Exception as e:
            logger.error(f"Failed to create PAUSE.flag: {e}")
            return False
    
    def _save_checkpoint(self, data: Dict[str, Any]) -> bool:
        """Save checkpoint to checkpoint.json (runtime mutable file)."""
        try:
            import json
            with self.checkpoint_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Checkpoint saved: {self.checkpoint_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return False
    
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load checkpoint from checkpoint.json if exists."""
        try:
            if not self.checkpoint_path.exists():
                return None
            import json
            with self.checkpoint_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    def clear_checkpoint(self) -> bool:
        """Remove checkpoint file."""
        try:
            if self.checkpoint_path.exists():
                self.checkpoint_path.unlink()
                logger.info("Checkpoint removed")
            return True
        except Exception as e:
            logger.error(f"Failed to remove checkpoint: {e}")
            return False

    def clear_pause(self) -> bool:
        """Remove PAUSE.flag."""
        try:
            if self.pause_flag.exists():
                self.pause_flag.unlink()
                logger.info("PAUSE.flag removed")
            return True
        except Exception as e:
            logger.error(f"Failed to remove PAUSE.flag: {e}")
            return False

    def generate_pause_report(self, state: dict = None) -> str:
        """
        Generate a full RETURN_TO_CHATGPT body when pause is triggered.

        Args:
            state: Optional structured state dict. If None, reads from manifest.

        Returns:
            Full formatted RETURN_TO_CHATGPT string.
        """
        from automation.control.return_report import ReturnReportGenerator
        from automation.control.status_scheduler import StatusScheduler

        scheduler = StatusScheduler(self.repo_root)
        if state is None:
            state = scheduler.build_state()

        # Read pause_reason from PAUSE.flag or checkpoint
        pause_reason = self._read_pause_reason_from_source()

        generator = ReturnReportGenerator(self.repo_root)
        report = generator.generate_pause_report(state, pause_reason=pause_reason)
        generator.write_report(report, filename="LATEST_PAUSE_RETURN_TO_CHATGPT.txt")
        return report

    def _read_pause_reason_from_source(self) -> str:
        """Read pause_reason from PAUSE.flag or checkpoint."""
        # Try PAUSE.flag first
        if self.is_paused():
            try:
                text = self.pause_flag.read_text(encoding="utf-8")
                for line in text.strip().split("\n"):
                    if line.startswith("reason="):
                        return line.split("=", 1)[1]
            except Exception:
                pass
        # Try checkpoint
        checkpoint = self.load_checkpoint()
        if checkpoint:
            return checkpoint.get("pause_reason", "manual_pause_requested")
        return "manual_pause_requested"

    def get_pause_info(self) -> Optional[dict]:
        """Return pause info if paused, else None."""
        if not self.is_paused():
            return None
        try:
            text = self.pause_flag.read_text(encoding="utf-8")
            info = {}
            for line in text.strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    info[k] = v
            # Also load checkpoint for stall info
            checkpoint = self.load_checkpoint()
            if checkpoint:
                info["checkpoint"] = checkpoint
            return info
        except Exception:
            return {"paused": True, "reason": "unknown"}

    def _check_rtc_validity(self) -> Optional[str]:
        """
        Validate latest RETURN_TO_CHATGPT truth source.
        Returns None if valid, error string if invalid/missing/stale.
        Checks:
        1. Truth source file exists
        2. File contains required formal body fields
        3. File is not synthetic (no synthetic markers)
        4. File is not stale (beyond 7 days)
        """
        rtc_path = self.repo_root / "automation" / "control" / "latest_return_to_chatgpt.runtime.txt"
        if not rtc_path.exists():
            return "rtc_truth_source_missing: latest_return_to_chatgpt.runtime.txt not found"
        try:
            content = rtc_path.read_text(encoding="utf-8")
            # Reject synthetic RTC (must come from formal RETURN_TO_CHATGPT block)
            if "[SYNTHETIC]" in content or "synthetically generated" in content.lower():
                return "rtc_rejected_synthetic: RTC contains synthetic markers"
            # Check required formal body fields
            required_fields = ["round_id:", "task_type:", "status:", "formal_status_code:",
                               "recommended_next_action:", "final_recommendation:"]
            missing = [f for f in required_fields if f not in content]
            if missing:
                return f"rtc_malformed: missing required fields: {missing}"
            # Check freshness (stale if > 7 days old)
            import re
            ts_match = re.search(r'timestamp:\s*([\d\-T:Z]+)', content)
            if ts_match:
                from datetime import datetime
                try:
                    ts = ts_match.group(1)
                    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    age_days = (datetime.now().astimezone() - parsed).days
                    if age_days > 7:
                        return f"rtc_stale: RTC is {age_days} days old (max 7 days)"
                except (ValueError, TypeError):
                    return "rtc_malformed: cannot parse timestamp"
        except Exception as e:
            return f"rtc_read_error: {e}"
        return None

    def _check_pause_reason_resolved(self) -> Optional[str]:
        """
        Check if pause reason has been resolved.
        Returns None if resolved, error string if unresolved.
        - insufficient_balance: requires sentinel cleared OR user override evidence
        - api_quota_exhausted: requires sentinel cleared
        - model_unavailable: requires sentinel cleared
        - usage_source_unavailable: requires sentinel cleared
        - unknown_usage_exhaustion: requires user override evidence
        - Non-usage pauses (manual, failure, stall): require only pre-resume checks
        """
        pause_info = self.get_pause_info()
        if not pause_info:
            return None  # Not paused, no resolution needed
        reason = pause_info.get("reason", "")
        sub_reason = pause_info.get("sub_reason", "")
        if reason != self.REASON_USAGE:
            return None  # Non-usage pauses resolved by pre-resume checks passing
        # Check sentinel still active
        active_sentinel = self.detect_usage_sub_reason()
        if active_sentinel:
            return f"pause_reason_unresolved: {sub_reason} sentinel still active at {active_sentinel}"
        # Check for user override evidence in checkpoint
        checkpoint = self.load_checkpoint()
        if checkpoint and checkpoint.get("pause_reason_resolved", False):
            return None
        if sub_reason == self.USAGE_SUB_UNKNOWN:
            return "pause_reason_unresolved: unknown_usage_exhaustion requires explicit user override"
        return None

    def pre_resume_checks(self, authorized_scope: list = None) -> Dict[str, Any]:
        """
        Pre-resume checks before allowing /start to actually resume.
        Must check: health / blocker / state consistency / authorized scope /
        RTC validity/freshness / pause reason resolution.
        Returns dict with: can_resume, reason, failed_checks
        """
        failed_checks = []
        
        # 1. Health check - basic system health
        try:
            critical_files = [
                self.repo_root / "automation" / "control" / "status_scheduler.py",
                self.repo_root / "automation" / "control" / "pause_state.py"
            ]
            for f in critical_files:
                if not f.exists():
                    failed_checks.append(f"health_check: missing critical file {f.name}")
        except Exception as e:
            failed_checks.append(f"health_check: exception {e}")
        
        # 2. Blocker status check
        try:
            lock_path = self.repo_root / "automation" / "control" / "AUTO_MODE_ACTIVATION_LOCK"
            if lock_path.exists():
                import json
                with lock_path.open("r", encoding="utf-8") as f:
                    lock = json.load(f)
                    if lock.get("blocked"):
                        failed_checks.append(f"blocker_check: system is blocked - {lock.get('reason', 'unknown')}")
        except Exception as e:
            failed_checks.append(f"blocker_check: exception {e}")
        
        # 3. State consistency check (before/after pause)
        try:
            checkpoint = self.load_checkpoint()
            if checkpoint:
                required_fields = ["round_id", "pause_reason"]
                for field in required_fields:
                    if field not in checkpoint:
                        failed_checks.append(f"state_consistency: checkpoint missing {field}")
        except Exception as e:
            failed_checks.append(f"state_consistency: exception {e}")
        
        # 4. Authorized scope check
        if authorized_scope:
            try:
                current_scope = self._read_pause_reason_from_source()
                if current_scope and current_scope not in authorized_scope:
                    failed_checks.append(f"authorized_scope: pause reason {current_scope} not in authorized scope {authorized_scope}")
            except Exception as e:
                failed_checks.append(f"authorized_scope: exception {e}")
        
        # 5. RTC validity / freshness check (GAP-3)
        rtc_error = self._check_rtc_validity()
        if rtc_error:
            failed_checks.append(f"rtc_check: {rtc_error}")
        
        # 6. Pause reason resolution check (GAP-4)
        resolution_error = self._check_pause_reason_resolved()
        if resolution_error:
            failed_checks.append(f"pause_resolution: {resolution_error}")
        
        can_resume = len(failed_checks) == 0
        reason = "; ".join(failed_checks) if failed_checks else ""
        
        return {
            "can_resume": can_resume,
            "reason": reason,
            "failed_checks": failed_checks
        }
    
    def update_pause_reason(self, reason: str, extra_data: Dict[str, Any] = None) -> bool:
        """Update pause reason in PAUSE.flag with additional data."""
        try:
            content = f"paused_at=auto\nreason={reason}\n"
            if extra_data:
                for k, v in extra_data.items():
                    content += f"{k}={v}\n"
            self.pause_flag.write_text(content, encoding="utf-8")
            logger.info(f"PAUSE.flag updated: {reason}")
            return True
        except Exception as e:
            logger.error(f"Failed to update PAUSE.flag: {e}")
            return False
