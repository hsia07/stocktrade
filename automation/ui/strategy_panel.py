"""
R026: Modular Trading Interface - Strategy Panel Component

Provides strategy display and interaction panel.
R026 scope ONLY: UI component, NO strategy execution logic.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class StrategyStatus(Enum):
    """Strategy status enumeration."""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    BACKTESTING = "backtesting"


@dataclass
class StrategyInfo:
    """Strategy information for display."""
    id: str
    name: str
    status: StrategyStatus
    performance: Dict[str, float]
    market: str


class StrategyPanel:
    """Modular strategy panel for trading interface."""

    def __init__(self):
        self.strategies: List[StrategyInfo] = []
        self.selected_strategy: Optional[str] = None
        self.market_filter: str = "all"

    def add_strategy(self, strategy_id: str, name: str, status: StrategyStatus, performance: Dict[str, float], market: str) -> StrategyInfo:
        """Add a strategy to the panel."""
        strategy = StrategyInfo(
            id=strategy_id,
            name=name,
            status=status,
            performance=performance,
            market=market
        )
        self.strategies.append(strategy)
        return strategy

    def select_strategy(self, strategy_id: str) -> bool:
        """Select a strategy for interaction."""
        if any(s.id == strategy_id for s in self.strategies):
            self.selected_strategy = strategy_id
            return True
        return False

    def filter_by_market(self, market: str) -> List[StrategyInfo]:
        """Filter strategies by market."""
        self.market_filter = market
        if market == "all":
            return self.strategies
        return [s for s in self.strategies if s.market == market]

    def get_selected_strategy(self) -> Optional[StrategyInfo]:
        """Get selected strategy info."""
        if self.selected_strategy is None:
            return None
        return next((s for s in self.strategies if s.id == self.selected_strategy), None)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for UI rendering."""
        return {
            "strategies": [
                {
                    "id": s.id,
                    "name": s.name,
                    "status": s.status.value,
                    "performance": s.performance,
                    "market": s.market
                }
                for s in self.strategies
            ],
            "selected": self.selected_strategy,
            "market_filter": self.market_filter
        }
