"""
Auto-Advance Controller

Two-mode governance for candidate-pass auto-advancement:

Auto-candidate mode (formal_status_code == auto_candidate_ready):
- Bypasses manual STOP_GATES (merge/push/activation/authorization)
- Still blocked by safety gates: blockers, evidence, pause
- Requires machine-checkable automated signoff (hash, law, evidence)
- Designed for BLOCKER_E + BLOCKER_F auto-advance path

Bounded auto-mode (all other status codes):
- Original behavior preserved: STOP_GATES fully enforced
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
        "signoff_gate",
        "blocker_gate",
        "pause_gate",
        "evidence_gate",
        "review_gate",
        "round_status_gate",
    ]

    SIGNOFF_REQUIREMENTS = [
        "hash_verified",
        "law_compliance_verified",
        "evidence_validated",
    ]

    BLOCKED_STATUS_CODES = [
        "blocked",
        "candidate_ready_awaiting_manual_review",
    ]

    AUTO_CANDIDATE_READY = "auto_candidate_ready"

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.pause_manager = PauseStateManager(self.repo_root)
        self.evidence_checker = EvidenceChecker(self.repo_root)

    def is_auto_candidate_status(self, formal_code: str) -> bool:
        return formal_code == self.AUTO_CANDIDATE_READY

    def verify_automated_signoff(self, round_result: Dict[str, Any]) -> List[str]:
        """
        Check machine-verifiable signoff conditions for auto-candidate path.
        Returns list of missing/unverified requirements (empty = all passed).
        """
        signoff = round_result.get("automated_signoff", {})
        missing = []
        for req in self.SIGNOFF_REQUIREMENTS:
            if not signoff.get(req, False):
                missing.append(req)
        return missing

    def can_auto_advance(self, round_result: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        Return (can_advance, reason, gate_type).

        Two paths:
        - Auto-candidate path (formal_status_code == auto_candidate_ready):
          bypasses manual STOP_GATES (merge/push/activation/authorization),
          still blocked by safety gates (blockers, evidence, pause),
          requires automated signoff verification.
        - Bounded auto-mode path (all other status codes): full STOP_GATES
          enforcement, unchanged from pre-BLOCKER_F behavior.

        For a NEW round dispatch (round_result has no candidate yet),
        this returns True with gate_type="construction_bootstrap" so the
        caller knows to enter construction phase instead of stopping.
        """
        # Special case: new round with no materialized candidate
        if round_result.get("is_new_round_dispatch", False):
            if not round_result.get("candidate_exists", False):
                return True, "entering_construction_bootstrap", "construction_bootstrap_gate"
            return True, "candidate_exists_proceed", "none"

        # 1. Round must be completed
        if round_result.get("status") != "completed":
            return False, "status_not_completed", "round_status_gate"

        # 2. formal_status_code must not be blocked or awaiting review
        formal_code = round_result.get("formal_status_code", "")
        if formal_code in self.BLOCKED_STATUS_CODES:
            return False, f"formal_status_code={formal_code}", "review_gate"

        # 3. Determine if this is an auto-candidate
        is_auto = self.is_auto_candidate_status(formal_code)

        # 4. Blockers — block always (both paths)
        blockers = round_result.get("blockers_found", [])
        if blockers:
            return False, f"blockers_present: {blockers}", "blocker_gate"

        # 5. Evidence completeness — required always (both paths)
        evidence_dir = round_result.get("evidence_directory")
        if evidence_dir:
            complete, missing = self.evidence_checker.check_completeness(Path(evidence_dir))
            if not complete:
                return False, f"evidence_incomplete: {missing}", "evidence_gate"

        # 6. Pause — blocks always (both paths)
        if self.pause_manager.is_paused():
            return False, "pause_requested", "pause_gate"

        # 7. Path selection
        if is_auto:
            # Auto-candidate path: require machine-checkable signoff
            missing_signoff = self.verify_automated_signoff(round_result)
            if missing_signoff:
                return False, f"signoff_incomplete: {missing_signoff}", "signoff_gate"
            return True, "auto_candidate_path_clear", "none"

        # Bounded auto-mode: check manual STOP_GATES
        for gate in ["merge_gate", "push_gate", "activation_gate", "authorization_gate"]:
            if round_result.get(f"{gate}_encountered"):
                return False, f"{gate}_encountered", gate

        return True, "all_conditions_met", "none"

    def get_stop_gates(self) -> List[str]:
        """Return list of gates that will block auto-advance."""
        return self.STOP_GATES.copy()
