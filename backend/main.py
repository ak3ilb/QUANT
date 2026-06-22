"""
QUANT Backend — FastAPI Application
Medallion-grade quantitative trading analysis platform.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import uvicorn
import pandas as pd

from algorithm_registry import get_algorithm_registry
from data_fetcher import DataFetcher
from indicator_engine import IndicatorEngine
from quant_engine import QuantEngine
from strategies import StrategyRunner
from signal_engine import STRATEGIES, SignalEngine

app = FastAPI(
    title="QUANT — Medallion-Grade Trading Analysis",
    description="Quantitative trading platform with RenTech-inspired algorithms",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
data_fetcher = DataFetcher()
indicator_engine = IndicatorEngine()
quant_engine = QuantEngine()
strategy_runner = StrategyRunner()
# backtest_engine is a standalone CLI: run `python3 backtest_engine.py` directly
signal_engine = SignalEngine()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "QUANT Backend"}


# ─── Data Endpoints ───────────────────────────────────────────────────────────

@app.get("/api/data")
async def get_data(
    symbol: str = Query("BTCUSD", description="Ticker symbol"),
    interval: str = Query("1d", description="Timeframe: 1m, 5m, 15m, 1h, 4h, 1d, 1w"),
    bars: int = Query(365, ge=1, le=5000, description="Number of bars to fetch"),
    source: str = Query("auto", description="Data source: auto, tradingview, yfinance"),
):
    """Fetch OHLCV data for a symbol."""
    try:
        df = await data_fetcher.fetch(symbol, interval, bars, source)
        records = df.reset_index().to_dict(orient="records")
        import math
        # Convert timestamps to strings for JSON, and NaNs to None
        for r in records:
            for k, v in r.items():
                if hasattr(v, "isoformat"):
                    r[k] = v.isoformat()
                elif isinstance(v, float) and math.isnan(v):
                    r[k] = None
        return {"symbol": symbol, "interval": interval, "count": len(records), "data": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/live")
async def get_live_data(symbol: str = Query("BTCUSD")):
    """Get live OHLCV from TradingView CDP bridge."""
    try:
        data = await data_fetcher.fetch_live_from_tradingview()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Indicator Endpoints ──────────────────────────────────────────────────────

@app.get("/api/indicators")
async def get_indicators(
    symbol: str = Query("BTCUSD"),
    interval: str = Query("1d"),
    bars: int = Query(365, ge=1, le=5000),
    indicators: str = Query("all", description="Comma-separated list or 'all'"),
):
    """Fetch data with technical indicators computed."""
    try:
        df = await data_fetcher.fetch(symbol, interval, bars)
        if indicators == "all":
            df = indicator_engine.compute_all(df)
        else:
            indicator_list = [i.strip() for i in indicators.split(",")]
            df = indicator_engine.compute_selected(df, indicator_list)

        records = df.reset_index().to_dict(orient="records")
        for r in records:
            for k, v in r.items():
                if hasattr(v, "isoformat"):
                    r[k] = v.isoformat()
                elif isinstance(v, float) and (v != v):  # NaN check
                    r[k] = None
        return {"symbol": symbol, "interval": interval, "count": len(records), "data": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Quant Engine Endpoints ──────────────────────────────────────────────────

@app.get("/api/regime")
async def get_regime(
    symbol: str = Query("BTCUSD"),
    interval: str = Query("1d"),
    bars: int = Query(365, ge=50, le=5000),
):
    """Detect market regime using HMM (Bull/Bear/Sideways)."""
    try:
        df = await data_fetcher.fetch(symbol, interval, bars)
        result = quant_engine.detect_regime(df)
        return {"symbol": symbol, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kelly")
async def get_kelly(
    symbol: str = Query("BTCUSD"),
    strategy: str = Query("nova"),
    interval: str = Query("1d"),
    bars: int = Query(365, ge=10, le=5000),
):
    """Calculate Kelly Criterion position sizing."""
    try:
        df = await data_fetcher.fetch(symbol, interval, bars)
        df = indicator_engine.compute_all(df)
        result = quant_engine.kelly_sizing(df, strategy)
        return {"symbol": symbol, "strategy": strategy, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/montecarlo")
async def get_montecarlo(
    symbol: str = Query("BTCUSD"),
    interval: str = Query("1d"),
    bars: int = Query(365, ge=50, le=5000),
    simulations: int = Query(1000, ge=1, le=10000),
    forecast_bars: int = Query(30, ge=1, le=365),
    seed: Optional[int] = Query(None, description="Optional deterministic seed"),
):
    """Run Monte Carlo simulation for price path forecasting."""
    try:
        df = await data_fetcher.fetch(symbol, interval, bars)
        result = quant_engine.geometric_brownian_motion(df, simulations, forecast_bars, seed)
        return {"symbol": symbol, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/markov")
async def get_markov(
    symbol: str = Query("BTCUSD"),
    interval: str = Query("1d"),
    bars: int = Query(365, ge=2, le=5000),
):
    """Markov Chain state transition analysis."""
    try:
        df = await data_fetcher.fetch(symbol, interval, bars)
        result = quant_engine.markov_analysis(df)
        return {"symbol": symbol, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Strategy & Backtest Endpoints ────────────────────────────────────────────

class BacktestRequest(BaseModel):
    symbol: str = "BTCUSD"
    strategy: str = "nova"
    interval: str = "1d"
    bars: int = Field(365, ge=50, le=5000)
    initial_cash: float = Field(10000.0, gt=0)
    commission: float = Field(0.001, ge=0, le=1)
    params: Optional[dict] = None


@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    """Backtest is run via CLI: python3 backtest_engine.py"""
    return {"status": "Use the CLI backtest engine directly: python3 backtest_engine.py"}


# ─── Signal Endpoints ────────────────────────────────────────────────────────

@app.get("/api/signal")
async def get_signal(
    symbol: str = Query("BTCUSD"),
    strategy: str = Query("all"),
    interval: str = Query("1d"),
    bars: int = Query(365, ge=50, le=5000),
):
    """Get current trading signal with confidence score."""
    try:
        df = await data_fetcher.fetch(symbol, interval, bars)
        df = indicator_engine.compute_all(df)
        regime = quant_engine.detect_regime(df)
        if strategy.lower() == "all":
            result = {
                "strategy": "all",
                "signals": signal_engine.get_all_signals(df, regime),
            }
        elif strategy.lower() in STRATEGIES:
            result = signal_engine.get_signal(df, strategy, regime)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown strategy '{strategy}'. Expected one of: all, {', '.join(STRATEGIES)}",
            )
        return {"symbol": symbol, **result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/algorithms")
async def get_algorithms():
    """Return source-aware algorithm metadata and caveats."""
    return {"algorithms": get_algorithm_registry()}


# ─── Medallion Command Center ──────────────────────────────────────────────────

_MATRIX_CACHE = {}

@app.get("/api/medallion-matrix")
async def get_medallion_matrix(symbol: str = Query("BTCUSD")):
    """
    Evaluates all strategies across multiple timeframes simultaneously.
    Returns the massive payload for the Command Center Grid.
    (Now operates entirely decoupled via matrix_worker.py)
    """
    import json
    import os
    try:
        matrix_file = f"/tmp/latest_matrix_{symbol}.json"
        
        # Fallback to the old generic one if symbol specific doesn't exist yet
        if not os.path.exists(matrix_file):
            matrix_file = "/tmp/latest_matrix.json"
            
        with open(matrix_file, "r") as f:
            return json.load(f)
    except Exception as e:
        return {"error": "Matrix daemon has not generated the first payload yet or is offline."}
    
# ─── Control Endpoints ───────────────────────────────────────────────────────

@app.get("/api/paper-ledger")
async def get_paper_ledger():
    """Fetch the paper trader ledger from DuckDB with equity and unrealized P&L."""
    import duckdb
    import os
    import json

    INITIAL = 100.0
    from paper_trader.broker_config import STANDARD_ACCOUNT, SPREAD_WIDTH, qty_to_lots
    from paper_trader.risk_manager import RiskManager
    from paper_trader.price_resolver import resolve_mark_price

    _rm = RiskManager()

    empty = {
        "balance": INITIAL,
        "equity": INITIAL,
        "locked_margin": 0.0,
        "unrealized_pnl": 0.0,
        "account": {
            "type": STANDARD_ACCOUNT["name"],
            "initial_deposit": INITIAL,
            "max_leverage": STANDARD_ACCOUNT["max_leverage"],
            "commission": "none",
            "min_spread": "0.20",
        },
        "stats": {"win_rate": 0.0, "total_spread_cost": 0.0, "total_trades": 0, "wins": 0, "losses": 0},
        "open_positions": [],
        "history": [],
    }
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'quant_vault.duckdb')
        if not os.path.exists(db_path):
            return empty

        con = duckdb.connect(database=db_path, read_only=True)
        tables = con.execute("SHOW TABLES").df()
        if 'paper_ledger' not in tables['name'].values:
            con.close()
            return empty

        df = con.execute("SELECT * FROM paper_ledger ORDER BY entry_time DESC").df()
        con.close()

        if df.empty:
            return empty

        closed = df[df['status'] == 'CLOSED']
        open_df = df[df['status'] == 'OPEN']

        cash_balance = INITIAL
        if not closed.empty:
            cash_balance += float(closed['pnl_usd'].sum())

        locked_margin = 0.0
        unrealized_pnl = 0.0
        total_spread_cost = 0.0

        def _matrix_price(symbol):
            path = f"/tmp/latest_matrix_{symbol}.json"
            matrix_px = None
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        data = json.load(f)
                    matrix_px = data.get("matrix", {}).get("1h", {}).get("current_price")
                except Exception:
                    pass
            return resolve_mark_price(symbol, matrix_px, "1h")

        open_positions = []
        for _, row in open_df.iterrows():
            margin = float(row['size_usd'])
            locked_margin += margin
            cash_balance -= margin

            mark = row['current_price'] if row['current_price'] == row['current_price'] else None
            if mark is None or mark == "":
                mark = _matrix_price(row['symbol'])
            if mark is None:
                mark = float(row['entry_price'])

            mark = float(mark)
            entry = float(row['entry_price'])
            qty = float(row['qty'])
            direction = row['direction']
            sym = str(row['symbol']).upper()
            lots = float(row['lots']) if 'lots' in row.index and row['lots'] == row['lots'] else qty_to_lots(sym, qty)
            spread_w = SPREAD_WIDTH.get(sym, 0.20)
            total_spread_cost += lots * spread_w  # open leg spread already paid

            pos_dict = {
                "direction": direction,
                "entry_price": entry,
                "qty": qty,
                "size_usd": margin,
                "stop_price": float(row['stop_price']) if 'stop_price' in row.index and row['stop_price'] == row['stop_price'] else None,
                "sde_target": float(row['sde_target']) if 'sde_target' in row.index and row['sde_target'] == row['sde_target'] else None,
            }
            pos_unrealized = _rm.unrealized_pnl(pos_dict, mark, sym)
            unrealized_pnl += pos_unrealized

            live_conf = None
            path = f"/tmp/latest_matrix_{row['symbol']}.json"
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        mdata = json.load(f)
                    live_conf = mdata.get("matrix", {}).get("1h", {}).get("signals", {}).get("medallion", {}).get("confidence")
                except Exception:
                    pass

            rec = row.to_dict()
            lev = float(row['leverage']) if 'leverage' in row.index and row['leverage'] == row['leverage'] else (
                float(row['leveraged_size']) / margin if margin > 0 else STANDARD_ACCOUNT["max_leverage"]
            )
            rec['current_price'] = mark
            rec['unrealized_pnl'] = pos_unrealized
            rec['live_confidence'] = live_conf
            rec['lots'] = lots
            rec['leverage'] = lev
            rec['fees_paid'] = 0.0
            rec['swap_usd'] = 0.0
            rec['spread_width'] = spread_w
            rec['notional_usd'] = qty * entry
            for k, v in list(rec.items()):
                if hasattr(v, 'isoformat'):
                    rec[k] = v.isoformat()
                elif isinstance(v, float) and v != v:  # NaN
                    rec[k] = None
            open_positions.append(rec)

        equity = cash_balance + locked_margin + unrealized_pnl

        total_trades = len(closed)
        wins = int((closed['pnl_usd'] > 0).sum()) if not closed.empty else 0
        losses = total_trades - wins
        if not closed.empty:
            for _, row in closed.iterrows():
                sym = str(row['symbol']).upper()
                lots_h = float(row['lots']) if 'lots' in row.index and row['lots'] == row['lots'] else qty_to_lots(sym, float(row['qty']))
                spread_w = SPREAD_WIDTH.get(sym, 0.20)
                total_spread_cost += lots_h * spread_w * 2  # open + close legs

        win_rate = wins / total_trades if total_trades > 0 else 0.0

        history_df = closed.head(50)
        history = history_df.to_dict(orient="records")
        for row in history:
            row['fees_paid'] = 0.0
            for k, v in list(row.items()):
                if hasattr(v, 'isoformat'):
                    row[k] = v.isoformat()
                elif v != v:  # NaN
                    row[k] = None

        return {
            "balance": float(cash_balance),
            "equity": float(equity),
            "locked_margin": float(locked_margin),
            "unrealized_pnl": float(unrealized_pnl),
            "account": {
                "type": STANDARD_ACCOUNT["name"],
                "initial_deposit": INITIAL,
                "max_leverage": STANDARD_ACCOUNT["max_leverage"],
                "commission": "none",
                "min_spread": "0.20",
            },
            "stats": {
                "win_rate": float(win_rate),
                "total_spread_cost": float(total_spread_cost),
                "total_fees": 0.0,
                "total_trades": int(total_trades),
                "wins": wins,
                "losses": losses,
            },
            "open_positions": open_positions,
            "history": history,
        }
    except Exception as e:
        return {**empty, "error": str(e)}


@app.get("/api/learning-stats")
async def get_learning_stats():
    """Continuous learning state: Thompson bandit, drift detector, online model."""
    try:
        from learning_engine import get_learning_engine
        return get_learning_engine().get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/intelligence/context")
async def get_intelligence_context(symbol: str = Query("BTCUSD")):
    try:
        from intelligence.context_builder import resolve_context
        ctx = resolve_context(symbol.upper())
        return ctx
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/intelligence/calendar")
async def get_intelligence_calendar(hours: int = Query(48, ge=1, le=168)):
    try:
        from intelligence_store import get_upcoming_events
        return {"events": get_upcoming_events(hours=hours)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/intelligence/sentiment")
async def get_intelligence_sentiment(symbol: str = Query("BTCUSD"), hours: int = Query(4, ge=1, le=48)):
    try:
        from intelligence.nlp.sentiment_engine import rolling_sentiment
        return rolling_sentiment([symbol.upper()], hours=hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/intelligence/data-quality")
async def get_intelligence_data_quality():
    try:
        from intelligence.validation.price_validator import get_data_quality_summary
        return get_data_quality_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/intelligence/headlines")
async def get_intelligence_headlines(
    symbol: str = Query("BTCUSD"),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=100),
):
    try:
        from intelligence_store import get_headlines
        from intelligence.context_builder import build_context
        from ai.nlp.impact_scorer import enrich_headline_with_impact

        ctx = build_context(symbol.upper())
        raw = get_headlines(symbol=symbol.upper(), hours=hours, limit=limit)
        headlines = [enrich_headline_with_impact(h, ctx) for h in raw]
        return {"symbol": symbol.upper(), "count": len(headlines), "headlines": headlines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/services")
async def get_system_services():
    try:
        from system_services import get_services_status
        return get_services_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/status")
async def get_ai_status(symbol: str = Query("BTCUSD")):
    try:
        from intelligence.context_builder import resolve_context
        from intelligence.nlp.sentiment_engine import rolling_sentiment
        from ml.data.readiness import readiness_summary
        from learning_engine import get_learning_engine

        sym = symbol.upper()
        ctx = resolve_context(sym)
        sentiment = rolling_sentiment([sym], hours=4)
        learning = get_learning_engine().get_stats()
        ml_ready = readiness_summary()
        return {
            "symbol": sym,
            "context": ctx,
            "sentiment": sentiment,
            "learning": learning,
            "ml_readiness": {
                "trainable_count": ml_ready["trainable_count"],
                "total_pairs": ml_ready["total_pairs"],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ml/readiness")
async def get_ml_readiness():
    try:
        from ml.data.readiness import readiness_summary
        return readiness_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data-sync/status")
async def get_data_sync_status():
    """Historical 1-year sync manifest (free API sources)."""
    try:
        from data.sync_manifest import build_status_summary
        from data.sync_logger import read_status_snapshot
        from data.sync_completion import is_pipeline_complete, _load_flag
        summary = build_status_summary()
        snapshot = read_status_snapshot()
        flag = _load_flag()
        return {
            **summary,
            "pipeline_complete": is_pipeline_complete(),
            "pipeline_completed_at": flag.get("completed_at") if flag else None,
            "cron_removed": flag.get("cron_removed") if flag else None,
            "snapshot_updated_at": snapshot.get("updated_at") if snapshot else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/data-sync/run")
async def run_data_sync(days: int = Query(365, ge=30, le=730)):
    """Trigger historical sync (runs in background thread)."""
    import threading
    from historical_sync_cron import run_full

    def _run():
        run_full(days_back=days, max_rounds=50, train_on_complete=True)

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started", "days": days}


@app.get("/api/ml/metrics")
async def get_ml_metrics():
    """Latest ML training metrics and evaluation report."""
    import json
    import os
    from ml.evaluate.report import read_eval_report
    from ml.models.registry import list_models

    path = os.path.join(os.path.dirname(__file__), "ml", "saved_models", "latest_metrics.json")
    if not os.path.exists(path):
        return {"status": "no_runs_yet", "models": list_models()}
    with open(path) as f:
        metrics = json.load(f)
    eval_report = read_eval_report()
    return {**metrics, "eval": eval_report, "models": list_models()}


@app.get("/api/ml/finrl/status")
async def get_finrl_status_api():
    """FinRL DRL stack: deps, vault bars, models, paper signal preview."""
    try:
        from ml.finrl.status import get_finrl_status
        return get_finrl_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ml/finrl/signal")
async def get_finrl_signal_api(symbol: str = "BTCUSD", interval: str = "1h"):
    try:
        from ml.finrl.status import get_paper_signal
        return get_paper_signal(symbol.upper(), interval)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/context")
async def get_ai_context(symbol: str = "BTCUSD", interval: str = "1h"):
    """Fused runtime context: news, sessions, matrix, broker, FinRL."""
    try:
        from ai.context_fusion import fuse_context
        import json
        import os

        matrix_tf = {}
        json_path = f"/tmp/latest_matrix_{symbol.upper()}.json"
        if os.path.exists(json_path):
            with open(json_path) as f:
                data = json.load(f)
            matrix_tf = data.get("matrix", {}).get(interval, {})
        return fuse_context(symbol.upper(), matrix_tf, interval)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai/study")
async def get_ai_study(symbol: str = "BTCUSD", interval: str = "1h", refresh: bool = False):
    """Realtime AI study: layer scores, live learning, algorithm decode."""
    try:
        from ai.study.engine import get_study_engine
        engine = get_study_engine()
        if refresh:
            engine.run_historical_study(symbol.upper(), interval, force=True)
        return engine.get_dashboard(symbol.upper(), interval)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/study/tick")
async def ai_study_tick(symbol: str = "BTCUSD", interval: str = "1h"):
    """Force historical re-evaluation (background-friendly)."""
    import threading
    from ai.study.engine import get_study_engine

    def _run():
        get_study_engine().run_historical_study(symbol.upper(), interval, force=True)

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started", "symbol": symbol.upper(), "interval": interval}


@app.get("/api/ml/finrl/analyze")
async def get_finrl_analyze(symbol: str = "BTCUSD", interval: str = "1h"):
    try:
        from ml.finrl.analyze import analyze_run
        return analyze_run(symbol=symbol.upper(), interval=interval)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ml/finrl/train")
async def trigger_finrl_train(
    symbol: str = "BTCUSD",
    interval: str = "1h",
    model: str = "ppo",
    timesteps: int = 50000,
    auto_dates: bool = True,
):
    """Background FinRL PPO/SAC training on vault data."""
    import threading
    from ml.finrl import config as finrl_config
    from ml.finrl.status import auto_date_splits
    from ml.finrl.train import train

    splits = auto_date_splits(symbol.upper(), interval) if auto_dates else {}
    start = splits.get("train_start", finrl_config.TRAIN_START_DATE) if splits else finrl_config.TRAIN_START_DATE
    end = splits.get("train_end", finrl_config.TRAIN_END_DATE) if splits else finrl_config.TRAIN_END_DATE

    def _run():
        try:
            train(symbol=symbol.upper(), interval=interval, start_date=start, end_date=end,
                  model_name=model, total_timesteps=timesteps, data_source="vault")
        except Exception as exc:
            from ml.finrl.status import save_train_result
            save_train_result({"status": "error", "detail": str(exc)})

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started", "symbol": symbol.upper(), "interval": interval, "train_window": [start, end]}


@app.post("/api/control/symbol")
async def change_symbol(symbol: str):
    """Change TradingView chart symbol via CDP bridge."""
    try:
        result = await data_fetcher.change_tv_symbol(symbol)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
