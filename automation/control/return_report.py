"""
Return Report Generator

Generates formal RETURN_TO_CHATGPT formatted reports for pause,
stop, and phase-transition events.

The output format matches the project's canonical RETURN_TO_CHATGPT
schema so that it can be consumed by the OpenCode chat output channel.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("return_report")


class ReturnReportGenerator:
    """Generate formal RETURN_TO_CHATGPT bodies."""

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent

    def generate_pause_report(
        self,
        state: Dict[str, Any],
        pause_reason: str = "",
    ) -> str:
        """
        Generate a full RETURN_TO_CHATGPT body for a pause event.

        Args:
            state: Structured state dict from StatusScheduler.build_state()
            pause_reason: Why pause was triggered

        Returns:
            Full formatted RETURN_TO_CHATGPT string.
        """
        now = datetime.now(timezone.utc).isoformat()
        current_round = state.get("current_round", "unknown")
        last_completed = state.get("last_completed_round", "unknown")
        next_round = state.get("next_round", "unknown")
        chain_status = state.get("chain_status", "unknown")
        auto_run = state.get("auto_run", False)
        stop_reason = state.get("stop_reason", "")
        stop_gate = state.get("stop_gate_type", "")

        lines = [
            "---",
            "# RETURN_TO_CHATGPT",
            f"## PAUSE REPORT - {current_round}",
            "",
            "### round_id",
            f'"{current_round}"',
            "",
            "### task_type",
            '"pause_execution"',
            "",
            f"### reply_id",
            f'"pause-report-{now.replace(":", "").replace("-", "")}"',
            "",
            "### status",
            '"paused"',
            "",
            "### formal_status_code",
            '"paused_awaiting_resume_authorization"',
            "",
            "### pause_timestamp",
            f'"{now}"',
            "",
            "### pause_reason",
            f'"{pause_reason or stop_reason or "manual_pause_requested"}"',
            "",
            "### current_round",
            f'"{current_round}"',
            "",
            "### last_completed_round",
            f'"{last_completed}"',
            "",
            "### next_round_to_dispatch",
            f'"{next_round}"',
            "",
            "### chain_status",
            f'"{chain_status}"',
            "",
            "### auto_run",
            f"{str(auto_run).lower()}",
            "",
            "### stop_gate_type",
            f'"{stop_gate}"',
            "",
            "### stop_reason",
            f'"{stop_reason}"',
            "",
            "---",
            "",
            "## Summary",
            f"Chain paused at round {current_round}.",
            f"Resume target: {next_round}.",
            f"Pause reason: {pause_reason or stop_reason or 'manual pause request'}.",
            "",
        ]

        return "\n".join(lines)

    def generate_stop_report(
        self,
        state: Dict[str, Any],
        stop_reason: str,
        stop_gate: str,
    ) -> str:
        """Generate a full RETURN_TO_CHATGPT body for a stop event."""
        now = datetime.now(timezone.utc).isoformat()
        current_round = state.get("current_round", "unknown")
        last_completed = state.get("last_completed_round", "unknown")
        next_round = state.get("next_round", "unknown")
        chain_status = state.get("chain_status", "unknown")

        lines = [
            "---",
            "# RETURN_TO_CHATGPT",
            f"## STOP REPORT - {current_round}",
            "",
            "### round_id",
            f'"{current_round}"',
            "",
            "### task_type",
            '"stop_execution"',
            "",
            f"### reply_id",
            f'"stop-report-{now.replace(":", "").replace("-", "")}"',
            "",
            "### status",
            '"stopped"',
            "",
            "### formal_status_code",
            '"stopped_at_gate"',
            "",
            "### stop_timestamp",
            f'"{now}"',
            "",
            "### stop_reason",
            f'"{stop_reason}"',
            "",
            "### stop_gate_type",
            f'"{stop_gate}"',
            "",
            "### current_round",
            f'"{current_round}"',
            "",
            "### last_completed_round",
            f'"{last_completed}"',
            "",
            "### next_round_to_dispatch",
            f'"{next_round}"',
            "",
            "### chain_status",
            f'"{chain_status}"',
            "",
            "---",
            "",
            "## Summary",
            f"Chain stopped at round {current_round} due to {stop_gate}.",
            f"Reason: {stop_reason}.",
            f"Next round staged: {next_round}.",
            "",
        ]

        return "\n".join(lines)

    def write_report(self, report_text: str, filename: str = "LATEST_PAUSE_RETURN_TO_CHATGPT.txt") -> Path:
        """
        Write report to the canonical output channel file.

        Returns the path written.
        """
        out_path = self.repo_root / "automation" / "control" / filename
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(report_text, encoding="utf-8")
            logger.info(f"Return report written to {out_path}")
        except Exception as e:
            logger.error(f"Failed to write return report: {e}")
        return out_path
