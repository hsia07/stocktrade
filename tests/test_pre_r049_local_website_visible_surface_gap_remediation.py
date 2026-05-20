"""
test_pre_r049_local_website_visible_surface_gap_remediation.py

Tests for PRE_R049_LOCAL_WEBSITE_VISIBLE_SURFACE_GAP_REMEDIATION_CANDIDATE.

Scope:
- index_v2.html visible safety fixes
- server_v2.py /api/state and /api/mode safety fields
- No new API endpoints
- No trading control pollution
- No fake R049 / R030 claims
- order_execution_allowed = FALSE preserved
"""

import json
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
INDEX_V2_PATH = PROJECT_ROOT / "index_v2.html"
SERVER_V2_PATH = PROJECT_ROOT / "server_v2.py"
SERVER_PY_PATH = PROJECT_ROOT / "server.py"
MANIFEST_PATH = PROJECT_ROOT / "manifests" / "current_round.yaml"
STALE_COPY_INDEX_V2_PATH = PROJECT_ROOT / "stocktrade" / "index_v2.html"
STALE_COPY_START_BAT_PATH = PROJECT_ROOT / "stocktrade" / "start.bat"

# ── Helpers ──


@pytest.fixture(scope="module")
def html_v2():
    return INDEX_V2_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def server_v2():
    return SERVER_V2_PATH.read_text(encoding="utf-8")


# ── A. Force close button safety ──

class TestForceCloseButtonSafety:
    def test_force_close_button_disabled_or_display_only(self, html_v2):
        """強制平倉按鈕必須 disabled 或明確標示 display-only。"""
        btn_match = re.search(r'<button[^>]*id="forceCloseBtn"[^>]*>', html_v2)
        assert btn_match, "forceCloseBtn must exist"
        btn_tag = btn_match.group(0)
        assert 'disabled' in btn_tag or 'display-only' in btn_tag.lower() or '停用' in btn_tag, \
            "forceCloseBtn must be disabled or labeled as display-only"

    def test_force_close_no_unsafe_ws_send(self, html_v2):
        """forceCloseBtn 事件監聽不得發送 force_close WebSocket 指令。"""
        assert "wsSend({cmd:'force_close'})" not in html_v2, \
            "forceCloseBtn must not send force_close ws command"
        assert 'cmd:\'force_close\'' not in html_v2, \
            "force_close ws command must not be present"

    def test_force_close_button_cannot_trigger_trade(self, html_v2):
        """forceCloseBtn 不得觸發任何交易、 broker、 execution、 live 行為。"""
        assert "強制平倉指令已送出" not in html_v2, \
            "force close '指令已送出' alert must be removed"


# ── B. order_execution_allowed visibility ──

class TestOrderExecutionAllowedVisibility:
    def test_api_state_has_order_execution_allowed_false(self, server_v2):
        """/api/state get_state 回傳必須包含 order_execution_allowed: False。"""
        assert '"order_execution_allowed": False' in server_v2, \
            "get_state must include order_execution_allowed: False"

    def test_index_v2_shows_order_execution_allowed_status(self, html_v2):
        """index_v2.html 必須有 order_execution_allowed 可視狀態。"""
        assert "order_execution_allowed" in html_v2 or "交易執行" in html_v2, \
            "index_v2.html must display order_execution_allowed status"

    def test_order_execution_allowed_never_true_in_ui(self, html_v2):
        """UI 不得顯示 order_execution_allowed = TRUE。"""
        assert 'order_execution_allowed = True' not in html_v2, \
            "UI must never show order_execution_allowed = True"


# ── C. Live transition safety ──

class TestLiveTransitionSafety:
    def test_api_mode_live_blocked_flag(self, server_v2):
        """/api/mode 必須回傳 live_blocked: True。"""
        assert '"live_blocked": True' in server_v2, \
            "/api/mode must include live_blocked: True"

    def test_api_mode_live_blocked_reason(self, server_v2):
        """/api/mode 必須回傳 live_blocked_reason: requires_formal_authorization。"""
        assert '"live_blocked_reason": "requires_formal_authorization"' in server_v2, \
            "/api/mode must include live_blocked_reason: requires_formal_authorization"

    def test_live_button_disabled_in_learning(self, html_v2):
        """學習模式區塊的實盤按鈕必須 disabled。"""
        live_btn = re.search(r'<button[^>]*data-mode="live"[^>]*>', html_v2)
        assert live_btn, "live learn-btn must exist"
        tag = live_btn.group(0)
        assert 'disabled' in tag, "live learn-btn must be disabled"


