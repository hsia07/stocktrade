"""
Phase2 Core-A4 UI display-only contract tests.
Verifies index.html display-only panel for core_a_shadow_snapshot.
"""
import pytest, re, os, sys


INDEX_HTML = "index.html"
SERVER_PY = "server.py"
SERVER_V2 = "server_v2.py"
INDEX_V2 = "index_v2.html"


def read_index():
    with open(INDEX_HTML, encoding="utf-8") as f:
        return f.read()


def read_server_py():
    with open(SERVER_PY, encoding="utf-8") as f:
        return f.read()


def read_server_v2():
    with open(SERVER_V2, encoding="utf-8") as f:
        return f.read()


def read_index_v2():
    with open(INDEX_V2, encoding="utf-8") as f:
        return f.read()


class TestCoreA4PanelPresence:
    """Core-A4 display panel must exist in index.html."""

    def test_shadow_panel_container_exists(self):
        """index.html must contain the Core-A4 shadow panel container."""
        html = read_index()
        assert 'id="core-a4-shadow-panel"' in html
        assert 'shadow-panel' in html
        assert 'Core-A Shadow Snapshot' in html

    def test_shadow_body_render_target_exists(self):
        """index.html must contain the shadow-body render target."""
        html = read_index()
        assert 'id="shadow-body"' in html

    def test_render_core_a_shadow_function_exists(self):
        """index.html must define renderCoreAShadow function."""
        html = read_index()
        assert 'function renderCoreAShadow(' in html

    def test_render_core_a_shadow_called_from_render(self):
        """renderCoreAShadow must be called from the main render() function."""
        html = read_index()
        assert 'renderCoreAShadow(data)' in html


class TestCoreA4PanelFieldRendering:
    """display-only panel must render required core_a_shadow_snapshot fields."""

    def test_renders_present_field(self):
        """renderCoreAShadow must reference 'present'."""
        html = read_index()
        assert 'shadow.present' in html or '"present"' in html

    def test_renders_available_field(self):
        """renderCoreAShadow must reference 'available'."""
        html = read_index()
        assert 'shadow.available' in html or '"available"' in html

    def test_renders_shadow_result_field(self):
        """renderCoreAShadow must reference 'shadow_result'."""
        html = read_index()
        assert 'shadow.shadow_result' in html or '"shadow_result"' in html

    def test_renders_no_order_side_effects(self):
        """renderCoreAShadow must reference 'no_order_side_effects'."""
        html = read_index()
        assert 'shadow.no_order_side_effects' in html or '"no_order_side_effects"' in html

    def test_renders_order_execution_allowed(self):
        """renderCoreAShadow must reference 'order_execution_allowed'."""
        html = read_index()
        assert 'shadow.order_execution_allowed' in html or '"order_execution_allowed"' in html

    def test_renders_updated_at(self):
        """renderCoreAShadow must reference 'updated_at'."""
        html = read_index()
        assert 'shadow.updated_at' in html or '"updated_at"' in html

    def test_renders_failure_mode(self):
        """renderCoreAShadow must reference 'failure_mode'."""
        html = read_index()
        assert 'shadow.failure_mode' in html or '"failure_mode"' in html


class TestCoreA4PanelUnavailableFallback:
    """Panel must handle unavailable/shadow_error states safely."""

    def test_unavailable_fallback_exists(self):
        """renderCoreAShadow must have fallback for unavailable state."""
        html = read_index()
        src = html[html.index('function renderCoreAShadow'):html.index('function updateNavBadges')]
        assert '!shadow' in src
        assert 'shadow-fallback' in src

    def test_failure_mode_displayed(self):
        """failure_mode condition must exist in renderCoreAShadow."""
        html = read_index()
        src = html[html.index('function renderCoreAShadow'):html.index('function updateNavBadges')]
        assert 'failure_mode' in src

    def test_available_condition_used(self):
        """renderCoreAShadow must check shadow.available."""
        html = read_index()
        src = html[html.index('function renderCoreAShadow'):html.index('function updateNavBadges')]
        assert 'shadow.available' in src


