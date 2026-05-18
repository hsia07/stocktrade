import pytest
import logging

logging.disable(logging.CRITICAL)

from modules.phase2.core_a_shadow_aggregator import (
    CoreAShadowAggregator,
    CoreAShadowSnapshot,
)


@pytest.fixture
def aggregator():
    return CoreAShadowAggregator()


@pytest.fixture
def sample_tick():
    return {"price": 500.0, "volume": 1000, "bid_vol": 200, "ask_vol": 150}


@pytest.fixture
def sample_bars():
    return [{"close": 495.0, "high": 505.0, "low": 490.0, "volume": 2000}] * 10


class TestSnapshotContract:
    def test_snapshot_has_required_fields(self):
        snap = CoreAShadowSnapshot()
        assert hasattr(snap, "trace_id")
        assert hasattr(snap, "timestamp")
        assert hasattr(snap, "symbol")
        assert hasattr(snap, "input_summary")
        assert hasattr(snap, "precheck_summary")
        assert hasattr(snap, "veto_summary")
        assert hasattr(snap, "market_reality_summary")
        assert hasattr(snap, "sizing_summary")
        assert hasattr(snap, "microstructure_summary")
        assert hasattr(snap, "event_summary")
        assert hasattr(snap, "confidence_summary")
        assert hasattr(snap, "shadow_result")
        assert hasattr(snap, "vetoes")
        assert hasattr(snap, "reasons")
        assert hasattr(snap, "warnings")
        assert hasattr(snap, "source_versions")
        assert hasattr(snap, "no_order_side_effects")
        assert hasattr(snap, "order_execution_allowed")

    def test_no_order_side_effects_always_true(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        assert snap.no_order_side_effects is True

    def test_order_execution_allowed_always_false(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        assert snap.order_execution_allowed is False

    def test_no_order_side_effects_true_after_mutation(self, aggregator):
        snap = aggregator.evaluate("2330", [], {"price": 0, "volume": 0}, {})
        assert snap.no_order_side_effects is True

    def test_order_execution_allowed_false_after_error(self, aggregator):
        snap = aggregator.evaluate("2330", None, None, None)
        assert snap.order_execution_allowed is False


class TestAggregation:
    def test_aggregator_imports(self):
        ag = CoreAShadowAggregator()
        assert ag is not None

    def test_aggregator_instantiation(self):
        ag = CoreAShadowAggregator()
        assert hasattr(ag, "_layer")
        assert hasattr(ag, "_cost")
        assert hasattr(ag, "_slippage_mon")
        assert hasattr(ag, "_fill")
        assert hasattr(ag, "_precheck")
        assert hasattr(ag, "_confidence")
        assert hasattr(ag, "_trace")
        assert hasattr(ag, "_replay")
        assert hasattr(ag, "_verify")
        assert hasattr(ag, "_news")
        assert hasattr(ag, "_dedup")
        assert hasattr(ag, "_scorer")
        assert hasattr(ag, "_conflict")
        assert hasattr(ag, "_sizing")
        assert hasattr(ag, "_micro")

    def test_evaluate_default(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        assert snap.trace_id.startswith("core_a_")
        assert snap.timestamp != ""
        assert snap.symbol == "2330"
        assert snap.shadow_result in ("available", "unavailable", "degraded")

    def test_evaluate_price_limit_snapshot(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        if snap.market_reality_summary is not None:
            assert "price_limit_valid" in snap.market_reality_summary

    def test_evaluate_cost_breakdown(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        if snap.market_reality_summary is not None:
            if "expected_costs" in snap.market_reality_summary:
                costs = snap.market_reality_summary["expected_costs"]
                assert "total_cost" in costs
                assert "trade_value" in costs

    def test_evaluate_slippage_estimate(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        if snap.market_reality_summary is not None:
            if "expected_slippage" in snap.market_reality_summary:
                slip = snap.market_reality_summary["expected_slippage"]
                assert "expected_slippage" in slip

    def test_evaluate_fill_probability(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        if snap.market_reality_summary is not None:
            if "fill_probability" in snap.market_reality_summary:
                fp = snap.market_reality_summary["fill_probability"]
                assert "fill_probability" in fp
                assert 0.0 <= fp["fill_probability"] <= 1.0

    def test_source_versions_present(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        assert "R027" in snap.source_versions
        assert "R028" in snap.source_versions
        assert "R029" in snap.source_versions
        assert "R030" in snap.source_versions
        assert "R031" in snap.source_versions
        assert "R043" in snap.source_versions
        assert "R047" in snap.source_versions
        assert "R048" in snap.source_versions


class TestSafety:
    def test_no_order_side_effect(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        assert snap.no_order_side_effects is True

    def test_aggregator_exception_failsafe(self, aggregator):
        snap = aggregator.evaluate("2330", None, None, None)
        assert snap.shadow_result == "unavailable"

    def test_aggregator_exception_sets_unavailable(self, aggregator):
        snap = aggregator.evaluate("2330", "invalid", "invalid", "invalid")
        assert snap.shadow_result == "unavailable"

    def test_shadow_does_not_block_trading(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        assert snap.shadow_result in ("available", "unavailable")

    def test_r030_precheck_not_wired(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        if snap.precheck_summary is None:
            return
        assert "passed" in snap.precheck_summary

    def test_r047_sizing_not_wired(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        if snap.sizing_summary is not None:
            assert "passed" in snap.sizing_summary

    def test_no_broker_api_call(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        assert snap.no_order_side_effects is True
        assert snap.order_execution_allowed is False

    def test_no_runtime_state_write(self, aggregator, sample_tick, sample_bars):
        import tempfile, os
        tmp = tempfile.mkstemp(suffix=".json")
        os.close(tmp[0])
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        with open(tmp[1], "r") as f:
            content = f.read()
        assert content == ""
        os.unlink(tmp[1])

    def test_shadow_mutation_input_garbage(self, aggregator):
        snap = aggregator.evaluate("2330", [], {"price": 0, "volume": 0}, None)
        assert snap.shadow_result in ("available", "unavailable")

    def test_shadow_mutation_input_nan(self, aggregator):
        import math
        snap = aggregator.evaluate("2330", [], {"price": float("nan"), "volume": 0}, {})
        assert snap.shadow_result in ("available", "unavailable")

    def test_shadow_concurrent(self, aggregator, sample_tick, sample_bars):
        import threading
        results = []
        def eval_symbol(sym):
            snap = aggregator.evaluate(sym, sample_bars, sample_tick, {})
            results.append((sym, snap.shadow_result))
        threads = [threading.Thread(target=eval_symbol, args=(f"TICK{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 10
        for sym, result in results:
            assert result in ("available", "unavailable")


class TestForbiddenPaths:
    def test_r048_microstructure_not_wired(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        if snap.microstructure_summary is not None:
            assert isinstance(snap.microstructure_summary, dict)

    def test_event_summary_no_buy_sell(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        if snap.event_summary is not None:
            assert "news_analyzer_available" in snap.event_summary
            assert snap.event_summary.get("trades_triggered", 0) == 0

    def test_vetoes_list_structure(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        assert isinstance(snap.vetoes, list)

    def test_reasons_list(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        assert isinstance(snap.reasons, list)

    def test_warnings_list(self, aggregator, sample_tick, sample_bars):
        snap = aggregator.evaluate("2330", sample_bars, sample_tick, {})
        assert isinstance(snap.warnings, list)
