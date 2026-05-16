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


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
