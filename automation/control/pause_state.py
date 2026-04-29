"""
Pause State Manager

Implements Telegram /pause semantics:
- /pause creates PAUSE.flag in automation/control/
- Safe stop happens AFTER current round completes, BEFORE next dispatch
- Never interrupts atomic steps
- Readable from truth source / control state
- Supports multiple pause reasons: manual, usage_exhausted, connection_failure
- Saves checkpoint on pause for recovery
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("pause_state")


class PauseStateManager:
    """Manage pause state via PAUSE.flag."""
    
    PAUSE_FLAG_NAME = "PAUSE.flag"
    CHECKPOINT_PATH = "automation/control/checkpoint.json"
    
    # Pause reasons
    REASON_MANUAL = "manual_pause_requested"
    REASON_FAILURE = "paused_after_failure"
    REASON_STALL = "auto_paused_by_stall"  # Phase A+ non-usage stall monitoring
    REASON_USAGE = "paused_by_usage"  # Phase B only, blocked
    
    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.pause_flag = self.repo_root / "automation" / "control" / self.PAUSE_FLAG_NAME
        self.checkpoint_path = self.repo_root / self.CHECKPOINT_PATH

    def is_paused(self) -> bool:
        """Check if PAUSE.flag exists."""
        return self.pause_flag.exists()

    def set_pause(self, reason: str = "", checkpoint_data: Dict[str, Any] = None) -> bool:
        """Create PAUSE.flag and save checkpoint."""
        try:
            content = f"paused_at=auto\nreason={reason}\n"
            self.pause_flag.write_text(content, encoding="utf-8")
            logger.info(f"PAUSE.flag created: {reason}")
            # Save checkpoint if provided
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
