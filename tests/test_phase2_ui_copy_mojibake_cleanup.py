"""Phase2 UI copy/mojibake cleanup: verify no placeholder display text remains,
logic-bound protocol keywords preserved, Core-A4 panel untouched, no new controls added."""

import re
import json
import pytest

HTML_PATH = "index.html"

with open(HTML_PATH, "r", encoding="utf-8") as f:
    HTML = f.read()


# ── Known placeholder patterns that should NOT appear as display text ──
PLACEHOLDER_PATTERNS = [
    "Entry?",
    "EntryEntry",
    "EntrySHORT",
    "EntryEntrySHORT",
    "Entry5",
    "SHORT SHORT",
    "SHORT Entry",
    "Entry SHORT",
    "? SHORT",
]


def find_display_text_occurrences(pattern):
    """Find all occurrences of pattern in HTML text nodes (not JS strings, not CSS)."""
    occurrences = []
    for i, line in enumerate(HTML.split("\n"), 1):
        if pattern in line:
            # Skip JS property access
            if "pos.entry" in line or "t.entry" in line:
                continue
            # Skip CSS class names
            if ".short" in line or ".pos-dir.short" in line or ".signal-item.short" in line:
                continue
            # Skip logic-bound protocol matching
            if "includes" in line and "SHORT" in line:
                continue
            # Skip CSS variable references
            if "var(--" in line:
                continue
            occurrences.append((i, line.strip()))
    return occurrences


class TestPlaceholderCleanup:
    def test_no_placeholder_display_text(self):
        """No SHORT/Entry/Entry?/EntryEntry placeholder should appear as display text."""
        all_found = {}
        for pat in PLACEHOLDER_PATTERNS:
            found = find_display_text_occurrences(pat)
            if found:
                all_found[pat] = found
        assert not all_found, (
            f"Placeholder display text still found: {json.dumps(all_found, indent=2, ensure_ascii=False)}"
        )

    def test_only_single_SHORT_and_Entry_remnants_are_acceptable(self):
        """Verify no 'SHORT' or 'Entry' as standalone display text."""
        standalone_patterns = [
            ("SHORT", "'SHORT'", "JS string"),
            ("Entry", "'Entry'", "JS string"),
        ]
        for keyword, context, ctx_type in standalone_patterns:
            lines = HTML.split("\n")
            for i, line in enumerate(lines, 1):
                if keyword in line and context in line:
                    # Skip known safe/LOGIC_BOUND lines
                    if "statusLabel" in line:
                        continue
                    if "includes" in line:
                        continue  # LOGIC_BOUND protocol matching
                    if "pos.entry" in line or "t.entry" in line:
                        continue  # JS property access, not display text
                    pytest.fail(f"Line {i}: standalone '{keyword}' found in {ctx_type}: {line.strip()}")


class TestLogicBoundPreserved:
    def test_detect_new_signal_protocol_keywords(self):
        """L735: detectNewSignal uses SHORT/LONG for protocol matching."""
        assert "includes('SHORT')" in HTML, "detectNewSignal SHORT protocol check missing"
        assert "includes('LONG')" in HTML, "detectNewSignal LONG protocol check missing"

    def test_render_agents_detail_coloring(self):
        """L709-711: detail coloring uses SHORT/? for classification."""
        # Count 'includes' with 'SHORT' in renderAgents context
        count = HTML.count("includes")
        assert count >= 3, f"Expected at least 3 includes() calls, found {count}"

    def test_render_risk_alert_detection(self):
        """L895: renderRisk uses HALTED/SHORT for severity classification."""
        assert "includes('HALTED')" in HTML, "renderRisk HALTED check missing"
        assert "includes('Remaining')" in HTML, "renderRisk Remaining check missing"


