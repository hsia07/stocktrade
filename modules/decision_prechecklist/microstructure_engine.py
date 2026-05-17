from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timezone, time
from enum import Enum


class MarketSession(Enum):
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"


@dataclass
class FillFeasibility:
    symbol: str
    side: str
    quantity: int
    price: float
    fillable_qty: int
    avg_fill_price: float
    slippage_bps: float
    reason: str = ""


@dataclass
class LimitUpDownInfo:
    symbol: str
    limit_up: float
    limit_down: float
    reference_price: float
    distance_to_up_pct: float
    distance_to_down_pct: float


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
    previous_close: float = 0.0

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

    def get_limit_up_down(self, pct: float = 0.10) -> LimitUpDownInfo:
        ref = self.previous_close if self.previous_close > 0 else self.mid_price()
        limit_up = ref * (1 + pct)
        limit_down = ref * (1 - pct)
        mid = self.mid_price()
        return LimitUpDownInfo(
            symbol=self.symbol,
            limit_up=round(limit_up, 2),
            limit_down=round(limit_down, 2),
            reference_price=round(ref, 2),
            distance_to_up_pct=((limit_up - mid) / mid * 100) if mid > 0 else 0,
            distance_to_down_pct=((mid - limit_down) / mid * 100) if mid > 0 else 0,
        )

    def assess_fill(self, side: str, quantity: int, price: float) -> FillFeasibility:
        levels = self.asks if side.lower() == "buy" else self.bids
        remaining = quantity
        filled = 0
        total_cost = 0.0
        fill_price = price
        for level in levels:
            if remaining <= 0:
                break
            if (side.lower() == "buy" and level.price > price) or (side.lower() == "sell" and level.price < price):
                continue
            take = min(remaining, level.volume)
            filled += take
            total_cost += take * level.price
            remaining -= take
            fill_price = level.price
        avg_price = total_cost / filled if filled > 0 else 0.0
        slippage_bps = abs(avg_price - price) / price * 10000 if price > 0 and filled > 0 else 0
        reason = ""
        if filled < quantity:
            reason = "insufficient_depth"
        return FillFeasibility(
            symbol=self.symbol,
            side=side,
            quantity=quantity,
            price=price,
            fillable_qty=filled,
            avg_fill_price=round(avg_price, 2),
            slippage_bps=round(slippage_bps, 2),
            reason=reason,
        )


@dataclass
class MicrostructureFeatures:
    symbol: str
    spread_bps: float
    order_book_imbalance: float
    avg_trade_size: float
    trade_frequency: float
    volatility_bps: float
    liquidity_tier: int
    fill_feasibility: FillFeasibility | None = None
    limit_up_down: LimitUpDownInfo | None = None
    market_session: MarketSession = MarketSession.REGULAR


class MicrostructureEngine:
    TAIWAN_REGULAR_START = time(9, 0)
    TAIWAN_REGULAR_END = time(13, 30)
    TAIWAN_PRE_START = time(8, 30)
    TAIWAN_POST_END = time(14, 30)

    def __init__(self):
        self._snapshots: dict[str, list[OrderBookSnapshot]] = {}

    def record_snapshot(self, snapshot: OrderBookSnapshot) -> None:
        if snapshot.symbol not in self._snapshots:
            self._snapshots[snapshot.symbol] = []
        self._snapshots[snapshot.symbol].append(snapshot)

    def get_snapshots(self, symbol: str) -> list[OrderBookSnapshot]:
        return self._snapshots.get(symbol, [])

    def get_current_session(self, dt: datetime | None = None) -> MarketSession:
        now = dt if dt is not None else datetime.now(timezone.utc)
        taipei = now.astimezone(timezone.utc)
        t = taipei.time()
        if self.TAIWAN_REGULAR_START <= t <= self.TAIWAN_REGULAR_END:
            return MarketSession.REGULAR
        if self.TAIWAN_PRE_START <= t < self.TAIWAN_REGULAR_START:
            return MarketSession.PRE_MARKET
        if self.TAIWAN_REGULAR_END < t <= self.TAIWAN_POST_END:
            return MarketSession.AFTER_HOURS
        return MarketSession.CLOSED

    def compute_features(self, symbol: str, side: str = "buy", quantity: int = 0, price: float = 0.0) -> MicrostructureFeatures | None:
        snaps = self._snapshots.get(symbol, [])
        if not snaps:
            return None
        latest = snaps[-1]
        spread = latest.spread()
        mid = latest.mid_price()
        spread_bps = (spread / mid) * 10000 if mid > 0 else 0
        imb = latest.imbalance()
        limit_up_down = latest.get_limit_up_down() if latest.previous_close > 0 else None
        fill_feas = latest.assess_fill(side, quantity, price) if quantity > 0 and price > 0 else None
        session = self.get_current_session()
        return MicrostructureFeatures(
            symbol=symbol,
            spread_bps=spread_bps,
            order_book_imbalance=imb,
            avg_trade_size=0.0,
            trade_frequency=0.0,
            volatility_bps=0.0,
            liquidity_tier=1 if spread_bps < 10 else (2 if spread_bps < 50 else 3),
            fill_feasibility=fill_feas,
            limit_up_down=limit_up_down,
            market_session=session,
        )

    def clear(self) -> None:
        self._snapshots.clear()
