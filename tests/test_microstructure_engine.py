import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.microstructure_engine import MicrostructureEngine, OrderBookSnapshot, OrderBookLevel


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


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
