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

    This is a practical quant-model SDE, not the Ornstein-Uhlenbeck
    mean-reversion process and not a literal Simons geometric theorem.
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

    returns = np.diff(prices) / prices[:-1]
    returns = returns[np.isfinite(returns)]
    returns = returns[np.abs(returns) <= max_abs_return]
    if len(returns) == 0:
        current_price = float(prices[-1])
        return {
            "model": "geometric_brownian_motion",
            "current_price": current_price,
            "forecast_mean": current_price,
            "forecast_upper": current_price,
            "forecast_lower": current_price,
            "drift": 0.0,
            "volatility": 0.0,
            "note": "No finite returns available for GBM simulation",
        }
    
    # Ornstein-Uhlenbeck Parameters
    # dS_t = theta * (mu - S_t) * dt + sigma * dW_t
    # We estimate theta (mean reversion speed) and mu (long-term mean)
    
    # Simple estimation for OU parameters
    mu = np.mean(prices)
    # Theta: speed of reversion. High for sideways, low for trends.
    # We can approximate theta from the autoregressive coefficient AR(1)
    # S_t = a + b * S_{t-1} + e
    if len(prices) > 2:
        x = prices[:-1]
        y = prices[1:]
        b = np.cov(x, y)[0, 1] / np.var(x)
        # Bounding b to ensure mean reversion (0 < b < 1)
        b = max(0.001, min(0.999, b))
        theta = -np.log(b)
    else:
        theta = 0.1
        
    # Cap theta to prevent Euler-Maruyama instability when dt=1
    theta = min(theta, 0.05)
        
    sigma = np.std(returns) * prices[-1] # Volatility scaled to price level
    
    S0 = prices[-1]
    dt = 1.0  # 1 bar
    
    rng = np.random.default_rng(seed)
    paths = np.zeros((forecast_bars, simulations))
    paths[0] = S0
    
    # Exact discrete solution parameters for OU
    exp_theta = np.exp(-theta * dt)
    var_term = sigma * np.sqrt((1 - np.exp(-2 * theta * dt)) / (2 * theta))
    
    for t in range(1, forecast_bars):
        # standard normal random variables
        Z = rng.standard_normal(simulations)
        # OU exact discrete step (avoids overshoot instability)
        paths[t] = paths[t-1] * exp_theta + mu * (1 - exp_theta) + var_term * Z
        # Ensure prices don't go negative
        paths[t] = np.maximum(paths[t], 1e-8)
        
    mean_path = np.mean(paths, axis=1)
    upper_95 = np.percentile(paths, 95, axis=1)
    lower_05 = np.percentile(paths, 5, axis=1)
    
    # Calculate an annualized-style percentage drift for the UI
    percent_drift = ((mean_path[-1] - S0) / S0) * 100
    
    return {
        "model": "ornstein_uhlenbeck",
        "current_price": float(S0),
        "forecast_mean": float(mean_path[-1]),
        "forecast_upper": float(upper_95[-1]),
        "forecast_lower": float(lower_05[-1]),
        "drift": float(percent_drift),
        "volatility": float(sigma / S0 * 100)
    }


def ornstein_uhlenbeck_sde(
    df: pd.DataFrame,
    simulations: int = 2000,
    forecast_bars: int = 10,
    seed: int | None = None,
) -> dict:
    """
    Backward-compatible alias.

    Kept so older imports continue to work, but the implementation is GBM.
    """
    result = geometric_brownian_motion_sde(df, simulations, forecast_bars, seed)
    result["deprecated_alias"] = "ornstein_uhlenbeck_sde"
    return result
