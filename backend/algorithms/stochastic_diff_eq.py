# pyrefly: ignore [missing-import]
import numpy as np
import pandas as pd


def _clean_positive_prices(df: pd.DataFrame) -> np.ndarray:
    if df.empty or "close" not in df.columns:
        return np.array([], dtype=float)

    prices = pd.to_numeric(df["close"], errors="coerce").replace([np.inf, -np.inf], np.nan)
    prices = prices.dropna()
    prices = prices[prices > 0]
    return prices.to_numpy(dtype=float)


def geometric_brownian_motion_sde(
    df: pd.DataFrame,
    simulations: int = 2000,
    forecast_bars: int = 10,
    seed: int | None = None,
    max_abs_return: float = 0.5,
) -> dict:
    """
    Geometric Brownian Motion (GBM) Monte Carlo forecast.

    dS_t = mu * S_t * dt + sigma * S_t * dW_t
    """
    simulations = max(1, int(simulations))
    forecast_bars = max(1, int(forecast_bars))

    prices = _clean_positive_prices(df)
    if len(prices) < 50:
        current_price = float(prices[-1]) if len(prices) else 0.0
        return {
            "model": "geometric_brownian_motion",
            "current_price": current_price,
            "forecast_mean": current_price,
            "forecast_upper": current_price,
            "forecast_lower": current_price,
            "drift": 0.0,
            "volatility": 0.0,
            "note": "Insufficient positive finite close prices for GBM simulation",
        }

    log_returns = np.diff(np.log(prices))
    log_returns = log_returns[np.isfinite(log_returns)]
    log_returns = log_returns[np.abs(log_returns) <= max_abs_return]
    if len(log_returns) == 0:
        current_price = float(prices[-1])
        return {
            "model": "geometric_brownian_motion",
            "current_price": current_price,
            "forecast_mean": current_price,
            "forecast_upper": current_price,
            "forecast_lower": current_price,
            "drift": 0.0,
            "volatility": 0.0,
            "note": "No finite log returns available for GBM simulation",
        }

    mu = float(np.mean(log_returns))
    sigma = float(np.std(log_returns))
    if sigma <= 0:
        sigma = 1e-6

    S0 = float(prices[-1])
    dt = 1.0

    rng = np.random.default_rng(seed)
    paths = np.zeros((forecast_bars, simulations))
    paths[0] = S0

    for t in range(1, forecast_bars):
        z = rng.standard_normal(simulations)
        paths[t] = paths[t - 1] * np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * z)
        paths[t] = np.maximum(paths[t], 1e-8)

    mean_path = np.mean(paths, axis=1)
    upper_95 = np.percentile(paths, 95, axis=1)
    lower_05 = np.percentile(paths, 5, axis=1)
    percent_drift = ((mean_path[-1] - S0) / S0) * 100

    return {
        "model": "geometric_brownian_motion",
        "current_price": S0,
        "forecast_mean": float(mean_path[-1]),
        "forecast_upper": float(upper_95[-1]),
        "forecast_lower": float(lower_05[-1]),
        "drift": float(percent_drift),
        "volatility": float(sigma * 100),
    }


def ornstein_uhlenbeck_sde(
    df: pd.DataFrame,
    simulations: int = 2000,
    forecast_bars: int = 10,
    seed: int | None = None,
    max_abs_return: float = 0.5,
) -> dict:
    """
    Ornstein-Uhlenbeck mean-reversion Monte Carlo forecast.

    dS_t = theta * (mu - S_t) * dt + sigma * dW_t
    """
    simulations = max(1, int(simulations))
    forecast_bars = max(1, int(forecast_bars))

    prices = _clean_positive_prices(df)
    if len(prices) < 50:
        current_price = float(prices[-1]) if len(prices) else 0.0
        return {
            "model": "ornstein_uhlenbeck",
            "current_price": current_price,
            "forecast_mean": current_price,
            "forecast_upper": current_price,
            "forecast_lower": current_price,
            "drift": 0.0,
            "volatility": 0.0,
            "note": "Insufficient positive finite close prices for OU simulation",
        }

    returns = np.diff(prices) / prices[:-1]
    returns = returns[np.isfinite(returns)]
    returns = returns[np.abs(returns) <= max_abs_return]
    if len(returns) == 0:
        current_price = float(prices[-1])
        return {
            "model": "ornstein_uhlenbeck",
            "current_price": current_price,
            "forecast_mean": current_price,
            "forecast_upper": current_price,
            "forecast_lower": current_price,
            "drift": 0.0,
            "volatility": 0.0,
            "note": "No finite returns available for OU simulation",
        }

    mu = float(np.mean(prices))
    if len(prices) > 2:
        x = prices[:-1]
        y = prices[1:]
        b = np.cov(x, y)[0, 1] / np.var(x)
        b = max(0.001, min(0.999, float(b)))
        theta = -np.log(b)
    else:
        theta = 0.1

    theta = min(theta, 0.05)
    sigma = float(np.std(returns) * prices[-1])
    S0 = float(prices[-1])
    dt = 1.0

    rng = np.random.default_rng(seed)
    paths = np.zeros((forecast_bars, simulations))
    paths[0] = S0

    exp_theta = np.exp(-theta * dt)
    var_term = sigma * np.sqrt((1 - np.exp(-2 * theta * dt)) / (2 * theta)) if theta > 0 else sigma

    for t in range(1, forecast_bars):
        z = rng.standard_normal(simulations)
        paths[t] = paths[t - 1] * exp_theta + mu * (1 - exp_theta) + var_term * z
        paths[t] = np.maximum(paths[t], 1e-8)

    mean_path = np.mean(paths, axis=1)
    upper_95 = np.percentile(paths, 95, axis=1)
    lower_05 = np.percentile(paths, 5, axis=1)
    percent_drift = ((mean_path[-1] - S0) / S0) * 100

    return {
        "model": "ornstein_uhlenbeck",
        "current_price": S0,
        "forecast_mean": float(mean_path[-1]),
        "forecast_upper": float(upper_95[-1]),
        "forecast_lower": float(lower_05[-1]),
        "drift": float(percent_drift),
        "volatility": float(sigma / S0 * 100) if S0 else 0.0,
    }