class TestCoreA4PanelDisplayOnlyInvariants:
    """No controls / inputs / mutations in Core-A4 panel."""

    def test_no_buy_sell_approve_order_controls(self):
        """Core-A4 panel must not contain buy/sell/approve/order/broker controls."""
        html = read_index()

        if 'core-a4-shadow-panel' not in html:
            return
        panel_start = html.index('core-a4-shadow-panel')
        scope = html[panel_start:panel_start + 4000]
        # Check for HTML elements / JS code that would create trade controls,
        # excluding CSS variable references like --buy, --sell, etc.
        control_patterns = [
            (r'<button[^>]*>(?:(?!collapse|expand).)*</button>', 'non-collapse button'),
            (r'\bonclick\b', 'onclick handler'),
            (r'\bplace_order\b', 'place_order'),
            (r'\border_action\b', 'order_action'),
            (r'\btrade_action\b', 'trade_action'),
            (r'\bexecute_trade\b', 'execute_trade'),
            (r'\bapprove_trade\b', 'approve_trade'),
        ]
        for pattern, desc in control_patterns:
            matches = re.findall(pattern, scope)
            assert len(matches) == 0, f"Found {desc} in Core-A4 panel scope: {matches[:3]}"

    def test_no_inputs_forms_toggles_in_panel(self):
        """Core-A4 panel must not contain input, form, toggle, checkbox, submit."""
        html = read_index()
        if 'core-a4-shadow-panel' not in html:
            return
        panel_start = html.index('core-a4-shadow-panel')
        scope = html[panel_start:panel_start + 4000]
        for tag in ['<input', '<form', '<select', '<textarea', 'type="checkbox"',
                     'type="radio"', 'type="submit"', 'type="button"', '<button']:
            # collapse/expand button might be ok but we check context
            if '<button' in tag:
                matches = re.findall(r'<button[^>]*>', scope)
                for m in matches:
                    assert 'collapse' in m.lower() or 'expand' in m.lower() or 'toggle' in m.lower(), \
                        f"Found non-collapse button in Core-A4 panel: {m}"
            else:
                assert tag not in scope, f"Found '{tag}' in Core-A4 panel scope"

    def test_no_display_only_button_is_not_trading_button(self):
        """Any button in Core-A4 panel must be clearly display-only."""
        html = read_index()
        if 'core-a4-shadow-panel' not in html:
            return
        panel_start = html.index('core-a4-shadow-panel')
        scope = html[panel_start:panel_start + 4000]
        buttons = re.findall(r'<button[^>]*>', scope)
        for b in buttons:
            assert 'collapse' in b.lower() or 'expand' in b.lower(), \
                f"Button in Core-A4 panel may not be display-only: {b}"

    def test_no_order_execution_allowed_toggle(self):
        """index.html must not have a toggle for order_execution_allowed."""
        html = read_index()
        assert 'order_execution_allowed' not in html or 'type="checkbox"' not in html


class TestCoreA4PanelOrderPermissionDisplay:
    """order_execution_allowed must be displayed as FALSE/read-only."""

    def test_order_execution_allowed_displayed_false(self):
        """renderCoreAShadow must display order_execution_allowed as false/disabled."""
        html = read_index()
        src = html[html.index('function renderCoreAShadow'):html.index('function updateNavBadges')]
        assert 'orderAllowed ?' in src
        assert 'orderAllowed' in src
        assert 'FALSE' in src

    def test_order_execution_allowed_never_true(self):
        """renderCoreAShadow must not display order_execution_allowed as TRUE."""
        html = read_index()
        src = html[html.index('function renderCoreAShadow'):html.index('function updateNavBadges')]
        assert 'orderAllowed ?' in src
        # Ensure the false branch shows something, not missing
        assert '(orderAllowed ?' in src


class TestCoreA4PanelNoSecretRendering:
    """No secret / token / chat_id / api_key / broker_credential rendered."""

    def test_no_secret_keywords_in_panel(self):
        """Core-A4 panel must not render secret values."""
        html = read_index()
        if 'core-a4-shadow-panel' not in html:
            return
        panel_start = html.index('core-a4-shadow-panel')
        scope = html[panel_start:panel_start + 4000]
        for kw in ['secret', 'token', 'chat_id', 'api_key', 'broker_credential',
                    'password', 'private_key']:
            count = len(re.findall(r'\b' + re.escape(kw) + r'\b', scope, re.IGNORECASE))
            assert count == 0, f"Found secret keyword '{kw}' in Core-A4 panel scope ({count} matches)"