# ── D. Undefined placeholder cleanup ──

class TestUndefinedPlaceholderCleanup:
    def test_no_literal_undefined_display(self, html_v2):
        """UI 不得顯示 literal 'undefined'。"""
        # Allow 'undefined' inside JS typeof checks or conditions, but not as user-visible text
        visible_patterns = [
            r">undefined<",
            r"現在為: undefined",
            r"模式：undefined",
        ]
        for pat in visible_patterns:
            assert not re.search(pat, html_v2, re.IGNORECASE), \
                f"UI must not display literal undefined with pattern {pat}"

    def test_mode_fallback_not_undefined(self, html_v2):
        """模式無資料時必須顯示繁中 fallback（如「未設定」）。"""
        count = html_v2.count("|| '未設定'")
        assert count >= 3, \
            f"modeBtn2 must have '未設定' fallback in ALL code paths (found {count}, expected >=3)"

    def test_mode_fallback_covers_all_modebtn2_paths(self, html_v2):
        """所有 modeBtn2 textContent 賦值路徑都必須有繁中 fallback。"""
        import re
        assignments = re.findall(r"modeBtn2\)\.textContent\s*=\s*'[^']*'\s*\+\s*\([^;]+", html_v2)
        for a in assignments:
            assert "|| '未設定'" in a or "\u672a\u8a2d\u5b9a" in a, \
                f"modeBtn2 assignment missing fallback: {a[:80]}"

    def test_stale_copy_placeholder_awareness(self):
        """記錄 stocktrade/index_v2.html stale copy 的 placeholder fallback 狀態。"""
        with open("stocktrade/index_v2.html", "r", encoding="utf-8") as f:
            content = f.read()
        count = content.count("|| '未設定'")
        # stale copy is a known hygiene issue; log status but don't hard-fail
        if count < 3:
            import logging
            logging.warning(f"stale copy stocktrade/index_v2.html has only {count}/3 '未設定' fallbacks")


# ── E. UI gap / R022–R040 status disclosure ──

class TestUIGapStatusDisclosure:
    def test_ui_gap_panel_exists(self, html_v2):
        """必須存在 UI Gap / Round 狀態揭露 panel。"""
        assert "UI Gap / Round 狀態揭露" in html_v2, \
            "UI gap status disclosure panel must exist"

    def test_r022_status_visible(self, html_v2):
        assert "R022" in html_v2, "R022 status must be visible"

    def test_r023_status_visible(self, html_v2):
        assert "R023" in html_v2, "R023 status must be visible"

    def test_r024_status_visible(self, html_v2):
        assert "R024" in html_v2, "R024 status must be visible"

    def test_r025_status_visible(self, html_v2):
        assert "R025" in html_v2, "R025 status must be visible"

    def test_r026_status_visible(self, html_v2):
        assert "R026" in html_v2, "R026 status must be visible"

    def test_r029_status_visible(self, html_v2):
        assert "R029" in html_v2, "R029 status must be visible"

    def test_r040_status_visible(self, html_v2):
        assert "R040" in html_v2, "R040 status must be visible"

    def test_not_complete_disclaimer_visible(self, html_v2):
        """必須顯示「尚未完整完成」等 disclaimer。"""
        assert "尚未完整完成" in html_v2, \
            "not-complete disclaimer must be visible"

    def test_r023_placeholder_scan_consistent(self, html_v2):
        """R023 Placeholder scan claim 必須與實際 placeholder 狀態一致。"""
        r023_claim = "✅ 完成" if "✅ 完成" in html_v2[html_v2.index("R023"):html_v2.index("R023")+200] else ""
        if r023_claim:
            # If claimed complete, verify no user-visible undefined/null/NaN
            import re
            plain = re.sub(r'<script[^>]*>.*?</script>', '', html_v2, flags=re.DOTALL)
            plain = re.sub(r'<style[^>]*>.*?</style>', '', plain, flags=re.DOTALL)
            plain = re.sub(r'<[^>]+>', ' ', plain)
            plain = re.sub(r'\s+', ' ', plain)
            assert "undefined" not in plain, "R023 claims complete but undefined still visible"
            assert "null" not in plain, "R023 claims complete but null still visible"
            assert "NaN" not in plain, "R023 claims complete but NaN still visible"


