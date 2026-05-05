"""
R026: Strategy Interaction Module"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class InteractionType(Enum):
    """Interaction type enumeration."""
    SELECT = "select"
    FILTER = "filter"
    SORT = "sort"
    VIEW = "view"


@dataclass`
class InteractionEvent:
    """Represents an interaction event."""
    strategy_id: str
    interaction_type: InteractionType
    timestamp: float
    metadata: Optional[Dict[str, Any]]


class StrategyInteractionManager:
    """Manages strategy interactions."""

    def __init__(self):
        self.interactions: List[InteractionEvent] = []
        self.selected_strategy: Optional[str] = None
        self.view_mode: str = "detail"

    def select_strategy(self, strategy_id: str) -> bool:
        """Select a strategy for interaction."""
        self.selected_strategy = strategy_id
        self._record_interaction(
            strategy_id, InteractionType.SELECT,
            {"new_selection": strategy_id}
        )
        return True

    def filter_strategies(self, filter_criteria: Dict[str, Any]) -> List[str]:
        """Filter strategies (UI only, NO execution)."""
        self._record_interaction(
            "filter", InteractionType.FILTER,
            filter_criteria
        )
        # This is UI-only, NO strategy execution
        return []

    def sort_strategies(self, sort_by: str, ascending: bool = False) -> None:
        """Sort strategies (UI only)."""
        self._record_interaction(
            "sort", InteractionType.SORT,
            {"sort_by": sort_by, "ascending": ascending}
        )

    def view_strategy_detail(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """View strategy detail (UI only, NO execution)."""
        self._record_interaction(
            strategy_id, InteractionType.VIEW,
            {"view_mode": "detail"}
        )
        # This is display-only, NO trading logic
        if self.selected_strategy == strategy_id:
            return {
                "id": strategy_id,
                "detail": "UI display only",
                "execution": False  # NO execution
            }
        return None

    def _record_interaction(
        self, strategy_id: str,
        interaction_type: InteractionType,
        metadata: Optional[Dict[str, Any]]
    ) -> None:
        """Record interaction event (for UI tracking only)."""
        import time
        event = InteractionEvent(
            strategy_id=strategy_id,
            interaction_type=interaction_type,
            timestamp=time.time(),
            metadata=metadata
        )
        self.interactions.append(event)

    def get_interaction_history(self) -> List[Dict[str, Any]]:
        """Get interaction history (UI tracking)."""
        return [
            {
                "strategy_id": e.strategy_id,
                "type": e.interaction_type.value,
                "timestamp": e.timestamp,
                "metadata": e.metadata
            }
            for e in self.interactions
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for UI rendering."""
        return {
            "selected_strategy": self.selected_strategy,
            "view_mode": self.view_mode,
            "interaction_count": len(self.interactions),
            "recent_interactions": [
                {
                    "strategy_id": e.strategy_id,
                    "type": e.interaction_type.value,
                    "timestamp": e.timestamp
                }
                for e in self.interactions[-5:]
            ]
        }
