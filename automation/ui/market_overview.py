"""
R026: Modular Trading Interface - Market Overview Component

Provides market overview display and interaction.
R026 scope ONLY: UI component, NO market data fetching or trading.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MarketItem:
    """Market item information."""
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    volume: int
    market_type: str


class MarketOverview:
    """Modular market overview component."""

    def __init__(self):
        self.markets: List[MarketItem] = []
        self.sort_by: str = "volume"
        self.sort_ascending: bool = False

    def add_market_item(self, symbol: str, name: str, price: float, change: float, change_percent: float, volume: int, market_type: str) -> MarketItem:
        """Add a market item to overview."""
        item = MarketItem(
            symbol=symbol,
            name=name,
            price=price,
            change=change,
            change_percent=change_percent,
            volume=volume,
            market_type=market_type
        )
        self.markets.append(item)
        return item

    def sort_items(self, by: str = "volume", ascending: bool = False) -> None:
        """Sort market items."""
        self.sort_by = by
        self.sort_ascending = ascending
        reverse = not ascending
        if by == "volume":
            self.markets.sort(key=lambda x: x.volume, reverse=reverse)
        elif by == "price":
            self.markets.sort(key=lambda x: x.price, reverse=reverse)
        elif by == "change":
            self.markets.sort(key=lambda x: x.change_percent, reverse=reverse)

    def filter_by_type(self, market_type: str) -> List[MarketItem]:
        """Filter markets by type."""
        if market_type == "all":
            return self.markets
        return [m for m in self.markets if m.market_type == market_type]

    def get_top_items(self, count: int = 10) -> List[MarketItem]:
        """Get top market items by current sort."""
        return self.markets[:count]

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
                    "market_type": m.market_type
                }
                for m in self.markets
            ],
            "sort_by": self.sort_by,
            "sort_ascending": self.sort_ascending
        }
