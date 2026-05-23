from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import copy


CONFIDENCE_SOURCE_KEYS = frozenset({
    "signal_technical",
    "event_news_disclosure",
    "market_reality_liquidity",
    "risk_gate_veto",
    "regime_uncertainty",
    "data_freshness_reliability",
    "calibration_quality",
})

CONFIDENCE_SOURCE_LABELS = {
    "signal_technical": "Signal / Technical Source",
    "event_news_disclosure": "Event / News / Official Disclosure Source",
    "market_reality_liquidity": "Market Reality / Liquidity Source",
    "risk_gate_veto": "Risk Gate / Veto Source",
    "regime_uncertainty": "Regime / Uncertainty Source",
    "data_freshness_reliability": "Data Freshness / Source Reliability",
    "calibration_quality": "Calibration / Confidence Quality Source",
}

DEFAULT_SOURCE_CONFIG: dict[str, dict[str, float]] = {
    "signal_technical": {"weight": 0.20, "min_raw": 0.0},
    "event_news_disclosure": {"weight": 0.15, "min_raw": 0.0},
    "market_reality_liquidity": {"weight": 0.15, "min_raw": 0.0},
    "risk_gate_veto": {"weight": 0.15, "min_raw": 0.0},
    "regime_uncertainty": {"weight": 0.10, "min_raw": 0.0},
    "data_freshness_reliability": {"weight": 0.10, "min_raw": 0.0},
    "calibration_quality": {"weight": 0.15, "min_raw": 0.0},
}

SOURCE_CATEGORY_MAPPING = {
    "pattern": "signal_technical",
    "fundamental": "event_news_disclosure",
    "regime_alignment": "regime_uncertainty",
    "signal_source_reliability": "data_freshness_reliability",
    "timeframe_alignment": "market_reality_liquidity",
    "data_quality": "data_freshness_reliability",
    "contradiction_resolution": "risk_gate_veto",
}


@dataclass
class ConfidenceSource:
    source_key: str
    source_label: str
    category: str
    weight: float
    raw_value: float
    normalized_score: float
    calibrated_bucket: str
    confidence_contribution: float
    reason_codes: list[str] = field(default_factory=list)
    is_missing: bool = False
    is_stale: bool = False
    is_conflicting: bool = False
    is_uncalibrated: bool = False
    is_veto_related: bool = False
    source_reliability: float = 1.0
    freshness_metadata: dict[str, Any] = field(default_factory=dict)
    trace_audit_payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaiwanMarketCompatibilityMarkers:
    price_limit_relevant: bool = False
    t2_settlement_relevant: bool = False
    auction_session_uncertain: bool = False
    odd_lot_round_lot_relevant: bool = False
    liquidity_shortage_flag: bool = False
    near_limit_chase_prohibited_reason: str = ""
    suspension_attention_disposition_flag: bool = False
    expected_cost_slippage_placeholder: float | None = None
    fill_probability_placeholder: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "price_limit_relevant": self.price_limit_relevant,
            "t2_settlement_relevant": self.t2_settlement_relevant,
            "auction_session_uncertain": self.auction_session_uncertain,
            "odd_lot_round_lot_relevant": self.odd_lot_round_lot_relevant,
            "liquidity_shortage_flag": self.liquidity_shortage_flag,
            "near_limit_chase_prohibited_reason": self.near_limit_chase_prohibited_reason,
            "suspension_attention_disposition_flag": self.suspension_attention_disposition_flag,
            "expected_cost_slippage_placeholder": self.expected_cost_slippage_placeholder,
            "fill_probability_placeholder": self.fill_probability_placeholder,
        }


