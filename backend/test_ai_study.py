import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from ai.study.engine import StudyEngine
from ai.study.store import init_study_tables, recent_events


class StudyEngineTests(unittest.TestCase):
    def test_dashboard_shape(self):
        engine = StudyEngine()
        dash = engine.get_dashboard("BTCUSD", "1h")
        self.assertEqual(dash["status"], "ok")
        self.assertIn("layers", dash)
        self.assertGreater(len(dash["layers"]), 5)
        self.assertIn("live_learning", dash)
        first_algo = dash["layers"][0].get("evaluated_algorithms", [])
        if first_algo:
            self.assertIn("score_kind", first_algo[0])

    def test_record_event(self):
        init_study_tables()
        engine = StudyEngine()
        engine.record_trade_closed({
            "symbol": "BTCUSD",
            "strategy": "medallion",
            "won": True,
            "pnl_pct": 0.01,
            "trade_id": "test-trade",
        })
        events = recent_events(limit=5, symbol="BTCUSD")
        self.assertTrue(any(e["event_type"] == "trade_closed" for e in events))


if __name__ == "__main__":
    unittest.main()
