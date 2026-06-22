import os
import json
import time
from datetime import datetime
from portfolio import Portfolio
from risk_manager import RiskManager

SYMBOLS = ["BTCUSD", "XAUUSD"]
TIMEFRAME = "1h" # We trade the 1h to survive broker commissions

def run_execution_engine():
    print("Initializing Medallion Paper Trading Execution Daemon...")
    portfolio = Portfolio(initial_balance=100.0)
    risk_manager = RiskManager(kelly_fraction=0.5) # Half-Kelly
    
    print(f"Starting Balance: ${portfolio.get_balance():.2f}")
    
    while True:
        try:
            for symbol in SYMBOLS:
                json_path = f"/tmp/latest_matrix_{symbol}.json"
                if not os.path.exists(json_path):
                    continue
                    
                with open(json_path, "r") as f:
                    try:
                        data = json.load(f)
                    except:
                        continue
                        
                matrix = data.get("matrix", {})
                tf_data = matrix.get(TIMEFRAME, {})
                if not tf_data:
                    continue
                    
                current_price = tf_data.get("current_price")
                sde_forecast = tf_data.get("sde_forecast")
                signals = tf_data.get("signals", {})
                medallion = signals.get("medallion", {})
                
                action = medallion.get("action", "HOLD")
                confidence = medallion.get("confidence", 0.5)
                raw_kelly = tf_data.get("kelly_recommended_pct", 0.0)
                
                # Check for existing position
                position = portfolio.get_position(symbol)
                
                if position:
                    # Holding Algorithm & Exit/Stop Algorithm
                    should_close, reason = risk_manager.check_stop_loss(position, current_price, confidence)
                    
                    # Also exit if SDE forecast has been reached/crossed (mean reversion satisfied)
                    # BUT ONLY IF we are actually in profit to cover fees!
                    if not should_close:
                        if position['direction'] == "BUY" and current_price >= sde_forecast:
                            pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                            if pnl_pct > 0.0025: # 0.25% to clear 0.2% fees + slippage
                                should_close = True
                                reason = "SDE Target Reached (In Profit)"
                        elif position['direction'] == "SELL" and current_price <= sde_forecast:
                            pnl_pct = (position['entry_price'] - current_price) / position['entry_price']
                            if pnl_pct > 0.0025:
                                should_close = True
                                reason = "SDE Target Reached (In Profit)"
                            
                    # Exit if signal completely flips
                    if not should_close:
                        if position['direction'] == "BUY" and action == "SELL" and confidence > 0.6:
                            should_close = True
                            reason = "Signal Flipped to SELL"
                        elif position['direction'] == "SELL" and action == "BUY" and confidence > 0.6:
                            should_close = True
                            reason = "Signal Flipped to BUY"
                            
                    if should_close:
                        # Apply slippage on exit
                        executed_price = risk_manager.apply_slippage(current_price, "SELL" if position['direction'] == "BUY" else "BUY")
                        portfolio.close_position(symbol, executed_price, reason)
                
                else:
                    # Entry Algorithm
                    # We enter if Medallion gives a high conviction signal
                    if action in ["BUY", "SELL"] and confidence >= 0.75:
                        # FEE-AWARE Expected Value: Ensure target is far enough away to cover 0.22% round-trip costs
                        expected_move_pct = abs(sde_forecast - current_price) / current_price
                        
                        if expected_move_pct > 0.003: # Must expect at least 0.30% move
                            # Check SDE validity
                            if action == "BUY" and sde_forecast > current_price:
                                margin_usd, leveraged_size_usd, qty, fee_usd = risk_manager.calculate_position_size(portfolio.get_balance(), raw_kelly, symbol, current_price)
                                
                                if margin_usd > 0:
                                    # Execute Trade
                                    executed_price = risk_manager.apply_slippage(current_price, action)
                                    portfolio.open_position(symbol, action, executed_price, margin_usd, leveraged_size_usd, qty, raw_kelly, confidence, fee_usd)
                                
                            elif action == "SELL" and sde_forecast < current_price:
                                margin_usd, leveraged_size_usd, qty, fee_usd = risk_manager.calculate_position_size(portfolio.get_balance(), raw_kelly, symbol, current_price)
                                
                                if margin_usd > 0:
                                    executed_price = risk_manager.apply_slippage(current_price, action)
                                    portfolio.open_position(symbol, action, executed_price, margin_usd, leveraged_size_usd, qty, raw_kelly, confidence, fee_usd)
                            
            time.sleep(1) # High frequency polling
            
        except Exception as e:
            print(f"[ERROR] Execution Engine Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run_execution_engine()
