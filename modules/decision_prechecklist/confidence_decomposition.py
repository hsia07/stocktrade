from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


CONFIDENCE_SOURCE_KEYS = frozenset({
    "pattern",
    "fundamental",
    "regime_alignment",
    "signal_source_reliability",
    "timeframe_alignment",
    "data_quality",
    "contradiction_resolution",
})


@dataclass
class ConfidenceSource:
    key: str
    label: str
    weight: float
    raw_score: float
    calibrated_score: float
    justification: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfidenceDecompositionReport:
    raw_confidence: float
    overall_calibrated: float
    sources: list[ConfidenceSource] = field(default_factory=list)
    veto_reason: str = ""
    is_fallback: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def get_source(self, key: str) -> ConfidenceSource | None:
        for s in self.sources:
            if s.key == key:
                return s
        return None

    def get_source_summary(self) -> dict[str, dict[str, float]]:
        return {
            s.key: {
                "weight": s.weight,
                "raw": s.raw_score,
                "calibrated": s.calibrated_score,
            }
            for s in self.sources
        }


DEFAULT_SOURCE_CONFIG: dict[str, dict[str, float]] = {
    "pattern": {"weight": 0.20, "min_raw": 0.0},
    "fundamental": {"weight": 0.20, "min_raw": 0.0},
    "regime_alignment": {"weight": 0.15, "min_raw": 0.0},
    "signal_source_reliability": {"weight": 0.15, "min_raw": 0.0},
    "timeframe_alignment": {"weight": 0.10, "min_raw": 0.0},
    "data_quality": {"weight": 0.10, "min_raw": 0.0},
    "contradiction_resolution": {"weight": 0.10, "min_raw": 0.0},
}


class ConfidenceSourceDecomposer:
    def __init__(
        self,
        source_config: dict[str, dict[str, float]] | None = None,
        brier_penalty_threshold: float = 0.30,
        low_experience_threshold: int = 5,
        default_regime_uncertainty_penalty: float = 0.0,
    ):
        self._config = source_config or DEFAULT_SOURCE_CONFIG
        self._validate_config()
        self._brier_penalty_threshold = brier_penalty_threshold
        self._low_experience_threshold = low_experience_threshold
        self._default_regime_uncertainty_penalty = default_regime_uncertainty_penalty

        self._key_to_label = {
            "pattern": "Pattern Recognition",
            "fundamental": "Fundamental Conviction",
            "regime_alignment": "Regime Alignment",
            "signal_source_reliability": "Signal Source Reliability",
            "timeframe_alignment": "Timeframe Alignment",
            "data_quality": "Data Quality",
            "contradiction_resolution": "Contradiction Resolution",
        }

    def _validate_config(self) -> None:
        total_weight = sum(cfg.get("weight", 0) for cfg in self._config.values())
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(
                f"Source config weights must sum to 1.0, got {total_weight:.4f}"
            )
        missing = CONFIDENCE_SOURCE_KEYS - set(self._config.keys())
        if missing:
            raise ValueError(f"Missing source keys in config: {missing}")
        extra = set(self._config.keys()) - CONFIDENCE_SOURCE_KEYS
        if extra:
            raise ValueError(f"Unknown source keys in config: {extra}")

    def decompose(
        self,
        raw_confidence: float,
        source_scores: dict[str, float] | None = None,
        historical_brier_score: float | None = None,
        num_past_decisions: int = 0,
        regime_uncertainty: float = 0.0,
    ) -> ConfidenceDecompositionReport:
        if raw_confidence < 0.0 or raw_confidence > 1.0:
            return ConfidenceDecompositionReport(
                raw_confidence=raw_confidence,
                overall_calibrated=0.0,
                sources=[],
                veto_reason=f"raw_confidence out of range [0,1]: {raw_confidence}",
                is_fallback=True,
                details={
                    "historical_brier_score": historical_brier_score,
                    "num_past_decisions": num_past_decisions,
                    "regime_uncertainty": regime_uncertainty,
                },
            )

        source_scores = source_scores or {}
        sources: list[ConfidenceSource] = []
        overall_calibrated = 0.0
        veto_reason = ""

        brier_penalty = 1.0
        if historical_brier_score is not None and historical_brier_score > self._brier_penalty_threshold:
            brier_penalty = 0.5

        experience_penalty = 1.0
        if num_past_decisions < self._low_experience_threshold:
            experience_penalty = 0.8

        regime_penalty = max(0.0, 1.0 - regime_uncertainty)

        for key, cfg in self._config.items():
            weight = cfg["weight"]
            min_raw = cfg.get("min_raw", 0.0)
            raw_score = source_scores.get(key, raw_confidence)
            raw_score = max(0.0, min(1.0, raw_score))

            if raw_score < min_raw:
                sources = []
                return ConfidenceDecompositionReport(
                    raw_confidence=raw_confidence,
                    overall_calibrated=0.0,
                    sources=[],
                    veto_reason=(
                        f"source '{key}' raw_score {raw_score:.4f} "
                        f"below min_raw {min_raw:.4f}"
                    ),
                    is_fallback=False,
                    details={
                        "historical_brier_score": historical_brier_score,
                        "num_past_decisions": num_past_decisions,
                        "regime_uncertainty": regime_uncertainty,
                    },
                )

            sub_calibrated = raw_score * brier_penalty * experience_penalty * regime_penalty
            sub_calibrated = max(0.0, min(1.0, sub_calibrated))

            sources.append(ConfidenceSource(
                key=key,
                label=self._key_to_label.get(key, key),
                weight=weight,
                raw_score=raw_score,
                calibrated_score=sub_calibrated,
                justification=f"raw={raw_score:.4f} * brier={brier_penalty:.2f} * exp={experience_penalty:.2f} * regime={regime_penalty:.2f}",
                metadata={
                    "brier_penalty": brier_penalty,
                    "experience_penalty": experience_penalty,
                    "regime_penalty": regime_penalty,
                },
            ))

            overall_calibrated += sub_calibrated * weight

        return ConfidenceDecompositionReport(
            raw_confidence=raw_confidence,
            overall_calibrated=overall_calibrated,
            sources=sources,
            veto_reason=veto_reason,
            is_fallback=False,
            details={
                "historical_brier_score": historical_brier_score,
                "num_past_decisions": num_past_decisions,
                "regime_uncertainty": regime_uncertainty,
                "brier_penalty": brier_penalty,
                "experience_penalty": experience_penalty,
                "regime_penalty": regime_penalty,
            },
        )
