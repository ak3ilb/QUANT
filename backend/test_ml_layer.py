import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from ai.nlp.impact_scorer import score_headline_impact
from ml.data.readiness import assess_readiness, min_rows_for


class ImpactScorerTests(unittest.TestCase):
    def test_bullish_headline_positive_delta(self):
        impact = score_headline_impact(
            "test-1", 0.4, "bullish", ["BTCUSD"],
            {"session_quality": 1.0, "event_risk": 0.1, "trade_allowed": True, "data_quality": "ok"},
        )
        self.assertEqual(impact["impact_direction"], "bullish")
        self.assertGreater(impact["prob_bull_delta"], 0)
        self.assertEqual(impact["trade_gate"], "allow")

    def test_high_event_risk_warns(self):
        impact = score_headline_impact(
            "test-2", 0.3, "bullish", ["XAUUSD"],
            {"session_quality": 0.8, "event_risk": 0.8, "in_pre_event_window": True, "trade_allowed": True},
        )
        self.assertEqual(impact["trade_gate"], "warn")


class ReadinessTests(unittest.TestCase):
    def test_btc_1d_lower_threshold(self):
        self.assertEqual(min_rows_for("BTCUSD", "1d"), 300)

    def test_assess_returns_all_pairs(self):
        rows = assess_readiness()
        self.assertEqual(len(rows), 14)


class MlLayerTests(unittest.TestCase):
    def test_registry_list_empty_ok(self):
        from ml.models.registry import list_models
        self.assertIsInstance(list_models(), list)


if __name__ == "__main__":
    unittest.main()
