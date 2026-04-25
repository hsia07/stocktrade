"""
Pause State Manager

Implements Telegram /pause semantics:
- /pause creates PAUSE.flag in automation/control/
- Safe stop happens AFTER current round completes, BEFORE next dispatch
- Never interrupts atomic steps
- Readable from truth source / control state
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("pause_state")


class PauseStateManager:
    """Manage pause state via PAUSE.flag."""

    PAUSE_FLAG_NAME = "PAUSE.flag"

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.pause_flag = self.repo_root / "automation" / "control" / self.PAUSE_FLAG_NAME

    def is_paused(self) -> bool:
        """Check if PAUSE.flag exists."""
        return self.pause_flag.exists()

    def set_pause(self, reason: str = "") -> bool:
        """Create PAUSE.flag."""
        try:
            content = f"paused_at=auto\nreason={reason}\n"
            self.pause_flag.write_text(content, encoding="utf-8")
            logger.info(f"PAUSE.flag created: {reason}")
            return True
        except Exception as e:
            logger.error(f"Failed to create PAUSE.flag: {e}")
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

        generator = ReturnReportGenerator(self.repo_root)
        report = generator.generate_pause_report(state, pause_reason="manual_pause_requested")
        generator.write_report(report, filename="LATEST_PAUSE_RETURN_TO_CHATGPT.txt")
        return report

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
            return info
        except Exception:
            return {"paused": True, "reason": "unknown"}
