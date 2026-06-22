import time
import json
import asyncio
import random
import pandas as pd
from datetime import datetime
import os
import requests

from intelligence.context_builder import resolve_context, context_to_regime
from quant_engine import QuantEngine
from indicator_engine import IndicatorEngine
from signal_engine import STRATEGIES, SignalEngine
from data_vault import store_ohlcv, get_ohlcv
from algorithms.candlestick_patterns import detect_candlestick_patterns
from cdp_lock import cdp_lock, jittered_settle_ms

try:
    from tv_launcher import ensure_tradingview_ready
except ImportError:
    def ensure_tradingview_ready():
        return False

SYMBOLS = ["BTCUSD", "XAUUSD"]
PAIR_SYMBOLS = {"BTCUSD": "XAUUSD", "XAUUSD": "BTCUSD"}
TV_SYMBOLS = {"BTCUSD": "BINANCE:BTCUSD", "XAUUSD": "OANDA:XAUUSD"}
TIMEFRAMES = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "1D"}
CDP_URL = "http://localhost:3001"

loop_counter = 0
symbol_cycle_index = 0
cdp_backoff = 2


def cdp_healthy():
    try:
        resp = requests.get(f"{CDP_URL}/health", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def _bars_to_df(data):
    if 'bars' not in data or len(data['bars']) == 0:
        return None
    df = pd.DataFrame(data['bars'])
    if df['time'].iloc[-1] > 20000000000:
        df['time'] = pd.to_datetime(df['time'], unit='ms')
    else:
        df['time'] = pd.to_datetime(df['time'], unit='s')
    df.attrs["source"] = data.get("source", "tradingview_cdp")
    df.attrs["actual_symbol"] = data.get("actualSymbol")
    df.attrs["actual_resolution"] = data.get("actualResolution")
    df.attrs["extracted_at"] = data.get("extractedAt")
    return df


def _validate_identity(data, tv_symbol, tv_tf):
    if data.get("actualSymbol") != tv_symbol:
        raise ValueError(f"Symbol mismatch: {tv_symbol} vs {data.get('actualSymbol')}")
    if data.get("actualResolution") != tv_tf:
        raise ValueError(f"Resolution mismatch: {tv_tf} vs {data.get('actualResolution')}")


async def fetch_live_bars(symbol, tf_label, tv_tf):
    """Lightweight fetch for 1m/5m — lastbar + merge into vault."""
    global cdp_backoff
    tv_symbol = TV_SYMBOLS.get(symbol, symbol)
    try:
        with cdp_lock():
            resp = requests.get(
                f"{CDP_URL}/extract/lastbar",
                params={"symbol": tv_symbol, "resolution": tv_tf},
                timeout=20,
            )
        if resp.status_code != 200:
            return False, None
        data = resp.json()
        if data.get("error"):
            return False, None
        _validate_identity(data, tv_symbol, tv_tf)

        new_df = _bars_to_df(data)
        if new_df is None:
            return False, None

        existing = get_ohlcv(symbol, tf_label, 365)
        if not existing.empty:
            existing['time'] = pd.to_datetime(existing['time'])
            combined = pd.concat([existing, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=['time'], keep='last').sort_values('time')
            if len(combined) > 500:
                combined = combined.tail(500)
            df = combined
        else:
            # Need more history on first run
            with cdp_lock():
                hist = requests.get(
                    f"{CDP_URL}/extract/history",
                    params={
                        "symbol": tv_symbol,
                        "resolution": tv_tf,
                        "maxBars": 365,
                        "settleMs": jittered_settle_ms(),
                    },
                    timeout=30,
                )
            if hist.status_code == 200:
                hdata = hist.json()
                _validate_identity(hdata, tv_symbol, tv_tf)
                df = _bars_to_df(hdata)
                if df is None:
                    df = new_df
            else:
                df = new_df

        df = detect_candlestick_patterns(df)
        store_ohlcv(symbol, tf_label, df)
        cdp_backoff = 2
        return True, float(df['close'].iloc[-1])
    except Exception as e:
        print(f"Error fetching live bars for {symbol} {tf_label}: {e}", flush=True)
        cdp_backoff = min(cdp_backoff * 2, 60)
        return False, None


async def fetch_history_bars(symbol, tf_label, tv_tf):
    """Full history fetch for higher timeframes."""
    global cdp_backoff
    tv_symbol = TV_SYMBOLS.get(symbol, symbol)
    try:
        with cdp_lock():
            resp = requests.get(
                f"{CDP_URL}/extract/history",
                params={
                    "symbol": tv_symbol,
                    "resolution": tv_tf,
                    "maxBars": 365,
                    "settleMs": jittered_settle_ms(),
                },
                timeout=30,
            )
        if resp.status_code != 200:
            return False, None
        data = resp.json()
        if data.get("error"):
            return False, None
        _validate_identity(data, tv_symbol, tv_tf)

        df = _bars_to_df(data)
        if df is None:
            return False, None

        df = detect_candlestick_patterns(df)
        store_ohlcv(symbol, tf_label, df)
        cdp_backoff = 2
        return True, float(df['close'].iloc[-1])
    except Exception as e:
        print(f"Error fetching history for {symbol} {tf_label}: {e}", flush=True)
        cdp_backoff = min(cdp_backoff * 2, 60)
        return False, None


async def compute_matrix():
    global loop_counter, symbol_cycle_index, cdp_backoff

    quant_engine = QuantEngine()
    indicator_engine = IndicatorEngine()
    signal_engine = SignalEngine()

    while True:
        try:
            if not cdp_healthy():
                print("[MATRIX] CDP bridge unhealthy — attempting TV launch...", flush=True)
                ensure_tradingview_ready()
                await asyncio.sleep(cdp_backoff)
                cdp_backoff = min(cdp_backoff * 2, 60)
                continue

            loop_counter += 1
            symbol = SYMBOLS[symbol_cycle_index % len(SYMBOLS)]
            symbol_cycle_index += 1

            while os.path.exists("/tmp/history_sync.lock"):
                lock_age = 0
                try:
                    lock_age = time.time() - os.path.getmtime("/tmp/history_sync.lock")
                except OSError:
                    pass
                if lock_age > 1800:
                    print(f"[MATRIX] Stale history_sync.lock ({lock_age:.0f}s) — proceeding anyway", flush=True)
                    break
                print("Waiting for history_sync to finish deep extraction...", flush=True)
                await asyncio.sleep(5)

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
                should_fetch = False
                if tf_label in ["1m", "5m"]:
                    should_fetch = True
                elif tf_label == "15m" and loop_counter % 3 == 0:
                    should_fetch = True
                elif tf_label == "1h" and loop_counter % 6 == 0:
                    should_fetch = True
                elif tf_label in ["4h", "1d"] and loop_counter % 24 == 0:
                    should_fetch = True

                if tf_label not in matrix_results:
                    should_fetch = True

                if not should_fetch:
                    continue

                print(f"[{datetime.now()}] Processing {symbol} - {tf_label}...", flush=True)
                if tf_label in ["1m", "5m"]:
                    fetch_ok, live_price = await fetch_live_bars(symbol, tf_label, tv_tf)
                else:
                    fetch_ok, live_price = await fetch_history_bars(symbol, tf_label, tv_tf)

                if not fetch_ok:
                    live_price = None

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

                    bocpd = quant_engine.bocpd_break(df)
                    regime["structural_break"] = bocpd.get("structural_break", False)
                    regime["changepoint_prob"] = bocpd.get("changepoint_prob", 0.0)
                    regime["bocpd_run_length"] = bocpd.get("run_length", 0)

                    vol_imb = quant_engine.signed_volume_imbalance(df)
                    regime["volume_imbalance"] = vol_imb.get("imbalance_ratio", 0.0)
                    regime["buy_pressure"] = vol_imb.get("buy_pressure", 0.5)
                    regime["volume_signal"] = vol_imb.get("signal", "NEUTRAL")

                    current_price = float(df["close"].iloc[-1])
                    raw_price = live_price if live_price else current_price
                    try:
                        from paper_trader.price_resolver import resolve_mark_price
                        current_price = resolve_mark_price(symbol, raw_price, tf_label)
                    except Exception:
                        current_price = raw_price

                    kalman = quant_engine.kalman_fair_value(df)
                    regime["kalman_fair_value"] = kalman.get("fair_value", current_price)
                    regime["kalman_z"] = kalman.get("innovation_z", 0.0)
                    regime["kalman_signal"] = kalman.get("signal", "NEUTRAL")

                    pair_symbol = PAIR_SYMBOLS.get(symbol)
                    if pair_symbol:
                        pair_df = get_ohlcv(pair_symbol, tf_label, 365)
                        if not pair_df.empty:
                            df_for_coint = df.reset_index()
                            coint = quant_engine.cointegration_spread(df_for_coint, pair_df)
                            regime["spread_zscore"] = coint.get("spread_zscore", 0.0)
                            regime["spread_signal"] = coint.get("signal", "NEUTRAL")
                            regime["cointegration_ready"] = coint.get("pair_ready", False)
                        else:
                            regime["spread_zscore"] = 0.0
                            regime["spread_signal"] = "NEUTRAL"
                            regime["cointegration_ready"] = False
                    else:
                        regime["spread_zscore"] = 0.0
                        regime["spread_signal"] = "NEUTRAL"
                        regime["cointegration_ready"] = False

                    regime["berlekamp_up"] = quant_engine.berlekamp_massey(df).get("prediction_binary", 0)
                    regime["hyper_instability"] = quant_engine.simons_hypersurface(df).get("instability_detected", False)
                    regime["cheeger_invariant"] = quant_engine.cheeger_simons_characters(df).get("cyclic_invariant", 0.0)

                    markov = quant_engine.markov_analysis(df)
                    regime["markov_state"] = markov.get("current_state", "Flat")
                    regime["markov_p_up"] = markov.get("prob_next_up", 0.5)

                    sde_result = quant_engine.monte_carlo(df)
                    regime["sde_forecast"] = sde_result.get("forecast_mean", 0.0)
                    regime["sde_model"] = sde_result.get("model", "ornstein_uhlenbeck")
                    regime["kernel_p_value"] = quant_engine.kernel_regression(df).get("p_value", 1.0)
                    regime["kelly_recommended_pct"] = quant_engine.kelly_sizing(df, "medallion").get("recommended_size_pct", 0.0)

                    kde_levels = quant_engine.kde_liquidity_nodes(df)
                    if kde_levels and current_price > 0:
                        nearest_level = min(kde_levels, key=lambda level: abs(level - current_price))
                        regime["kde_nearest_level"] = nearest_level
                        regime["kde_distance_pct"] = abs(current_price - nearest_level) / current_price * 100.0
                    else:
                        regime["kde_nearest_level"] = None
                        regime["kde_distance_pct"] = 0.0

                    try:
                        intel_ctx = resolve_context(symbol, current_price)
                    except Exception:
                        intel_ctx = {}
                    regime.update(context_to_regime(intel_ctx))
                    if intel_ctx:
                        regime["intelligence"] = intel_ctx

                    tf_signals = {
                        strat: signal_engine.get_signal(df, strat, regime)
                        for strat in STRATEGIES
                    }

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
                        "markov_p_up": float(regime.get("markov_p_up", 0.5)),
                        "markov_state": regime.get("markov_state", "Flat"),
                        "kde_distance_pct": float(regime.get("kde_distance_pct", 0.0)),
                        "volume_imbalance": float(regime.get("volume_imbalance", 0.0)),
                        "buy_pressure": float(regime.get("buy_pressure", 0.5)),
                        "changepoint_prob": float(regime.get("changepoint_prob", 0.0)),
                        "kalman_z": float(regime.get("kalman_z", 0.0)),
                        "spread_zscore": float(regime.get("spread_zscore", 0.0)),
                        "context": regime.get("intelligence", {}),
                        "data_quality": regime.get("data_quality", "unknown"),
                        "session_quality": float(regime.get("session_quality", 0.5)),
                        "event_risk": float(regime.get("event_risk", 0.0)),
                        "sentiment_1h": float(regime.get("sentiment_1h", 0.0)),
                        "price_divergence": float(regime.get("price_divergence", 0.0)),
                        "current_price": current_price,
                        "kernel_p_value": float(regime["kernel_p_value"]),
                        "kelly_recommended_pct": float(regime["kelly_recommended_pct"]),
                        "active_patterns": str(df['active_patterns'].iloc[-1]) if 'active_patterns' in df.columns else "",
                    }

                    if tf_label == "1h":
                        levels = kde_levels

                except Exception as e:
                    print(f"Matrix Compute Error {symbol} {tf_label}: {e}", flush=True)

            try:
                from paper_trader.price_resolver import resolve_mark_price
                ref = matrix_results.get("1h", {}).get("current_price") or matrix_results.get("5m", {}).get("current_price")
                fresh_mark = resolve_mark_price(symbol, ref, "1h")
                for tf_key in matrix_results:
                    matrix_results[tf_key]["current_price"] = fresh_mark
            except Exception:
                pass

            payload = {
                "symbol": symbol,
                "matrix": matrix_results,
                "magnetic_levels": levels,
                "last_updated": datetime.now().isoformat(),
            }
            tmp_output_file = f"{json_path}.tmp"
            try:
                with open(tmp_output_file, "w") as f:
                    json.dump(payload, f)
                os.replace(tmp_output_file, json_path)
                print(f"Updated {json_path}", flush=True)
            except Exception as e:
                if os.path.exists(tmp_output_file):
                    os.remove(tmp_output_file)
                print(f"Failed to write json for {symbol}: {e}", flush=True)

            pause = 15 + random.uniform(0, 5)
            await asyncio.sleep(pause)

        except Exception as e:
            print(f"Main Loop Error: {e}", flush=True)
            await asyncio.sleep(1)


async def main():
    print("Starting Matrix Daemon via TradingView CDP", flush=True)
    ensure_tradingview_ready()
    await compute_matrix()


if __name__ == "__main__":
    asyncio.run(main())
