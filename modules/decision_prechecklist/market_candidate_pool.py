from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MarketCandidate:
    symbol: str
    name: str
    sector: str
    price: float
    volume: int
    market_cap: float
    liquidity_score: float
    is_taiwan_stock: bool = True
    extra: dict[str, Any] = field(default_factory=dict)


class CandidatePool:
    def __init__(self):
        self._candidates: dict[str, MarketCandidate] = {}

    def add(self, candidate: MarketCandidate) -> None:
        self._candidates[candidate.symbol] = candidate

    def remove(self, symbol: str) -> bool:
        return self._candidates.pop(symbol, None) is not None

    def get(self, symbol: str) -> MarketCandidate | None:
        return self._candidates.get(symbol)

    def query(self, sector: str | None = None, min_liquidity: float = 0.0) -> list[MarketCandidate]:
        results = list(self._candidates.values())
        if sector:
            results = [c for c in results if c.sector == sector]
        if min_liquidity > 0:
            results = [c for c in results if c.liquidity_score >= min_liquidity]
        return results

    def all(self) -> list[MarketCandidate]:
        return list(self._candidates.values())

    def count(self) -> int:
        return len(self._candidates)

    def clear(self) -> None:
        self._candidates.clear()


class ArbitraryStockQuerier:
    def __init__(self, pool: CandidatePool | None = None):
        self._pool = pool or CandidatePool()

    @property
    def pool(self) -> CandidatePool:
        return self._pool

    def get_candidate(self, symbol: str) -> MarketCandidate | None:
        return self._pool.get(symbol)

    def list_by_sector(self, sector: str) -> list[MarketCandidate]:
        return self._pool.query(sector=sector)

    def list_by_liquidity(self, min_score: float) -> list[MarketCandidate]:
        return self._pool.query(min_liquidity=min_score)
