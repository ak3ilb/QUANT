import numpy as np
import pandas as pd
from scipy.stats import linregress

def ornstein_uhlenbeck_sde(df: pd.DataFrame, simulations: int = 1000, forecast_bars: int = 30) -> dict:
    """
    Stochastic Differential Equation: Ornstein-Uhlenbeck process
    dx_t = theta * (mu - x_t) * dt + sigma * dW_t
    Used for mean-reverting statistical arbitrage.
    """
    if len(df) < 50:
        return {"forecast_mean": float(df['close'].iloc[-1]) if not df.empty else 0.0}
        
    prices = df['close'].values
    dt = 1.0
    
    # Estimate OU parameters using linear regression: x_{t} - x_{t-1} = a + b * x_{t-1} + error
    x_t = prices[1:]
    x_t_1 = prices[:-1]
    
    slope, intercept, _, _, stderr = linregress(x_t_1, x_t - x_t_1)
    
    # If slope >= 0, it is not mean reverting. We cap it to a small negative number.
    b = min(slope, -0.0001)
    a = intercept
    
    theta = -b / dt
    mu = a / (theta * dt)
    sigma = stderr / np.sqrt(dt)
    
    S0 = prices[-1]
    paths = np.zeros((forecast_bars, simulations))
    paths[0] = S0
    
    for t in range(1, forecast_bars):
        dW = np.random.standard_normal(simulations) * np.sqrt(dt)
        paths[t] = paths[t-1] + theta * (mu - paths[t-1]) * dt + sigma * dW
        
    mean_path = np.mean(paths, axis=1)
    upper_95 = np.percentile(paths, 95, axis=1)
    lower_05 = np.percentile(paths, 5, axis=1)
    
    return {
        "current_price": float(S0),
        "forecast_mean": float(mean_path[-1]),
        "forecast_upper": float(upper_95[-1]),
        "forecast_lower": float(lower_05[-1]),
        "theta": float(theta),
        "equilibrium_mu": float(mu)
    }
