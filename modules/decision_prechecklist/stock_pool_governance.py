from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class PoolTier(Enum):
    CORE = "core"
    WATCH = "watch"
    EXPLORE = "explore"
    RESTRICTED = "restricted"
    EXCLUDED = "excluded"


@dataclass
class TieredStock:
    symbol: str
    tier: PoolTier
    max_position_pct: float = 0.05
    max_daily_trades: int = 10
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


DEFAULT_TIER_LIMITS: dict[PoolTier, dict[str, float]] = {
    PoolTier.CORE: {"max_position_pct": 0.05, "max_daily_trades": 20},
    PoolTier.WATCH: {"max_position_pct": 0.03, "max_daily_trades": 10},
    PoolTier.EXPLORE: {"max_position_pct": 0.01, "max_daily_trades": 5},
    PoolTier.RESTRICTED: {"max_position_pct": 0.005, "max_daily_trades": 2},
    PoolTier.EXCLUDED: {"max_position_pct": 0.0, "max_daily_trades": 0},
}


class TierGovernor:
    def __init__(self):
        self._stocks: dict[str, TieredStock] = {}

    def register(self, stock: TieredStock) -> None:
        self._stocks[stock.symbol] = stock

    def get(self, symbol: str) -> TieredStock | None:
        return self._stocks.get(symbol)

    def get_tier(self, symbol: str) -> PoolTier | None:
        s = self._stocks.get(symbol)
        return s.tier if s else None

    def can_trade(self, symbol: str, daily_trade_count: int = 0) -> bool:
        s = self._stocks.get(symbol)
        if s is None:
            return False
        if s.tier == PoolTier.EXCLUDED:
            return False
        limits = DEFAULT_TIER_LIMITS.get(s.tier, {})
        max_trades = int(limits.get("max_daily_trades", 0))
        if max_trades > 0 and daily_trade_count >= max_trades:
            return False
        return True

    def max_position(self, symbol: str) -> float:
        s = self._stocks.get(symbol)
        if s is None:
            return 0.0
        limits = DEFAULT_TIER_LIMITS.get(s.tier, {})
        return limits.get("max_position_pct", 0.0)

    def list_by_tier(self, tier: PoolTier) -> list[TieredStock]:
        return [s for s in self._stocks.values() if s.tier == tier]

    def count_by_tier(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in self._stocks.values():
            counts[s.tier.value] = counts.get(s.tier.value, 0) + 1
        return counts