@dataclass
class ConfidenceDecompositionReport:
    trace_id: str | None = None
    decision_chain_compatible: bool = True
    raw_confidence: float = 0.0
    overall_calibrated: float = 0.0
    final_confidence_is_trade_authority: bool = False
    confidence_source_breakdown: list[ConfidenceSource] = field(default_factory=list)
    vetoes: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    risk_snapshot_compatibility: dict[str, Any] = field(default_factory=dict)
    threshold_config_version: str = "v1"
    source_config_version: str = "v1"
    final_confidence_summary: dict[str, float] = field(default_factory=dict)
    is_fallback: bool = False
    is_uncalibrated: bool = False
    is_missing_source: bool = False
    is_stale_source: bool = False
    is_conflicting_source: bool = False
    taiwan_market_markers: TaiwanMarketCompatibilityMarkers = field(default_factory=TaiwanMarketCompatibilityMarkers)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def sources(self) -> list[ConfidenceSource]:
        return self.confidence_source_breakdown

    @property
    def veto_reason(self) -> str:
        return "; ".join(self.vetoes) if self.vetoes else ""

    def get_source(self, key: str) -> ConfidenceSource | None:
        for s in self.confidence_source_breakdown:
            if s.source_key == key:
                return s
        return None

    def get_source_summary(self) -> dict[str, dict[str, Any]]:
        return {
            s.source_key: {
                "category": s.category,
                "weight": s.weight,
                "raw_value": s.raw_value,
                "normalized_score": s.normalized_score,
                "calibrated_bucket": s.calibrated_bucket,
                "confidence_contribution": s.confidence_contribution,
                "reason_codes": s.reason_codes,
                "is_missing": s.is_missing,
                "is_stale": s.is_stale,
                "is_conflicting": s.is_conflicting,
                "is_uncalibrated": s.is_uncalibrated,
                "is_veto_related": s.is_veto_related,
                "source_reliability": s.source_reliability,
            }
            for s in self.confidence_source_breakdown
        }

    def append_trace_audit(self, trace_id: str | None = None) -> None:
        if trace_id is not None:
            self.trace_id = trace_id
        for src in self.confidence_source_breakdown:
            src.trace_audit_payload = {
                "trace_id": self.trace_id,
                "decision_chain_compatible": self.decision_chain_compatible,
                "raw_confidence": self.raw_confidence,
                "overall_calibrated": self.overall_calibrated,
                "final_confidence_is_trade_authority": self.final_confidence_is_trade_authority,
                "threshold_config_version": self.threshold_config_version,
                "source_config_version": self.source_config_version,
            }


def _calibrate_bucket(score: float) -> str:
    if score >= 0.8:
        return "high"
    elif score >= 0.5:
        return "medium"
    elif score >= 0.2:
        return "low"
    else:
        return "very_low"


