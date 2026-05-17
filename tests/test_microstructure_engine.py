import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.microstructure_engine import MicrostructureEngine, OrderBookSnapshot, OrderBookLevel, MarketSession, LimitUpDownInfo, FillFeasibility


def test_engine_initialization():
    e = MicrostructureEngine()
    assert e is not None


def test_record_snapshot():
    e = MicrostructureEngine()
    snap = OrderBookSnapshot(
        symbol="2330.TW",
        bids=[OrderBookLevel(price=500.0, volume=1000, side="buy")],
        asks=[OrderBookLevel(price=501.0, volume=800, side="sell")],
    )
    e.record_snapshot(snap)
    assert len(e.get_snapshots("2330.TW")) == 1


def test_spread():
    snap = OrderBookSnapshot(
        symbol="2330.TW",
        bids=[OrderBookLevel(price=500.0, volume=1000, side="buy")],
        asks=[OrderBookLevel(price=501.0, volume=800, side="sell")],
    )
    assert snap.spread() == 1.0


def test_mid_price():
    snap = OrderBookSnapshot(
        symbol="2330.TW",
        bids=[OrderBookLevel(price=500.0, volume=1000, side="buy")],
        asks=[OrderBookLevel(price=501.0, volume=800, side="sell")],
    )
    assert snap.mid_price() == 500.5


def test_imbalance():
    snap = OrderBookSnapshot(
        symbol="2330.TW",
        bids=[OrderBookLevel(price=500.0, volume=1000, side="buy")],
        asks=[OrderBookLevel(price=501.0, volume=500, side="sell")],
    )
    imb = snap.imbalance()
    assert 0 < imb < 1


def test_spread_empty():
    snap = OrderBookSnapshot(symbol="A")
    assert snap.spread() == 0.0


def test_compute_features():
    e = MicrostructureEngine()
    snap = OrderBookSnapshot(
        symbol="2330.TW",
        bids=[OrderBookLevel(price=500.0, volume=1000, side="buy")],
        asks=[OrderBookLevel(price=501.0, volume=800, side="sell")],
    )
    e.record_snapshot(snap)
    features = e.compute_features("2330.TW")
    assert features is not None
    assert features.symbol == "2330.TW"
    assert features.spread_bps > 0
    assert features.liquidity_tier >= 1


def test_compute_features_no_data():
    e = MicrostructureEngine()
    assert e.compute_features("NONEXISTENT") is None


def test_clear():
    e = MicrostructureEngine()
    snap = OrderBookSnapshot(symbol="A")
    e.record_snapshot(snap)
    e.clear()
    assert len(e.get_snapshots("A")) == 0


def test_limit_up_down():
    snap = OrderBookSnapshot(
        symbol="2330.TW",
        bids=[OrderBookLevel(price=500.0, volume=1000, side="buy")],
        asks=[OrderBookLevel(price=501.0, volume=800, side="sell")],
        previous_close=500.0,
    )
    lud = snap.get_limit_up_down(pct=0.10)
    assert lud.limit_up == 550.0
    assert lud.limit_down == 450.0
    assert lud.distance_to_up_pct > 0
    assert lud.distance_to_down_pct > 0


def test_limit_up_down_default_pct():
    snap = OrderBookSnapshot(
        symbol="2330.TW",
        bids=[OrderBookLevel(price=500.0, volume=1000, side="buy")],
        asks=[OrderBookLevel(price=501.0, volume=800, side="sell")],
        previous_close=500.0,
    )
    lud = snap.get_limit_up_down()
    assert lud.limit_up == 550.0
    assert lud.limit_down == 450.0


def test_fill_feasibility_buy():
    snap = OrderBookSnapshot(
        symbol="2330.TW",
        bids=[OrderBookLevel(price=500.0, volume=1000, side="buy")],
        asks=[OrderBookLevel(price=501.0, volume=800, side="sell"), OrderBookLevel(price=502.0, volume=500, side="sell")],
    )
    ff = snap.assess_fill("buy", 1000, 502.0)
    assert ff.fillable_qty == 1000
    assert ff.avg_fill_price > 0
    assert ff.slippage_bps >= 0
    assert ff.reason == ""


def test_fill_feasibility_insufficient_depth():
    snap = OrderBookSnapshot(
        symbol="2330.TW",
        bids=[OrderBookLevel(price=500.0, volume=1000, side="buy")],
        asks=[OrderBookLevel(price=501.0, volume=100, side="sell")],
    )
    ff = snap.assess_fill("buy", 1000, 502.0)
    assert ff.fillable_qty < 1000
    assert ff.reason == "insufficient_depth"


def test_fill_feasibility_sell():
    snap = OrderBookSnapshot(
        symbol="2330.TW",
        bids=[OrderBookLevel(price=500.0, volume=2000, side="buy"), OrderBookLevel(price=499.0, volume=1000, side="buy")],
        asks=[OrderBookLevel(price=501.0, volume=800, side="sell")],
    )
    ff = snap.assess_fill("sell", 1500, 499.0)
    assert ff.fillable_qty == 1500
    assert ff.avg_fill_price > 0
    assert ff.reason == ""


def test_compute_features_with_fill_and_limit():
    e = MicrostructureEngine()
    snap = OrderBookSnapshot(
        symbol="2330.TW",
        bids=[OrderBookLevel(price=500.0, volume=1000, side="buy")],
        asks=[OrderBookLevel(price=501.0, volume=800, side="sell")],
        previous_close=500.0,
    )
    e.record_snapshot(snap)
    features = e.compute_features("2330.TW", side="buy", quantity=500, price=502.0)
    assert features is not None
    assert features.fill_feasibility is not None
    assert features.fill_feasibility.fillable_qty == 500
    assert features.limit_up_down is not None
    assert features.market_session is not None


def test_market_session_closed():
    from datetime import datetime, timezone, time
    e = MicrostructureEngine()
    snap = OrderBookSnapshot(symbol="2330.TW")
    e.record_snapshot(snap)
    features = e.compute_features("2330.TW")
    # depends on current time; just verify it returns a valid MarketSession
    assert isinstance(features.market_session, MarketSession)


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
