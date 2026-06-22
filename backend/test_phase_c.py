import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from algorithms.drift_detector import PageHinkleyDetector
from algorithms.thompson_ensemble import thompson_select_strategy, update_bandit, _default_bandit_state
from algorithms.online_logistic import OnlineLogisticModel, blend_probabilities, regime_to_features
from learning_engine import LearningEngine


class PhaseCTests(unittest.TestCase):
    def setUp(self):
        self.test_db = os.path.join(os.path.dirname(__file__), "test_learning.duckdb")
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_thompson_prefers_historically_winning_strategy(self):
        bandit = _default_bandit_state()
        bandit["nova"]["alpha"] = 20.0
        bandit["piggy"]["beta"] = 20.0

        signals = {
            "nova": {"action": "BUY", "confidence": 0.8},
            "piggy": {"action": "BUY", "confidence": 0.8},
            "limroy": {"action": "HOLD", "confidence": 0.5},
            "dejavu": {"action": "HOLD", "confidence": 0.5},
            "medallion": {"action": "HOLD", "confidence": 0.5},
        }

        picks = [thompson_select_strategy(signals, bandit, rng=__import__("numpy").random.default_rng(42))[0] for _ in range(30)]
        self.assertGreater(picks.count("nova"), picks.count("piggy"))

    def test_drift_reduces_size_multiplier(self):
        det = PageHinkleyDetector(delta=0.005, threshold=3.0)
        for _ in range(8):
            det.update(1.0)
        for _ in range(20):
            det.update(0.0)
        self.assertLess(det.size_multiplier(), 1.0)

    def test_online_model_updates_and_predicts(self):
        model = OnlineLogisticModel()
        features = regime_to_features(
            {
                "current_price": 100.0,
                "volume_imbalance": 0.2,
                "buy_pressure": 0.7,
                "changepoint_prob": 0.6,
                "kalman_z": -1.0,
            }
        )
        for _ in range(10):
            model.partial_update(features, 1)
        prob = model.predict_prob(features)
        self.assertIsNotNone(prob)
        self.assertGreater(prob, 0.5)

    def test_blend_probabilities(self):
        blended = blend_probabilities(0.7, 0.9, True)
        self.assertGreater(blended, 0.7)
        self.assertLess(blended, 0.9)

    def test_learning_engine_persists_bandit(self):
        engine = LearningEngine(db_path=self.test_db)
        engine.on_trade_closed(
            {
                "trade_id": "T1",
                "strategy": "nova",
                "pnl_usd": 1.5,
                "pnl_pct": 0.02,
                "direction": "BUY",
                "won": True,
                "entry_features": regime_to_features({"current_price": 100.0}),
            }
        )

        reloaded = LearningEngine(db_path=self.test_db)
        self.assertGreater(reloaded.bandit_state["nova"]["alpha"], 1.0)
        stats = reloaded.get_stats()
        self.assertIn("bandit", stats)
        self.assertIn("drift", stats)


if __name__ == "__main__":
    unittest.main()
