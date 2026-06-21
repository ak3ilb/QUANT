import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde
from scipy.signal import find_peaks

def kde_liquidity_nodes(df: pd.DataFrame) -> list:
    if len(df) < 50:
        return []
        
    prices = df['close'].values
    volumes = df['volume'].values
    
    try:
        kde = gaussian_kde(prices, weights=volumes)
        x_grid = np.linspace(prices.min(), prices.max(), 200)
        pdf = kde.evaluate(x_grid)
        
        peaks, _ = find_peaks(pdf, distance=10)
        
        peak_prices = x_grid[peaks]
        peak_densities = pdf[peaks]
        
        top_indices = np.argsort(peak_densities)[-3:][::-1]
        return [float(peak_prices[i]) for i in top_indices]
    except:
        return []
