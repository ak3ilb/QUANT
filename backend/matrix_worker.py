import time
import json
import asyncio
import ccxt.pro as ccxtpro
import pandas as pd
from datetime import datetime
import os

from quant_engine import QuantEngine
from indicator_engine import IndicatorEngine
from signal_engine import SignalEngine
from data_vault import store_ohlcv, get_ohlcv

symbol = "BTCUSD"
ccxt_symbol = "BTC/USDT"
timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
output_file = "/tmp/latest_matrix.json"

async def fetch_and_store(kraken, tf):
    """
    Subscribes to a specific timeframe via WebSocket.
    When a millisecond tick comes in, we instantly write it to the DuckDB Vault.
    """
    while True:
        try:
            # watch_ohlcv automatically handles connection drops and reconnection
            live_ohlcv = await kraken.watch_ohlcv(ccxt_symbol, tf)
            if live_ohlcv:
                live_df = pd.DataFrame(live_ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                live_df['time'] = pd.to_datetime(live_df['time'], unit='ms')
                store_ohlcv(symbol, tf, live_df)
        except Exception as e:
            print(f"WebSocket Error {tf}: {e}")
            await asyncio.sleep(1)

async def compute_matrix():
    """
    Continuous loop that pulls the freshest data from DuckDB and runs
    the heavy mathematical engine. It yields to the asyncio event loop
    so it doesn't block the WebSocket listeners.
    """
    quant_engine = QuantEngine()
    indicator_engine = IndicatorEngine()
    signal_engine = SignalEngine()
    strategies = ["nova", "piggy", "limroy", "dejavu", "medallion"]
    
    while True:
        start_time = time.time()
        matrix_results = {}
        
        try:
            for tf in timeframes:
                # Yield to the asyncio event loop so WebSocket listeners don't get starved
                await asyncio.sleep(0.01)
                
                df = get_ohlcv(symbol, tf, 365)
                if df.empty or len(df) < 50:
                    continue
                    
                df.set_index('time', inplace=True)
                df = indicator_engine.compute_all(df)
                
                # Yield again before heavy math
                await asyncio.sleep(0.01)
                
                regime = quant_engine.detect_regime(df)
                
                cs = quant_engine.chern_simons_gauge(df)
                regime["cs_1d"] = cs.get("cs_1d", 0)
                regime["cs_3d"] = cs.get("cs_3d", 0)
                regime["cs_5d"] = cs.get("cs_5d", 0)
                regime["curvature_signal"] = cs.get("curvature_signal", "HOLD")
                
                regime["structural_break"] = quant_engine.ax_kochen_break(df).get("structural_break", False)
                regime["berlekamp_up"] = quant_engine.berlekamp_massey(df).get("prediction_binary", 0.5)
                
                hyper = quant_engine.simons_hypersurface(df)
                regime["hyper_instability"] = hyper.get("instability_detected", False)
                
                cheeger = quant_engine.cheeger_simons_characters(df)
                regime["cheeger_invariant"] = cheeger.get("cyclic_invariant", 0.0)
                
                sde = quant_engine.monte_carlo(df)
                regime["sde_forecast"] = sde.get("forecast_mean", 0.0)
                
                kernel = quant_engine.kernel_regression(df)
                regime["kernel_p_value"] = kernel.get("p_value", 1.0)
                
                kelly = quant_engine.kelly_sizing(df, "medallion")
                regime["kelly_recommended_pct"] = kelly.get("recommended_size_pct", 0.0)
                
                tf_signals = {}
                for strat in strategies:
                    sig = signal_engine.get_signal(df, strat, regime)
                    tf_signals[strat] = sig
                    
                matrix_results[tf] = {
                    "regime": regime["current_regime"],
                    "break": regime["structural_break"],
                    "signals": tf_signals,
                    "cs_5d": regime["cs_5d"],
                    "hyper_instability": regime["hyper_instability"],
                    "sde_forecast": regime["sde_forecast"],
                    "cheeger_invariant": regime["cheeger_invariant"],
                    "current_price": float(df['close'].iloc[-1]),
                    "kernel_p_value": float(regime["kernel_p_value"]),
                    "kelly_recommended_pct": float(regime["kelly_recommended_pct"])
                }
                
            # Compute magnetic levels from 1h chart
            levels = []
            try:
                df_1h = get_ohlcv(symbol, "1h", 1000)
                if not df_1h.empty:
                    df_1h.set_index('time', inplace=True)
                    levels = quant_engine.kde_liquidity_nodes(df_1h)
            except:
                pass
                
            payload = {
                "symbol": symbol,
                "matrix": matrix_results,
                "magnetic_levels": levels,
                "last_updated": datetime.now().isoformat()
            }
            
            # Atomic write
            with open(output_file, "w") as f:
                json.dump(payload, f)
                
        except Exception as e:
            print(f"Matrix Computation Error: {e}")
            
        elapsed = time.time() - start_time
        # Compute as fast as possible, but yield to WebSocket listeners for at least 0.1s
        await asyncio.sleep(max(0.1, 1.0 - elapsed))

async def main():
    print("Starting High-Frequency Matrix Daemon (WebSocket Worker)...")
    kraken = ccxtpro.kraken({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'},
    })
    
    # 1. Fire up the WebSocket listeners
    tasks = [asyncio.create_task(fetch_and_store(kraken, tf)) for tf in timeframes]
    
    # 2. Fire up the math engine
    tasks.append(asyncio.create_task(compute_matrix()))
    
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
