import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from algorithms.feature_builder import FEATURE_NAMES, build_features, features_to_vector
from data.finrl_patterns import (
    build_finrl_regime_extras,
    fetch_ccxt_ohlcv_optional,
    rolling_turbulence_proxy,
)


class FinrlPatternTests(unittest.TestCase):
    def test_rolling_turbulence_bounded(self):
        close = pd.Series(np.linspace(100, 110, 200) + np.random.randn(200) * 0.5)
        t = rolling_turbulence_proxy(close)
        self.assertGreaterEqual(t, 0.0)
        self.assertLessEqual(t, 1.0)

    def test_regime_extras_keys(self):
        close = pd.Series(np.random.randn(100).cumsum() + 100)
        extras = build_finrl_regime_extras(close, vix_level=20.0)
        self.assertIn("turbulence_norm", extras)
        self.assertIn("vix_norm", extras)
        self.assertAlmostEqual(extras["vix_norm"], (20 - 12) / 28, places=4)

    def test_feature_vector_includes_finrl_fields(self):
        df = pd.DataFrame({
            "close": np.linspace(100, 105, 80),
            "open": np.linspace(100, 105, 80),
            "high": np.linspace(101, 106, 80),
            "low": np.linspace(99, 104, 80),
            "volume": np.ones(80),
        })
        feats = build_features(df, regime={"turbulence_norm": 0.3, "vix_norm": 0.7})
        vec = features_to_vector(feats)
        self.assertEqual(len(FEATURE_NAMES), len(vec))
        self.assertIn("turbulence_norm", FEATURE_NAMES)
        self.assertIn("vix_norm", FEATURE_NAMES)

    def test_ccxt_optional_empty_without_package(self):
        # Should not raise; returns empty if ccxt missing or network blocked
        df = fetch_ccxt_ohlcv_optional(days_back=1)
        self.assertIsInstance(df, pd.DataFrame)


if __name__ == "__main__":
    unittest.main()