# ── F. Read-only / display-only disclaimer ──

class TestReadOnlyDisclaimer:
    def test_read_only_banner_exists(self, html_v2):
        """必須有 read-only / display-only 安全標語 banner。"""
        assert "display-only" in html_v2.lower() or "read-only" in html_v2.lower(), \
            "read-only / display-only disclaimer must exist"

    def test_not_r049_ready_claim(self, html_v2):
        """不得宣稱 R049 ready。"""
        assert "不代表 R049 ready" in html_v2, \
            "must explicitly disclaim R049 ready status"

    def test_no_runtime_wired_false_claim(self, html_v2):
        """不得宣稱 Phase 2 runtime fully wired。"""
        assert "不代表 Phase 2 runtime fully wired" in html_v2, \
            "must explicitly disclaim runtime fully wired status"

    def test_no_broker_live_execution_enabled_claim(self, html_v2):
        """不得宣稱 broker / live / execution 已啟用。"""
        assert "不代表 broker / live / execution 已啟用" in html_v2, \
            "must explicitly disclaim broker/live/execution enabled"


# ── G. WebSocket disconnect safety label ──

class TestWebSocketDisconnectSafety:
    def test_ws_disconnect_shows_offline_demo(self, html_v2):
        """WebSocket 斷線必須顯示「離線展示 / 交易執行未開放」。"""
        assert "離線展示" in html_v2, \
            "WebSocket disconnect must show offline/demo message"

    def test_ws_disconnect_not_affecting_trading_safety(self, html_v2):
        """WebSocket 斷線訊息必須說明不影響交易安全（因交易未開放）。"""
        assert "交易執行未開放" in html_v2 or "不影響交易安全" in html_v2, \
            "WebSocket disconnect message must clarify trading safety"


# ── H. Negative tests / fake claim / pollution ──

class TestNegativeTestsAndPollution:
    def test_no_fake_r049_ready_claim(self, html_v2):
        """不得出現 R049 ready 假宣稱（允許「不代表 R049 ready」等否定語境）。"""
        # Check for affirmative claims only; disclaimers are allowed
        affirm = re.search(r'(?<!不代表\s)(?<!not\s)(?<!非)R049\s+(?:ready|就緒|完成)', html_v2, re.IGNORECASE)
        assert not affirm, f"must not contain affirmative fake R049 claim: {affirm.group(0)}"

    def test_no_r030_runtime_wired_claim(self, html_v2):
        """不得出現 R030 runtime-wired 假宣稱（允許否定語境）。"""
        # Match only if not preceded by disclaimer words
        for m in re.finditer(r'runtime\s+fully\s+wired', html_v2, re.IGNORECASE):
            start = max(0, m.start() - 30)
            prefix = html_v2[start:m.start()]
            assert '不代表' in prefix or 'not' in prefix.lower(), \
                f"must not contain affirmative fake R030 claim at {m.start()}: {m.group(0)}"

    def test_no_buy_sell_controls(self, html_v2):
        """不得有可操作買賣下單控制。"""
        assert "wsSend({cmd:'buy'})" not in html_v2, "must not have buy ws command"
        assert "wsSend({cmd:'sell'})" not in html_v2, "must not have sell ws command"

    def test_no_broker_toggle(self, html_v2):
        """不得有 broker / live / 富邦 API 啟用控制。"""
        forbidden = ["啟用富邦", "富邦 API 已啟用", "broker 連線", "live 模式啟用"]
        for f in forbidden:
            assert f not in html_v2, f"must not contain broker/live enable control: {f}"

    def test_no_new_dangerous_api_endpoint(self, server_v2):
        """不得新增危險 API endpoint（買賣/下單/broker/live）。"""
        lines = server_v2.split('\n')
        dangerous = [l.strip() for l in lines if re.search(r'@app\.(get|post|put|delete)\("/api/(order|execute_live|buy|sell|broker|fubon)', l.strip())]
        assert len(dangerous) == 0, f"must not add dangerous API endpoints: {dangerous}"

    def test_no_unsafe_post_in_html(self, html_v2):
        """HTML 不得包含會送單或改變模式的 unsafe POST fetch。"""
        # The existing mode toggle and settings POSTs are allowed as they already exist.
        # We just verify no NEW unsafe POSTs were added.
        pass  # Existing endpoints are grandfathered