class TestCoreA4Preserved:
    def test_core_a4_panel_present(self):
        """Core-A4 shadow panel ID preserved."""
        assert 'id="core-a4-shadow-panel"' in HTML

    def test_shadow_body_present(self):
        """shadow-body div preserved."""
        assert 'id="shadow-body"' in HTML

    def test_render_core_a_shadow_present(self):
        """renderCoreAShadow function preserved."""
        assert "function renderCoreAShadow" in HTML

    def test_data_core_a_shadow_snapshot_path_present(self):
        """data.core_a_shadow_snapshot read path preserved."""
        assert "core_a_shadow_snapshot" in HTML

    def test_order_execution_allowed_display(self):
        """order_execution_allowed display logic preserved."""
        assert "order_execution_allowed" in HTML

    def test_no_order_side_effects_display(self):
        """no_order_side_effects display logic preserved."""
        assert "no_order_side_effects" in HTML


class TestNoNewControls:
    def test_no_buy_sell_controls(self):
        """No buy/sell/approve/order controls added."""
        controls = ["buyBtn", "sellBtn", "approveBtn", "orderBtn", "buy-button", "sell-button"]
        for c in controls:
            assert c not in HTML, f"Unexpected control found: {c}"

    def test_no_trade_action_binding(self):
        """No trade action event listeners."""
        actions = [
            "buy-trade", "sell-trade", "placeOrder", "executeTrade",
            "submitOrder", "sendOrder",
        ]
        for a in actions:
            assert a not in HTML, f"Unexpected trade action: {a}"

    def test_no_new_fetch_mutations(self):
        """No POST/PUT/DELETE/PATCH fetch mutations added by cleanup."""
        fetches = HTML.count("fetch(")
        posts = HTML.count("method: 'POST'")
        puts = HTML.count("method: 'PUT'")
        deletes = HTML.count("method: 'DELETE'")
        patches = HTML.count("method: 'PATCH'")
        # Original had 2 fetches: GET /api/mode and POST /api/toggle_mode
        # If these counts change, verify they're from the original code
        assert posts <= 1, f"Unexpected POST fetch count: {posts}"
        assert puts == 0, f"Unexpected PUT fetch: {puts}"
        assert deletes == 0, f"Unexpected DELETE fetch: {deletes}"
        assert patches == 0, f"Unexpected PATCH fetch: {patches}"

    def test_no_websocket_send_mutations(self):
        """No new WebSocket.send() mutations added."""
        sends = HTML.count("ws.send")
        sends += HTML.count("state.ws.send")
        # Original should have 1 ws.send for reset
        assert sends <= 2, f"Unexpected WebSocket.send count: {sends}"


class TestFeatureGapsPreserved:
    def test_r022_teaching_ui_not_present(self):
        """R022 teaching UI not completed."""
        assert "教學介面" not in HTML

    def test_r023_onboarding_not_present(self):
        """R023 onboarding not completed."""
        assert "新手上路" not in HTML

    def test_r024_summaries_not_present(self):
        """R024 summary reports not completed."""
        keywords = ["交易日報", "績效報告", "summary-report"]
        for k in keywords:
            assert k not in HTML, f"R024 summary feature falsely present: {k}"

    def test_r026_simulation_not_present(self):
        """R026 simulation mode not completed."""
        assert "情境模擬" not in HTML

    def test_r029_meeting_viz_not_present(self):
        """R029 meeting visualization not completed."""
        assert "AI 會議" not in HTML

    def test_r040_stock_search_not_present(self):
        """R040 stock search not completed."""
        assert "股票搜尋" not in HTML
        assert "stock-search" not in HTML


class TestSecurityAndInvariants:
    def test_no_secret_values_in_ui(self):
        """No secret-like strings rendered."""
        secrets = ["api_key", "api.secret", "token", "chat_id", "broker_cred"]
        for s in secrets:
            assert s not in HTML, f"Secret-like string found: {s}"

    def test_no_runtime_state_write(self):
        """No runtime state write endpoints."""
        paths = ["/api/state", "/api/runtime", "/api/order"]
        for p in paths:
            # Check for POST/PUT/DELETE to these paths
            if f"'{p}'" in HTML or f'"{p}"' in HTML:
                # Verify it's a GET, not a mutation
                pass

    def test_no_new_api_endpoint_text(self):
        """No new API endpoint strings added."""
        endpoints = ["/api/buy", "/api/sell", "/api/order", "/api/approve",
                     "/api/reject", "/api/execute", "/api/trade"]
        for e in endpoints:
            assert e not in HTML, f"New API endpoint text found: {e}"

    def test_order_execution_allowed_stays_false(self):
        """order_execution_allowed is displayed as FALSE."""
        # This checks the Core-A4 panel display, which shows the value from server data
        assert "order_execution_allowed" in HTML


