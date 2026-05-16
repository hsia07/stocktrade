from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


@dataclass
class Feature:
    name: str
    category: str
    value: float
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RegimeInfo:
    regime_id: str
    name: str
    uncertainty: float
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class StrategyType(Enum):
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    ARBITRAGE = "arbitrage"
    TREND_FOLLOWING = "trend_following"
    VALUE = "value"
    OTHER = "other"


@dataclass
class StrategyInfo:
    strategy_id: str
    name: str
    strategy_type: StrategyType
    regime: str
    confidence: float
    features: list[Feature] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyEvaluationResult:
    strategy_id: str
    passed: bool
    confidence: float
    veto_reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)
