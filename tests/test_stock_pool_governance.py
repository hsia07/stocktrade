import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.stock_pool_governance import TierGovernor, TieredStock, PoolTier, DEFAULT_TIER_LIMITS


def test_governor_initialization():
    g = TierGovernor()
    assert g is not None


def test_register_and_get():
    g = TierGovernor()
    s = TieredStock(symbol="2330.TW", tier=PoolTier.CORE)
    g.register(s)
    assert g.get("2330.TW") is not None
    assert g.get_tier("2330.TW") == PoolTier.CORE


def test_can_trade_core():
    g = TierGovernor()
    g.register(TieredStock(symbol="2330.TW", tier=PoolTier.CORE))
    assert g.can_trade("2330.TW") is True


def test_can_trade_excluded():
    g = TierGovernor()
    g.register(TieredStock(symbol="BAD", tier=PoolTier.EXCLUDED))
    assert g.can_trade("BAD") is False


def test_can_trade_nonexistent():
    g = TierGovernor()
    assert g.can_trade("NONEXISTENT") is False


def test_trade_count_limit():
    g = TierGovernor()
    g.register(TieredStock(symbol="WATCH", tier=PoolTier.WATCH))
    assert g.can_trade("WATCH", daily_trade_count=5) is True
    assert g.can_trade("WATCH", daily_trade_count=15) is False


def test_max_position():
    g = TierGovernor()
    g.register(TieredStock(symbol="CORE", tier=PoolTier.CORE))
    g.register(TieredStock(symbol="RESTRICTED", tier=PoolTier.RESTRICTED))
    assert g.max_position("CORE") == 0.05
    assert g.max_position("RESTRICTED") == 0.005
    assert g.max_position("NONEXISTENT") == 0.0


def test_list_by_tier():
    g = TierGovernor()
    g.register(TieredStock(symbol="A", tier=PoolTier.CORE))
    g.register(TieredStock(symbol="B", tier=PoolTier.CORE))
    g.register(TieredStock(symbol="C", tier=PoolTier.WATCH))
    core = g.list_by_tier(PoolTier.CORE)
    assert len(core) == 2


def test_count_by_tier():
    g = TierGovernor()
    g.register(TieredStock(symbol="A", tier=PoolTier.CORE))
    g.register(TieredStock(symbol="B", tier=PoolTier.WATCH))
    counts = g.count_by_tier()
    assert counts.get("core") == 1
    assert counts.get("watch") == 1


def test_default_tier_limits():
    assert DEFAULT_TIER_LIMITS[PoolTier.CORE]["max_position_pct"] == 0.05
    assert DEFAULT_TIER_LIMITS[PoolTier.EXCLUDED]["max_daily_trades"] == 0


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
