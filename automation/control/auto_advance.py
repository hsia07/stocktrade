"""
Auto-Advance Controller

Governance rules for candidate-pass auto-advancement:
- Auto-advance ONLY if round completed with no blockers, no gates, complete evidence
- Merge / push / activation / authorization gates always STOP
- /pause gate always STOP
- Evidence incompleteness always STOP
"""

import logging
from typing import Dict, Any, Tuple, List
from pathlib import Path

from automation.control.pause_state import PauseStateManager
from automation.control.evidence_checker import EvidenceChecker

logger = logging.getLogger("auto_advance")


class AutoAdvanceController:
    """Determine whether a completed round may auto-advance to the next."""

    STOP_GATES = [
        "merge_gate",
        "push_gate",
        "activation_gate",
        "authorization_gate",
        "blocker_gate",
        "pause_gate",
        "evidence_gate",
        "review_gate",
        "round_status_gate",
    ]

    BLOCKED_STATUS_CODES = [
        "blocked",
        "candidate_ready_awaiting_manual_review",
    ]

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.pause_manager = PauseStateManager(self.repo_root)
        self.evidence_checker = EvidenceChecker(self.repo_root)

    def can_auto_advance(self, round_result: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        Return (can_advance, reason, gate_type).

        For a NEW round dispatch (round_result has no candidate yet),
        this returns True with gate_type="construction_bootstrap" so the
        caller knows to enter construction phase instead of stopping.
        """
        # Special case: new round with no materialized candidate
        # should enter construction bootstrap, NOT stop at candidate_gate
        if round_result.get("is_new_round_dispatch", False):
            if not round_result.get("candidate_exists", False):
                return True, "entering_construction_bootstrap", "construction_bootstrap_gate"
            # If candidate exists for new dispatch, allow to proceed
            return True, "candidate_exists_proceed", "none"

        # Standard advance checks for completed rounds
        # Gate types: merge_gate, push_gate, activation_gate, authorization_gate,
        #             blocker_gate, pause_gate, evidence_gate, review_gate,
        #             round_status_gate, none
        # 1. Round must be completed
        if round_result.get("status") != "completed":
            return False, "status_not_completed", "round_status_gate"

        # 2. formal_status_code must not be blocked or awaiting review
        formal_code = round_result.get("formal_status_code", "")
        if formal_code in self.BLOCKED_STATUS_CODES:
            return False, f"formal_status_code={formal_code}", "review_gate"

        # 3. No blockers
        blockers = round_result.get("blockers_found", [])
        if blockers:
            return False, f"blockers_present: {blockers}", "blocker_gate"

        # 4. Evidence completeness
        evidence_dir = round_result.get("evidence_directory")
        if evidence_dir:
            complete, missing = self.evidence_checker.check_completeness(Path(evidence_dir))
            if not complete:
                return False, f"evidence_incomplete: {missing}", "evidence_gate"

        # 5. No merge/push/activation/authorization gate encountered
        for gate in ["merge_gate", "push_gate", "activation_gate", "authorization_gate"]:
            if round_result.get(f"{gate}_encountered"):
                return False, f"{gate}_encountered", gate

        # 6. /pause gate
        if self.pause_manager.is_paused():
            return False, "pause_requested", "pause_gate"

        return True, "all_conditions_met", "none"

    def get_stop_gates(self) -> List[str]:
        """Return list of gates that will block auto-advance."""
        return self.STOP_GATES.copy()
