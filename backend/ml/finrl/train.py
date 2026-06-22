"""FinRL train.py flow for QUANT."""
from __future__ import annotations

import os
from datetime import datetime

from ml.finrl import config
from ml.finrl.agent_sb3 import DRLAgent
from ml.finrl.env_crypto import make_gym_env
from ml.finrl.preprocessor import data_split
from ml.finrl.processor import QuantDataProcessor


def train(
    symbol: str = config.DEFAULT_SYMBOL,
    interval: str = config.DEFAULT_INTERVAL,
    start_date: str = config.TRAIN_START_DATE,
    end_date: str = config.TRAIN_END_DATE,
    model_name: str = "ppo",
    total_timesteps: int = config.DEFAULT_TIMESTEPS,
    data_source: str = "vault_then_fetch",
    use_vix: bool = True,
    use_turbulence: bool = True,
    cwd: str | None = None,
    model_kwargs: dict | None = None,
) -> dict:
    dp = QuantDataProcessor(data_source=data_source, use_vix=use_vix, use_turbulence=use_turbulence)
    df = dp.download_data([symbol], start_date, end_date, interval)
    df = dp.preprocess(df)
    df = data_split(df, start_date, end_date)
    price, tech, turb = dp.df_to_array(df, if_vix=use_vix)

    if len(price) < 80:
        raise ValueError(f"Insufficient bars after preprocess: {len(price)} (need ≥80)")

    env_config = {
        "price_array": price,
        "tech_array": tech,
        "turbulence_array": turb,
        "if_train": True,
    }

    def _factory():
        return make_gym_env(
            env_config,
            lookback=config.LOOKBACK,
            initial_capital=config.INITIAL_CAPITAL,
            buy_cost_pct=config.BUY_COST_PCT,
            sell_cost_pct=config.SELL_COST_PCT,
            gamma=config.GAMMA,
            include_turbulence_state=use_turbulence,
        )

    agent = DRLAgent(_factory)
    mk = dict(model_kwargs or {})
    if len(price) < 1000 and model_name.lower() == "ppo":
        mk.setdefault("n_steps", min(512, max(64, len(price) // 3)))
        mk.setdefault("batch_size", 32)
    model = agent.get_model(model_name, mk)
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    save_dir = cwd or os.path.join(config.TRAINED_MODEL_DIR, f"{symbol}_{interval}_{model_name}_{run_id}")
    path = agent.train_model(model, total_timesteps=total_timesteps, cwd=save_dir)

    dp.save_dataset(df, f"{symbol}_{interval}_train")
    result = {
        "status": "complete",
        "model_path": path,
        "symbol": symbol,
        "interval": interval,
        "bars": len(price),
        "timesteps": total_timesteps,
        "model_name": model_name,
        "start_date": start_date,
        "end_date": end_date,
        "use_vix": use_vix,
        "use_turbulence": use_turbulence,
        "lookback": config.LOOKBACK,
        "include_turbulence_state": use_turbulence,
    }
    from ml.finrl.status import save_train_result
    save_train_result(result)
    return result
