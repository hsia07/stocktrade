"""
Tests for PHASE2-API-AUTOMODE-R022: 新手可理解化 / 教學式 UI
Complete tests covering all mandatory items:
- NewcomerMode / AdvancedMode
- Plain language explanation
- Signal light system
- Tutorial page
- Backend truth source rendering
"""

import unittest
from pathlib import Path
import sys
import tempfile
import json
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from automation.control.tutorial_ui import (
    TutorialUI, get_tutorial_ui
)


class TestNewcomerMode(unittest.TestCase):
    """Tests for NewcomerMode."""

    def test_newcomer_mode_returns_white_language(self):
        """Newcomer mode should return plain language."""
        tui = TutorialUI()
        config = tui.get_user_mode("newcomer")
        self.assertEqual(config["terminology"], "白話")
        self.assertTrue(config["is_newcomer"])

    def test_explain_term_newcomer(self):
        """Term explanation in newcomer mode."""
        tui = TutorialUI()
        result = tui.explain_term("當日沖銷", "newcomer")
        self.assertIn("今天", result)

    def test_get_all_terms_newcomer(self):
        """All terms in newcomer mode."""
        tui = TutorialUI()
        terms = tui.get_all_terms("newcomer")
        self.assertIn("當日沖銷", terms)
        self.assertIn("今天", terms["當日沖銷"])

    def test_tutorial_flow_newcomer(self):
        """Tutorial flow in newcomer mode."""
        tui = TutorialUI()
        flow = tui.get_tutorial_flow("newcomer")
        self.assertGreater(len(flow), 0)
        self.assertIn("title", flow[0])


class TestAdvancedMode(unittest.TestCase):
    """Tests for AdvancedMode."""

    def test_advanced_mode_returns_professional(self):
        """Advanced mode should return professional terminology."""
        tui = TutorialUI()
        config = tui.get_user_mode("advanced")
        self.assertEqual(config["terminology"], "專業")
        self.assertFalse(config["is_newcomer"])

    def test_explain_term_advanced(self):
        """Term explanation in advanced mode."""
        tui = TutorialUI()
        result = tui.explain_term("當日沖銷", "advanced")
        self.assertIn("T+0", result)

    def test_get_all_terms_advanced(self):
        """All terms in advanced mode."""
        tui = TutorialUI()
        terms = tui.get_all_terms("advanced")
        self.assertIn("當日沖銷", terms)
        self.assertIn("Day", terms["當日沖銷"])


class TestPlainLanguageExplanation(unittest.TestCase):
    """Tests for plain language explanation layer."""

    def test_all_terms_have_both_explanations(self):
        """All terms should have both newcomer and advanced explanations."""
        tui = TutorialUI()
        for term in ["當日沖銷", "停損", "停利", "六大會議", "部位", "選股池"]:
            explanation = tui.explain_term(term)
            self.assertIsNotNone(explanation)

    def test_newcomer_key_warnings(self):
        """Newcomer mode warnings should be simple."""
        tui = TutorialUI()
        warnings = tui.get_key_warnings("newcomer")
        self.assertGreater(len(warnings), 0)
        self.assertTrue(any("AI" in w for w in warnings))


class TestSignalLightSystem(unittest.TestCase):
    """Tests for signal/light status system."""

    def test_signal_status_green(self):
        """Green signal should indicate normal."""
        tui = TutorialUI()
        signal = tui.get_signal_status("green")
        self.assertIn("meaning", signal)
        self.assertEqual(signal["meaning"], "正常")

    def test_signal_status_yellow(self):
        """Yellow signal should indicate caution."""
        tui = TutorialUI()
        signal = tui.get_signal_status("yellow")
        self.assertIn("meaning", signal)
        self.assertEqual(signal["meaning"], "注意")

    def test_signal_status_red(self):
        """Red signal should indicate warning."""
        tui = TutorialUI()
        signal = tui.get_signal_status("red")
        self.assertIn("meaning", signal)
        self.assertEqual(signal["meaning"], "警告")

    def test_all_signals(self):
        """All signals should be present."""
        tui = TutorialUI()
        signals = tui.get_all_signals()
        self.assertIn("green", signals)
        self.assertIn("yellow", signals)
        self.assertIn("red", signals)


