"""FinRL test.py flow — evaluate trained DRL policy on holdout window."""
from __future__ import annotations

import os

from ml.finrl import config
from ml.finrl.agent_sb3 import DRLAgent
from ml.finrl.env_crypto import CryptoTradingEnv, make_gym_env
from ml.finrl.preprocessor import data_split
from ml.finrl.processor import QuantDataProcessor


def test(
    model_path: str,
    model_name: str = "ppo",
    symbol: str = config.DEFAULT_SYMBOL,
    interval: str = config.DEFAULT_INTERVAL,
    start_date: str = config.TEST_START_DATE,
    end_date: str = config.TEST_END_DATE,
    data_source: str = "vault_then_fetch",
    use_vix: bool = False,
    use_turbulence: bool = False,
) -> dict:
    if not os.path.isfile(model_path):
        raise FileNotFoundError(model_path)

    dp = QuantDataProcessor(data_source=data_source, use_vix=use_vix, use_turbulence=use_turbulence)
    df = dp.download_data([symbol], start_date, end_date, interval)
    df = dp.preprocess(df)
    df = data_split(df, start_date, end_date)
    price, tech, turb = dp.df_to_array(df, if_vix=use_vix)

    env_config = {
        "price_array": price,
        "tech_array": tech,
        "turbulence_array": turb,
        "if_train": False,
    }
    try:
        env = make_gym_env(env_config, lookback=config.LOOKBACK, initial_capital=config.INITIAL_CAPITAL)
    except ImportError:
        env = CryptoTradingEnv(env_config, lookback=config.LOOKBACK, initial_capital=config.INITIAL_CAPITAL)

    model = DRLAgent.load_model(model_name, model_path)
    result = DRLAgent.predict(env, model)
    result.update({
        "status": "complete",
        "model_path": model_path,
        "symbol": symbol,
        "interval": interval,
        "start_date": start_date,
        "end_date": end_date,
        "bars": len(price),
    })
    return result
