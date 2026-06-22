import numpy as np
import pandas as pd


def _align_closes(df_a: pd.DataFrame, df_b: pd.DataFrame) -> pd.DataFrame:
    a = df_a[["close"]].copy()
    b = df_b[["close"]].copy()
    a.columns = ["close_a"]
    b.columns = ["close_b"]

    if "time" in df_a.columns:
        a.index = pd.to_datetime(df_a["time"])
    if "time" in df_b.columns:
        b.index = pd.to_datetime(df_b["time"])

    merged = a.join(b, how="inner")
    merged = merged.replace([np.inf, -np.inf], np.nan).dropna()
    merged = merged[(merged["close_a"] > 0) & (merged["close_b"] > 0)]
    return merged


def engle_granger_spread(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    z_entry: float = 2.0,
) -> dict:
    """
    Engle-Granger style spread z-score between two price series.
    df_a = dependent (e.g. BTC), df_b = regressor (e.g. XAU).
    """
    merged = _align_closes(df_a, df_b)
    if len(merged) < 60:
        return {
            "hedge_ratio": 1.0,
            "spread_zscore": 0.0,
            "half_life_bars": None,
            "signal": "NEUTRAL",
            "pair_ready": False,
        }

    log_a = np.log(merged["close_a"].values)
    log_b = np.log(merged["close_b"].values)

    beta = float(np.cov(log_b, log_a)[0, 1] / np.var(log_b)) if np.var(log_b) > 0 else 1.0
    alpha = float(log_a.mean() - beta * log_b.mean())
    spread = log_a - (alpha + beta * log_b)

    spread_mean = float(np.mean(spread))
    spread_std = float(np.std(spread))
    z = (spread[-1] - spread_mean) / spread_std if spread_std > 0 else 0.0

    # AR(1) half-life of spread mean reversion
    spread_lag = spread[:-1]
    spread_diff = np.diff(spread)
    if len(spread_lag) > 5 and np.var(spread_lag) > 0:
        phi = float(np.cov(spread_lag, spread_diff)[0, 1] / np.var(spread_lag))
        denom = 1.0 + phi
        half_life = float(-np.log(2) / np.log(denom)) if phi < 0 and denom > 0 else None
    else:
        half_life = None

    if z >= z_entry:
        signal = "SHORT_SPREAD"
    elif z <= -z_entry:
        signal = "LONG_SPREAD"
    else:
        signal = "NEUTRAL"

    return {
        "hedge_ratio": beta,
        "intercept": alpha,
        "spread_zscore": float(z),
        "half_life_bars": half_life,
        "signal": signal,
        "pair_ready": True,
    }
