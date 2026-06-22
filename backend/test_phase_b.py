import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from algorithms.signed_volume import signed_volume_imbalance
from algorithms.bocpd import bocpd_break
from algorithms.kalman_fair_value import kalman_fair_value
from algorithms.cointegration import engle_granger_spread
from signal_engine import SignalEngine


def _ohlcv_df(n: int = 120, trend: float = 0.001) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    close = 100.0 + np.cumsum(rng.normal(trend, 0.5, n))
    open_ = close - rng.normal(0, 0.2, n)
    volume = rng.integers(500, 5000, n).astype(float)
    return pd.DataFrame({"open": open_, "close": close, "volume": volume})


class PhaseBTests(unittest.TestCase):
    def test_signed_volume_detects_buy_pressure(self):
        df = _ohlcv_df()
        df.loc[df.index[-20:], "close"] = df.loc[df.index[-20:], "open"] + 1.0
        result = signed_volume_imbalance(df, window=20)

        self.assertGreater(result["imbalance_ratio"], 0.0)
        self.assertGreater(result["buy_pressure"], 0.5)
        self.assertEqual(result["signal"], "BUY_PRESSURE")

    def test_bocpd_returns_bounded_probability(self):
        df = _ohlcv_df(200)
        # Inject volatility regime shift
        df.loc[df.index[150:], "close"] = df.loc[df.index[150:], "close"] * (
            1 + np.linspace(0, 0.3, 50)
        )

        result = bocpd_break(df)

        self.assertEqual(result["model"], "bocpd")
        self.assertGreaterEqual(result["changepoint_prob"], 0.0)
        self.assertLessEqual(result["changepoint_prob"], 1.0)
        self.assertIsInstance(result["structural_break"], bool)

    def test_kalman_fair_value_zscore(self):
        df = _ohlcv_df()
        df.loc[df.index[-5:], "close"] = df.loc[df.index[-5:], "close"] + 10.0

        result = kalman_fair_value(df)

        self.assertGreater(result["innovation_z"], 0.0)
        self.assertIn(result["signal"], {"OVERVALUED", "NEUTRAL", "UNDERVALUED"})

    def test_cointegration_spread_on_synthetic_pair(self):
        n = 150
        t = np.arange(n, dtype=float)
        x = 100 + 0.1 * t + np.random.default_rng(1).normal(0, 0.5, n)
        y = 2.0 * x + np.random.default_rng(2).normal(0, 0.5, n)
        df_x = pd.DataFrame({"time": pd.date_range("2024-01-01", periods=n, freq="h"), "close": x})
        df_y = pd.DataFrame({"time": pd.date_range("2024-01-01", periods=n, freq="h"), "close": y})

        result = engle_granger_spread(df_y, df_x)

        self.assertTrue(result["pair_ready"])
        self.assertIsNotNone(result["hedge_ratio"])
        self.assertIn("spread_zscore", result)

    def test_piggy_uses_kalman_undervalued(self):
        engine = SignalEngine()
        df = _ohlcv_df(80)
        regime = {
            "current_regime": "Sideways",
            "confidence": 0.5,
            "kalman_z": -2.5,
            "sde_forecast": float(df["close"].iloc[-1]),
            "kernel_p_value": 0.5,
        }
        signal = engine.get_signal(df, "piggy", regime)

        self.assertIn(signal["action"], {"BUY", "HOLD", "SELL"})
        self.assertGreater(signal["bayesian_prob_bull"], 0.5)


if __name__ == "__main__":
    unittest.main()
