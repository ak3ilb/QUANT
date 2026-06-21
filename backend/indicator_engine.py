import pandas as pd
import pandas_ta as ta
import numpy as np

class IndicatorEngine:
    def __init__(self):
        pass
        
    def compute_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute standard set of indicators for Quant models."""
        df = df.copy()
        
        # Make sure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
            
        # Trend
        df.ta.ema(length=9, append=True)
        df.ta.ema(length=21, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.ema(length=200, append=True)
        
        # Momentum
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        
        # Volatility
        df.ta.atr(length=14, append=True)
        df.ta.bbands(length=20, std=2, append=True)
        
        # Volume
        df.ta.obv(append=True)
        
        # Custom calculated fields
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = df['close'].pct_change().apply(lambda x: np.log(1+x) if not pd.isna(x) else np.nan)
        df['volatility_20'] = df['returns'].rolling(window=20).std()
        
        return df.dropna(subset=['EMA_50', 'RSI_14'])

    def compute_selected(self, df: pd.DataFrame, indicators: list) -> pd.DataFrame:
        """Compute only selected indicators."""
        df = df.copy()
        for ind in indicators:
            if hasattr(df.ta, ind):
                getattr(df.ta, ind)(append=True)
        return df
