"""
Tests for PHASE2-API-AUTOMODE-R023: 首頁與新手操作體驗強化
"""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from automation.control.homepage_enhancement import (
    HomepageEnhancement, HomepageContent, NewcomerExperience, get_homepage_enhancement
)


class TestHomepageContent(unittest.TestCase):
    """Tests for HomepageContent."""

    def test_get_all_sections_newcomer(self):
        """Newcomer mode should return newcomer-friendly titles."""
        hc = HomepageContent("newcomer")
        sections = hc.get_all_sections()
        self.assertGreater(len(sections), 0)
        self.assertEqual(sections[0]["title"], "歡迎使用")

    def test_get_all_sections_advanced(self):
        """Advanced mode should return professional titles."""
        hc = HomepageContent("advanced")
        sections = hc.get_all_sections()
        self.assertGreater(len(sections), 0)
        self.assertEqual(sections[0]["title"], "歡迎使用當沖機器人")

    def test_get_section_by_id(self):
        """Get section by ID."""
        hc = HomepageContent("newcomer")
        section = hc.get_section("intro")
        self.assertIsNotNone(section)
        self.assertEqual(section["section_id"], "intro")


class TestNewcomerExperience(unittest.TestCase):
    """Tests for NewcomerExperience."""

    def test_get_all_guides(self):
        """Get all quick guides."""
        ne = NewcomerExperience()
        guides = ne.get_all_guides()
        self.assertGreater(len(guides), 0)

    def test_get_guide_by_id(self):
        """Get guide by ID."""
        ne = NewcomerExperience()
        guide = ne.get_guide("first_time")
        self.assertIsNotNone(guide)
        self.assertEqual(guide["guide_id"], "first_time")


class TestHomepageEnhancement(unittest.TestCase):
    """Tests for HomepageEnhancement."""

    def test_render_homepage_newcomer(self):
        """Render homepage in newcomer mode."""
        he = HomepageEnhancement(user_mode="newcomer")
        data = he.render_homepage()
        self.assertIn("sections", data)
        self.assertIn("guides", data)
        self.assertEqual(data["mode"], "newcomer")

    def test_render_homepage_advanced(self):
        """Render homepage in advanced mode."""
        he = HomepageEnhancement(user_mode="advanced")
        data = he.render_homepage()
        self.assertIn("sections", data)
        self.assertIn("guides", data)
        self.assertEqual(data["mode"], "advanced")

    def test_get_homepage_sections(self):
        """Get homepage sections."""
        he = HomepageEnhancement()
        sections = he.get_homepage_sections()
        self.assertGreater(len(sections), 0)

    def test_get_quick_guides(self):
        """Get quick guides."""
        he = HomepageEnhancement()
        guides = he.get_quick_guides()
        self.assertGreater(len(guides), 0)


class TestFactory(unittest.TestCase):
    """Test factory function."""

    def test_get_homepage_enhancement(self):
        """Factory should return HomepageEnhancement."""
        he = get_homepage_enhancement()
        self.assertIsInstance(he, HomepageEnhancement)


class TestR023MandatoryItems(unittest.TestCase):
    """Verify R023 mandatory items present."""

    def test_homepage_sections_present(self):
        """Homepage sections must be present."""
        he = HomepageEnhancement()
        sections = he.get_homepage_sections()
        self.assertGreaterEqual(len(sections), 4)

    def test_newcomer_experience_present(self):
        """Newcomer experience guides must be present."""
        he = HomepageEnhancement()
        guides = he.get_quick_guides()
        self.assertGreaterEqual(len(guides), 3)


if __name__ == "__main__":
    unittest.main()