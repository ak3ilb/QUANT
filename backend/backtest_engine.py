import sys
import pandas as pd
from datetime import datetime
from data_vault import get_ohlcv
from signal_engine import SignalEngine
from indicator_engine import IndicatorEngine
from paper_trader.risk_manager import RiskManager
from quant_engine import QuantEngine

def run_backtest(symbol="BTCUSD", tf="5m"):
    print(f"[{datetime.now()}] Initializing Medallion Backtest Engine for {symbol} {tf}...")
    
    # 1. Load historical data
    df = get_ohlcv(symbol, tf)
    if df.empty:
        print(f"ERROR: No historical data found for {symbol} {tf} in DuckDB.")
        return
        
    print(f"Loaded {len(df)} historical candles from {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
    
    # 2. Initialize Engines
    indicator_engine = IndicatorEngine()
    signal_engine = SignalEngine()
    quant_engine = QuantEngine()
    risk_manager = RiskManager(kelly_fraction=0.5)
    
    # 3. State Tracking
    balance = 100.0
    positions = [] # Current open positions
    trade_history = []
    
    total_fees_paid = 0.0
    wins = 0
    losses = 0
    
    # We need a rolling window to feed the engines. The engines expect a dataframe.
    # To simulate realtime, we should feed the dataframe incrementally.
    # To optimize, we can calculate indicators on the whole dataframe first, but the Matrix Worker
    # calculates probabilities based on the latest slices.
    # SignalEngine's get_signal operates on the dataframe passed to it.
    
    print("\nPre-computing topological indicators across entire dataset (Look-ahead safe)...")
    df = indicator_engine.compute_all(df)
    
    print("\nStarting chronological simulation...")
    
    # We start from the last 50 candles for a quick backtest to avoid hours of Monte Carlo calculations
    start_idx = max(50, len(df) - 50)
    
    for i in range(start_idx, len(df)):
        print(f"Backtesting bar {i}/{len(df)}...", end='\r', flush=True)
        # Slice data up to the current candle to simulate "now"
        current_slice = df.iloc[:i].copy()
        current_row = df.iloc[i-1]
        
        current_price = current_row['close']
        current_time = current_row['time']
        
        # 1. Evaluate Open Positions (Stop Loss / Take Profit / Signal Flips)
        for pos in positions[:]:
            # Recalculate signal for exit logic
            sde_forecast = current_row.get('sde_forecast', current_price)
            # We don't recalculate the full matrix, we just check stop loss and hard SDE targets
            
            should_close = False
            reason = ""
            
            # Check SDE target
            if pos['direction'] == "BUY" and current_price >= sde_forecast:
                should_close, reason = True, "SDE Target Reached"
            elif pos['direction'] == "SELL" and current_price <= sde_forecast:
                should_close, reason = True, "SDE Target Reached"
                
            # Check Risk Manager Stop Loss
            if not should_close:
                stop_hit, stop_reason = risk_manager.check_stop_loss(pos, current_price, pos['confidence'])
                if stop_hit:
                    should_close, reason = True, stop_reason
            
            if should_close:
                # Execute Exit
                executed_price = risk_manager.apply_slippage(current_price, "SELL" if pos['direction'] == "BUY" else "BUY")
                
                # Exit fee
                exit_value = pos['qty'] * executed_price
                exit_fee = exit_value * 0.001
                total_fees_paid += exit_fee
                pos['fees_paid'] += exit_fee
                
                if pos['direction'] == "BUY":
                    gross_pnl = (executed_price - pos['entry_price']) * pos['qty']
                else:
                    gross_pnl = (pos['entry_price'] - executed_price) * pos['qty']
                    
                net_pnl = gross_pnl - pos['fees_paid']
                balance += (pos['margin_usd'] + net_pnl)
                
                if net_pnl > 0:
                    wins += 1
                else:
                    losses += 1
                    
                trade_history.append({
                    "direction": pos['direction'],
                    "entry_time": pos['entry_time'],
                    "exit_time": current_time,
                    "net_pnl": net_pnl,
                    "fees_paid": pos['fees_paid']
                })
                
                positions.remove(pos)
        
        # 2. Look for Entries if no position is open (Simplification: 1 position max)
        if len(positions) == 0:
            # Replicate the matrix_worker logic to compute regime
            regime = quant_engine.detect_regime(current_slice)
            cs = quant_engine.chern_simons_gauge(current_slice)
            regime["cs_1d"] = cs.get("cs_1d", 0)
            regime["cs_3d"] = cs.get("cs_3d", 0)
            regime["cs_5d"] = cs.get("cs_5d", 0)
            regime["curvature_value"] = cs.get("curvature_value", regime["cs_5d"])
            regime["curvature_signal"] = cs.get("curvature_signal", "HOLD")
            
            regime["structural_break"] = quant_engine.ax_kochen_break(current_slice).get("structural_break", False)
            regime["berlekamp_up"] = quant_engine.berlekamp_massey(current_slice).get("prediction_binary", 0.5)
            regime["hyper_instability"] = quant_engine.simons_hypersurface(current_slice).get("instability_detected", False)
            regime["cheeger_invariant"] = quant_engine.cheeger_simons_characters(current_slice).get("cyclic_invariant", 0.0)
            sde_forecast = quant_engine.monte_carlo(current_slice).get("forecast_mean", 0.0)
            regime["sde_forecast"] = sde_forecast
            regime["kernel_p_value"] = quant_engine.kernel_regression(current_slice).get("p_value", 1.0)
            raw_kelly = quant_engine.kelly_sizing(current_slice, "medallion").get("recommended_size_pct", 0.0)
            regime["kelly_recommended_pct"] = raw_kelly
        
            # Generate Signal
            medallion_signal = signal_engine.get_signal(current_slice, "medallion", regime)
            action = medallion_signal.get("action", "HOLD")
            confidence = medallion_signal.get("confidence", 0.5)
                
            if action in ["BUY", "SELL"] and confidence >= 0.85:
                if (action == "BUY" and sde_forecast > current_price) or (action == "SELL" and sde_forecast < current_price):
                    margin_usd, leveraged_size_usd, qty, entry_fee = risk_manager.calculate_position_size(
                        balance, raw_kelly, symbol, current_price
                    )
                    
                    if margin_usd > 0:
                        executed_price = risk_manager.apply_slippage(current_price, action)
                        
                        balance -= (margin_usd + entry_fee)
                        total_fees_paid += entry_fee
                        
                        positions.append({
                            "direction": action,
                            "entry_time": current_time,
                            "entry_price": executed_price,
                            "margin_usd": margin_usd,
                            "leveraged_size": leveraged_size_usd,
                            "qty": qty,
                            "confidence": confidence,
                            "fees_paid": entry_fee
                        })
    
    # Force close any open positions at the end of the simulation
    for pos in positions:
        executed_price = df.iloc[-1]['close']
        exit_value = pos['qty'] * executed_price
        exit_fee = exit_value * 0.001
        total_fees_paid += exit_fee
        pos['fees_paid'] += exit_fee
        
        if pos['direction'] == "BUY":
            gross_pnl = (executed_price - pos['entry_price']) * pos['qty']
        else:
            gross_pnl = (pos['entry_price'] - executed_price) * pos['qty']
            
        net_pnl = gross_pnl - pos['fees_paid']
        balance += (pos['margin_usd'] + net_pnl)
        
        if net_pnl > 0:
            wins += 1
        else:
            losses += 1
            
        trade_history.append({
            "direction": pos['direction'],
            "entry_time": pos['entry_time'],
            "exit_time": df.iloc[-1]['time'],
            "net_pnl": net_pnl,
            "fees_paid": pos['fees_paid']
        })

    # Print Report
    print("\n" + "="*50)
    print("      MEDALLION BACKTEST REPORT")
    print("="*50)
    print(f"Symbol:          {symbol} ({tf})")
    print(f"Total Candles:   {len(df)}")
    print(f"Start Date:      {df['time'].iloc[0]}")
    print(f"End Date:        {df['time'].iloc[-1]}")
    print("-" * 50)
    print(f"Starting Bal:    $100.00")
    print(f"Ending Bal:      ${balance:.2f}")
    print(f"Net PNL:         ${balance - 100.00:.2f}")
    print(f"Total Fees Paid: ${total_fees_paid:.2f}")
    print("-" * 50)
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
    print(f"Total Trades:    {total_trades}")
    print(f"Wins:            {wins}")
    print(f"Losses:          {losses}")
    print(f"Win Rate:        {win_rate:.2f}%")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_backtest("BTCUSD", "1h")
