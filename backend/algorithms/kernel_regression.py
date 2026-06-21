import numpy as np
from scipy import stats

def kernel_regression(df, window=10, bandwidth=0.1, max_lookback=2000):
    """
    Higher-Dimensional Kernel Regression (RBF Kernel)
    Finds historical environments similar to the current one and predicts the immediate next move.
    Also calculates the p-value of the prediction to test for statistical significance.
    """
    if len(df) < window + 2:
        return {"prob_bull": 0.5, "p_value": 1.0}
        
    # We only care about the most recent history to keep calculations fast
    df_subset = df.tail(max_lookback).copy()
    
    # Calculate returns
    returns = df_subset['close'].pct_change().dropna().values
    if len(returns) < window + 1:
        return {"prob_bull": 0.5, "p_value": 1.0}
        
    # Create rolling windows of length `window`
    # X will be the historical environments
    # y will be the immediate next return after each environment
    shape = (returns.size - window, window)
    strides = (returns.itemsize, returns.itemsize)
    X = np.lib.stride_tricks.as_strided(returns, shape=shape, strides=strides)
    y = returns[window:]
    
    # The current environment is the very last window
    current_env = returns[-window:]
    
    # We don't want to match the current environment against itself
    X_history = X[:-1]
    y_history = y[:-1]
    
    if len(X_history) == 0:
        return {"prob_bull": 0.5, "p_value": 1.0}
        
    # Calculate Euclidean distances between current environment and all historical environments
    # using broadcasting
    distances = np.linalg.norm(X_history - current_env, axis=1)
    
    # Apply RBF (Radial Basis Function) Kernel
    # Weights are exponentially higher for very close matches
    weights = np.exp(-(distances ** 2) / (2 * (bandwidth ** 2)))
    
    # Normalize weights so they sum to 1
    weight_sum = np.sum(weights)
    if weight_sum == 0:
        return {"prob_bull": 0.5, "p_value": 1.0}
        
    normalized_weights = weights / weight_sum
    
    # The predicted next return is the weighted average of historical next returns
    expected_return = np.sum(normalized_weights * y_history)
    
    # Calculate the weighted variance to find statistical significance
    weighted_variance = np.sum(normalized_weights * (y_history - expected_return) ** 2)
    
    # Effective sample size (Kish's formula)
    n_eff = 1.0 / np.sum(normalized_weights ** 2)
    
    if n_eff <= 1 or weighted_variance == 0:
        return {"prob_bull": 0.5, "p_value": 1.0}
        
    # Standard error
    se = np.sqrt(weighted_variance / n_eff)
    
    # Calculate t-statistic (testing null hypothesis that expected_return == 0)
    t_stat = expected_return / se
    
    # Calculate p-value (two-tailed)
    p_value = 2 * (1 - stats.t.cdf(np.abs(t_stat), df=n_eff-1))
    
    # Map expected return to a probability of being BULLISH (0 to 1)
    # Using a sigmoid function centered at 0
    # Scaled by historical volatility for normalization
    vol = np.std(returns)
    if vol == 0:
        prob_bull = 0.5
    else:
        z_score = expected_return / vol
        prob_bull = 1 / (1 + np.exp(-z_score))
        
    return {
        "prob_bull": float(prob_bull),
        "p_value": float(p_value)
    }

