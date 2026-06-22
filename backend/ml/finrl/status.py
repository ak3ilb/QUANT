"""FinRL status, model discovery, and paper-trader bridge."""
from __future__ import annotations

import glob
import json
import os
from datetime import datetime, timezone

from data_vault import get_ohlcv
from ml.finrl import config


def _rl_deps_ok() -> dict:
    missing = []
    for pkg in ("gymnasium", "stable_baselines3", "stockstats"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return {"installed": len(missing) == 0, "missing": missing}


def vault_stats(symbol: str, interval: str) -> dict:
    df = get_ohlcv(symbol.upper(), interval, bars=500_000)
    if df.empty:
        return {"bars": 0, "start": None, "end": None, "trainable": False}
    return {
        "bars": len(df),
        "start": str(df["time"].iloc[0]),
        "end": str(df["time"].iloc[-1]),
        "trainable": len(df) >= 120,
    }


def auto_date_splits(symbol: str, interval: str, train_ratio: float = 0.8) -> dict:
    """Derive train/test/trade windows from stored OHLCV."""
    df = get_ohlcv(symbol.upper(), interval, bars=500_000)
    if len(df) < 60:
        return {}
    n = len(df)
    train_end_idx = int(n * train_ratio)
    test_end_idx = int(n * 0.9)
    t0 = pd_timestamp(df["time"].iloc[0])
    t_train_end = pd_timestamp(df["time"].iloc[train_end_idx])
    t_test_end = pd_timestamp(df["time"].iloc[test_end_idx])
    t_end = pd_timestamp(df["time"].iloc[-1])
    return {
        "train_start": t0.strftime("%Y-%m-%d"),
        "train_end": t_train_end.strftime("%Y-%m-%d"),
        "test_start": t_train_end.strftime("%Y-%m-%d"),
        "test_end": t_test_end.strftime("%Y-%m-%d"),
        "trade_start": t_test_end.strftime("%Y-%m-%d"),
        "trade_end": (t_end + __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%d"),
        "bars": n,
    }


def pd_timestamp(ts):
    import pandas as pd
    return pd.Timestamp(ts)


def find_latest_model(symbol: str | None = None, interval: str | None = None) -> str | None:
    """Most recent model.zip under TRAINED_MODEL_DIR."""
    pattern = os.path.join(config.TRAINED_MODEL_DIR, "**", "model.zip")
    paths = glob.glob(pattern, recursive=True)
    if not paths:
        return None
    if symbol and interval:
        sym = symbol.upper()
        matched = [p for p in paths if f"{sym}_{interval}" in p.replace("\\", "/")]
        if matched:
            paths = matched
    elif symbol:
        sym = symbol.upper()
        matched = [p for p in paths if sym in p.replace("\\", "/")]
        if matched:
            paths = matched
    paths.sort(key=os.path.getmtime, reverse=True)
    return paths[0]


def list_models() -> list[dict]:
    pattern = os.path.join(config.TRAINED_MODEL_DIR, "**", "model.zip")
    rows = []
    for path in glob.glob(pattern, recursive=True):
        rows.append({
            "path": path,
            "name": os.path.basename(os.path.dirname(path)),
            "modified": datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc).isoformat(),
        })
    rows.sort(key=lambda r: r["modified"], reverse=True)
    return rows


def read_latest_train_result() -> dict | None:
    meta_path = os.path.join(config.TRAINED_MODEL_DIR, "latest_train.json")
    if not os.path.isfile(meta_path):
        return None
    try:
        with open(meta_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_train_result(result: dict) -> None:
    os.makedirs(config.TRAINED_MODEL_DIR, exist_ok=True)
    path = os.path.join(config.TRAINED_MODEL_DIR, "latest_train.json")
    with open(path, "w") as f:
        json.dump({**result, "saved_at": datetime.now(timezone.utc).isoformat()}, f, indent=2)


def _train_meta_for_model(model_path: str | None) -> dict:
    meta = read_latest_train_result() or {}
    if model_path and meta.get("model_path") != model_path:
        # Best-effort: infer from path name
        meta = {}
    return meta


def get_paper_signal(symbol: str = config.DEFAULT_SYMBOL, interval: str = config.DEFAULT_INTERVAL) -> dict:
    """Signal dict for paper_trader / matrix signals slot."""
    model_path = find_latest_model(symbol, interval)
    if not model_path:
        return {"status": "no_model", "symbol": symbol, "action": "HOLD", "confidence": 0.0}

    if not _rl_deps_ok()["installed"]:
        return {"status": "rl_deps_missing", "symbol": symbol, "action": "HOLD", "confidence": 0.0}

    from ml.finrl.trade import paper_trade_signal

    meta = _train_meta_for_model(model_path)
    raw = paper_trade_signal(
        model_path,
        symbol=symbol,
        interval=interval,
        use_vix=meta.get("use_vix", False),
    )
    if raw.get("status") != "ok":
        return {**raw, "action": "HOLD", "confidence": 0.0, "strategy": "finrl_ppo"}

    side = raw.get("side", "hold")
    action = {"buy": "BUY", "sell": "SELL", "hold": "HOLD"}.get(side, "HOLD")
    strength = float(raw.get("strength", 0.0))
    vs = vault_stats(symbol, interval)
    model_reliable = vs.get("bars", 0) >= config.MIN_TRAIN_BARS

    if not model_reliable:
        return {
            "status": "ok",
            "symbol": symbol,
            "interval": interval,
            "action": "HOLD",
            "confidence": 0.5,
            "confidence_kind": "action_strength",
            "model_reliable": False,
            "strength": strength,
            "strategy": "finrl_ppo",
            "model_path": model_path,
            "raw_action": raw.get("action"),
            "gated_reason": f"vault_bars={vs.get('bars', 0)} < {config.MIN_TRAIN_BARS}",
        }

    confidence = min(0.95, 0.55 + strength * 0.4) if action != "HOLD" else 0.5

    return {
        "status": "ok",
        "symbol": symbol,
        "interval": interval,
        "action": action,
        "confidence": confidence,
        "confidence_kind": "action_strength",
        "model_reliable": model_reliable,
        "strength": strength,
        "strategy": "finrl_ppo",
        "model_path": model_path,
        "raw_action": raw.get("action"),
    }


def get_finrl_status() -> dict:
    deps = _rl_deps_ok()
    splits_btc = auto_date_splits("BTCUSD", "1h")
    splits_xau = auto_date_splits("XAUUSD", "1h")
    models = list_models()
    paper_btc = None
    if find_latest_model("BTCUSD", "1h") and deps["installed"]:
        try:
            paper_btc = get_paper_signal("BTCUSD", "1h")
        except Exception as e:
            paper_btc = {"status": "error", "detail": str(e)[:200]}

    return {
        "status": "ok",
        "rl_dependencies": deps,
        "default_symbol": config.DEFAULT_SYMBOL,
        "default_interval": config.DEFAULT_INTERVAL,
        "vault": {
            "BTCUSD_1h": vault_stats("BTCUSD", "1h"),
            "BTCUSD_1d": vault_stats("BTCUSD", "1d"),
            "XAUUSD_1h": vault_stats("XAUUSD", "1h"),
        },
        "auto_splits": {"BTCUSD_1h": splits_btc, "XAUUSD_1h": splits_xau},
        "models": models[:10],
        "latest_models": {
            "BTCUSD_1h": find_latest_model("BTCUSD", "1h"),
            "XAUUSD_1h": find_latest_model("XAUUSD", "1h"),
        },
        "latest_model": find_latest_model(),
        "last_train": read_latest_train_result(),
        "paper_signal_preview": paper_btc,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