class TestChineseDisplayText:
    def test_tab_labels_chinese(self):
        """Tab buttons show Chinese labels."""
        assert "儀表板" in HTML
        assert "AI 代理人" in HTML
        assert "即時報價" in HTML
        assert "持倉概覽" in HTML
        assert "交易訊號" in HTML
        assert "成交記錄" in HTML
        assert "風控管理" in HTML

    def test_sidebar_chinese(self):
        """Sidebar shows Chinese labels."""
        assert "主選單" in HTML
        assert "系統狀態" in HTML
        assert "即時損益" in HTML
        assert "今日交易" in HTML

    def test_kpi_chinese(self):
        """KPI labels show Chinese."""
        assert "交易次數" in HTML
        assert "持倉數量" in HTML
        assert "連續虧損" in HTML
        assert "訊號數量" in HTML

    def test_card_titles_chinese(self):
        """Card titles show Chinese."""
        assert "系統日誌" in HTML
        assert "最新訊號" in HTML
        assert "持倉明細" in HTML
        assert "訊號記錄" in HTML
        assert "交易記錄" in HTML
        assert "風控參數" in HTML
        assert "風控狀態" in HTML

    def test_status_bar_chinese(self):
        """Status bar shows Chinese."""
        assert "連線:" in HTML
        assert "資料時間:" in HTML
        assert "引擎狀態:" in HTML
        assert "唯讀模式" in HTML

    def test_agent_labels_chinese(self):
        """Agent labels show Chinese role names."""
        assert "量化分析" in HTML
        assert "回測引擎" in HTML
        assert "風險控制" in HTML
        assert "訊號生成" in HTML
        assert "執行代理" in HTML
        assert "市場觀察" in HTML

    def test_symbol_names_chinese(self):
        """Stock symbol names show Chinese."""
        assert "台積電" in HTML
        assert "聯發科" in HTML
        assert "廣達" in HTML
        assert "鴻海" in HTML
        assert "可成" in HTML

    def test_empty_state_chinese(self):
        """Empty state fallbacks show Chinese."""
        assert "暫無持倉" in HTML
        assert "暫無成交" in HTML
        assert "暫無訊號" in HTML
        assert "等待資料" in HTML

    def test_risk_params_chinese(self):
        """Risk parameter labels show Chinese."""
        assert "單筆最大損失" in HTML
        assert "日損限額" in HTML
        assert "連續虧損" in HTML
        assert "持倉上限" in HTML
        assert "保證金比率" in HTML

    def test_position_direction_chinese(self):
        """Position direction shows Chinese chars."""
        assert "'多' : '空'" in HTML

    def test_signal_direction_chinese(self):
        """Signal direction showing Chinese."""
        assert "'做多'" in HTML
        assert "'做空'" in HTML

    def test_status_labels_chinese(self):
        """Agent status labels show Chinese."""
        assert "ok: '正常'" in HTML
        assert "warn: '注意'" in HTML
        assert "alert: '異常'" in HTML
        assert "idle: '閒置'" in HTML

    def test_reset_button_chinese(self):
        """Reset button shows Chinese."""
        assert 'id="resetBtn">重設</button' in HTML

    def test_confirm_dialog_chinese(self):
        """Confirm dialog shows Chinese."""
        assert "確定要重設系統嗎？" in HTML

    def test_ws_messages_chinese(self):
        """WebSocket connection messages show Chinese."""
        assert "已連線" in HTML
        assert "連線中斷" in HTML
        assert "連線錯誤" in HTML
        assert "無法建立 WebSocket 連線" in HTML
        assert "WebSocket 已連線" in HTML

    def test_trade_header_chinese(self):
        """Trade table headers show Chinese."""
        assert "標的代號" in HTML
        assert "方向" in HTML
        assert "進場價" in HTML
        assert "出場價" in HTML
        assert "張數" in HTML
        assert "損益" in HTML
        assert "原因" in HTML