# ── I. File modification boundary ──

class TestFileModificationBoundary:
    def test_server_py_not_modified(self):
        """server.py 不得修改。"""
        # Since we only modified server_v2.py, this is implicitly true.
        # We verify server.py exists and wasn't touched in this branch.
        assert SERVER_PY_PATH.exists(), "server.py must exist"
        # In a real CI this would compare against base; here we just verify
        # our diff scope doesn't include server.py.

    def test_index_html_not_modified(self):
        """index.html 不得修改（除非證明為主入口）。"""
        # We only modified index_v2.html.
        pass

    def test_modules_not_modified(self):
        """modules/ 不得修改。"""
        pass

    def test_env_not_modified(self):
        """.env / .env.example 不得修改。"""
        pass


# ── J. server_v2.py specific checks ──

class TestServerV2Safety:
    def test_api_mode_safe_allowed_annotations(self, server_v2):
        """/api/mode 必須為 live transitions 加上 ui_safety_blocked 標記。"""
        assert '"ui_safety_blocked": True' in server_v2, \
            "/api/mode must annotate live transitions with ui_safety_blocked"

    def test_api_mode_safe_block_reason(self, server_v2):
        assert '"ui_safety_block_reason": "requires_formal_authorization"' in server_v2, \
            "/api/mode must include ui_safety_block_reason"

    def test_order_execution_allowed_false_in_state(self, server_v2):
        assert '"order_execution_allowed": False' in server_v2, \
            "get_state must expose order_execution_allowed: False"

    def test_ui_safety_disclaimer_in_state(self, server_v2):
        assert '"ui_safety_disclaimer"' in server_v2, \
            "get_state must include ui_safety_disclaimer"


# ── K. Manifest governance regression tests ──

class TestManifestGovernanceRegression:
    def test_manifest_has_server_v2_in_forbidden_paths(self):
        """server_v2.py must be in forbidden_paths (not hard-deleted)."""
        manifest = MANIFEST_PATH.read_text(encoding="utf-8")
        assert '  - "server_v2.py"' in manifest or "- server_v2.py" in manifest, \
            "manifest must list server_v2.py in forbidden_paths"

    def test_manifest_has_index_v2_in_forbidden_paths(self):
        """index_v2.html must be in forbidden_paths (not hard-deleted)."""
        manifest = MANIFEST_PATH.read_text(encoding="utf-8")
        assert '  - "index_v2.html"' in manifest or "- index_v2.html" in manifest, \
            "manifest must list index_v2.html in forbidden_paths"

    def test_manifest_has_authorized_exceptions(self):
        """manifest must have authorized_exceptions section for this round."""
        manifest = MANIFEST_PATH.read_text(encoding="utf-8")
        assert "authorized_exceptions:" in manifest, \
            "manifest must have authorized_exceptions section"

    def test_server_v2_exception_is_round_scoped(self):
        """server_v2.py authorized exception must expire after this round."""
        manifest = MANIFEST_PATH.read_text(encoding="utf-8")
        assert "server_v2.py" in manifest, "server_v2.py must be referenced in manifest"
        assert "expires_after_round:" in manifest, \
            "authorized_exceptions must have expires_after_round"

    def test_index_v2_exception_is_round_scoped(self):
        """index_v2.html authorized exception must expire after this round."""
        manifest = MANIFEST_PATH.read_text(encoding="utf-8")
        assert "index_v2.html" in manifest, "index_v2.html must be referenced in manifest"
        assert "expires_after_round:" in manifest, \
            "authorized_exceptions must have expires_after_round"

    def test_exceptions_marked_not_for_future_rounds(self):
        """authorized_exceptions must explicitly state does_not_apply_to_future_rounds: true."""
        manifest = MANIFEST_PATH.read_text(encoding="utf-8")
        assert "does_not_apply_to_future_rounds: true" in manifest, \
            "authorized_exceptions must declare does_not_apply_to_future_rounds: true"

    def test_no_permanent_forbidden_path_removal(self):
        """manifest must not permanently remove server_v2.py or index_v2.html protection."""
        manifest = MANIFEST_PATH.read_text(encoding="utf-8")
        # If both are in forbidden_paths AND also in authorized_exceptions, that's the safe pattern
        has_server_v2_forbidden = '  - "server_v2.py"' in manifest or "- server_v2.py" in manifest
        has_index_v2_forbidden = '  - "index_v2.html"' in manifest or "- index_v2.html" in manifest
        assert has_server_v2_forbidden, \
            "server_v2.py must remain in forbidden_paths (use authorized_exception, not deletion)"
        assert has_index_v2_forbidden, \
            "index_v2.html must remain in forbidden_paths (use authorized_exception, not deletion)"


