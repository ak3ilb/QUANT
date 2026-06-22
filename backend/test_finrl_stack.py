import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from ml.finrl.env_crypto import CryptoTradingEnv
from ml.finrl.preprocessor import FeatureEngineer, add_technical_indicator, data_split
from ml.finrl.processor import QuantDataProcessor, df_to_arrays, vault_to_finrl_df


def _sample_panel(n: int = 120) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n, freq="h")
    rows = []
    for tic in ["BTCUSD"]:
        for i, d in enumerate(dates):
            price = 40000 + i * 10 + np.sin(i / 10) * 100
            rows.append({
                "date": d.strftime("%Y-%m-%d %H:%M:%S"),
                "tic": tic,
                "open": price,
                "high": price + 50,
                "low": price - 50,
                "close": price,
                "volume": 1000.0,
            })
    return pd.DataFrame(rows)


class FinrlStackTests(unittest.TestCase):
    def test_data_split(self):
        df = _sample_panel(100)
        part = data_split(df, "2024-01-02", "2024-01-05")
        self.assertGreater(len(part), 0)
        self.assertLess(len(part), len(df))

    def test_technical_indicators(self):
        df = FeatureEngineer.clean_data(_sample_panel(100))
        out = add_technical_indicator(df)
        for col in ["macd", "rsi_30", "close_30_sma"]:
            self.assertIn(col, out.columns)

    def test_feature_engineer_preprocess(self):
        fe = FeatureEngineer(use_vix=False, use_turbulence=False)
        out = fe.preprocess_data(_sample_panel(100))
        self.assertFalse(out.isnull().values.any())

    def test_df_to_arrays_shapes(self):
        fe = FeatureEngineer(use_vix=False)
        df = fe.preprocess_data(_sample_panel(100))
        price, tech, turb = df_to_arrays(df, if_vix=False)
        self.assertEqual(price.shape[0], tech.shape[0])
        self.assertEqual(price.shape[1], 1)
        self.assertEqual(turb.shape[0], price.shape[0])

    def test_crypto_env_episode(self):
        fe = FeatureEngineer(use_vix=False)
        df = fe.preprocess_data(_sample_panel(80))
        price, tech, turb = df_to_arrays(df)
        env = CryptoTradingEnv({"price_array": price, "tech_array": tech, "turbulence_array": turb})
        obs, _ = env.reset()
        self.assertEqual(len(obs), env.state_dim)
        total_reward = 0.0
        done = False
        while not done:
            action = np.zeros(env.action_dim)
            obs, reward, done, truncated, info = env.step(action)
            total_reward += reward
            self.assertFalse(truncated)
        self.assertGreater(env.episode_return, 0)

    def test_quant_processor_download_mock(self):
        df = vault_to_finrl_df("NONEXISTENT", "1h")
        self.assertTrue(df.empty or isinstance(df, pd.DataFrame))


if __name__ == "__main__":
    unittest.main()
