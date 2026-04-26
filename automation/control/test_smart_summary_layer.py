import unittest
from automation.control.smart_summary_layer import SmartSummaryLayer, SummarySource, SummaryValidator


class TestSmartSummaryLayer(unittest.TestCase):
    def setUp(self):
        self.summary = SmartSummaryLayer()

    def test_generate_market_summary(self):
        data = {"symbol": "AAPL", "price": 150.0, "change": 2.5, "change_pct": 1.69, "volatility": 0.5}
        result = self.summary.generate_summary(data, "market")
        self.assertEqual(result["category"], "market")
        self.assertIn("summary", result)
        self.assertTrue(SummaryValidator.validate_summary_structure(result))

    def test_generate_system_summary(self):
        data = {"status": "healthy", "uptime": 24, "messages_processed": 1000}
        result = self.summary.generate_summary(data, "system")
        self.assertEqual(result["category"], "system")
        self.assertTrue(SummaryValidator.validate_summary_structure(result))

    def test_generate_risk_summary(self):
        data = {"level": "medium", "factors": ["volatility", "liquidity"]}
        result = self.summary.generate_summary(data, "risk")
        self.assertEqual(result["category"], "risk")
        self.assertTrue(SummaryValidator.validate_summary_structure(result))

    def test_generate_next_steps_summary(self):
        data = {"actions": ["action1", "action2"]}
        result = self.summary.generate_summary(data, "next_steps")
        self.assertEqual(result["category"], "next_steps")
        self.assertTrue(SummaryValidator.validate_summary_structure(result))

    def test_invalid_category(self):
        with self.assertRaises(ValueError):
            self.summary.generate_summary({}, "invalid_category")

    def test_get_categories(self):
        categories = self.summary.get_categories()
        self.assertEqual(len(categories), 4)
        self.assertIn("market", categories)
        self.assertIn("system", categories)
        self.assertIn("risk", categories)
        self.assertIn("next_steps", categories)

    def test_batch_generate(self):
        data = {
            "market": {"symbol": "AAPL", "price": 150, "change": 1, "change_pct": 0.67, "volatility": 0.5},
            "system": {"status": "healthy", "uptime": 10, "messages_processed": 500}
        }
        results = self.summary.batch_generate(data)
        self.assertIn("market", results)
        self.assertIn("system", results)

    def test_source_info(self):
        market_source = self.summary.get_source_info("market")
        self.assertEqual(market_source, "market_data_feed")


class TestSummarySource(unittest.TestCase):
    def test_get_source(self):
        source = SummarySource()
        self.assertEqual(source.get_source("market"), "market_data_feed")
        self.assertEqual(source.get_source("system"), "system_status")
        self.assertEqual(source.get_source("risk"), "risk_assessment_engine")
        self.assertEqual(source.get_source("next_steps"), "workflow_coordinator")

    def test_invalid_source(self):
        source = SummarySource()
        self.assertEqual(source.get_source("invalid"), "unknown")


class TestSummaryValidator(unittest.TestCase):
    def test_validate_summary_structure_valid(self):
        summary = {"summary": "test", "category": "market", "source": "market_data_feed", "metadata": {}, "generated_at": "2026"}
        self.assertTrue(SummaryValidator.validate_summary_structure(summary))

    def test_validate_summary_structure_invalid(self):
        summary = {"summary": "test"}
        self.assertFalse(SummaryValidator.validate_summary_structure(summary))

    def test_validate_category(self):
        summary = {"category": "market"}
        self.assertTrue(SummaryValidator.validate_category(summary, "market"))
        self.assertFalse(SummaryValidator.validate_category(summary, "system"))

    def test_validate_source(self):
        summary = {"source": "market_data_feed"}
        self.assertTrue(SummaryValidator.validate_source(summary, "market_data_feed"))
        self.assertFalse(SummaryValidator.validate_source(summary, "unknown"))


if __name__ == "__main__":
    unittest.main()