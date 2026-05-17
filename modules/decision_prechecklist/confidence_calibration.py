from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .confidence_decomposition import ConfidenceDecompositionReport


@dataclass
class CalibratedConfidence:
    raw_confidence: float
    calibrated_confidence: float
    calibration_factor: float
    veto_reason: str
    is_fallback: bool
    details: dict[str, Any] = field(default_factory=dict)
    decomposition: Any = None


class ConfidenceCalibrationGuard:
    def __init__(self, default_calibration_factor: float = 0.5):
        self._default_calibration_factor = default_calibration_factor

    def evaluate(
        self,
        raw_confidence: float,
        historical_brier_score: float | None = None,
        num_past_decisions: int = 0,
        regime_uncertainty: float = 0.0,
        decomposition: ConfidenceDecompositionReport | None = None,
    ) -> CalibratedConfidence:
        if decomposition is not None:
            if decomposition.veto_reason:
                return CalibratedConfidence(
                    raw_confidence=raw_confidence,
                    calibrated_confidence=0.0,
                    calibration_factor=0.0,
                    veto_reason=decomposition.veto_reason,
                    is_fallback=decomposition.is_fallback,
                    details=decomposition.details,
                    decomposition=decomposition,
                )
            return CalibratedConfidence(
                raw_confidence=raw_confidence,
                calibrated_confidence=decomposition.overall_calibrated,
                calibration_factor=decomposition.overall_calibrated / max(raw_confidence, 1e-9),
                veto_reason="",
                is_fallback=False,
                details=decomposition.details,
                decomposition=decomposition,
            )

        if raw_confidence < 0.0 or raw_confidence > 1.0:
            return CalibratedConfidence(
                raw_confidence=raw_confidence,
                calibrated_confidence=0.0,
                calibration_factor=0.0,
                veto_reason=f"raw_confidence out of range [0,1]: {raw_confidence}",
                is_fallback=True,
                details={
                    "historical_brier_score": historical_brier_score,
                    "num_past_decisions": num_past_decisions,
                    "regime_uncertainty": regime_uncertainty,
                },
            )

        if raw_confidence <= 0.5:
            return CalibratedConfidence(
                raw_confidence=raw_confidence,
                calibrated_confidence=0.0,
                calibration_factor=0.0,
                veto_reason=f"raw_confidence <= 0.5: {raw_confidence:.4f}",
                is_fallback=True,
                details={
                    "historical_brier_score": historical_brier_score,
                    "num_past_decisions": num_past_decisions,
                    "regime_uncertainty": regime_uncertainty,
                },
            )

        if historical_brier_score is not None and historical_brier_score > 0.3:
            cal_factor = self._default_calibration_factor * 0.5
        elif num_past_decisions < 5:
            cal_factor = self._default_calibration_factor * 0.8
        else:
            cal_factor = self._default_calibration_factor

        cal_factor = max(0.0, cal_factor * (1.0 - regime_uncertainty))

        calibrated = raw_confidence * cal_factor

        return CalibratedConfidence(
            raw_confidence=raw_confidence,
            calibrated_confidence=calibrated,
            calibration_factor=cal_factor,
            veto_reason="",
            is_fallback=False,
            details={
                "historical_brier_score": historical_brier_score,
                "num_past_decisions": num_past_decisions,
                "regime_uncertainty": regime_uncertainty,
            },
        )

    def get_calibrated_confidence_for_sizing(
        self, raw_confidence: float, **kwargs
    ) -> float:
        result = self.evaluate(raw_confidence, **kwargs)
        if result.veto_reason:
            return 0.0
        return result.calibrated_confidence
