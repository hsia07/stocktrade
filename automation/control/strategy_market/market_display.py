"""
R026: Strategy Market - Display and Interaction Module"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class MarketType(Enum):
    """Market type enumeration."""
    TWSE = "twse"
    TPEX = "tpex"
    ALL = "all"


@dataclass`
class MarketItem:
    """Market item for strategy market display."""
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    volume: int
    market_type: MarketType


class StrategyMarketDisplay:
    """Strategy market display and interaction."""

    def __init__(self, filter_market: MarketType = MarketType.ALL):
        self.market_items: List[MarketItem] = []
        self.filter_market = filter_market
        self.sort_by = "volume"
        self.sort_ascending = False

    def add_market_item(
        self, symbol: str, name: str, price: float,
        change: float, change_percent: float, volume: int, market_type: MarketType
    ) -> MarketItem:
        """Add a market item to display."""
        item = MarketItem(
            symbol=symbol, name=name, price=price,
            change=change, change_percent=change_percent,
            volume=volume, market_type=market_type
        )
        self.market_items.append(item)
        return item

    def filter_by_market(self, market: MarketType) -> List[MarketItem]:
        """Filter market items by type."""
        self.filter_market = market
        if market == MarketType.ALL:
            return self.market_items
        return [m for m in self.market_items if m.market_type == market]

    def sort_items(self, by: str = "volume", ascending: bool = False) -> None:
        """Sort market items."""
        self.sort_by = by
        self.sort_ascending = ascending
        reverse = not ascending
        if by == "volume":
            self.market_items.sort(key=lambda x: x.volume, reverse=reverse)
        elif by == "price":
            self.market_items.sort(key=lambda x: x.price, reverse=reverse)
        elif by == "change":
            self.market_items.sort(key=lambda x: x.change_percent, reverse=reverse)

    def get_top_items(self, count: int = 10) -> List[MarketItem]:
        """Get top market items by current sort."""
        return self.market_items[:count]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for UI rendering."""
        return {
            "markets": [
                {
                    "symbol": m.symbol,
                    "name": m.name,
                    "price": m.price,
                    "change": m.change,
                    "change_percent": m.change_percent,
                    "volume": m.volume,
                    "market_type": m.market_type.value
                }
                for m in self.market_items
            ],
            "filter_market": self.filter_market.value,
            "sort_by": self.sort_by,
            "sort_ascending": self.sort_ascending
        }
