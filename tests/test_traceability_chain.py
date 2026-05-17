import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from modules.decision_prechecklist.traceability_chain import (
    TraceabilityChain,
    TraceabilityLink,
    ChainVerificationResult,
)


def test_chain_initialization():
    chain = TraceabilityChain(chain_id="test-chain")
    assert chain.chain_id == "test-chain"
    assert chain.links == []
    assert chain.last_hash == ""


def test_add_link():
    chain = TraceabilityChain(chain_id="test-chain")
    link = chain.add_link(
        trace_id="trace-001",
        symbol="2330.TW",
        side="buy",
        final_decision="EXECUTE",
        total_steps=8,
        veto_count=0,
    )
    assert link.link_id == "test-chain-L0000"
    assert link.chain_index == 0
    assert link.previous_link_hash == ""
    assert len(link.link_hash) == 64
    assert len(chain.links) == 1
    assert chain.last_hash == link.link_hash


def test_add_two_links():
    chain = TraceabilityChain(chain_id="test-chain")
    link1 = chain.add_link(
        trace_id="trace-001", symbol="2330.TW", side="buy",
        final_decision="EXECUTE", total_steps=8, veto_count=0,
    )
    link2 = chain.add_link(
        trace_id="trace-002", symbol="2330.TW", side="sell",
        final_decision="EXECUTE", total_steps=7, veto_count=1,
    )
    assert link2.chain_index == 1
    assert link2.previous_link_hash == link1.link_hash
    assert link2.link_id == "test-chain-L0001"
    assert len(chain.links) == 2


def test_add_link_with_order_fill_pnl():
    chain = TraceabilityChain()
    link = chain.add_link(
        trace_id="trace-001", symbol="2330.TW", side="buy",
        final_decision="EXECUTE", total_steps=8, veto_count=0,
        order_ref="ORD-001", fill_ref="FILL-001", pnl_ref="PNL-001",
    )
    assert link.order_ref == "ORD-001"
    assert link.fill_ref == "FILL-001"
    assert link.pnl_ref == "PNL-001"


def test_add_link_with_details():
    chain = TraceabilityChain()
    link = chain.add_link(
        trace_id="trace-001", symbol="2330.TW", side="buy",
        final_decision="BLOCKED", total_steps=8, veto_count=2,
        details={"veto_codes": ["SINGLE_SIGNAL_DIRECT_TRADE", "TAIWAN_CONSTRAINT"]},
    )
    assert link.veto_count == 2
    assert link.details["veto_codes"] == ["SINGLE_SIGNAL_DIRECT_TRADE", "TAIWAN_CONSTRAINT"]


def test_verify_empty_chain():
    chain = TraceabilityChain()
    result = chain.verify_chain()
    assert result.valid
    assert result.total_links == 0
    assert result.broken_at == -1


def test_verify_single_link_chain():
    chain = TraceabilityChain()
    chain.add_link(
        trace_id="trace-001", symbol="2330.TW", side="buy",
        final_decision="EXECUTE", total_steps=8, veto_count=0,
    )
    result = chain.verify_chain()
    assert result.valid
    assert result.total_links == 1
    assert result.broken_at == -1


def test_verify_multi_link_chain():
    chain = TraceabilityChain()
    for i in range(5):
        chain.add_link(
            trace_id=f"trace-{i:03d}", symbol="2330.TW", side="buy",
            final_decision="EXECUTE", total_steps=8, veto_count=0,
        )
    result = chain.verify_chain()
    assert result.valid
    assert result.total_links == 5
    assert result.broken_at == -1


