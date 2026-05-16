from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone


@dataclass
class OrderBookLevel:
    price: float
    volume: int
    side: str


@dataclass
class OrderBookSnapshot:
    symbol: str
    bids: list[OrderBookLevel] = field(default_factory=list)
    asks: list[OrderBookLevel] = field(default_factory=list)
    timestamp: str = ""

    def spread(self) -> float:
        if not self.bids or not self.asks:
            return 0.0
        return self.asks[0].price - self.bids[0].price

    def mid_price(self) -> float:
        if not self.bids or not self.asks:
            return 0.0
        return (self.bids[0].price + self.asks[0].price) / 2.0

    def imbalance(self) -> float:
        bid_vol = sum(b.volume for b in self.bids[:5])
        ask_vol = sum(a.volume for a in self.asks[:5])
        total = bid_vol + ask_vol
        if total == 0:
            return 0.0
        return (bid_vol - ask_vol) / total


@dataclass
class MicrostructureFeatures:
    symbol: str
    spread_bps: float
    order_book_imbalance: float
    avg_trade_size: float
    trade_frequency: float
    volatility_bps: float
    liquidity_tier: int


class MicrostructureEngine:
    def __init__(self):
        self._snapshots: dict[str, list[OrderBookSnapshot]] = {}

    def record_snapshot(self, snapshot: OrderBookSnapshot) -> None:
        if snapshot.symbol not in self._snapshots:
            self._snapshots[snapshot.symbol] = []
        self._snapshots[snapshot.symbol].append(snapshot)

    def get_snapshots(self, symbol: str) -> list[OrderBookSnapshot]:
        return self._snapshots.get(symbol, [])

    def compute_features(self, symbol: str) -> MicrostructureFeatures | None:
        snaps = self._snapshots.get(symbol, [])
        if not snaps:
            return None
        latest = snaps[-1]
        spread = latest.spread()
        mid = latest.mid_price()
        spread_bps = (spread / mid) * 10000 if mid > 0 else 0
        imb = latest.imbalance()
        return MicrostructureFeatures(
            symbol=symbol,
            spread_bps=spread_bps,
            order_book_imbalance=imb,
            avg_trade_size=0.0,
            trade_frequency=0.0,
            volatility_bps=0.0,
            liquidity_tier=1 if spread_bps < 10 else (2 if spread_bps < 50 else 3),
        )

    def clear(self) -> None:
        self._snapshots.clear()
