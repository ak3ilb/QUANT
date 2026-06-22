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
from backtest_engine import BacktestEngine
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
backtest_engine = BacktestEngine()
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
        result = quant_engine.monte_carlo(df, simulations, forecast_bars, seed)
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
    """Run a full backtest with a named strategy."""
    try:
        df = await data_fetcher.fetch(req.symbol, req.interval, req.bars)
        df = indicator_engine.compute_all(df)
        result = backtest_engine.run(df, req.strategy, req.initial_cash, req.commission, req.params)
        return {"symbol": req.symbol, "strategy": req.strategy, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

@app.post("/api/control/symbol")
async def change_symbol(symbol: str):
    """Change TradingView chart symbol via CDP bridge."""
    try:
        result = await data_fetcher.change_tv_symbol(symbol)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
