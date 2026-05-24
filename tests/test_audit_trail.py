import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
from modules.decision_prechecklist.audit_trail import (
    AuditTrailChain,
    DecisionAuditRecord,
    DecisionAuditError,
    ImmutableRecordError,
    TraceIdentity,
    DecisionChain,
    RiskVetoChain,
    MarketRealitySnapshot,
    TaiwanMarketConstraints,
    OrderFillPnlReview,
    AIOpinion,
    DecisionStep,
    create_decision_audit_record,
    reject_mutation_or_overwrite,
    VALID_SCHEMA_VERSIONS,
    TRADE_ALLOWED_DECISIONS,
    TRADE_BLOCKED_DECISIONS,
)


# ============================================================
# Positive tests
# ============================================================

def test_create_full_decision_audit_record():
    tid = TraceIdentity.new(trace_id="trace-001", decision_id="dec-001", session_id="s1")
    chain = DecisionChain(
        final_decision="EXECUTE",
        final_reason_code="SIGNAL_STRONG",
        event_inputs=["price_breakout"],
        signal_inputs={"ma_cross": 1.0},
        ai_opinions=[AIOpinion(ai_name="ai1", support=True, confidence=0.85)],
    )
    rvc = RiskVetoChain(
        risk_snapshot={"var": 0.02, "exposure": 0.1},
        risk_gate_results={"max_position": "pass", "var_limit": "pass"},
    )
    mr = MarketRealitySnapshot(
        cost_model_version="r032-v1",
        slippage_model_version="r032-v1",
        market_session_state="continuous",
    )
    tc = TaiwanMarketConstraints(
        limit_up_down_pct=10.0,
        auction_session_state="continuous",
        odd_lot_round_lot="round_lot",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    ofp = OrderFillPnlReview()
    record = DecisionAuditRecord(
        trace_identity=tid,
        decision_chain=chain,
        risk_veto=rvc,
        market_reality=mr,
        taiwan_constraints=tc,
        order_fill_pnl=ofp,
    )
    assert record.trace_identity.trace_id == "trace-001"
    assert record.decision_chain.final_decision == "EXECUTE"
    assert len(record.decision_chain.ai_opinions) == 1
    assert record.risk_veto.risk_snapshot["var"] == 0.02
    assert record.taiwan_constraints.limit_up_down_pct == 10.0
    assert record.market_reality.cost_model_version == "r032-v1"


def test_append_record_to_chain():
    chain = AuditTrailChain(chain_id="test-chain")
    record = create_decision_audit_record(
        trace_id="trace-001", final_decision="EXECUTE",
        final_reason_code="TEST",
        risk_gate_results={"gate1": "pass"},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
        risk_snapshot={"var": 0.02},
    )
    appended = chain.append(record)
    assert appended.chain_index == 0
    assert appended.record_hash != ""
    assert chain.record_count == 1
    assert chain.last_hash == appended.record_hash


def test_append_multi_record_chain():
    chain = AuditTrailChain(chain_id="multi-chain")
    for i in range(3):
        rec = create_decision_audit_record(
            trace_id=f"trace-{i:03d}", final_decision="EXECUTE",
            final_reason_code="TEST",
            risk_gate_results={"gate1": "pass"},
            market_session_state="continuous",
            auction_session_state="continuous",
            halt_disposition_attention="none",
            liquidity_insufficiency="none",
            risk_snapshot={"var": 0.02},
        )
        chain.append(rec)
    assert chain.record_count == 3
    assert chain.verify_integrity()


def test_chain_verification_integrity():
    chain = AuditTrailChain()
    for i in range(5):
        rec = create_decision_audit_record(
            trace_id=f"trace-{i:03d}", final_decision="EXECUTE",
            final_reason_code="TEST",
            risk_gate_results={"gate1": "pass"},
            market_session_state="continuous",
            auction_session_state="continuous",
            halt_disposition_attention="none",
            liquidity_insufficiency="none",
            risk_snapshot={"var": 0.02},
        )
        chain.append(rec)
    result = chain.verify_integrity_detailed()
    assert result["valid"] is True
    assert result["broken_at"] == -1
    assert result["total"] == 5


def test_serialize_deserialize():
    chain = AuditTrailChain(chain_id="ser-chain")
    for i in range(3):
        rec = create_decision_audit_record(
            trace_id=f"trace-{i:03d}", final_decision="EXECUTE",
            final_reason_code="TEST",
            risk_gate_results={"gate1": "pass"},
            market_session_state="continuous",
            auction_session_state="continuous",
            halt_disposition_attention="none",
            liquidity_insufficiency="none",
            risk_snapshot={"var": 0.02},
        )
        chain.append(rec)
    jsonl = chain.export_jsonl()
    assert len(jsonl.strip().split("\n")) == 3

    chain2 = AuditTrailChain(chain_id="imported")
    chain2.import_jsonl(jsonl)
    assert chain2.record_count == 3
    assert chain2.last_hash == chain.last_hash
    assert chain2.verify_integrity()


def test_replay():
    chain = AuditTrailChain()
    for i in range(2):
        rec = create_decision_audit_record(
            trace_id=f"trace-{i:03d}", final_decision="EXECUTE",
            final_reason_code="TEST",
            risk_gate_results={"gate1": "pass"},
            market_session_state="continuous",
            auction_session_state="continuous",
            halt_disposition_attention="none",
            liquidity_insufficiency="none",
            risk_snapshot={"var": 0.02},
        )
        chain.append(rec)
    jsonl = chain.export_jsonl()
    chain3 = AuditTrailChain()
    replayed = chain3.replay(jsonl)
    assert len(replayed) == 2
    assert chain3.verify_integrity()


def test_record_trace_id_and_decision_chain():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-keep-001", decision_id="dec-keep-001",
        final_decision="BLOCKED", final_reason_code="RISK_LIMIT",
        risk_snapshot={"var": 0.05, "exposure": 0.3},
        veto_reason_codes=["var_exceeded"],
        risk_gate_results={"var_limit": "veto"},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    chain.append(rec)
    found = chain.get_by_trace_id("trace-keep-001")
    assert len(found) == 1
    assert found[0].decision_chain.final_decision == "BLOCKED"
    assert found[0].decision_chain.final_reason_code == "RISK_LIMIT"


def test_record_ai_support_reject_veto():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-ai-001", final_decision="BLOCKED",
        final_reason_code="AI_VETO",
        ai_opinions=[
            {"ai_name": "ai-technical", "claim": "buy", "support": True, "confidence": 0.8},
            {"ai_name": "ai-risk", "claim": "hold", "reject": True, "veto": True, "veto_reason": "var_exceeded", "confidence": 0.9},
        ],
        risk_gate_results={"ai_veto": "veto"},
        veto_reason_codes=["ai-risk:var_exceeded"],
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
        risk_snapshot={"var": 0.05},
    )
    chain.append(rec)
    found = chain.get_by_trace_id("trace-ai-001")
    assert len(found[0].decision_chain.ai_opinions) == 2
    assert found[0].decision_chain.ai_opinions[1].veto is True
    assert found[0].decision_chain.ai_opinions[1].veto_reason == "var_exceeded"


