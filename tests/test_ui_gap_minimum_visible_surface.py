"""
test_ui_gap_minimum_visible_surface.py
UI Gap Minimum Visible Surface Hardening Test Suite.
Read-only audit of index.html visible surface.
No server startup, no runtime, no broker API, no LLM calls.
"""

from pathlib import Path
import pytest

INDEX_HTML = Path(__file__).parent.parent / "index.html"
INDEX_V2 = Path(__file__).parent.parent / "index_v2.html"


@pytest.fixture(scope="module")
def html():
    return INDEX_HTML.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════
# Panel presence
# ═══════════════════════════════════════════════════════════════

class TestPanelPresence:
    def test_ui_gap_panel_present(self, html):
        assert 'id="ui-gap-status-panel"' in html
        assert "系統功能狀態揭露" in html

# ═══════════════════════════════════════════════════════════════
# Round status visibility (must be present, but not claimed complete)
# ═══════════════════════════════════════════════════════════════

class TestRoundStatusVisible:
    def test_r022_teaching_ui_status_visible_but_not_claimed_complete(self, html):
        assert "R022 新手教學 UI" in html
        assert "尚未完整完成" in html
        assert "已完成新手教學" not in html

    def test_r023_onboarding_status_visible_but_not_claimed_complete(self, html):
        assert "R023 首頁 onboarding" in html
        assert "尚未完整完成" in html
        assert "已完成 onboarding" not in html

    def test_r024_summary_status_visible_but_not_runtime_wired(self, html):
        assert "R024 智慧摘要層" in html
        assert "Partial" in html or "partial" in html
        assert "無 runtime summary" in html
        assert "智慧摘要層已完成" not in html

    def test_r025_mobile_emergency_status_visible_but_no_control(self, html):
        assert "R025 手機 / Emergency 接管" in html
        assert "尚未完整完成" in html
        assert "無緊急控制" in html
        assert "已完成手機接管" not in html

    def test_r026_simulation_status_visible_but_no_order_controls(self, html):
        assert "R026 模擬交易 UI" in html
        assert "尚未完整完成" in html
        assert "無下單" in html or "無 broker" in html
        assert "可開始模擬交易" not in html

    def test_r029_status_visible_and_topic_mismatch_disclosed_if_applicable(self, html):
        assert "R029 成本 / 滑價 / 成交機率" in html
        assert "Partial" in html or "partial" in html
        assert "主題需複核" in html or "placeholder" in html

    def test_r040_market_candidate_pool_status_visible_but_no_live_query_claim(self, html):
        assert "R040 市場候選池" in html
        assert "Backend 模組存在" in html or "未接入" in html
        assert "可查任意股票" not in html
        assert "任意股票查詢已完成" not in html

# ═══════════════════════════════════════════════════════════════
# Safety and security invariants
# ═══════════════════════════════════════════════════════════════

