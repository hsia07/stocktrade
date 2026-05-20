"""
test_r029_r030_six_ai_meeting_trace_chain_backlog_labeling.py

Tests for R029_R030_SIX_AI_MEETING_TRACE_CHAIN_BACKLOG_LABELING_REWORK_BEFORE_R049.

Scope:
- Verify no source file claims "REAL_MEETING_ENGINE_IMPLEMENTED"
- Verify meeting table / roundtable absence is properly recorded
- Verify formal trace_id vs decision_id distinction
- Verify decision_chain absence
- Verify per-AI veto record absence
- Verify learning/decisions API is not live meeting record
- Verify R049 readiness remains FALSE while blockers exist
- No trading control pollution
- No order_execution_allowed changes
- No broker / live / execution pollution
"""

import json
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
SERVER_V2_PATH = PROJECT_ROOT / "server_v2.py"
INDEX_V2_HTML_PATH = PROJECT_ROOT / "index_v2.html"
GOVERNANCE_AUDIT_DIR = PROJECT_ROOT / "_governance" / "audit"


class TestSixAIMeetingFalseClaimPrevention:
    """Prevents false "full meeting implemented" claims."""

    def test_no_real_meeting_engine_implemented_claim(self, server_v2_text):
        """Source must not claim REAL_MEETING_ENGINE_IMPLEMENTED."""
        assert "REAL_MEETING_ENGINE_IMPLEMENTED" not in server_v2_text, \
            "Source must not contain REAL_MEETING_ENGINE_IMPLEMENTED claim"

    def test_no_affirmative_full_meeting_claim(self, server_v2_text):
        """Source must not claim full six-AI meeting is implemented."""
        patterns = [
            r"六大AI.*完整",
            r"六角色.*完整",
            r"meeting.*complete",
            r"meeting.*implemented",
            r"六AI.*已完成",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, server_v2_text)
            assert not matches, f"Source must not contain affirmative full-meeting claim: {pattern}"


class TestMeetingTableRoundtableAbsence:
    """Verifies meeting table / roundtable absence is properly recorded."""

    def test_no_roundtable_or_meeting_table_source(self, server_v2_text):
        """server_v2.py must not contain meeting table / roundtable source."""
        patterns = [
            "roundtable",
            "meeting_table",
            "MeetingTable",
            "Roundtable",
        ]
        for pattern in patterns:
            assert pattern not in server_v2_text, \
                f"server_v2.py must not contain {pattern} — meeting table not implemented"

    def test_six_ai_classes_not_meeting_brain(self, server_v2_text):
        """Six AI classes exist as standalone classes, not a meeting brain."""
        six_ai_classes = [
            "class QuantResearcher",
            "class Backtester",
            "class RiskOfficer",
            "class SignalEngineer",
            "class ExecutionEngineer",
            "class MarketAnalyst",
        ]
        for cls in six_ai_classes:
            assert cls in server_v2_text, f"{cls} must exist as standalone class"


class TestTraceIdVsDecisionId:
    """Verifies formal trace_id vs decision_id distinction."""

    def test_decision_id_not_treated_as_formal_trace_id(self, server_v2_text):
        """decision_id (D{timestamp}) must not be called trace_id."""
        lines = server_v2_text.split("\n")
        for i, line in enumerate(lines, 1):
            if "decision_id" in line:
                assert "trace_id" not in line.lower() or "decision_id" not in line.lower(), \
                    f"Line {i}: decision_id must not be conflated with trace_id"

    def test_trace_id_formal_field_not_in_decision_log(self, server_v2_text):
        """decision_log records must not have formal trace_id field."""
        if "decision_log" in server_v2_text:
            decision_log_pattern = re.search(
                r'def log_decision\(self.*?\n(.*?)LearningDataStore\.append',
                server_v2_text, re.DOTALL
            )
            if decision_log_pattern:
                content = decision_log_pattern.group(0)
                assert '"trace_id"' not in content, \
                    "decision_log must not have formal trace_id field — only decision_id (weak ID)"