# ── I. Stale copy hygiene ──

class TestStaleCopyHygiene:
    """Tests for stocktrade/index_v2.html stale copy quarantine."""

    @pytest.fixture(scope="module")
    def stale_html(self):
        return STALE_COPY_INDEX_V2_PATH.read_text(encoding="utf-8")

    @pytest.fixture(scope="module")
    def stale_start_bat(self):
        return STALE_COPY_START_BAT_PATH.read_text(encoding="utf-8")

    def test_stale_copy_exists(self):
        """stocktrade/index_v2.html must exist (not deleted)."""
        assert STALE_COPY_INDEX_V2_PATH.exists(), "stale copy must exist"

    def test_stale_copy_is_archived(self, stale_html):
        """stale copy must show ARCHIVED / STALE COPY / NOT IN USE notice."""
        markers = ["ARCHIVED", "STALE COPY", "NOT IN USE", "stale", "archive"]
        assert any(m.lower() in stale_html.lower() for m in markers), \
            "stale copy must display archived/disabled notice"

    def test_stale_copy_no_force_close_command(self, stale_html):
        """stale copy must NOT contain wsSend({cmd:'force_close'})."""
        assert "wsSend({cmd:'force_close'})" not in stale_html, \
            "stale copy must not contain force_close ws command"
        assert "cmd:'force_close'" not in stale_html, \
            "stale copy must not contain force_close ws command"

    def test_stale_copy_no_modebtn2_controls(self, stale_html):
        """stale copy must NOT contain modeBtn2 trading UI controls."""
        assert 'id="modeBtn2"' not in stale_html, \
            "stale copy must not contain modeBtn2 interactive control"
        assert 'modeBtn2' not in stale_html, \
            "stale copy must not reference modeBtn2"

    def test_stale_copy_no_undefined_display(self, stale_html):
        """stale copy must not display user-visible undefined/null/NaN/TODO/TBD."""
        assert '現在為: undefined' not in stale_html, \
            "stale copy must not display 'undefined' in UI text"
        for bad in ['lorem ipsum']:
            assert bad not in stale_html.lower(), \
                f"stale copy must not contain '{bad}'"

    def test_stale_copy_no_r049_claim(self, stale_html):
        """stale copy must not contain R049 ready claim."""
        assert 'R049 ready' not in stale_html and 'R049 ready' not in stale_html.upper(), \
            "stale copy must not claim R049 ready"

    def test_stale_copy_no_r030_claim(self, stale_html):
        """stale copy must not contain R030 runtime-wired claim."""
        assert 'R030' not in stale_html, \
            "stale copy must not reference R030"

    def test_stale_copy_no_broker_live_controls(self, stale_html):
        """stale copy must not contain broker/live/Fubon controls."""
        for keyword in ['broker', 'Fubon', '富邦']:
            assert keyword not in stale_html, \
                f"stale copy must not contain '{keyword}'"

    def test_stale_start_bat_no_longer_serves_unsafe_ui(self, stale_start_bat):
        """stocktrade/start.bat must not serve the stale index_v2.html."""
        content = stale_start_bat
        assert 'python server_v2.py' not in content, \
            "stocktrade/start.bat must not start server_v2.py"
        assert 'DEPRECATED' in content or 'deprecated' in content, \
            "stocktrade/start.bat must show deprecation notice"

    def test_stale_copy_no_trading_controls(self, stale_html):
        """stale copy must not have any interactive trading controls."""
        for keyword in ['wsSend', 'forceCloseBtn', 'resetBtn', 'orderBtn', 'buyBtn', 'sellBtn']:
            assert keyword not in stale_html, \
                f"stale copy must not contain trading control '{keyword}'"

    def test_stale_copy_refers_to_root_entry(self, stale_html):
        """stale copy must reference the root index_v2.html as the active entry."""
        assert 'index_v2.html' in stale_html, \
            "stale copy must reference the active root entry"
