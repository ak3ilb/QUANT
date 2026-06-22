import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from algorithm_registry import ACADEMIC_REFERENCE, QUANT_MODEL, get_algorithm_registry
from algorithms.chern_simons import chern_simons_gauge
from algorithms.stochastic_diff_eq import geometric_brownian_motion_sde
from signal_engine import STRATEGIES, SignalEngine


def _signal_df(trend: str = "up") -> pd.DataFrame:
    close = np.linspace(100, 160, 80) if trend == "up" else np.linspace(160, 100, 80)
    return pd.DataFrame(
        {
            "close": close,
            "EMA_9": close + (2 if trend == "up" else -2),
            "EMA_21": close,
            "RSI_14": np.full_like(close, 55.0),
        }
    )


class AlgorithmAlignmentTests(unittest.TestCase):
    def test_registry_classifies_source_backed_algorithms(self):
        registry = get_algorithm_registry()
        by_id = {entry["id"]: entry for entry in registry}

        self.assertEqual(by_id["chern_simons_gauge"]["category"], ACADEMIC_REFERENCE)
        self.assertEqual(by_id["chern_simons_gauge"]["implementation_status"], "heuristic_analogy")
        self.assertIn("Chern", by_id["chern_simons_gauge"]["caveat"])
        self.assertEqual(by_id["geometric_brownian_motion_sde"]["category"], QUANT_MODEL)

    def test_gbm_seed_is_reproducible_and_finite(self):
        df = pd.DataFrame({"close": np.linspace(100.0, 120.0, 100)})

        first = geometric_brownian_motion_sde(df, simulations=250, forecast_bars=12, seed=7)
        second = geometric_brownian_motion_sde(df, simulations=250, forecast_bars=12, seed=7)

        self.assertEqual(first["model"], "geometric_brownian_motion")
        self.assertEqual(first["forecast_mean"], second["forecast_mean"])
        self.assertTrue(np.isfinite(first["forecast_upper"]))
        self.assertGreaterEqual(first["forecast_upper"], first["forecast_lower"])

    def test_gbm_rejects_non_positive_prices_without_nan_output(self):
        df = pd.DataFrame({"close": [0, -1, np.nan, np.inf]})

        result = geometric_brownian_motion_sde(df, simulations=10, forecast_bars=3, seed=1)

        self.assertEqual(result["forecast_mean"], 0.0)
        self.assertEqual(result["volatility"], 0.0)
        self.assertIn("Insufficient", result["note"])

    def test_signal_all_returns_every_strategy(self):
        engine = SignalEngine()
        regime = {"current_regime": "Sideways", "confidence": 0.5}

        signals = engine.get_all_signals(_signal_df("up"), regime)

        self.assertEqual(set(signals), set(STRATEGIES))
        self.assertTrue(all(signal["strategy"] in STRATEGIES for signal in signals.values()))

    def test_medallion_uses_curvature_value_for_direction(self):
        engine = SignalEngine()

        bullish = engine.get_signal(
            _signal_df("up"),
            "medallion",
            {
                "current_regime": "Sideways",
                "confidence": 0.5,
                "curvature_value": 10.0,
                "berlekamp_up": 1,
            },
        )
        bearish = engine.get_signal(
            _signal_df("down"),
            "medallion",
            {
                "current_regime": "Sideways",
                "confidence": 0.5,
                "curvature_value": -10.0,
                "berlekamp_up": 0,
            },
        )

        self.assertEqual(bullish["action"], "BUY")
        self.assertEqual(bearish["action"], "SELL")

    def test_chern_simons_output_is_matrix_ready(self):
        df = pd.DataFrame({"close": np.linspace(100.0, 105.0, 40)})

        result = chern_simons_gauge(df)

        self.assertIn("cs_5d", result)
        self.assertIn("curvature_value", result)
        self.assertIn("curvature_signal", result)
        self.assertEqual(result["model_status"], "heuristic_analogy")


if __name__ == "__main__":
    unittest.main()
