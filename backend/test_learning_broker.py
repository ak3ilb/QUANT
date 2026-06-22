"""Tests for learning engine singleton and broker-aware close events."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))


class TestLearningSingleton(unittest.TestCase):
    def test_get_learning_engine_singleton(self):
        from learning_engine import get_learning_engine

        a = get_learning_engine()
        b = get_learning_engine()
        self.assertIs(a, b)

    def test_reload_if_stale(self):
        from learning_engine import get_learning_engine

        eng = get_learning_engine()
        eng.reload_if_stale()
        stats = eng.get_stats()
        self.assertIn("bandit", stats)


class TestLearningBroker(unittest.TestCase):
    def test_overlay_context_features(self):
        from learning_engine import LearningEngine

        eng = LearningEngine()
        entry = {"session_quality": 0.5, "sentiment_1h_norm": 0.0, "event_risk": 0.0}
        ctx = {
            "symbol": "BTCUSD",
            "timeline": {"session_quality": 0.95},
            "news": {"avg_sentiment": 0.4},
            "regime_features": {
                "session_quality": 0.95,
                "btc_sentiment_1h": 0.4,
                "event_risk": 0.1,
            },
        }
        merged = eng._overlay_context_features(entry, ctx)
        self.assertGreaterEqual(merged["session_quality"], 0.9)


if __name__ == "__main__":
    unittest.main()
