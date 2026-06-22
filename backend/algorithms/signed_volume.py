import numpy as np
import pandas as pd


def signed_volume_imbalance(df: pd.DataFrame, window: int = 20) -> dict:
    """
    Order-flow proxy from OHLCV: sign(close-open) * volume, cumulative delta.
    """
    window = max(3, int(window))

    if len(df) < window + 1:
        return {
            "signed_volume": 0.0,
            "cumulative_delta": 0.0,
            "imbalance_ratio": 0.0,
            "buy_pressure": 0.5,
            "signal": "NEUTRAL",
        }

    close = pd.to_numeric(df["close"], errors="coerce")
    open_ = pd.to_numeric(df["open"], errors="coerce") if "open" in df.columns else close.shift(1)
    volume = pd.to_numeric(df["volume"], errors="coerce") if "volume" in df.columns else pd.Series(1.0, index=df.index)

    sign = np.sign(close - open_).replace(0, np.nan).fillna(0.0)
    signed_vol = sign * volume.fillna(0.0)

    cum_delta = float(signed_vol.tail(window).sum())
    total_vol = float(volume.tail(window).sum())
    last_signed = float(signed_vol.iloc[-1])

    imbalance_ratio = cum_delta / total_vol if total_vol > 0 else 0.0
    buy_pressure = 0.5 + 0.5 * max(-1.0, min(1.0, imbalance_ratio))

    if imbalance_ratio > 0.15:
        signal = "BUY_PRESSURE"
    elif imbalance_ratio < -0.15:
        signal = "SELL_PRESSURE"
    else:
        signal = "NEUTRAL"

    return {
        "signed_volume": last_signed,
        "cumulative_delta": cum_delta,
        "imbalance_ratio": float(imbalance_ratio),
        "buy_pressure": float(buy_pressure),
        "signal": signal,
    }
