import pandas as pd
import numpy as np

def kelly_sizing(df: pd.DataFrame, strategy: str = "medallion") -> dict:
    """
    The Single Unified Risk Engine.
    Uses the Kelly Criterion to allocate capital optimally.
    Based on the Renaissance standard of executing thousands of trades with a 50.75% win rate.
    """
    
    # 50.75% Edge as described
    w = 0.5075
    
    # Calculate historical average win and loss from standard deviation
    if len(df) < 10:
        return {"win_rate": w, "win_loss_ratio": 1.0, "full_kelly": 0, "recommended_size_pct": 0}
        
    returns = df['close'].pct_change().dropna()
    avg_win = returns[returns > 0].mean()
    avg_loss = abs(returns[returns < 0].mean())
    
    if pd.isna(avg_win) or pd.isna(avg_loss) or avg_loss == 0:
        r = 1.0
    else:
        r = avg_win / avg_loss
        
    # Kelly Formula: f* = W - ((1 - W) / R)
    f_star = w - ((1 - w) / r) if r > 0 else 0
    
    # Clamp to rational limits (between 0 and 1)
    f_star = max(0, min(1, f_star))
    
    # Half-Kelly is standard practice to manage variance
    fractional_kelly = f_star * 0.5
    
    return {
        "win_rate": w,
        "win_loss_ratio": r,
        "full_kelly": float(f_star),
        "fractional_kelly": float(fractional_kelly),
        "recommended_size_pct": float(fractional_kelly * 100)
    }