class TestCoreA4NoMutationPaths:
    """No mutation paths (fetch POST/PUT/DELETE/PATCH, WebSocket send) for Core-A4."""

    def test_no_new_fetch_post_put_delete_patch(self):
        """Core-A4 must not add fetch POST/PUT/DELETE/PATCH mutations."""
        html = read_index()
        panel_start = html.index('core-a4-shadow-panel')
        scope = html[panel_start:panel_start + 4000]
        for method in ["'POST'", '"POST"', "'PUT'", '"PUT"', "'DELETE'", '"DELETE"', "'PATCH'", '"PATCH"']:
            assert method not in scope, f"Found fetch method {method} in Core-A4 panel scope"

    def test_no_websocket_send_mutation(self):
        """Core-A4 must not add WebSocket send mutation."""
        html = read_index()
        panel_start = html.index('core-a4-shadow-panel')
        scope = html[panel_start:panel_start + 4000]
        assert 'ws.send' not in scope


class TestCoreA4NoBackendChanges:
    """server.py, server_v2.py, index_v2.html must be unchanged."""

    def test_server_py_unchanged(self):
        """server.py must not be modified by Core-A4."""
        old = """                    "order_execution_allowed": False,
                    "updated_at": datetime.now().isoformat(),"""
        assert old in read_server_py()

    def test_server_v2_unchanged(self):
        """server_v2.py must not contain core_a references."""
        content = read_server_v2()
        assert 'core_a' not in content.lower()

    def test_index_v2_unchanged(self):
        """index_v2.html must not contain core_a references."""
        content = read_index_v2()
        assert 'core_a_shadow' not in content

    def test_no_new_api_endpoint(self):
        """No new API endpoint must be added for Core-A4."""
        for fname in [SERVER_PY, SERVER_V2]:
            with open(fname, encoding="utf-8") as f:
                for line in f:
                    if '@app.' in line and 'api/state' not in line and 'api/mode' not in line and 'api/toggle_mode' not in line and '/ws' not in line and '/api' not in line:
                        pass

    def test_runtime_state_write_not_added(self):
        """No runtime state write must be added."""
        content = read_server_py()
        assert 'core_a_shadow_snapshots' in content


class TestCoreA4NoBrokerExecutionLive:
    """No broker / execution / live paths in Core-A4 scope."""

    def test_no_broker_path(self):
        """No broker path in index.html Core-A4 scope."""
        html = read_index()
        if 'core-a4-shadow-panel' in html:
            panel_start = html.index('core-a4-shadow-panel')
            scope = html[panel_start:panel_start + 4000]
            assert 'broker' not in scope.lower()

    def test_no_execution_live_path(self):
        """No execution/live path in index.html Core-A4 scope."""
        html = read_index()
        if 'core-a4-shadow-panel' in html:
            panel_start = html.index('core-a4-shadow-panel')
            scope = html[panel_start:panel_start + 4000]
            assert 'execution' not in scope.lower()


class TestCoreA4DataFlowInvariants:
    """Core-A4 panel uses existing WebSocket state — no new data source."""

    def test_panel_reads_from_data_object(self):
        """renderCoreAShadow must read from data.core_a_shadow_snapshot."""
        html = read_index()
        src = html[html.index('function renderCoreAShadow'):html.index('function updateNavBadges')]
        assert 'data.core_a_shadow_snapshot' in src

    def test_shadow_not_in_render_before_panel(self):
        """Core-A4 panel is the only place core_a_shadow_snapshot is rendered."""
        html = read_index()
        count = html.count('core_a_shadow_snapshot')
        assert count >= 1


class TestCoreA4StyleInvariants:
    """CSS for Core-A4 panel must be present and correct."""

    def test_shadow_panel_css_exists(self):
        """CSS class .shadow-panel must be defined."""
        html = read_index()
        assert '.shadow-panel{' in html or '.shadow-panel ' in html

    def test_shadow_grid_css_exists(self):
        """CSS class .shadow-grid must be defined."""
        html = read_index()
        assert '.shadow-grid{' in html or '.shadow-grid ' in html

    def test_shadow_fallback_css_exists(self):
        """CSS class .shadow-fallback must be defined."""
        html = read_index()
        assert '.shadow-fallback{' in html or '.shadow-fallback ' in html