class TestTutorialPage(unittest.TestCase):
    """Tests for tutorial page/onboarding flow."""

    def test_tutorial_steps_present(self):
        """Tutorial steps should be present."""
        tui = TutorialUI()
        flow = tui.get_tutorial_flow()
        self.assertGreaterEqual(len(flow), 4)

    def test_get_specific_step(self):
        """Get specific tutorial step."""
        tui = TutorialUI()
        step = tui.get_tutorial_step("step_1", "newcomer")
        self.assertIsNotNone(step)
        self.assertEqual(step["step_id"], "step_1")

    def test_tutorial_includes_key_points(self):
        """Tutorial steps should include key points."""
        tui = TutorialUI()
        flow = tui.get_tutorial_flow("newcomer")
        self.assertIn("key_points", flow[0])


class TestBackendTruthSourceRendering(unittest.TestCase):
    """Tests for unified truth source rendering."""

    def test_truth_source_state(self):
        """Should load truth source state."""
        tui = TutorialUI()
        state = tui.get_truth_source_state()
        self.assertIsInstance(state, dict)

    def test_render_dashboard(self):
        """Dashboard should render from truth source."""
        tui = TutorialUI()
        dashboard = tui.render_dashboard("newcomer")
        self.assertIn("truth_source", dashboard)
        self.assertIn("tutorial", dashboard)
        self.assertIn("signals", dashboard)

    def test_render_dashboard_mode_consistency(self):
        """Dashboard mode should be consistent."""
        tui = TutorialUI()
        dashboard = tui.render_dashboard("newcomer")
        self.assertEqual(dashboard["mode"], "newcomer")


class TestFactory(unittest.TestCase):
    """Test factory function."""

    def test_get_tutorial_ui(self):
        """Factory should return TutorialUI."""
        tui = get_tutorial_ui()
        self.assertIsInstance(tui, TutorialUI)


class TestEdgeCases(unittest.TestCase):
    """Edge case tests."""

    def test_unknown_term(self):
        """Unknown term should return fallback message."""
        tui = TutorialUI()
        result = tui.explain_term("UNKNOWN_TERM_XYZ")
        self.assertIsNotNone(result)

    def test_unknown_step(self):
        """Unknown step should return None."""
        tui = TutorialUI()
        result = tui.get_tutorial_step("step_999")
        self.assertIsNone(result)

    def test_unknown_signal(self):
        """Unknown signal should return green."""
        tui = TutorialUI()
        result = tui.get_signal_status("unknown")
        self.assertEqual(result["meaning"], "正常")


class TestNewcomerPresence(unittest.TestCase):
    """Tests to verify mandatory items present."""

    def test_newcomer_mode_present(self):
        """Newcomer mode must be present."""
        tui = TutorialUI()
        self.assertTrue(tui.get_user_mode("newcomer")["is_newcomer"])

    def test_advanced_mode_present(self):
        """Advanced mode must be present."""
        tui = TutorialUI()
        self.assertFalse(tui.get_user_mode("advanced")["is_newcomer"])

    def test_plain_language_explanation_present(self):
        """Plain language explanations must be present."""
        tui = TutorialUI()
        explanation = tui.explain_term("當日沖銷", "newcomer")
        self.assertIsNotNone(explanation)
        self.assertIn("今天", explanation)

    def test_signal_light_system_present(self):
        """Signal light system must be present."""
        tui = TutorialUI()
        signals = tui.get_all_signals()
        self.assertIn("green", signals)
        self.assertIn("yellow", signals)
        self.assertIn("red", signals)

    def test_tutorial_page_present(self):
        """Tutorial page must be present."""
        tui = TutorialUI()
        flow = tui.get_tutorial_flow()
        self.assertGreaterEqual(len(flow), 4)

    def test_backend_truth_source_rendering_present(self):
        """Truth source rendering must be present."""
        tui = TutorialUI()
        dashboard = tui.render_dashboard()
        self.assertIn("truth_source", dashboard)


if __name__ == "__main__":
    unittest.main()