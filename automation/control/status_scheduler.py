"""
Status Scheduler

Periodically reads current_round.yaml, builds structured state,
generates status summary, and sends via Telegram sender.
Also implements /pause and /start semantics.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

from automation.control.status_reporter import StatusReporter
from automation.control.pause_state import PauseStateManager
from automation.telegram.sender import TelegramSender

logger = logging.getLogger("status_scheduler")


class StatusScheduler:
    """Read structured state from canonical source and send status."""

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.reporter = StatusReporter(self.repo_root)
        self.pause_manager = PauseStateManager(self.repo_root)
        self.sender = TelegramSender()
        self.manifest_path = self.repo_root / "manifests" / "current_round.yaml"
        self.lock_path = self.repo_root / "automation" / "control" / "AUTO_MODE_ACTIVATION_LOCK"

    def _load_manifest(self) -> Dict[str, Any]:
        """Load current_round.yaml as structured dict."""
        if not self.manifest_path.exists():
            logger.warning("current_round.yaml not found")
            return {}
        try:
            with self.manifest_path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load current_round.yaml: {e}")
            return {}

    def _load_lock(self) -> Dict[str, Any]:
        """Load AUTO_MODE_ACTIVATION_LOCK as structured dict."""
        if not self.lock_path.exists():
            logger.warning("AUTO_MODE_ACTIVATION_LOCK not found")
            return {}
        try:
            with self.lock_path.open("r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load AUTO_MODE_ACTIVATION_LOCK: {e}")
            return {}

    def build_state(self) -> Dict[str, Any]:
        """
        Build canonical state dict ONLY from structured fields.
        NEVER reads notes or free-text fields for dispatch decisions.
        """
        manifest = self._load_manifest()
        lock = self._load_lock()
        chain_control = lock.get("chain_control", {})
        backlog = manifest.get("backlog", {})

        # Determine if any backlog items are still pending merge review
        backlog_pending = any(
            item.get("merge_review_status") == "pending"
            for item in backlog.values()
            if isinstance(item, dict)
        )

        state = {
            "current_round": manifest.get("current_round", "NONE"),
            "last_completed_round": manifest.get("last_completed_round", "unknown"),
            "next_round": manifest.get("next_round_to_dispatch", "unknown"),
            "auto_run": manifest.get("auto_run", False),
            "chain_status": manifest.get("chain_status", "unknown"),
            "auto_advanced": False,
            "stop_reason": "",
            "stop_gate_type": "",
            "evidence_complete": False,
            "candidate_branch": "",
            "candidate_commit": "",
            "awaiting_review": False,
            "lane_frozen": False,
            "paused": self.pause_manager.is_paused(),
            "backlog_pending": backlog_pending,
        }

        # Determine stop reason and gate type based on canonical state
        if state["paused"]:
            state["stop_reason"] = "pause_flag_active"
            state["stop_gate_type"] = "pause_gate"
        elif state["chain_status"] == "frozen_pending_backlog_merge" and backlog_pending:
            state["stop_reason"] = "backlog_merge_review_pending"
            state["stop_gate_type"] = "backlog_gate"
        elif not state["auto_run"]:
            state["stop_reason"] = "auto_run_false"
            state["stop_gate_type"] = "auto_run_gate"
        elif state["chain_status"] == "frozen_pending_backlog_merge" and not backlog_pending:
            state["stop_reason"] = "backlog_cleared_awaiting_unfreeze_authorization"
            state["stop_gate_type"] = "unfreeze_authorization_gate"

        return state

    def generate_and_send(self) -> Dict[str, Any]:
        """
        Build state, generate summary, format for Telegram, send.
        Returns send result dict.
        """
        state = self.build_state()
        summary = self.reporter.generate_summary(state)
        formatted = self.reporter.format_for_telegram(summary)
        summary["formatted_text"] = formatted
        result = self.sender.send_status(summary)
        return result

    def check_can_start(self) -> Dict[str, Any]:
        """
        /start semantics: check if chain can resume from structured state.

        Returns dict with:
        - can_start: bool
        - reason: str (empty if can_start=True)
        - resume_from_round: str
        """
        manifest = self._load_manifest()
        lock = self._load_lock()
        chain_control = lock.get("chain_control", {})
        backlog = manifest.get("backlog", {})

        reasons = []

        # Check 1: PAUSE flag
        if self.pause_manager.is_paused():
            reasons.append("PAUSE.flag is active")

        # Check 2: auto_run
        if not manifest.get("auto_run", False):
            reasons.append("auto_run is false")

        # Check 3: chain_status
        chain_status = manifest.get("chain_status", "")
        if chain_status == "frozen_pending_backlog_merge":
            backlog_pending = any(
                item.get("merge_review_status") == "pending"
                for item in backlog.values()
                if isinstance(item, dict)
            )
            if backlog_pending:
                reasons.append("backlog merge review pending")
            else:
                reasons.append("chain frozen awaiting unfreeze authorization")

        # Check 4: state consistency
        last_completed = manifest.get("last_completed_round", "")
        next_round = manifest.get("next_round_to_dispatch", "")
        if not last_completed or not next_round:
            reasons.append("structured state incomplete (missing last_completed or next_round)")

        resume_from = next_round if next_round else "unknown"

        if reasons:
            return {
                "can_start": False,
                "reason": "; ".join(reasons),
                "resume_from_round": resume_from,
            }

        return {
            "can_start": True,
            "reason": "",
            "resume_from_round": resume_from,
        }

    def check_can_pause(self) -> Dict[str, Any]:
        """
        /pause semantics: safe stop after current round completes, before next dispatch.

        Returns dict with:
        - can_pause: bool
        - reason: str
        - current_round: str
        """
        manifest = self._load_manifest()
        current_round = manifest.get("current_round", "NONE")
        chain_status = manifest.get("chain_status", "")

        # Already paused
        if self.pause_manager.is_paused():
            return {"can_pause": False, "reason": "Already paused", "current_round": current_round}

        # Safe to pause if no round is currently in progress
        if current_round == "NONE" or chain_status == "frozen_pending_backlog_merge":
            return {"can_pause": True, "reason": "", "current_round": current_round}

        # If a round is in progress, pause should happen AFTER it completes
        return {"can_pause": True, "reason": "pause_after_current_round_completes", "current_round": current_round}
