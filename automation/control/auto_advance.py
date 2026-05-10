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

BLOCKER_I: Next-round dispatch scaffold.
- After auto-candidate signoff passes, can_dispatch_next_round checks if the
  next round is defined. dispatch_next_round creates the candidate scaffold
  (branch name, evidence skeleton) but does NOT merge, push, promote, or PR.
- merge / push / promote remain blocked at the caller level.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List, Optional
from pathlib import Path

from automation.control.pause_state import PauseStateManager
from automation.control.evidence_checker import EvidenceChecker
from automation.control.evidence_gate_orchestrator import EvidenceGateOrchestrator

logger = logging.getLogger("auto_advance")

ROUND_SEQUENCE: list[str] = [
    "BLOCKER_G",
    "FIX-EVIDENCE-CHECKER-INDENTATION",
    "BLOCKER_F",
    "BLOCKER_E",
    "BLOCKER_I",
    "BLOCKER_H",
    "BLOCKER_C",
    "BLOCKER_D",
    "AUTO_ADVANCE_OPERATIONAL",
]


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

    UNDEFINED_ROUND_VALUES = ["", "none", "undefined", "law_undefined"]

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.pause_manager = PauseStateManager(self.repo_root)
        self.evidence_checker = EvidenceChecker(self.repo_root)
        self.evidence_gate_orchestrator = EvidenceGateOrchestrator(self.repo_root)

    def is_auto_candidate_status(self, formal_code: str) -> bool:
        return formal_code == self.AUTO_CANDIDATE_READY

    def _is_round_defined(self, round_id: str) -> Tuple[bool, str]:
        """
        Check whether a round_id is defined (not None, empty, NONE, undefined, law_undefined).

        Returns:
            (True, "") if defined,
            (False, "reason") if undefined.
        """
        if round_id is None:
            return False, "round_id_is_None"
        normalized = round_id.strip().lower()
        if normalized in self.UNDEFINED_ROUND_VALUES:
            return False, f"round_id_is_undefined: '{round_id}'"
        return True, ""

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

        # 1. Current round must be defined (blocks construction/dispatch for NONE/undefined)
        round_id = round_result.get("round_id", "")
        is_defined, undefined_reason = self._is_round_defined(round_id)
        if not is_defined:
            return False, f"undefined_round: {undefined_reason}", "undefined_round_gate"

        # 2. Round must be completed
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

        # 5. Evidence gate — unified orchestrator verdict (both paths)
        evidence_dir = round_result.get("evidence_directory")
        if evidence_dir:
            gate_report = self.evidence_gate_orchestrator.run_evidence_gate(Path(evidence_dir))
            if gate_report["verdict"] == "BLOCKED":
                blocked_at = gate_report.get("blocked_at_gate", "unknown")
                return False, f"evidence_blocked:gate={blocked_at}", "evidence_gate"

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

    def determine_next_round(self, current_round_id: str) -> Optional[str]:
        """Return the next round ID based on ROUND_SEQUENCE, or None if last."""
        current_upper = current_round_id.strip().upper()
        for i, rid in enumerate(ROUND_SEQUENCE):
            if rid == current_upper:
                if i + 1 < len(ROUND_SEQUENCE):
                    return ROUND_SEQUENCE[i + 1]
                return None
        return None

    def can_dispatch_next_round(self, round_result: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        Check whether the system may dispatch the next round.

        Returns (can_dispatch, reason, gate_or_detail).

        Conditions:
        1. auto-candidate path must be clear (can_auto_advance returns go)
        2. A next round ID must be determinable from the current round
        3. merge / push / promote remain blocked at caller level (enforced
           externally, not checked here)

        The round_result must contain a "round_id" key for sequence lookup.
        """
        # 0. Current round must be defined (defense-in-depth, checked before auto-advance)
        current_round = round_result.get("round_id", "")
        is_defined, undefined_reason = self._is_round_defined(current_round)
        if not is_defined:
            return False, f"undefined_round: {undefined_reason}", "undefined_round_gate"

        can_advance, reason, gate = self.can_auto_advance(round_result)
        if not can_advance:
            return False, f"auto_advance_blocked: {reason}", gate
        next_round = self.determine_next_round(current_round)
        if not next_round:
            return False, f"no_next_round_defined: {current_round}", "sequence_end_gate"

        return True, f"can_dispatch:{next_round}", next_round

    def dispatch_next_round(self, round_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create the next-round candidate scaffold (directory + skeleton).

        Returns a dict with dispatch outcome. Does NOT merge, push, promote,
        or create a PR. The caller must enforce those constraints.

        The scaffold includes:
        - A candidate directory under automation/control/candidates/
        - Minimal evidence.json with round_id and timestamp
        - A task.txt placeholder

        The caller is responsible for creating the git branch.
        """
        can_dispatch, reason, detail = self.can_dispatch_next_round(round_result)
        if not can_dispatch:
            return {
                "dispatch_executed": False,
                "reason": reason,
                "detail": detail,
                "scaffold_created": False,
                "scaffold_path": None,
                "next_round_id": None,
                "merge_executed": False,
                "push_executed": False,
                "promote_executed": False,
                "pr_created": False,
            }

        next_round_id = detail
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        scaffold_dir = self.repo_root / "automation" / "control" / "candidates" / next_round_id
        scaffold_dir.mkdir(parents=True, exist_ok=True)

        evidence = {
            "round_id": next_round_id,
            "task_type": "auto_dispatch_scaffold",
            "phase": "governance",
            "law_compliance": "04",
            "dispatched_at": timestamp,
            "source_round": round_result.get("round_id", "unknown"),
            "scaffold_only": True,
            "merge_blocked": True,
            "push_blocked": True,
            "promote_blocked": True,
        }
        evidence_path = scaffold_dir / "evidence.json"
        evidence_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")

        task_path = scaffold_dir / "task.txt"
        task_path.write_text(
            f"=== AUTO-DISPATCHED SCAFFOLD ===\n"
            f"round_id: {next_round_id}\n"
            f"dispatched_at: {timestamp}\n"
            f"source_round: {round_result.get('round_id', 'unknown')}\n"
            f"This is a scaffold only. No merge, push, promote, or PR was executed.\n",
            encoding="utf-8",
        )

        return {
            "dispatch_executed": True,
            "reason": reason,
            "detail": detail,
            "scaffold_created": True,
            "scaffold_path": str(scaffold_dir),
            "next_round_id": next_round_id,
            "merge_executed": False,
            "push_executed": False,
            "promote_executed": False,
            "pr_created": False,
        }
