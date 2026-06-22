import random

class RiskManager:
    def __init__(self, kelly_fraction=0.5):
        # Medallion rarely used full Kelly, usually Half-Kelly or Quarter-Kelly to reduce volatility
        self.kelly_fraction = kelly_fraction 

    def calculate_position_size(self, balance, raw_kelly_pct, symbol, price):
        """
        Takes the raw kelly % calculated by the Quant Engine and applies fractional Kelly,
        100x leverage, and strict lot sizing.
        """
        # Ensure we don't bet negative or > 100%
        kelly = max(0.0, min(1.0, raw_kelly_pct / 100.0))
        
        # Apply fractional Kelly
        fractional_kelly = kelly * self.kelly_fraction
        
        # Calculate margin allocation (how much of our $100 we put up)
        margin_usd = balance * fractional_kelly
        
        # Apply 100x Leverage to get true position size
        leveraged_size_usd = margin_usd * 100.0
        
        # Calculate raw quantity
        raw_qty = leveraged_size_usd / price
        
        # Apply strict lot sizing
        if symbol == "XAUUSD":
            # Gold typically requires 0.01 lot minimums (1 oz)
            qty = max(0.01, round(raw_qty, 2))
        else: # BTCUSD
            # Crypto typically allows 0.001 fractional minimums
            qty = max(0.001, round(raw_qty, 3))
            
        # Re-calculate actual leveraged size based on rounded qty
        actual_leveraged_size = qty * price
        
        # The margin we actually lock up is the actual size / 100
        actual_margin_usd = actual_leveraged_size / 100.0
        
        # If the minimum lot requires more margin than we have, reject trade
        if actual_margin_usd > balance:
            return 0, 0, 0, 0
            
        # Calculate Commission Fee (0.1% of LEVERAGED size)
        fee_usd = actual_leveraged_size * 0.001
        
        return actual_margin_usd, actual_leveraged_size, qty, fee_usd

    def apply_slippage(self, price, direction, volatility_atr=None):
        """
        Simulate "The Devil" (execution slippage). 
        Buys execute slightly higher, Sells execute slightly lower.
        """
        # Base slippage of 0.01%
        base_slippage = 0.0001 
        
        # If volatile, slippage is higher. We use a randomized factor to simulate order slicing spread
        spread_factor = random.uniform(0.5, 2.0)
        
        slippage_pct = base_slippage * spread_factor
        
        if direction == "BUY":
            executed_price = price * (1 + slippage_pct)
        else:
            executed_price = price * (1 - slippage_pct)
            
        return executed_price
        
    def check_stop_loss(self, position, current_price, current_confidence):
        """
        Self-Correction / Drop Bleeding Signals.
        Returns (should_close, reason)
        """
        # 1. Probability Decay (Signal flips or confidence drops below 50%)
        # If the Bayesian engine loses faith, we exit immediately.
        if current_confidence < 0.50:
            return True, "Confidence Decay < 50%"
            
        # 2. Hard Stop Loss (e.g., 2% drop on the asset)
        entry_price = position['entry_price']
        if position['direction'] == "BUY":
            pnl_pct = (current_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - current_price) / entry_price
            
        if pnl_pct <= -0.02:
            return True, "Hard Stop Loss Hit (-2%)"
            
        return False, None