class TestDecisionChainAbsence:
    """Verifies decision_chain is not implemented."""

    def test_no_decision_chain_in_server_v2(self, server_v2_text):
        """server_v2.py must not contain decision_chain field."""
        assert "decision_chain" not in server_v2_text, \
            "decision_chain not implemented — decisions are isolated"


class TestPerAIVetoRecordAbsence:
    """Verifies per-AI veto record is not implemented."""

    def test_no_per_ai_veto_recording(self, server_v2_text):
        """Individual AI veto recording must not be claimed."""
        patterns = [
            "per.*ai.*veto",
            "veto.*record.*ai",
            "ai.*veto.*log",
            "quant.*veto",
            "backtest.*veto",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, server_v2_text, re.IGNORECASE)
            if matches:
                assert False, f"Source must not claim per-AI veto recording: {pattern}"

    def test_consensus_scoring_not_full_meeting(self, server_v2_text):
        """get_consensus_score() is consensus scoring, not full meeting."""
        assert "get_consensus_score" in server_v2_text, \
            "Consensus scoring engine exists but is not a full meeting"
        if "def get_consensus_score" in server_v2_text:
            match = re.search(
                r"def get_consensus_score.*?\"\"\"(.*?)\"\"\"",
                server_v2_text, re.DOTALL
            )
            if match:
                doc = match.group(1)
                assert "meeting" not in doc.lower() or "meeting" in " roundtable", \
                    "get_consensus_score docstring must not claim meeting"


class TestLearningAPINotLiveMeetingRecord:
    """Verifies /api/learning/decisions is learning log, not live meeting."""

    def test_learning_decisions_api_returns_decision_log(self, server_v2_text):
        """learning/decisions endpoint must return decision_log, not live meeting."""
        pattern = re.search(
            r'@app\.get\("/api/learning/decisions"\).*?return.*?decision_log',
            server_v2_text, re.DOTALL
        )
        assert pattern, \
            "/api/learning/decisions must return decision_log (learning log, not live meeting)"

    def test_no_live_meeting_record_claim(self, server_v2_text):
        """Source must not claim learning API is live meeting record."""
        patterns = [
            "live.*meeting",
            "meeting.*record",
            "meeting.*log",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, server_v2_text, re.IGNORECASE)
            if matches:
                assert False, f"Source must not claim learning API is live meeting: {pattern}"


class TestR049ReadinessBlockersRecorded:
    """Verifies R049 readiness blockers are properly recorded."""

    def test_r049_readiness_false_in_index_v2_html(self, html_v2_text):
        """index_v2.html must disclaim R049 readiness."""
        disclaimers = [
            "不代表 R049 ready",
            "不代表 R049",
        ]
        found = any(d in html_v2_text for d in disclaimers)
        assert found, "index_v2.html must explicitly disclaim R049 ready status"

    def test_no_affirmative_r049_ready_claim(self, html_v2_text):
        """HTML must not contain affirmative R049 ready claim."""
        affirm = re.search(
            r'(?<!不代表\s)(?<!not\s)(?<!非)R049\s+(?:ready|就緒|完成)',
            html_v2_text, re.IGNORECASE
        )
        assert not affirm, "Must not claim affirmative R049 ready status"

    def test_six_ai_meeting_label_conservative(self, html_v2_text):
        """Six AI meeting label must be conservative."""
        conservative_patterns = [
            "共識評分",
            "六大角色",
            "六角色",
            "AI.*評分",
            "共識",
        ]
        found = any(re.search(p, html_v2_text) for p in conservative_patterns)
        assert found, "Six AI panel must use conservative labels (not full meeting)"

    def test_no_meeting_table_claim_in_html(self, html_v2_text):
        """HTML must not claim meeting table exists."""
        patterns = [
            "開會桌",
            "會議桌",
            "meeting table",
            "roundtable",
            "六AI開會",
        ]
        for pattern in patterns:
            assert pattern not in html_v2_text, \
                f"HTML must not claim meeting table: {pattern}"


