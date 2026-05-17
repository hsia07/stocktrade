import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from modules.decision_prechecklist.confidence_decomposition import (
    ConfidenceSourceDecomposer,
    ConfidenceDecompositionReport,
    ConfidenceSource,
    CONFIDENCE_SOURCE_KEYS,
    DEFAULT_SOURCE_CONFIG,
)


def test_decomposer_initializes_with_default_config():
    decomposer = ConfidenceSourceDecomposer()
    assert len(decomposer._config) == 7
    assert abs(sum(c["weight"] for c in decomposer._config.values()) - 1.0) < 0.001


def test_decomposer_rejects_bad_weights():
    bad_config = {
        k: {"weight": 0.5, "min_raw": 0.0} for k in list(CONFIDENCE_SOURCE_KEYS)[:2]
    }
    remaining = CONFIDENCE_SOURCE_KEYS - set(bad_config.keys())
    for k in remaining:
        bad_config[k] = {"weight": 1.0, "min_raw": 0.0}
    with pytest.raises(ValueError, match="weights must sum to 1.0"):
        ConfidenceSourceDecomposer(source_config=bad_config)


def test_decomposer_rejects_missing_keys():
    bad_config = DEFAULT_SOURCE_CONFIG.copy()
    del bad_config["pattern"]
    with pytest.raises(ValueError) as excinfo:
        ConfidenceSourceDecomposer(source_config=bad_config)
    assert "Missing source keys" in str(excinfo.value) or "weights must sum" in str(excinfo.value)


def test_decomposer_rejects_extra_keys():
    bad_config = DEFAULT_SOURCE_CONFIG.copy()
    bad_config["unknown_key"] = {"weight": 0.0, "min_raw": 0.0}
    with pytest.raises(ValueError, match="Unknown source keys"):
        ConfidenceSourceDecomposer(source_config=bad_config)


def test_decompose_returns_all_seven_sources():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.8)
    assert len(result.sources) == 7
    keys = {s.key for s in result.sources}
    assert keys == CONFIDENCE_SOURCE_KEYS


def test_decompose_with_source_scores():
    decomposer = ConfidenceSourceDecomposer()
    scores = {
        "pattern": 0.9,
        "fundamental": 0.7,
        "regime_alignment": 0.6,
        "signal_source_reliability": 0.8,
        "timeframe_alignment": 0.7,
        "data_quality": 0.9,
        "contradiction_resolution": 0.5,
    }
    result = decomposer.decompose(raw_confidence=0.8, source_scores=scores)
    assert len(result.sources) == 7
    for s in result.sources:
        expected_raw = scores[s.key]
        assert s.raw_score == expected_raw


def test_decompose_low_raw_still_decomposes():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.0)
    assert not result.veto_reason
    assert result.overall_calibrated == 0.0
    assert len(result.sources) == 7


def test_decompose_negative_raw_veto():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=-0.1)
    assert result.veto_reason
    assert "out of range" in result.veto_reason


def test_decompose_over_one_raw_veto():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=1.5)
    assert result.veto_reason
    assert "out of range" in result.veto_reason


def test_decompose_brier_penalty():
    decomposer = ConfidenceSourceDecomposer()
    result_no_penalty = decomposer.decompose(
        raw_confidence=0.8, historical_brier_score=0.2
    )
    result_penalty = decomposer.decompose(
        raw_confidence=0.8, historical_brier_score=0.5
    )
    assert result_penalty.overall_calibrated < result_no_penalty.overall_calibrated


def test_decompose_experience_penalty():
    decomposer = ConfidenceSourceDecomposer()
    result_experienced = decomposer.decompose(
        raw_confidence=0.8, num_past_decisions=50
    )
    result_novice = decomposer.decompose(
        raw_confidence=0.8, num_past_decisions=2
    )
    assert result_novice.overall_calibrated < result_experienced.overall_calibrated


def test_decompose_regime_penalty():
    decomposer = ConfidenceSourceDecomposer()
    result_low = decomposer.decompose(
        raw_confidence=0.8, regime_uncertainty=0.1
    )
    result_high = decomposer.decompose(
        raw_confidence=0.8, regime_uncertainty=0.8
    )
    assert result_high.overall_calibrated < result_low.overall_calibrated


def test_decompose_individual_source_veto():
    config = {k: dict(v) for k, v in DEFAULT_SOURCE_CONFIG.items()}
    config["pattern"]["min_raw"] = 0.5
    decomposer = ConfidenceSourceDecomposer(source_config=config)
    result = decomposer.decompose(
        raw_confidence=0.8,
        source_scores={"pattern": 0.3},
    )
    assert result.veto_reason
    assert "pattern" in result.veto_reason
    assert "below min_raw" in result.veto_reason


def test_get_source_summary():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.8)
    summary = result.get_source_summary()
    assert len(summary) == 7
    for key in CONFIDENCE_SOURCE_KEYS:
        assert key in summary
        assert "weight" in summary[key]
        assert "raw" in summary[key]
        assert "calibrated" in summary[key]


def test_get_source_found():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.8)
    source = result.get_source("pattern")
    assert source is not None
    assert source.key == "pattern"


def test_get_source_not_found():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.8)
    source = result.get_source("nonexistent")
    assert source is None


def test_overall_calibrated_is_weighted_sum():
    decomposer = ConfidenceSourceDecomposer()
    result = decomposer.decompose(raw_confidence=0.8)
    expected = sum(s.calibrated_score * s.weight for s in result.sources)
    assert abs(result.overall_calibrated - expected) < 0.001


def test_confidence_source_dataclass():
    source = ConfidenceSource(
        key="test",
        label="Test Source",
        weight=0.5,
        raw_score=0.8,
        calibrated_score=0.6,
        justification="test",
    )
    assert source.key == "test"
    assert source.weight == 0.5


def test_confidence_decomposition_report_defaults():
    report = ConfidenceDecompositionReport(raw_confidence=0.8, overall_calibrated=0.6)
    assert report.sources == []
    assert report.veto_reason == ""
    assert not report.is_fallback
    assert report.details == {}


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
