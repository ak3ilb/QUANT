import numpy as np
import pandas as pd


def kalman_fair_value(
    df: pd.DataFrame,
    process_noise: float = 1e-4,
    measurement_noise: float = 1e-3,
    band_sigma: float = 2.0,
) -> dict:
    """
    1D Kalman filter fair-value estimate on log(close).
    Innovation z-score drives mean-reversion entries (Piggy strategy).
    """
    prices = pd.to_numeric(df["close"], errors="coerce").dropna().values
    if len(prices) < 10:
        current = float(prices[-1]) if len(prices) else 0.0
        return {
            "fair_value": current,
            "innovation_z": 0.0,
            "upper_band": current,
            "lower_band": current,
            "signal": "NEUTRAL",
        }

    log_prices = np.log(np.maximum(prices, 1e-8))
    x = float(log_prices[0])
    p = 1.0
    innovations = []
    fair_log = []

    q = float(process_noise)
    r = float(measurement_noise)

    for z in log_prices:
        x_pred = x
        p_pred = p + q
        innov = z - x_pred
        k = p_pred / (p_pred + r)
        x = x_pred + k * innov
        p = (1.0 - k) * p_pred
        fair_log.append(x)
        innovations.append(innov)

    innov_arr = np.array(innovations)
    tail = innov_arr[-min(30, len(innov_arr)) :]
    innov_std = float(np.std(tail)) if len(tail) > 1 else 1e-3
    if innov_std <= 0:
        innov_std = 1e-3

    fair = float(np.exp(fair_log[-1]))
    current = float(prices[-1])
    zscore = (log_prices[-1] - fair_log[-1]) / innov_std

    log_upper = fair_log[-1] + band_sigma * innov_std
    log_lower = fair_log[-1] - band_sigma * innov_std
    upper = float(np.exp(log_upper))
    lower = float(np.exp(log_lower))

    if zscore <= -band_sigma:
        signal = "UNDERVALUED"
    elif zscore >= band_sigma:
        signal = "OVERVALUED"
    else:
        signal = "NEUTRAL"

    return {
        "fair_value": fair,
        "innovation_z": float(zscore),
        "upper_band": upper,
        "lower_band": lower,
        "signal": signal,
    }
