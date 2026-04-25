"""
Status Reporter

Generate Telegram status summary for auto-mode governance.
Schema matches required fields for human oversight.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from automation.control.pause_state import PauseStateManager

logger = logging.getLogger("status_reporter")


class StatusReporter:
    """Produce status summary for Telegram / external monitoring."""

    def __init__(self, repo_root=None):
        from pathlib import Path
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.pause_manager = PauseStateManager(self.repo_root)

    def generate_summary(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate status summary dict with required schema.

        Required fields:
        - current_round
        - next_round
        - auto_advanced_true_or_false
        - stop_reason
        - stop_gate_type
        - evidence_complete_true_or_false
        - candidate_branch
        - candidate_commit
        - awaiting_review_true_or_false
        """
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_round": state.get("current_round", "unknown"),
            "next_round": state.get("next_round", "unknown"),
            "auto_advanced_true_or_false": state.get("auto_advanced", False),
            "stop_reason": state.get("stop_reason", ""),
            "stop_gate_type": state.get("stop_gate_type", ""),
            "evidence_complete_true_or_false": state.get("evidence_complete", False),
            "candidate_branch": state.get("candidate_branch", ""),
            "candidate_commit": state.get("candidate_commit", ""),
            "awaiting_review_true_or_false": state.get("awaiting_review", False),
            "paused_true_or_false": self.pause_manager.is_paused(),
            "lane_frozen_true_or_false": state.get("lane_frozen", False),
        }
        logger.info(f"Status summary generated for round {summary['current_round']}")
        return summary

    def format_for_telegram(self, summary: Dict[str, Any]) -> str:
        """Format summary as Telegram message."""
        lines = [
            f"*Round:* {summary['current_round']}",
            f"*Next:* {summary['next_round']}",
            f"*Auto-advanced:* {summary['auto_advanced_true_or_false']}",
            f"*Evidence complete:* {summary['evidence_complete_true_or_false']}",
            f"*Awaiting review:* {summary['awaiting_review_true_or_false']}",
            f"*Paused:* {summary['paused_true_or_false']}",
        ]
        if summary['stop_reason']:
            lines.append(f"*Stop reason:* {summary['stop_reason']}")
        if summary['stop_gate_type']:
            lines.append(f"*Stop gate:* {summary['stop_gate_type']}")
        return "\n".join(lines)
