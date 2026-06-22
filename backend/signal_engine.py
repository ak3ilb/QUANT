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
            
        current_close = float(df['close'].iloc[-1])
        active_patterns = str(df['active_patterns'].iloc[-1]).lower() if 'active_patterns' in df.columns else ""
        
        # Mathematical Invariants
        regime_state = regime.get("current_regime", "Unknown")
        regime_conf = float(regime.get("confidence", 0.5))
        sde_forecast = float(regime.get("sde_forecast", current_close))
        curvature = float(regime.get("curvature_value", regime.get("cs_5d", 0)))
        is_break = bool(regime.get("structural_break", False))
        berlekamp_up = float(regime.get("berlekamp_up", 0.5))
        cheeger = float(regime.get("cheeger_invariant", 0.5))
        p_value = float(regime.get("kernel_p_value", 1.0))
        
        # Base Prior anchors strictly at 0.5 (perfect neutrality)
        prior_bull = 0.5
        
        # Candlestick Confirmation Penalties
        is_bull_pattern = "bull" in active_patterns or "hammer" in active_patterns or "morning" in active_patterns
        is_bear_pattern = "bear" in active_patterns or "shooting" in active_patterns or "evening" in active_patterns
            
        action = "HOLD"
        
        # Strategy 1: Nova (Momentum Breakout -> Ax-Kochen + Chern-Simons)
        if strategy == "nova":
            if is_break and curvature > 0:
                prior_bull = 0.8
            elif is_break and curvature < 0:
                prior_bull = 0.2
            elif curvature > 500: # High upward acceleration
                prior_bull = 0.65
            elif curvature < -500:
                prior_bull = 0.35
                
        # Strategy 2: Piggy (Mean Reversion -> Ornstein-Uhlenbeck SDE Divergence)
        elif strategy == "piggy":
            # If SDE heavily diverges from current close
            divergence_pct = ((sde_forecast - current_close) / current_close) * 100
            if divergence_pct > 0.5 and regime_state != "Bull": # Snap upward
                prior_bull = 0.75
            elif divergence_pct < -0.5 and regime_state != "Bear": # Snap downward
                prior_bull = 0.25
                
        # Strategy 3: Limroy (Statistical Arbitrage -> Berlekamp-Massey + Kernel Regression)
        elif strategy == "limroy":
            # p_value < 0.05 implies high confidence in the localized kernel
            if p_value < 0.05:
                if berlekamp_up > 0.8:
                    prior_bull = 0.8
                elif berlekamp_up < 0.2:
                    prior_bull = 0.2
            else:
                prior_bull = 0.5 # Too much noise to stat arb
            
        # Strategy 4: Dejavu (HMM Pattern Matching + Candlesticks)
        elif strategy == "dejavu":
            if regime_state == "Bull":
                prior_bull = 0.6 + (regime_conf * 0.2)
            elif regime_state == "Bear":
                prior_bull = 0.4 - (regime_conf * 0.2)
                
        # Strategy 5: Medallion (Master Unified Ensemble)
        elif strategy == "medallion":
            # Combine all mathematical topology
            medallion_prior = 0.5
            if is_break: medallion_prior += 0.15 if curvature > 0 else -0.15
            if berlekamp_up > 0.8: medallion_prior += 0.1
            if berlekamp_up < 0.2: medallion_prior -= 0.1
            if sde_forecast > current_close: medallion_prior += 0.1
            if sde_forecast < current_close: medallion_prior -= 0.1
            
            # Constrain to strict limits before candlestick adjustment
            prior_bull = max(0.01, min(0.99, medallion_prior))

        # GLOBAL Candlestick dampener for ALL strategies
        if is_bull_pattern and prior_bull > 0.5:
            prior_bull = min(prior_bull + 0.1, 0.99) # Confirm the breakout
        elif is_bear_pattern and prior_bull > 0.5:
            prior_bull = 0.5 # Slash bullish confidence due to bear pattern at top
            
        if is_bear_pattern and prior_bull < 0.5:
            prior_bull = max(prior_bull - 0.1, 0.01) # Confirm the breakdown
        elif is_bull_pattern and prior_bull < 0.5:
            prior_bull = 0.5 # Slash bearish confidence due to bull pattern at bottom

        # Generate Action from pure math Bayesian posterior
        if prior_bull >= 0.65:
            action = "BUY"
        elif prior_bull <= 0.35:
            action = "SELL"
            
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
