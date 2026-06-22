"""Post-train analysis for FinRL DRL runs."""
from __future__ import annotations

import json
import os

import numpy as np

from data_vault import get_ohlcv
from ml.finrl import config
from ml.finrl.agent_sb3 import DRLAgent
from ml.finrl.env_crypto import CryptoTradingEnv, make_gym_env
from ml.finrl.preprocessor import data_split
from ml.finrl.processor import QuantDataProcessor
from ml.finrl.status import auto_date_splits, find_latest_model, read_latest_train_result


def analyze_run(
    model_path: str | None = None,
    model_name: str = "ppo",
    symbol: str = "BTCUSD",
    interval: str = "1h",
) -> dict:
    meta = read_latest_train_result() or {}
    model_path = model_path or find_latest_model(symbol, interval)
    if model_path and meta.get("symbol") and meta.get("symbol") != symbol.upper():
        meta = {}
    if not model_path or not os.path.isfile(model_path):
        return {"status": "error", "detail": "no model found"}

    use_vix = meta.get("use_vix", False)
    splits = auto_date_splits(symbol, interval)
    dp = QuantDataProcessor(data_source="vault", use_vix=use_vix)

    train_df = dp.download_data([symbol], splits["train_start"], splits["train_end"], interval)
    train_df = dp.preprocess(train_df)
    train_price, train_tech, _ = dp.df_to_array(train_df, if_vix=use_vix)

    test_df = dp.download_data([symbol], splits["test_start"], splits["test_end"], interval)
    test_df = dp.preprocess(test_df)
    test_price, test_tech, _ = dp.df_to_array(test_df, if_vix=use_vix)

    raw = get_ohlcv(symbol, interval, bars=500_000)
    close = raw["close"].astype(float)
    buy_hold_return = float(close.iloc[-1] / close.iloc[0] - 1.0) if len(close) > 1 else 0.0

    def _episode_return(price, tech):
        env = CryptoTradingEnv(
            {"price_array": price, "tech_array": tech, "turbulence_array": np.zeros(len(price))},
            lookback=config.LOOKBACK,
            initial_capital=config.INITIAL_CAPITAL,
        )
        gym_env = None
        try:
            gym_env = make_gym_env(
                {"price_array": price, "tech_array": tech, "turbulence_array": np.zeros(len(price))},
                lookback=config.LOOKBACK,
                initial_capital=config.INITIAL_CAPITAL,
            )
        except ImportError:
            pass
        model = DRLAgent.load_model(model_name, model_path)
        target = gym_env or env
        out = DRLAgent.predict(target, model)
        return out

    train_out = _episode_return(train_price, train_tech)
    test_out = _episode_return(test_price, test_tech)

    train_ret = train_out["episode_return"] - 1.0
    test_ret = test_out["episode_return"] - 1.0

    return {
        "status": "ok",
        "model_path": model_path,
        "symbol": symbol,
        "interval": interval,
        "meta": meta,
        "splits": splits,
        "data": {
            "vault_bars": len(raw),
            "train_bars": len(train_price),
            "test_bars": len(test_price),
            "period": f"{raw['time'].iloc[0]} → {raw['time'].iloc[-1]}" if len(raw) else None,
        },
        "returns": {
            "train_policy_return_pct": round(train_ret * 100, 3),
            "test_policy_return_pct": round(test_ret * 100, 3),
            "buy_hold_return_pct": round(buy_hold_return * 100, 3),
        },
        "assets": {
            "train_final": train_out["final_asset"],
            "test_final": test_out["final_asset"],
        },
        "assessment": _assess(train_ret, test_ret, buy_hold_return, len(train_price)),
    }


def _assess(train_r: float, test_r: float, bh_r: float, train_bars: int) -> dict:
    notes = []
    if train_bars < 500:
        notes.append("Very small dataset (~1 month BTC 1h) — treat metrics as smoke-test only.")
    if train_r > 0 and test_r < 0:
        notes.append("Possible overfit: positive train, negative test episode return.")
    if abs(train_r - test_r) < 0.001 and train_r == 0:
        notes.append("Policy may be near-hold (low exploration on short window).")
    if test_r > bh_r:
        notes.append("Test policy beat buy-and-hold on this window.")
    elif test_r < bh_r:
        notes.append("Test policy underperformed buy-and-hold.")
    return {"notes": notes, "reliable": train_bars >= 2000}


if __name__ == "__main__":
    print(json.dumps(analyze_run(), indent=2, default=str))
