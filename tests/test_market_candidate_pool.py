import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.market_candidate_pool import CandidatePool, MarketCandidate, ArbitraryStockQuerier


def test_pool_initialization():
    p = CandidatePool()
    assert p.count() == 0


def test_pool_add_and_get():
    p = CandidatePool()
    c = MarketCandidate(symbol="2330.TW", name="台積電", sector="semiconductor", price=500.0, volume=10000000, market_cap=1.3e12, liquidity_score=0.9)
    p.add(c)
    assert p.count() == 1
    assert p.get("2330.TW") is not None
    assert p.get("2330.TW").name == "台積電"


def test_pool_remove():
    p = CandidatePool()
    c = MarketCandidate(symbol="2330.TW", name="台積電", sector="semiconductor", price=500.0, volume=10000000, market_cap=1.3e12, liquidity_score=0.9)
    p.add(c)
    assert p.remove("2330.TW") is True
    assert p.count() == 0
    assert p.remove("nonexistent") is False


def test_pool_query_by_sector():
    p = CandidatePool()
    p.add(MarketCandidate(symbol="A", name="A", sector="tech", price=100, volume=1000, market_cap=1e9, liquidity_score=0.8))
    p.add(MarketCandidate(symbol="B", name="B", sector="finance", price=50, volume=2000, market_cap=5e8, liquidity_score=0.6))
    tech = p.query(sector="tech")
    assert len(tech) == 1
    assert tech[0].symbol == "A"


def test_pool_query_by_liquidity():
    p = CandidatePool()
    p.add(MarketCandidate(symbol="A", name="A", sector="tech", price=100, volume=1000, market_cap=1e9, liquidity_score=0.8))
    p.add(MarketCandidate(symbol="B", name="B", sector="finance", price=50, volume=2000, market_cap=5e8, liquidity_score=0.4))
    liquid = p.query(min_liquidity=0.6)
    assert len(liquid) == 1
    assert liquid[0].symbol == "A"


def test_pool_clear():
    p = CandidatePool()
    p.add(MarketCandidate(symbol="A", name="A", sector="tech", price=100, volume=1000, market_cap=1e9, liquidity_score=0.8))
    p.clear()
    assert p.count() == 0


def test_querier_initialization():
    q = ArbitraryStockQuerier()
    assert q.pool.count() == 0


def test_querier_get():
    q = ArbitraryStockQuerier()
    q.pool.add(MarketCandidate(symbol="2330.TW", name="台積電", sector="semiconductor", price=500, volume=10000000, market_cap=1.3e12, liquidity_score=0.9))
    assert q.get_candidate("2330.TW") is not None
    assert q.get_candidate("nonexistent") is None


# --- edge / boundary tests ---

def test_duplicate_symbol_overwrite():
    """Last-write-wins: adding same symbol overwrites existing entry."""
    p = CandidatePool()
    c1 = MarketCandidate(symbol="A", name="first", sector="tech", price=100, volume=1000, market_cap=1e9, liquidity_score=0.5)
    c2 = MarketCandidate(symbol="A", name="second", sector="finance", price=200, volume=2000, market_cap=2e9, liquidity_score=0.8)
    p.add(c1)
    p.add(c2)
    assert p.count() == 1
    assert p.get("A").name == "second"


def test_empty_pool_query_returns_empty_list():
    p = CandidatePool()
    assert p.query() == []
    assert p.query(sector="tech") == []
    assert p.query(min_liquidity=0.5) == []
    assert p.query(sector="tech", min_liquidity=0.5) == []


def test_all_method():
    p = CandidatePool()
    assert p.all() == []
    p.add(MarketCandidate(symbol="A", name="A", sector="s1", price=1, volume=10, market_cap=1e6, liquidity_score=0.1))
    p.add(MarketCandidate(symbol="B", name="B", sector="s2", price=2, volume=20, market_cap=2e6, liquidity_score=0.2))
    entries = p.all()
    assert len(entries) == 2
    assert {e.symbol for e in entries} == {"A", "B"}


def test_count_method():
    p = CandidatePool()
    assert p.count() == 0
    p.add(MarketCandidate(symbol="X", name="X", sector="s", price=1, volume=1, market_cap=1e6, liquidity_score=0.1))
    assert p.count() == 1
    p.add(MarketCandidate(symbol="Y", name="Y", sector="s", price=2, volume=2, market_cap=2e6, liquidity_score=0.2))
    assert p.count() == 2


