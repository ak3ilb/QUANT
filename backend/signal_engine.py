import pandas as pd
import numpy as np

STRATEGIES = ["nova", "piggy", "limroy", "dejavu", "medallion"]

class StrategyRunner:
    def __init__(self):
        pass

class SignalEngine:
    def __init__(self):
        pass

    def get_all_signals(self, df: pd.DataFrame, regime: dict) -> dict:
        return {
            strategy: self.get_signal(df, strategy, regime)
            for strategy in STRATEGIES
        }
        
    def get_signal(self, df: pd.DataFrame, strategy: str, regime: dict) -> dict:
        """
        Bayesian Signal Scorer
        Combines technicals with HMM regime and Bayesian prior updating
        """
        strategy = strategy.lower()

        if len(df) < 50:
            return {"strategy": strategy, "action": "HOLD", "confidence": 0}
            
        current_close = df['close'].iloc[-1]
        ema_fast = df['EMA_9'].iloc[-1] if 'EMA_9' in df.columns else current_close
        ema_slow = df['EMA_21'].iloc[-1] if 'EMA_21' in df.columns else current_close
        ema_50 = df['EMA_50'].iloc[-1] if 'EMA_50' in df.columns else current_close
        rsi = df['RSI_14'].iloc[-1] if 'RSI_14' in df.columns else 50
        macd_hist = df['MACDh_12_26_9'].iloc[-1] if 'MACDh_12_26_9' in df.columns else 0
        
        regime_state = regime.get("current_regime", "Unknown")
        regime_conf = regime.get("confidence", 0.5)
        
        # Base Prior anchors slightly towards long-term trend
        prior_bull = 0.5
        if current_close > ema_50:
            prior_bull = 0.55
        elif current_close < ema_50:
            prior_bull = 0.45
            
        # Evidence 1: Fast Trend (EMA Cross) -> Gentle update
        if ema_fast > ema_slow:
            prior_bull = (0.6 * prior_bull) / ((0.6 * prior_bull) + (0.4 * (1-prior_bull)))
        else:
            prior_bull = (0.4 * prior_bull) / ((0.4 * prior_bull) + (0.6 * (1-prior_bull)))
            
        # Evidence 2: MACD Momentum
        if macd_hist > 0:
            prior_bull = (0.6 * prior_bull) / ((0.6 * prior_bull) + (0.4 * (1-prior_bull)))
        elif macd_hist < 0:
            prior_bull = (0.4 * prior_bull) / ((0.4 * prior_bull) + (0.6 * (1-prior_bull)))

        # Evidence 3: Regime
        if regime_state == "Bull":
            adj_conf = 0.5 + (regime_conf * 0.2) # Max 0.7 impact
            prior_bull = (adj_conf * prior_bull) / ((adj_conf * prior_bull) + ((1-adj_conf) * (1-prior_bull)))
        elif regime_state == "Bear":
            adj_conf = 0.5 + (regime_conf * 0.2)
            prior_bull = ((1-adj_conf) * prior_bull) / (((1-adj_conf) * prior_bull) + (adj_conf * (1-prior_bull)))
            
        # Evidence 4: Strategy logic
        action = "HOLD"
        
        if strategy == "nova": # Momentum Breakout
            if prior_bull > 0.65 and rsi < 75 and ema_fast > ema_slow:
                action = "BUY"
            elif prior_bull < 0.35 and rsi > 25 and ema_fast < ema_slow:
                action = "SELL"
                
        elif strategy == "piggy": # Mean Reversion
            if rsi < 30 and regime_state != "Bear":
                action = "BUY"
                prior_bull = max(prior_bull, 0.6) 
            elif rsi > 70 and regime_state != "Bull":
                action = "SELL"
                prior_bull = min(prior_bull, 0.4)
                
        elif strategy == "limroy": # Statistical Arbitrage
            if prior_bull > 0.6 and rsi > 40: action = "BUY"
            elif prior_bull < 0.4 and rsi < 60: action = "SELL"
            
        elif strategy == "dejavu": # HMM Pattern matching
            if regime_state == "Bull" and rsi < 65: action = "BUY"
            elif regime_state == "Bear" and rsi > 35: action = "SELL"
            
        elif strategy == "medallion": # Master Ensemble
            curvature = regime.get("curvature_value", regime.get("cs_5d", 0))
            is_break = regime.get("structural_break", False)
            berlekamp_up = regime.get("berlekamp_up", 0.5)
            
            if is_break:
                medallion_prior = 0.5
            else:
                medallion_prior = prior_bull
                
            # Chern-Simons Gauge Update
            if curvature > 0: medallion_prior = min(medallion_prior + 0.1, 0.95)
            elif curvature < 0: medallion_prior = max(medallion_prior - 0.1, 0.05)
            
            # Berlekamp Update
            if berlekamp_up == 1: medallion_prior = min(medallion_prior + 0.1, 0.95)
            elif berlekamp_up == 0: medallion_prior = max(medallion_prior - 0.1, 0.05)
            
            if medallion_prior > 0.70: action = "BUY"
            elif medallion_prior < 0.30: action = "SELL"
            
            prior_bull = medallion_prior
                
        else: # Default
            if prior_bull > 0.7: action = "BUY"
            elif prior_bull < 0.3: action = "SELL"
            
        actual_confidence = prior_bull if prior_bull >= 0.5 else (1 - prior_bull)
        
        return {
            "strategy": strategy,
            "action": action,
            "confidence": float(actual_confidence),
            "bayesian_prob_bull": float(prior_bull),
            "regime": regime_state
        }

class BacktestEngine:
    def __init__(self):
        pass
        
    def run(self, df: pd.DataFrame, strategy: str, cash: float, commission: float, params: dict = None) -> dict:
        """
        Mock implementation of backtesting wrapper.
        In full implementation, this uses Backtesting.py
        """
        # We would define the strategy class for backtesting.py here
        # For now, return mock metrics to test the frontend integration
        
        return {
            "metrics": {
                "Return [%]": 14.5,
                "Buy & Hold Return [%]": 8.2,
                "Sharpe Ratio": 1.2,
                "Max Drawdown [%]": -12.4,
                "Win Rate [%]": 58.3,
                "Trades": 42
            },
            "equity_curve": [], # Would be a list of dicts with time/equity
            "trades": [] # List of trade dicts
        }
