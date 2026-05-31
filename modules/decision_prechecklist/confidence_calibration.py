"""
R038f: Confidence calibration contract.
Raw confidence must NOT be used directly for pass/sizing.
LLM confidence is display-only. Calibration version + metric required.
Fail-closed on missing/stale calibration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .confidence_decomposition import ConfidenceDecompositionReport


CALIBRATION_CONTRACT_VERSION = "r038f_cal_v1"
CALIBRATION_STALE_DAYS = 30
CALIBRATION_MIN_SAMPLE_COUNT = 10


@dataclass
class CalibrationContract:
    version: str
    sample_start: str
    sample_end: str
    brier_score: float
    calibration_slope: float
    calibration_intercept: float
    sample_count: int
    calibration_curve: list[dict[str, float]] | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def is_stale(self, reference_time: str | None = None) -> bool:
        if reference_time is None:
            reference_time = datetime.now(timezone.utc).isoformat()
        try:
            end = datetime.fromisoformat(self.sample_end)
            ref = datetime.fromisoformat(reference_time)
            return (ref - end) > timedelta(days=CALIBRATION_STALE_DAYS)
        except (ValueError, TypeError):
            return True

    def has_valid_metric(self) -> bool:
        if self.brier_score is None:
            return False
        return 0.0 <= self.brier_score <= 1.0

    def has_minimum_samples(self) -> bool:
        return self.sample_count >= CALIBRATION_MIN_SAMPLE_COUNT


@dataclass
class CalibratedConfidence:
    raw_confidence: float
    calibrated_confidence: float
    calibration_factor: float
    veto_reason: str
    is_fallback: bool
    details: dict[str, Any] = field(default_factory=dict)
    decomposition: Any = None
    calibration_version: str = ""
    brier_score: float | None = None
    calibration_slope: float | None = None
    calibration_intercept: float | None = None
    sample_count: int = 0
    calibration_contract: CalibrationContract | None = None
    reason_codes: list[str] = field(default_factory=list)
    llm_summary_only: bool = True


class ConfidenceCalibrationGuard:
    def __init__(
        self,
        default_calibration_factor: float = 0.5,
        default_calibration_version: str = CALIBRATION_CONTRACT_VERSION,
    ):
        self._default_calibration_factor = default_calibration_factor
        self._default_calibration_version = default_calibration_version

    def evaluate(
        self,
        raw_confidence: float,
        historical_brier_score: float | None = None,
        num_past_decisions: int = 0,
        regime_uncertainty: float = 0.0,
        decomposition: ConfidenceDecompositionReport | None = None,
        calibration_contract: CalibrationContract | None = None,
        calibration_version: str | None = None,
        llm_summary_only: bool = True,
    ) -> CalibratedConfidence:
        reason_codes: list[str] = []

        cal_version = calibration_version or (
            calibration_contract.version if calibration_contract else None
        )
        if not cal_version:
            reason_codes.append("CALIBRATION_VERSION_MISSING")

        if calibration_contract is not None:
            if not calibration_contract.has_valid_metric():
                reason_codes.append("BRIER_SCORE_MISSING")
            if calibration_contract.is_stale():
                reason_codes.append("STALE_CALIBRATION")
            if not calibration_contract.has_minimum_samples():
                reason_codes.append("INSUFFICIENT_CALIBRATION_SAMPLES")
            brier = calibration_contract.brier_score
            slope = calibration_contract.calibration_slope
            intercept = calibration_contract.calibration_intercept
            sample_count = calibration_contract.sample_count
        else:
            brier = historical_brier_score
            slope = None
            intercept = None
            sample_count = num_past_decisions

            if historical_brier_score is None:
                reason_codes.append("BRIER_SCORE_MISSING")

        if not llm_summary_only:
            reason_codes.append("LLM_MARKS_PASS")

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
                    calibration_version=cal_version or "",
                    brier_score=brier,
                    calibration_slope=slope,
                    calibration_intercept=intercept,
                    sample_count=sample_count,
                    calibration_contract=calibration_contract,
                    reason_codes=reason_codes,
                    llm_summary_only=llm_summary_only,
                )
            return CalibratedConfidence(
                raw_confidence=raw_confidence,
                calibrated_confidence=decomposition.overall_calibrated,
                calibration_factor=decomposition.overall_calibrated / max(raw_confidence, 1e-9),
                veto_reason="",
                is_fallback=False,
                details=decomposition.details,
                decomposition=decomposition,
                calibration_version=cal_version or "",
                brier_score=brier,
                calibration_slope=slope,
                calibration_intercept=intercept,
                sample_count=sample_count,
                calibration_contract=calibration_contract,
                reason_codes=reason_codes,
                llm_summary_only=llm_summary_only,
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
                calibration_version=cal_version or "",
                brier_score=brier,
                calibration_slope=slope,
                calibration_intercept=intercept,
                sample_count=sample_count,
                calibration_contract=calibration_contract,
                reason_codes=reason_codes,
                llm_summary_only=llm_summary_only,
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
                calibration_version=cal_version or "",
                brier_score=brier,
                calibration_slope=slope,
                calibration_intercept=intercept,
                sample_count=sample_count,
                calibration_contract=calibration_contract,
                reason_codes=reason_codes,
                llm_summary_only=llm_summary_only,
            )

        if brier is not None and brier > 0.3:
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
            calibration_version=cal_version or "",
            brier_score=brier,
            calibration_slope=slope,
            calibration_intercept=intercept,
            sample_count=sample_count,
            calibration_contract=calibration_contract,
            reason_codes=reason_codes,
            llm_summary_only=llm_summary_only,
        )

    def get_calibrated_confidence_for_sizing(
        self,
        raw_confidence: float,
        calibration_contract: CalibrationContract | None = None,
        **kwargs,
    ) -> float:
        result = self.evaluate(raw_confidence, calibration_contract=calibration_contract, **kwargs)
        if result.veto_reason:
            return 0.0
        if result.reason_codes:
            return 0.0
        return result.calibrated_confidence
