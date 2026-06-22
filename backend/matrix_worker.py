import time
import json
import asyncio
import pandas as pd
from datetime import datetime
import os
import requests
import traceback
import sys

from quant_engine import QuantEngine
from indicator_engine import IndicatorEngine
from signal_engine import STRATEGIES, SignalEngine
from data_vault import store_ohlcv, get_ohlcv
from algorithms.candlestick_patterns import detect_candlestick_patterns

SYMBOLS = ["BTCUSD"]
TV_SYMBOLS = {"BTCUSD": "BINANCE:BTCUSD"}
TIMEFRAMES = {"1h": "60"} # Only extract 1h since we upgraded our execution model
CDP_URL = "http://localhost:3001"

async def fetch_and_store_live(symbol, tf_label, tv_tf):
    try:
        tv_symbol = TV_SYMBOLS.get(symbol, symbol)
        # We need the last few candles to compute patterns, so we use /extract/history
        # The new CDP bridge handles symbol/timeframe switching and waiting automatically
        params = {"symbol": tv_symbol, "resolution": tv_tf, "maxBars": 365, "settleMs": 1500}
        resp = requests.get(f"{CDP_URL}/extract/history", params=params, timeout=30)
        data = resp.json()
        if 'bars' in data and len(data['bars']) > 0:
            df = pd.DataFrame(data['bars'])
            if df['time'].iloc[-1] > 20000000000:
                df['time'] = pd.to_datetime(df['time'], unit='ms')
            else:
                df['time'] = pd.to_datetime(df['time'], unit='s')
            df.attrs["source"] = data.get("source", "tradingview_cdp")
            df.attrs["actual_symbol"] = data.get("actualSymbol")
            df.attrs["actual_resolution"] = data.get("actualResolution")
            df.attrs["extracted_at"] = data.get("extractedAt")
                
            # Compute real-time candlestick patterns
            df = detect_candlestick_patterns(df)
            
            # Store all visible bars to ensure full data consistency and no gaps
            store_ohlcv(symbol, tf_label, df)
            return True
    except Exception as e:
        print(f"Error fetching live for {symbol} {tf_label}: {e}", flush=True)
    return False

loop_counter = 0

async def compute_matrix():
    quant_engine = QuantEngine()
    indicator_engine = IndicatorEngine()
    signal_engine = SignalEngine()


    global loop_counter
    while True:
        try:
            start_time = time.time()
            loop_counter += 1
            
            for symbol in SYMBOLS:
                # Check for history_sync lock
                while os.path.exists("/tmp/history_sync.lock"):
                    print("Waiting for history_sync to finish deep extraction...")
                    time.sleep(5)
                    
                # Load existing matrix if it exists to preserve higher timeframes
                existing_data = {}
                json_path = f"/tmp/latest_matrix_{symbol}.json"
                if os.path.exists(json_path):
                    try:
                        with open(json_path, "r") as f:
                            existing_data = json.load(f)
                    except Exception:
                        pass
                        
                matrix_results = existing_data.get("matrix", {})
                levels = existing_data.get("liquidity_levels", [])
                
                for tf_label, tv_tf in TIMEFRAMES.items():
                    # Always fetch our primary trading timeframe to keep pricing live
                    if tf_label == "1h":
                        should_fetch = True
                        
                    # If we don't have this timeframe at all, force fetch it
                    if tf_label not in matrix_results:
                        should_fetch = True
                        
                    if not should_fetch:
                        print(f"[{datetime.now()}] Skipping {symbol} - {tf_label} (Cached)", flush=True)
                        continue
                        
                    print(f"[{datetime.now()}] Processing {symbol} - {tf_label}...", flush=True)
                    await fetch_and_store_live(symbol, tf_label, tv_tf)
                    
                    # After storing, calculate matrix as usual
                    try:
                        df = get_ohlcv(symbol, tf_label, 365)
                        if df.empty or len(df) < 50:
                            continue
                            
                        df.set_index('time', inplace=True)
                        df = indicator_engine.compute_all(df)
                        
                        regime = quant_engine.detect_regime(df)
                        cs = quant_engine.chern_simons_gauge(df)
                        regime["cs_1d"] = cs.get("cs_1d", 0)
                        regime["cs_3d"] = cs.get("cs_3d", 0)
                        regime["cs_5d"] = cs.get("cs_5d", 0)
                        regime["curvature_value"] = cs.get("curvature_value", regime["cs_5d"])
                        regime["curvature_signal"] = cs.get("curvature_signal", "HOLD")
                        
                        regime["structural_break"] = quant_engine.ax_kochen_break(df).get("structural_break", False)
                        regime["berlekamp_up"] = quant_engine.berlekamp_massey(df).get("prediction_binary", 0.5)
                        regime["hyper_instability"] = quant_engine.simons_hypersurface(df).get("instability_detected", False)
                        regime["cheeger_invariant"] = quant_engine.cheeger_simons_characters(df).get("cyclic_invariant", 0.0)
                        regime["sde_forecast"] = quant_engine.monte_carlo(df).get("forecast_mean", 0.0)
                        regime["kernel_p_value"] = quant_engine.kernel_regression(df).get("p_value", 1.0)
                        regime["kelly_recommended_pct"] = quant_engine.kelly_sizing(df, "medallion").get("recommended_size_pct", 0.0)
                    
                        tf_signals = {}
                        for strat in STRATEGIES:
                            tf_signals[strat] = signal_engine.get_signal(df, strat, regime)
                            
                        matrix_results[tf_label] = {
                            "regime": regime["current_regime"],
                            "break": regime["structural_break"],
                            "signals": tf_signals,
                            "cs_5d": regime["cs_5d"],
                            "curvature_value": regime["curvature_value"],
                            "curvature_signal": regime["curvature_signal"],
                            "hyper_instability": regime["hyper_instability"],
                            "sde_forecast": regime["sde_forecast"],
                            "cheeger_invariant": regime["cheeger_invariant"],
                            "current_price": float(df['close'].iloc[-1]),
                            "kernel_p_value": float(regime["kernel_p_value"]),
                            "kelly_recommended_pct": float(regime["kelly_recommended_pct"]),
                            "active_patterns": str(df['active_patterns'].iloc[-1]) if 'active_patterns' in df.columns else ""
                        }
                        
                        # Also compute magnetic levels for 1h
                        if tf_label == "1h":
                            levels = quant_engine.kde_liquidity_nodes(df)
                        
                    except Exception as e:
                        print(f"Matrix Compute Error {symbol} {tf_label}: {e}", flush=True)
                    
                # Output matrix file specifically for this symbol
                payload = {
                    "symbol": symbol,
                    "matrix": matrix_results,
                    "magnetic_levels": levels,
                    "last_updated": datetime.now().isoformat()
                }
                output_file = f"/tmp/latest_matrix_{symbol}.json"
                tmp_output_file = f"{output_file}.tmp"
                try:
                    with open(tmp_output_file, "w") as f:
                        json.dump(payload, f)
                    os.replace(tmp_output_file, output_file)
                    print(f"Updated {output_file}", flush=True)
                except Exception as e:
                    if os.path.exists(tmp_output_file):
                        os.remove(tmp_output_file)
                    print(f"Failed to write json for {symbol}: {e}", flush=True)
            
            # Wait 30 seconds before re-calculating the 1h matrix to avoid browser spam
            time.sleep(30)
            
        except Exception as e:
            print(f"Main Loop Error: {e}", flush=True)
            time.sleep(1)
async def main():
    print("Starting High-Frequency Matrix Daemon via TradingView CDP", flush=True)
    await compute_matrix()

if __name__ == "__main__":
    asyncio.run(main())
