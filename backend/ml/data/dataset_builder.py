"""Build labeled ML dataset from stored OHLCV in DuckDB."""
import numpy as np

from algorithms.feature_builder import build_features, features_to_vector, FEATURE_NAMES
from data_vault import get_ohlcv


def build_direction_dataset(
    symbol: str = "BTCUSD",
    interval: str = "1h",
    min_rows: int = 500,
    horizon: int = 1,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    df = get_ohlcv(symbol, interval, bars=500_000)
    if len(df) < min_rows + horizon + 10:
        raise ValueError(f"Insufficient data: {len(df)} bars for {symbol} {interval}")

    x_rows, y_rows = [], []
    start = max(50, len(df) - 50_000)

    from data.finrl_patterns import build_finrl_regime_extras, fetch_vix_close

    vix_level = fetch_vix_close()

    for i in range(start, len(df) - horizon):
        slice_df = df.iloc[: i + 1].copy()
        finrl_regime = build_finrl_regime_extras(slice_df["close"], vix_level=vix_level)
        feats = build_features(slice_df, regime=finrl_regime)
        x_rows.append(features_to_vector(feats))
        future = float(df["close"].iloc[i + horizon])
        current = float(df["close"].iloc[i])
        y_rows.append(1 if future > current else 0)

    if len(x_rows) < min_rows:
        raise ValueError(f"Only {len(x_rows)} training rows after feature build")

    return np.vstack(x_rows), np.array(y_rows, dtype=int), FEATURE_NAMES


def train_test_split_time_series(
    x: np.ndarray, y: np.ndarray, test_ratio: float = 0.2
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    split = int(len(x) * (1.0 - test_ratio))
    return x[:split], x[split:], y[:split], y[split:]