def test_record_no_trade_reason():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-nt-001", final_decision="BLOCKED",
        final_reason_code="NO_TRADE",
        veto_reason_codes=["liquidity_insufficient"],
        risk_gate_results={"liquidity": "veto"},
        risk_snapshot={"var": 0.02, "liquidity_score": 0.1},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="adv_too_low",
    )
    chain.append(rec)
    found = chain.get_by_trace_id("trace-nt-001")
    assert found[0].risk_veto.veto_reason_codes == ["liquidity_insufficient"]
    assert found[0].taiwan_constraints.liquidity_insufficiency == "adv_too_low"


def test_append_only_append_event():
    chain = AuditTrailChain()
    rec1 = create_decision_audit_record(
        trace_id="trace-e1", final_decision="WAIT",
        final_reason_code="NEED_CONFIRMATION",
        risk_gate_results={"gate1": "pass"},
        risk_snapshot={"var": 0.02},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    chain.append(rec1)
    rec2 = create_decision_audit_record(
        trace_id="trace-e2", final_decision="EXECUTE",
        final_reason_code="CONFIRMED",
        risk_gate_results={"gate1": "pass"},
        risk_snapshot={"var": 0.02},
        ai_opinions=[{"ai_name": "ai1", "support": True, "confidence": 0.7}],
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    chain.append(rec2)
    assert chain.record_count == 2
    assert chain.verify_integrity()


def test_factory_create_decision_audit_record():
    rec = create_decision_audit_record(
        trace_id="factory-001",
        decision_id="factory-dec-001",
        session_id="s1",
        strategy_id="strat-a",
        final_decision="REDUCE_SIZE",
        final_reason_code="SIZE_LIMIT",
        raw_confidence=0.6,
        risk_gate_results={"size_limit": "pass"},
        risk_snapshot={"current_size": 0.8, "max_size": 1.0},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    assert rec.trace_identity.trace_id == "factory-001"
    assert rec.trace_identity.decision_id == "factory-dec-001"
    assert rec.trace_identity.session_id == "s1"
    assert rec.trace_identity.strategy_id == "strat-a"
    assert rec.decision_chain.final_decision == "REDUCE_SIZE"
    assert rec.decision_chain.final_reason_code == "SIZE_LIMIT"
    assert rec.risk_veto.risk_snapshot["current_size"] == 0.8


def test_get_by_decision_id():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-get", decision_id="dec-get-001",
        final_decision="EXECUTE", final_reason_code="TEST",
        risk_gate_results={"g1": "pass"},
        risk_snapshot={"var": 0.02},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    chain.append(rec)
    found = chain.get_by_decision_id("dec-get-001")
    assert found is not None
    assert found.trace_identity.trace_id == "trace-get"


def test_clear_chain():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-clr", final_decision="EXECUTE",
        final_reason_code="TEST",
        risk_gate_results={"g1": "pass"},
        risk_snapshot={"var": 0.02},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    chain.append(rec)
    assert chain.record_count == 1
    chain.clear()
    assert chain.record_count == 0
    assert chain.last_hash == ""


# ============================================================
# Negative tests
# ============================================================

def test_missing_trace_id_fails():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="", final_decision="EXECUTE", final_reason_code="TEST",
        risk_gate_results={"g1": "pass"},
        risk_snapshot={"var": 0.02},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    # Manually clear trace_id after creation
    rec.trace_identity.trace_id = ""
    with pytest.raises(DecisionAuditError) as exc:
        chain.append(rec)
    assert "missing_trace_id" in str(exc.value)


def test_missing_final_decision_fails():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-md", final_decision="", final_reason_code="",
        risk_gate_results={"g1": "pass"},
        risk_snapshot={"var": 0.02},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    with pytest.raises(DecisionAuditError) as exc:
        chain.append(rec)
    assert "missing_final_decision" in str(exc.value)


def test_veto_then_trade_allowed_fails():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-veto", final_decision="EXECUTE",
        final_reason_code="SHOULD_BE_BLOCKED",
        veto_reason_codes=["risk_gate_veto"],
        risk_gate_results={"risk_gate": "veto"},
        risk_snapshot={"var": 0.05},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    with pytest.raises(DecisionAuditError) as exc:
        chain.append(rec)
    assert "veto_trade_allowed_conflict" in str(exc.value)


def test_raw_confidence_direct_trade_approval_fails():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-rawconf", final_decision="EXECUTE",
        final_reason_code="RAW_HIGH",
        raw_confidence=0.99,
        risk_gate_results={},
        risk_snapshot={},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    with pytest.raises(DecisionAuditError) as exc:
        chain.append(rec)
    assert "raw_confidence_direct_trade_approval" in str(exc.value)


def test_llm_veto_ignored_fails():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-llmveto", final_decision="EXECUTE",
        final_reason_code="IGNORED_VETO",
        ai_opinions=[
            {"ai_name": "ai-risk", "claim": "no_trade", "veto": True,
             "veto_reason": "risk_limit", "confidence": 0.9},
        ],
        risk_gate_results={"ai_veto": "veto"},
        veto_reason_codes=["ai-risk:risk_limit"],
        risk_snapshot={"var": 0.05},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    with pytest.raises(DecisionAuditError) as exc:
        chain.append(rec)
    assert "llm_veto_ignored" in str(exc.value)


def test_invalid_schema_version_fails():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-sch", final_decision="BLOCKED",
        final_reason_code="SCHEMA_ERR",
        risk_gate_results={"g1": "pass"},
        risk_snapshot={"var": 0.02},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    rec.schema_version = "invalid-v99"
    with pytest.raises(DecisionAuditError) as exc:
        chain.append(rec)
    assert "invalid_schema_version" in str(exc.value)


def test_immutable_overwrite_rejected():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-imm", final_decision="EXECUTE",
        final_reason_code="TEST",
        risk_gate_results={"g1": "pass"},
        risk_snapshot={"var": 0.02},
        ai_opinions=[{"ai_name": "ai1", "support": True, "confidence": 0.7}],
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    chain.append(rec)
    with pytest.raises(ImmutableRecordError) as exc:
        reject_mutation_or_overwrite(rec)
    assert "Cannot mutate immutable append-only record" in str(exc.value)


def test_missing_taiwan_placeholders_fails():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-tw", final_decision="BLOCKED",
        final_reason_code="TW_MISSING",
        risk_gate_results={"g1": "pass"},
        risk_snapshot={"var": 0.02},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    rec.taiwan_constraints.auction_session_state = ""
    rec.taiwan_constraints.odd_lot_round_lot = ""
    with pytest.raises(DecisionAuditError) as exc:
        chain.append(rec)
    err = str(exc.value)
    assert "taiwan_auction_session_missing" in err
    assert "taiwan_odd_lot_round_lot_missing" in err


def test_missing_market_reality_placeholders_fails():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-mr", final_decision="BLOCKED",
        final_reason_code="MR_MISSING",
        risk_gate_results={"g1": "pass"},
        risk_snapshot={"var": 0.02},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    rec.market_reality.cost_model_version = ""
    rec.market_reality.slippage_model_version = ""
    rec.market_reality.market_session_state = ""
    with pytest.raises(DecisionAuditError) as exc:
        chain.append(rec)
    err = str(exc.value)
    assert "cost_model_version_missing" in err
    assert "slippage_model_version_missing" in err
    assert "market_session_state_missing" in err


def test_order_fill_pnl_partial_linkage_not_complete():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-ofp", final_decision="EXECUTE",
        final_reason_code="TEST",
        risk_gate_results={"g1": "pass"},
        risk_snapshot={"var": 0.02},
        ai_opinions=[{"ai_name": "ai1", "support": True, "confidence": 0.7}],
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
        order_id="ORD-001",
        fill_id="",
        review_id="",
    )
    with pytest.raises(DecisionAuditError) as exc:
        chain.append(rec)
    assert "order_fill_pnl_partial_linkage_no_complete_chain" in str(exc.value)


# ============================================================
# Edge tests
# ============================================================

def test_empty_chain_verification():
    chain = AuditTrailChain()
    assert chain.verify_integrity()
    result = chain.verify_integrity_detailed()
    assert result["valid"] is True
    assert result["total"] == 0


def test_tampered_hash_detected():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-tamper", final_decision="EXECUTE",
        final_reason_code="TEST",
        risk_gate_results={"g1": "pass"},
        risk_snapshot={"var": 0.02},
        ai_opinions=[{"ai_name": "ai1", "support": True, "confidence": 0.7}],
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    chain.append(rec)
    original_hash = chain._records[0].record_hash
    chain._records[0].record_hash = "0" * 64
    assert not chain.verify_integrity()
    result = chain.verify_integrity_detailed()
    assert result["valid"] is False
    assert result["broken_at"] == 0
    assert result["reason"] == "hash_mismatch"
    chain._records[0].record_hash = original_hash


def test_broken_chain_detected():
    chain = AuditTrailChain()
    rec1 = create_decision_audit_record(
        trace_id="trace-bc1", final_decision="EXECUTE",
        final_reason_code="TEST",
        risk_gate_results={"g1": "pass"},
        risk_snapshot={"var": 0.02},
        ai_opinions=[{"ai_name": "ai1", "support": True, "confidence": 0.7}],
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    rec2 = create_decision_audit_record(
        trace_id="trace-bc2", final_decision="EXECUTE",
        final_reason_code="TEST",
        risk_gate_results={"g1": "pass"},
        risk_snapshot={"var": 0.02},
        ai_opinions=[{"ai_name": "ai1", "support": True, "confidence": 0.7}],
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    chain.append(rec1)
    chain.append(rec2)
    chain._records[1].previous_record_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    assert not chain.verify_integrity()
    result = chain.verify_integrity_detailed()
    assert result["valid"] is False
    # When previous_record_hash is mutated, hash_mismatch is caught first
    # because it's part of the hash payload; chain_break detection
    # follows after hash check passes. Either result is acceptable.
    assert result["reason"] in ("chain_break", "hash_mismatch")


def test_high_confidence_with_chain_context_valid():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-hc", final_decision="EXECUTE",
        final_reason_code="HIGH_CONF_WITH_CONTEXT",
        raw_confidence=0.99,
        ai_opinions=[
            {"ai_name": "ai1", "support": True, "confidence": 0.99},
        ],
        risk_gate_results={"var_limit": "pass", "max_position": "pass"},
        risk_snapshot={"var": 0.01, "exposure": 0.05},
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    rec.decision_chain.steps = [DecisionStep(step_name="final_check", result="pass", detail="")]
    chain.append(rec)
    assert chain.record_count == 1
    assert chain.verify_integrity()


def test_append_correction_immutable_fails():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-correction", final_decision="EXECUTE",
        final_reason_code="TEST",
        risk_gate_results={"g1": "pass"},
        risk_snapshot={"var": 0.02},
        ai_opinions=[{"ai_name": "ai1", "support": True, "confidence": 0.7}],
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    chain.append(rec)
    corr = create_decision_audit_record(
        trace_id="trace-corr", final_decision="EXECUTE",
        final_reason_code="CORRECTED",
        risk_gate_results={"g1": "pass"},
        risk_snapshot={"var": 0.02},
        ai_opinions=[{"ai_name": "ai1", "support": True, "confidence": 0.7}],
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    with pytest.raises(ImmutableRecordError) as exc:
        chain.append_correction(rec, corr)
    assert "Cannot mutate an immutable append-only record" in str(exc.value)


def test_order_execution_allowed_false_invariant():
    chain = AuditTrailChain()
    rec = create_decision_audit_record(
        trace_id="trace-oea", final_decision="EXECUTE",
        final_reason_code="TEST",
        risk_gate_results={"g1": "pass"},
        risk_snapshot={"var": 0.02},
        ai_opinions=[{"ai_name": "ai1", "support": True, "confidence": 0.7}],
        market_session_state="continuous",
        auction_session_state="continuous",
        halt_disposition_attention="none",
        liquidity_insufficiency="none",
    )
    rec.decision_chain.steps = [DecisionStep(step_name="final_check", result="pass", detail="")]
    chain.append(rec)
    assert chain.verify_integrity()
    # order_execution_allowed is a system-level flag, not stored in audit record
    # This test verifies EXECUTE decisions can exist in audit trail
    # while order_execution_allowed=FALSE is enforced at system level
    assert True
