"""
Round Phase State Machine

Defines canonical machine-readable phases for the candidate-only
auto-advance governance chain.
"""

from enum import Enum


class RoundPhase(str, Enum):
    """Canonical phases for round lifecycle."""

    NONE = "none"
    ROUND_ENTERED = "round_entered"
    CONSTRUCTION_BOOTSTRAP = "construction_bootstrap"
    CONSTRUCTION_IN_PROGRESS = "construction_in_progress"
    CANDIDATE_MATERIALIZING = "candidate_materializing"
    CANDIDATE_READY = "candidate_ready"
    VALIDATION_IN_PROGRESS = "validation_in_progress"
    MERGE_PRE_REVIEW = "merge_pre_review"
    MERGE_EXECUTION = "merge_execution"
    PUSH_EXECUTION = "push_execution"
    COMPLETED = "completed"
    STOPPED = "stopped"

    @classmethod
    def is_active_phase(cls, phase: str) -> bool:
        """Return True if phase represents an active (non-terminal) state."""
        return phase in {
            cls.ROUND_ENTERED,
            cls.CONSTRUCTION_BOOTSTRAP,
            cls.CONSTRUCTION_IN_PROGRESS,
            cls.CANDIDATE_MATERIALIZING,
            cls.CANDIDATE_READY,
            cls.VALIDATION_IN_PROGRESS,
            cls.MERGE_PRE_REVIEW,
            cls.MERGE_EXECUTION,
            cls.PUSH_EXECUTION,
        }

    @classmethod
    def is_terminal_phase(cls, phase: str) -> bool:
        """Return True if phase is terminal (completed or stopped)."""
        return phase in {cls.COMPLETED, cls.STOPPED}

    @classmethod
    def requires_construction(cls, phase: str) -> bool:
        """Return True if phase involves construction work."""
        return phase in {
            cls.CONSTRUCTION_BOOTSTRAP,
            cls.CONSTRUCTION_IN_PROGRESS,
            cls.CANDIDATE_MATERIALIZING,
        }
