import pandas as pd
import numpy as np

class StrategyRunner:
    def __init__(self):
        pass

class SignalEngine:
    def __init__(self):
        pass
        
    def get_signal(self, df: pd.DataFrame, strategy: str, regime: dict) -> dict:
        """
        Bayesian Signal Scorer
        Combines technicals with HMM regime and Bayesian prior updating
        """
        if len(df) < 50:
            return {"action": "HOLD", "confidence": 0}
            
        current_close = df['close'].iloc[-1]
        ema_fast = df['EMA_9'].iloc[-1] if 'EMA_9' in df.columns else current_close
        ema_slow = df['EMA_21'].iloc[-1] if 'EMA_21' in df.columns else current_close
        rsi = df['RSI_14'].iloc[-1] if 'RSI_14' in df.columns else 50
        
        regime_state = regime.get("current_regime", "Unknown")
        regime_conf = regime.get("confidence", 0.5)
        
        # Base Prior (50% neutral)
        prior_bull = 0.5
        
        # Evidence 1: Trend
        if ema_fast > ema_slow:
            # P(E|Bull) = 0.8, P(E|Bear) = 0.3
            prior_bull = (0.8 * prior_bull) / ((0.8 * prior_bull) + (0.3 * (1-prior_bull)))
        else:
            prior_bull = (0.3 * prior_bull) / ((0.3 * prior_bull) + (0.8 * (1-prior_bull)))
            
        # Evidence 2: Regime
        if regime_state == "Bull":
            prior_bull = (regime_conf * prior_bull) / ((regime_conf * prior_bull) + ((1-regime_conf) * (1-prior_bull)))
        elif regime_state == "Bear":
            prior_bull = ((1-regime_conf) * prior_bull) / (((1-regime_conf) * prior_bull) + (regime_conf * (1-prior_bull)))
            
        # Evidence 3: Strategy logic
        action = "HOLD"
        
        if strategy == "nova": # Momentum Breakout
            if prior_bull > 0.75 and rsi < 70 and ema_fast > ema_slow:
                action = "BUY"
            elif prior_bull < 0.25 and rsi > 30 and ema_fast < ema_slow:
                action = "SELL"
                
        elif strategy == "piggy": # Mean Reversion
            if rsi < 30 and regime_state != "Bear":
                action = "BUY"
                prior_bull = max(prior_bull, 0.7) # Boost confidence
            elif rsi > 70 and regime_state != "Bull":
                action = "SELL"
                prior_bull = min(prior_bull, 0.3)
                
        elif strategy == "limroy": # Statistical Arbitrage (Mocked)
            if prior_bull > 0.6 and rsi > 50: action = "BUY"
            elif prior_bull < 0.4 and rsi < 50: action = "SELL"
            
        elif strategy == "dejavu": # HMM Pattern matching (Mocked)
            if regime_state == "Bull": action = "BUY"
            elif regime_state == "Bear": action = "SELL"
            
        elif strategy == "medallion": # Master Ensemble
            # Retrieve advanced signals if passed through regime dict
            curvature = regime.get("curvature_value", 0)
            is_break = regime.get("structural_break", False)
            berlekamp_up = regime.get("berlekamp_up", 0.5)
            
            # The Bayesian network combines technicals, HMM, and Chern-Simons
            # If structural break (Ax-Kochen), we rely entirely on momentum & gauge
            if is_break:
                medallion_prior = 0.5
            else:
                medallion_prior = prior_bull
                
            # Chern-Simons Gauge Update
            if curvature > 0: medallion_prior = min(medallion_prior + 0.15, 0.99)
            elif curvature < 0: medallion_prior = max(medallion_prior - 0.15, 0.01)
            
            # Berlekamp Update
            if berlekamp_up == 1: medallion_prior = min(medallion_prior + 0.1, 0.99)
            elif berlekamp_up == 0: medallion_prior = max(medallion_prior - 0.1, 0.01)
            
            if medallion_prior > 0.65: action = "BUY"
            elif medallion_prior < 0.35: action = "SELL"
            
            prior_bull = medallion_prior
                
        else: # Default
            if prior_bull > 0.8: action = "BUY"
            elif prior_bull < 0.2: action = "SELL"
            
        # Calculate actual confidence even during a HOLD
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