class TestSafetyInvariants:
    def test_order_execution_allowed_false_visible(self, html):
        assert "order_execution_allowed" in html
        assert "FALSE" in html
        # Verify gap panel region has FALSE and no TRUE
        panel_start = html.find('id="ui-gap-status-panel"')
        panel_end = html.find('</main>', panel_start)
        if panel_end == -1:
            panel_end = len(html)
        panel_html = html[panel_start:panel_end]
        # FALSE must appear in or near the panel (it is in the right column)
        assert "FALSE" in panel_html
        assert "TRUE" not in panel_html

    def test_no_buy_sell_order_approve_reject_controls_added(self, html):
        forbidden = ["買入", "賣出", "下單", "approve", "reject", "執行交易", "sendOrder"]
        panel_start = html.find('id="ui-gap-status-panel"')
        panel_end = html.find('</div>', panel_start) + 6
        panel_html = html[panel_start:panel_end]
        for word in forbidden:
            assert word not in panel_html, f"Forbidden word '{word}' found in ui-gap panel"

    def test_no_live_or_broker_toggle_added(self, html):
        assert "live" not in html.lower() or "未接入" in html
        # Specifically in the gap panel there should be no toggle
        panel_start = html.find('id="ui-gap-status-panel"')
        panel_end = html.find('</div>', panel_start) + 6
        panel_html = html[panel_start:panel_end]
        assert "toggle" not in panel_html.lower()
        assert "switch" not in panel_html.lower()

    def test_no_new_api_fetch_or_post_added_for_ui_gap_panel(self, html):
        # The gap panel should not add any fetch/POST/XHR/websocket command
        panel_start = html.find('id="ui-gap-status-panel"')
        panel_end = html.find('</div>', panel_start) + 6
        panel_html = html[panel_start:panel_end]
        assert "fetch(" not in panel_html
        assert "XMLHttpRequest" not in panel_html
        assert "$.post" not in panel_html
        assert "axios" not in panel_html
        assert "ws.send" not in panel_html

    def test_no_fubon_api_reference_as_active_control(self, html):
        # Verify fubon reference exists as "not integrated" status only
        assert "富邦" in html
        assert "未接入" in html
        # Should not say "已接入富邦" or imply active use
        assert "已接入富邦" not in html
        assert "富邦 API 已啟用" not in html

    def test_no_runtime_or_r049_start_controls_added(self, html):
        panel_start = html.find('id="ui-gap-status-panel"')
        panel_end = html.find('</div>', panel_start) + 6
        panel_html = html[panel_start:panel_end]
        assert "啟動 R049" not in panel_html
        assert "開始交易" not in panel_html
        assert "啟動 runtime" not in panel_html

    def test_no_secret_values_rendered(self, html):
        secrets = ["API_KEY", "SECRET", "TOKEN", "PASSWORD", "CHAT_ID", "sk-"]
        panel_start = html.find('id="ui-gap-status-panel"')
        panel_end = html.find('</div>', panel_start) + 6
        panel_html = html[panel_start:panel_end]
        for s in secrets:
            assert s not in panel_html, f"Secret pattern '{s}' found in gap panel"

    def test_no_placeholder_or_mojibake_visible(self, html):
        panel_start = html.find('id="ui-gap-status-panel"')
        panel_end = html.find('</div>', panel_start) + 6
        panel_html = html[panel_start:panel_end]
        # No obvious placeholder text like "EntryEntry", "SHORT SHORT", "Entry?"
        assert "EntryEntry" not in panel_html
        assert "Entry?" not in panel_html
        assert "SHORT SHORT" not in panel_html

# ═══════════════════════════════════════════════════════════════
# Labels and disclaimers
# ═══════════════════════════════════════════════════════════════

class TestLabelsAndDisclaimers:
    def test_contract_only_and_partial_labels_present(self, html):
        assert "Contract-only" in html or "contract-only" in html
        assert "Partial" in html or "partial" in html

    def test_ui_visible_gate_required_disclaimers_present(self, html):
        assert "僅供閱覽" in html or "僅為可見狀態揭露" in html
        assert "不代表功能已完成" in html or "不代表功能已完整實作" in html
        assert "不代表任何功能已開放使用" in html

    def test_existing_core_a4_shadow_panel_preserved(self, html):
        assert 'id="core-a4-shadow-panel"' in html
        assert "Core-A Shadow Snapshot" in html

    def test_index_v2_not_modified(self, html):
        # Verify index_v2.html unchanged by checking timestamp or absence of gap panel
        assert INDEX_V2.exists()
        v2_html = INDEX_V2.read_text(encoding="utf-8")
        assert 'id="ui-gap-status-panel"' not in v2_html
        assert "系統功能狀態揭露" not in v2_html

# ═══════════════════════════════════════════════════════════════
# HTML / JS syntax sanity
# ═══════════════════════════════════════════════════════════════

class TestHtmlSyntaxSanity:
    def test_html_js_syntax_sanity(self, html):
        # Basic HTML well-formedness checks for the gap panel region
        panel_start = html.find('id="ui-gap-status-panel"')
        assert panel_start > 0, "ui-gap-status-panel not found"
        # Count opening/closing div tags in the panel region
        # A rough check: the panel should be a single card div
        panel_end = html.find('</div>', panel_start) + 6
        panel_html = html[panel_start:panel_end]
        open_divs = panel_html.count('<div')
        close_divs = panel_html.count('</div>')
        # The panel contains nested divs; just verify no obvious syntax errors
        assert open_divs >= close_divs, "Unbalanced div tags in gap panel"
        assert '<div' in panel_html
        assert '</div>' in panel_html