class TestOrderExecutionSafety:
    """Verifies order execution safety is preserved."""

    def test_order_execution_allowed_false_preserved(self, server_v2_text):
        """order_execution_allowed must remain FALSE."""
        assert "ORDER_EXECUTION_ALLOWED = False" in server_v2_text or \
               "ORDER_EXECUTION_ALLOWED=False" in server_v2_text or \
               "order_execution_allowed = False" in server_v2_text, \
            "order_execution_allowed must remain FALSE"

    def test_execution_place_blocks_when_disabled(self, server_v2_text):
        """ExecutionEngineer.place() must check order_execution_allowed."""
        assert "if not ORDER_EXECUTION_ALLOWED" in server_v2_text or \
               "if not order_execution_allowed" in server_v2_text, \
            "ExecutionEngineer.place() must check ORDER_EXECUTION_ALLOWED before placing orders"


class TestAppendOnlyDecisionRecordPartial:
    """Verifies append-only decision record is partial."""

    def test_decision_log_exists(self, server_v2_text):
        """decision_log append-only record must exist."""
        assert "decision_log" in server_v2_text, "decision_log must exist"

    def test_outcome_log_exists(self, server_v2_text):
        """outcome_log append-only record must exist."""
        assert "outcome_log" in server_v2_text, "outcome_log must exist"

    def test_no_trace_id_field_in_decision_records(self, server_v2_text):
        """Decision records must not have trace_id field."""
        log_decision_pattern = re.search(
            r'def log_decision\(self, data.*?\n(.*?)self\.decision_log\.append',
            server_v2_text, re.DOTALL
        )
        if log_decision_pattern:
            content = log_decision_pattern.group(0)
            assert '"trace_id"' not in content and "'trace_id'" not in content, \
                "Decision records must not have trace_id field (only decision_id)"


class TestLocalArbitratorPartial:
    """Verifies local arbitrator is partial."""

    def test_get_consensus_score_exists(self, server_v2_text):
        """get_consensus_score() consensus scoring arbitrator must exist."""
        assert "def get_consensus_score" in server_v2_text, \
            "Consensus scoring arbitrator exists but is partial (not full meeting)"

    def test_risk_veto_exists(self, server_v2_text):
        """RiskOfficer veto must exist as a gate."""
        assert "def can_enter" in server_v2_text, \
            "RiskOfficer.can_enter() veto gate must exist"

    def test_consensus_threshold_gate_exists(self, server_v2_text):
        """CONSENSUS_THRESHOLD gate must exist."""
        assert "CONSENSUS_THRESHOLD" in server_v2_text, \
            "CONSENSUS_THRESHOLD gate must exist"


class TestSixAIClassesExist:
    """Verifies six AI agent classes exist as standalone inputs."""

    def test_quant_researcher_exists(self, server_v2_text):
        """QuantResearcher class must exist."""
        assert "class QuantResearcher" in server_v2_text

    def test_backtest_engineer_exists(self, server_v2_text):
        """Backtester class must exist (backtest AI role)."""
        assert "class Backtester" in server_v2_text

    def test_risk_officer_exists(self, server_v2_text):
        """RiskOfficer class must exist."""
        assert "class RiskOfficer" in server_v2_text

    def test_signal_engineer_exists(self, server_v2_text):
        """SignalEngineer class must exist."""
        assert "class SignalEngineer" in server_v2_text

    def test_execution_engineer_exists(self, server_v2_text):
        """ExecutionEngineer class must exist."""
        assert "class ExecutionEngineer" in server_v2_text

    def test_market_analyst_exists(self, server_v2_text):
        """MarketAnalyst class must exist."""
        assert "class MarketAnalyst" in server_v2_text


# ── Fixtures ──

@pytest.fixture(scope="module")
def server_v2_text():
    return SERVER_V2_PATH.read_text(encoding="utf-8")

@pytest.fixture(scope="module")
def html_v2_text():
    return INDEX_V2_HTML_PATH.read_text(encoding="utf-8")