class ConfidenceSourceDecomposer:
    def __init__(
        self,
        source_config: dict[str, dict[str, float]] | None = None,
        brier_penalty_threshold: float = 0.30,
        low_experience_threshold: int = 5,
        default_regime_uncertainty_penalty: float = 0.0,
        config_version: str = "v1",
        threshold_version: str = "v1",
    ):
        self._config = copy.deepcopy(source_config) if source_config is not None else copy.deepcopy(DEFAULT_SOURCE_CONFIG)
        self._validate_config()
        self._brier_penalty_threshold = brier_penalty_threshold
        self._low_experience_threshold = low_experience_threshold
        self._default_regime_uncertainty_penalty = default_regime_uncertainty_penalty
        self._config_version = config_version
        self._threshold_version = threshold_version

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

    def _build_reason_codes(
        self,
        key: str,
        raw_value: float,
        brier_penalty: float,
        experience_penalty: float,
        regime_penalty: float,
        is_missing: bool = False,
        is_stale: bool = False,
        is_conflicting: bool = False,
        is_uncalibrated: bool = False,
    ) -> list[str]:
        codes = [f"source={key}"]
        if is_missing:
            codes.append("missing_source")
        if is_stale:
            codes.append("stale_source")
        if is_conflicting:
            codes.append("conflicting_source")
        if is_uncalibrated:
            codes.append("uncalibrated")
        if brier_penalty < 1.0:
            codes.append("brier_penalty_applied")
        if experience_penalty < 1.0:
            codes.append("experience_penalty_applied")
        if regime_penalty < 1.0:
            codes.append("regime_uncertainty_penalty_applied")
        codes.append(f"raw={raw_value:.4f}")
        return codes

    def decompose(
        self,
        raw_confidence: float,
        source_scores: dict[str, float] | None = None,
        historical_brier_score: float | None = None,
        num_past_decisions: int = 0,
        regime_uncertainty: float = 0.0,
        trace_id: str | None = None,
        source_metadata: dict[str, dict[str, Any]] | None = None,
        taiwan_market_markers: TaiwanMarketCompatibilityMarkers | None = None,
    ) -> ConfidenceDecompositionReport:
        if raw_confidence < 0.0 or raw_confidence > 1.0:
            return ConfidenceDecompositionReport(
                raw_confidence=raw_confidence,
                overall_calibrated=0.0,
                final_confidence_is_trade_authority=False,
                is_fallback=True,
                vetoes=[f"raw_confidence out of range [0,1]: {raw_confidence}"],
                reason_codes=["invalid_raw_confidence", f"raw={raw_confidence}"],
                details={
                    "historical_brier_score": historical_brier_score,
                    "num_past_decisions": num_past_decisions,
                    "regime_uncertainty": regime_uncertainty,
                },
            )

        source_scores = source_scores or {}
        source_metadata = source_metadata or {}
        breakdown: list[ConfidenceSource] = []
        overall_calibrated = 0.0
        vetoes: list[str] = []
        all_reason_codes: list[str] = []

        is_uncalibrated = historical_brier_score is None

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

            is_missing = key not in source_scores
            is_stale = False
            is_conflicting = False
            meta = source_metadata.get(key, {})

            if meta.get("is_stale"):
                is_stale = True
            if meta.get("is_conflicting"):
                is_conflicting = True
            if meta.get("is_uncalibrated"):
                is_uncalibrated = True

            if is_missing or is_stale or is_conflicting:
                source_reliability = meta.get("source_reliability", 0.5 if is_missing else 0.3 if is_stale else 0.4)
            else:
                source_reliability = meta.get("source_reliability", 1.0)

            raw_score = max(0.0, min(1.0, raw_score))

            if raw_score < min_raw:
                veto_msg = (
                    f"source '{key}' raw_score {raw_score:.4f} "
                    f"below min_raw {min_raw:.4f}"
                )
                vetoes.append(veto_msg)
                all_reason_codes.append(f"veto={key}")

                is_veto_related = True
                calibrated_bucket = "veto"
                calibrated_score = 0.0
                contribution = 0.0

                breakdown.append(ConfidenceSource(
                    source_key=key,
                    source_label=CONFIDENCE_SOURCE_LABELS.get(key, key),
                    category=key,
                    weight=weight,
                    raw_value=raw_score,
                    normalized_score=raw_score,
                    calibrated_bucket=calibrated_bucket,
                    confidence_contribution=contribution,
                    reason_codes=[f"veto={key}", f"raw={raw_score:.4f}", f"min_raw={min_raw:.4f}"],
                    is_missing=is_missing,
                    is_stale=is_stale,
                    is_conflicting=is_conflicting,
                    is_uncalibrated=is_uncalibrated,
                    is_veto_related=is_veto_related,
                    source_reliability=source_reliability,
                    freshness_metadata=meta.get("freshness_metadata", {}),
                    metadata=meta,
                ))
                continue

            is_veto_related = key == "risk_gate_veto" and raw_score < min_raw

            calibrated_score = raw_score * brier_penalty * experience_penalty * regime_penalty
            calibrated_score = max(0.0, min(1.0, calibrated_score))
            calibrated_bucket = _calibrate_bucket(calibrated_score)

            if is_stale:
                calibrated_score *= 0.7
            if is_conflicting:
                calibrated_score *= 0.7
            calibrated_score = max(0.0, min(1.0, calibrated_score))
            calibrated_bucket = _calibrate_bucket(calibrated_score)

            contribution = calibrated_score * weight

            reason_codes = self._build_reason_codes(
                key, raw_score, brier_penalty, experience_penalty, regime_penalty,
                is_missing, is_stale, is_conflicting, is_uncalibrated,
            )

            breakdown.append(ConfidenceSource(
                source_key=key,
                source_label=CONFIDENCE_SOURCE_LABELS.get(key, key),
                category=key,
                weight=weight,
                raw_value=raw_score,
                normalized_score=raw_score,
                calibrated_bucket=calibrated_bucket,
                confidence_contribution=contribution,
                reason_codes=reason_codes,
                is_missing=is_missing,
                is_stale=is_stale,
                is_conflicting=is_conflicting,
                is_uncalibrated=is_uncalibrated,
                is_veto_related=is_veto_related,
                source_reliability=source_reliability,
                freshness_metadata=meta.get("freshness_metadata", {}),
                trace_audit_payload={},
                metadata=meta,
            ))

            all_reason_codes.extend(reason_codes)
            overall_calibrated += contribution

        final_report = ConfidenceDecompositionReport(
            trace_id=trace_id,
            decision_chain_compatible=True,
            raw_confidence=raw_confidence,
            overall_calibrated=overall_calibrated,
            final_confidence_is_trade_authority=False,
            confidence_source_breakdown=breakdown,
            vetoes=vetoes,
            reason_codes=all_reason_codes,
            risk_snapshot_compatibility={},
            threshold_config_version=self._threshold_version,
            source_config_version=self._config_version,
            final_confidence_summary={
                "raw": raw_confidence,
                "calibrated": overall_calibrated,
                "source_count": len(breakdown),
            },
            is_fallback=False,
            is_uncalibrated=is_uncalibrated,
            is_missing_source=any(s.is_missing for s in breakdown),
            is_stale_source=any(s.is_stale for s in breakdown),
            is_conflicting_source=any(s.is_conflicting for s in breakdown),
            taiwan_market_markers=taiwan_market_markers or TaiwanMarketCompatibilityMarkers(),
            details={
                "historical_brier_score": historical_brier_score,
                "num_past_decisions": num_past_decisions,
                "regime_uncertainty": regime_uncertainty,
                "brier_penalty": brier_penalty,
                "experience_penalty": experience_penalty,
                "regime_penalty": regime_penalty,
            },
        )

        final_report.append_trace_audit(trace_id)
        return final_report