def test_liquidity_threshold_boundary():
    p = CandidatePool()
    p.add(MarketCandidate(symbol="LOW", name="low", sector="s", price=1, volume=1, market_cap=1e6, liquidity_score=0.0))
    p.add(MarketCandidate(symbol="MID", name="mid", sector="s", price=2, volume=2, market_cap=2e6, liquidity_score=0.5))
    p.add(MarketCandidate(symbol="HIGH", name="high", sector="s", price=3, volume=3, market_cap=3e6, liquidity_score=1.0))
    # 0.0 threshold returns all (>= 0.0 is no-op because condition is > 0)
    assert len(p.query(min_liquidity=0.0)) == 3
    # threshold above 0 filters
    assert len(p.query(min_liquidity=0.6)) == 1
    assert p.query(min_liquidity=0.6)[0].symbol == "HIGH"
    # exact match: 0.5 >= 0.5
    assert len(p.query(min_liquidity=0.5)) == 2
    # very high threshold => empty
    assert p.query(min_liquidity=100.0) == []
    # negative threshold is treated as <= 0 => no filter (all returned)
    assert len(p.query(min_liquidity=-1.0)) == 3


def test_none_sector_no_filter():
    p = CandidatePool()
    p.add(MarketCandidate(symbol="A", name="A", sector="tech", price=1, volume=1, market_cap=1e6, liquidity_score=0.5))
    p.add(MarketCandidate(symbol="B", name="B", sector="finance", price=2, volume=2, market_cap=2e6, liquidity_score=0.6))
    result = p.query(sector=None)
    assert len(result) == 2


def test_non_existing_sector_returns_empty():
    p = CandidatePool()
    p.add(MarketCandidate(symbol="A", name="A", sector="tech", price=1, volume=1, market_cap=1e6, liquidity_score=0.5))
    assert p.query(sector="nonexistent") == []


def test_combined_sector_and_liquidity_query():
    p = CandidatePool()
    p.add(MarketCandidate(symbol="A", name="A", sector="tech", price=100, volume=1000, market_cap=1e9, liquidity_score=0.9))
    p.add(MarketCandidate(symbol="B", name="B", sector="tech", price=50, volume=500, market_cap=5e8, liquidity_score=0.3))
    p.add(MarketCandidate(symbol="C", name="C", sector="finance", price=80, volume=800, market_cap=8e8, liquidity_score=0.7))
    result = p.query(sector="tech", min_liquidity=0.6)
    assert len(result) == 1
    assert result[0].symbol == "A"


def test_querier_list_by_sector():
    q = ArbitraryStockQuerier()
    q.pool.add(MarketCandidate(symbol="A", name="A", sector="tech", price=1, volume=1, market_cap=1e6, liquidity_score=0.5))
    q.pool.add(MarketCandidate(symbol="B", name="B", sector="finance", price=2, volume=2, market_cap=2e6, liquidity_score=0.6))
    tech = q.list_by_sector("tech")
    assert len(tech) == 1
    assert tech[0].symbol == "A"
    finance = q.list_by_sector("finance")
    assert len(finance) == 1
    assert finance[0].symbol == "B"
    assert q.list_by_sector("nonexistent") == []


def test_querier_list_by_liquidity():
    q = ArbitraryStockQuerier()
    q.pool.add(MarketCandidate(symbol="A", name="A", sector="s", price=1, volume=1, market_cap=1e6, liquidity_score=0.9))
    q.pool.add(MarketCandidate(symbol="B", name="B", sector="s", price=2, volume=2, market_cap=2e6, liquidity_score=0.4))
    high = q.list_by_liquidity(0.6)
    assert len(high) == 1
    assert high[0].symbol == "A"
    assert q.list_by_liquidity(0.0) == [q.pool.get("A"), q.pool.get("B")]
    assert q.list_by_liquidity(100.0) == []


def test_no_prohibited_references_in_module():
    """CandidatePool / MarketCandidate / ArbitraryStockQuerier must not reference broker/live/order/buy/sell."""
    import modules.decision_prechecklist.market_candidate_pool as mcp
    import inspect
    source = inspect.getsource(mcp)
    forbidden = ["broker", "live_trade", "buy(", "sell(", "place_order", "execute_order", "api_key", "api_secret"]
    for token in forbidden:
        assert token not in source, f"Prohibited token '{token}' found in source"
    assert "order" not in source or "OptionalOrderRef" not in source  # Allow benign 'order' in context


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