def test_verify_detects_tampered_hash():
    chain = TraceabilityChain()
    chain.add_link(
        trace_id="trace-001", symbol="2330.TW", side="buy",
        final_decision="EXECUTE", total_steps=8, veto_count=0,
    )
    chain.add_link(
        trace_id="trace-002", symbol="2330.TW", side="sell",
        final_decision="EXECUTE", total_steps=7, veto_count=1,
    )
    link0 = chain._links[0]
    original_hash = link0.link_hash
    link0.link_hash = link0.link_hash[:-1] + "0"
    result = chain.verify_chain()
    assert not result.valid
    assert result.total_links == 2
    assert result.broken_at == 0
    link0.link_hash = original_hash


def test_verify_detects_broken_chain():
    chain = TraceabilityChain()
    link1 = chain.add_link(
        trace_id="trace-001", symbol="2330.TW", side="buy",
        final_decision="EXECUTE", total_steps=8, veto_count=0,
    )
    link2 = chain.add_link(
        trace_id="trace-002", symbol="2330.TW", side="sell",
        final_decision="EXECUTE", total_steps=7, veto_count=1,
    )
    link2.previous_link_hash = "0000" + link1.link_hash[4:]
    result = chain.verify_chain()
    assert not result.valid
    assert result.total_links == 2
    assert result.broken_at == 1


def test_export_import_jsonl():
    chain = TraceabilityChain(chain_id="test-chain")
    for i in range(3):
        chain.add_link(
            trace_id=f"trace-{i:03d}", symbol="2330.TW", side="buy",
            final_decision="EXECUTE", total_steps=8, veto_count=0,
        )
    jsonl = chain.export_jsonl()
    assert len(jsonl.strip().split("\n")) == 3

    chain2 = TraceabilityChain(chain_id="imported")
    chain2.import_jsonl(jsonl)
    assert len(chain2.links) == 3
    assert chain2.last_hash == chain.last_hash
    result2 = chain2.verify_chain()
    assert result2.valid


def test_clear():
    chain = TraceabilityChain()
    chain.add_link(
        trace_id="trace-001", symbol="2330.TW", side="buy",
        final_decision="EXECUTE", total_steps=8, veto_count=0,
    )
    assert len(chain.links) == 1
    chain.clear()
    assert chain.links == []
    assert chain.last_hash == ""


def test_link_verify_hash():
    chain = TraceabilityChain()
    link = chain.add_link(
        trace_id="trace-001", symbol="2330.TW", side="buy",
        final_decision="EXECUTE", total_steps=8, veto_count=0,
    )
    assert link.verify_hash()


def test_link_hash_changes_with_content():
    chain = TraceabilityChain()
    link1 = chain.add_link(
        trace_id="trace-001", symbol="2330.TW", side="buy",
        final_decision="EXECUTE", total_steps=8, veto_count=0,
    )
    link2 = chain.add_link(
        trace_id="trace-002", symbol="2330.TW", side="sell",
        final_decision="EXECUTE", total_steps=7, veto_count=1,
    )
    assert link1.link_hash != link2.link_hash


def test_chain_different_ids_have_different_hashes():
    chain1 = TraceabilityChain(chain_id="chain-A")
    chain1.add_link(
        trace_id="trace-001", symbol="2330.TW", side="buy",
        final_decision="EXECUTE", total_steps=8, veto_count=0,
    )
    chain2 = TraceabilityChain(chain_id="chain-B")
    chain2.add_link(
        trace_id="trace-001", symbol="2330.TW", side="buy",
        final_decision="EXECUTE", total_steps=8, veto_count=0,
    )
    assert chain1.links[0].link_hash != chain2.links[0].link_hash


def test_import_jsonl_with_verification():
    chain = TraceabilityChain(chain_id="export-chain")
    for i in range(5):
        chain.add_link(
            trace_id=f"trace-{i:03d}", symbol="2330.TW", side="buy",
            final_decision="EXECUTE", total_steps=8, veto_count=0,
        )
    jsonl = chain.export_jsonl()

    imported = TraceabilityChain(chain_id="imported-chain")
    imported.import_jsonl(jsonl)
    result = imported.verify_chain()
    assert result.valid
    assert result.total_links == 5


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
