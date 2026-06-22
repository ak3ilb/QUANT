"""FinRL trade.py flow — backtest mode + optional paper-trade signal hook."""
from __future__ import annotations

import json
import os
from datetime import datetime

import numpy as np

from ml.finrl import config
from ml.finrl.test import test


def backtest(
    model_path: str,
    model_name: str = "ppo",
    symbol: str = config.DEFAULT_SYMBOL,
    interval: str = config.DEFAULT_INTERVAL,
    start_date: str = config.TRADE_START_DATE,
    end_date: str = config.TRADE_END_DATE,
) -> dict:
    """FinRL trade.backtesting — run test() on trade window."""
    return test(
        model_path=model_path,
        model_name=model_name,
        symbol=symbol,
        interval=interval,
        start_date=start_date,
        end_date=end_date,
    )


def paper_trade_signal(
    model_path: str,
    model_name: str = "ppo",
    symbol: str = config.DEFAULT_SYMBOL,
    interval: str = config.DEFAULT_INTERVAL,
    use_vix: bool = False,
) -> dict:
    """
    Latest-bar action from trained policy for paper_trader integration.
    Returns continuous action in [-1, 1] per asset (FinRL CryptoEnv convention).
    """
    from ml.finrl.agent_sb3 import DRLAgent
    from ml.finrl.env_crypto import CryptoTradingEnv
    from ml.finrl.processor import QuantDataProcessor

    dp = QuantDataProcessor(data_source="vault_then_fetch", use_vix=use_vix)
    from ml.finrl.status import auto_date_splits

    splits = auto_date_splits(symbol, interval)
    start = splits.get("trade_start", config.TRADE_START_DATE) if splits else config.TRADE_START_DATE
    end = splits.get("trade_end", datetime.utcnow().strftime("%Y-%m-%d")) if splits else datetime.utcnow().strftime("%Y-%m-%d")
    price, tech, turb, _ = dp.build_arrays(symbol, interval, start, end)
    if len(price) < 10:
        return {"status": "insufficient_data", "symbol": symbol}

    from ml.finrl.status import _train_meta_for_model
    meta = _train_meta_for_model(model_path)
    lookback = int(meta.get("lookback", 1))
    include_turb = bool(meta.get("include_turbulence_state", meta.get("use_turbulence", False)))

    env = CryptoTradingEnv(
        {"price_array": price, "tech_array": tech, "turbulence_array": turb, "if_train": False},
        lookback=lookback,
        initial_capital=config.INITIAL_CAPITAL,
        include_turbulence_state=include_turb,
    )
    obs, _ = env.reset()
    while env.time < env.max_step:
        obs, _, done, _, _ = env.step(np.zeros(env.action_dim))
        if done:
            break

    model = DRLAgent.load_model(model_name, model_path)
    action, _ = model.predict(obs, deterministic=True)
    action = action.flatten() if hasattr(action, "flatten") else action

    side = "hold"
    strength = float(abs(action[0])) if len(action) else 0.0
    if len(action) and action[0] > 0.05:
        side = "buy"
    elif len(action) and action[0] < -0.05:
        side = "sell"

    return {
        "status": "ok",
        "symbol": symbol,
        "interval": interval,
        "side": side,
        "action": action.tolist() if hasattr(action, "tolist") else list(action),
        "strength": strength,
        "model_path": model_path,
    }


def save_results(result: dict, name: str = "trade") -> str:
    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    path = os.path.join(config.RESULTS_DIR, f"{name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
    with open(path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    return path