def get_compatible_report(
    raw_confidence: float,
    confidence_report: ConfidenceDecompositionReport,
) -> dict[str, Any]:
    return {
        "trace_id": confidence_report.trace_id,
        "decision_chain_compatible": confidence_report.decision_chain_compatible,
        "confidence_source_breakdown": [
            {
                "source_key": s.source_key,
                "category": s.category,
                "raw_value": s.raw_value,
                "calibrated_score": s.normalized_score,
                "calibrated_bucket": s.calibrated_bucket,
                "confidence_contribution": s.confidence_contribution,
                "reason_codes": s.reason_codes,
                "is_missing": s.is_missing,
                "is_stale": s.is_stale,
                "is_conflicting": s.is_conflicting,
                "is_uncalibrated": s.is_uncalibrated,
                "is_veto_related": s.is_veto_related,
                "source_reliability": s.source_reliability,
                "freshness_metadata": s.freshness_metadata,
            }
            for s in confidence_report.confidence_source_breakdown
        ],
        "vetoes": confidence_report.vetoes,
        "reason_codes": confidence_report.reason_codes,
        "risk_snapshot_compatibility": confidence_report.risk_snapshot_compatibility,
        "threshold_config_version": confidence_report.threshold_config_version,
        "source_config_version": confidence_report.source_config_version,
        "final_confidence_summary": confidence_report.final_confidence_summary,
        "final_confidence_is_trade_authority": confidence_report.final_confidence_is_trade_authority,
        "taiwan_market_markers": confidence_report.taiwan_market_markers.to_dict(),
        "is_uncalibrated": confidence_report.is_uncalibrated,
        "is_missing_source": confidence_report.is_missing_source,
        "is_stale_source": confidence_report.is_stale_source,
        "is_conflicting_source": confidence_report.is_conflicting_source,
    }