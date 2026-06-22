"""
Patterns borrowed from FinRL (reference/FinRL) — no runtime import of FinRL.

FinRL reference files:
  - finrl/meta/data_processors/processor_yahoofinance.py  (day-chunked yfinance)
  - finrl/meta/data_processors/processor_ccxt.py         (CCXT window pagination)
  - finrl/meta/preprocessor/preprocessors.py             (VIX, turbulence index)

FinRL does NOT implement news/NLP — see docs/source/faq.rst (sentiment is BYO).
QUANT intelligence layer (RSS + FinBERT/VADER + impact_scorer) fills that gap.
"""
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from data.rate_limiter import DELAY_YFINANCE, DELAY_BINANCE_PAGE


def fetch_yfinance_day_chunks(
    ticker: str,
    interval: str = "1m",
    days_back: int = 60,
    sleep_s: float | None = None,
) -> pd.DataFrame:
    """
    FinRL YahooFinanceProcessor.download_data pattern:
    download one calendar day at a time to work around yfinance 1m limits (~7 days/request).
    """
    import yfinance as yf

    sleep_s = sleep_s if sleep_s is not None else DELAY_YFINANCE
    end = datetime.now(timezone.utc).replace(tzinfo=None)
    start = end - timedelta(days=days_back)
    cursor = start
    frames = []

    while cursor < end:
        day_end = min(cursor + timedelta(days=1), end)
        try:
            chunk = yf.Ticker(ticker).history(
                start=cursor,
                end=day_end,
                interval=interval,
                auto_adjust=True,
            )
            if chunk is not None and not chunk.empty:
                frames.append(chunk)
        except Exception:
            pass
        cursor = day_end + timedelta(seconds=1)
        time.sleep(sleep_s)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames)
    df = df.reset_index()
    time_col = "Datetime" if "Datetime" in df.columns else "Date"
    df = df.rename(columns={time_col: "time"})
    if hasattr(df["time"].dt, "tz") and df["time"].dt.tz is not None:
        df["time"] = df["time"].dt.tz_localize(None)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})
    df["volume"] = df["Volume"] if "Volume" in df.columns else 0.0
    return df[["time", "open", "high", "low", "close", "volume"]].drop_duplicates(subset=["time"]).sort_values("time")


def fetch_ccxt_ohlcv_optional(
    pair: str = "BTC/USDT",
    interval: str = "1h",
    days_back: int = 365,
    exchange_id: str = "binance",
) -> pd.DataFrame:
    """
    FinRL CCXTEngineer-style pagination via ccxt (optional dependency).
    Returns empty DataFrame if ccxt missing or exchange blocked.
    """
    try:
        import ccxt
    except ImportError:
        return pd.DataFrame()

    if not hasattr(ccxt, exchange_id):
        return pd.DataFrame()

    exchange = getattr(ccxt, exchange_id)({"enableRateLimit": True})
    since_ms = int((datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp() * 1000)
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    rows = []
    cursor = since_ms

    while cursor < end_ms:
        try:
            batch = exchange.fetch_ohlcv(pair, timeframe=interval, since=cursor, limit=1000)
        except Exception:
            break
        if not batch:
            break
        rows.extend(batch)
        cursor = batch[-1][0] + 1
        if len(batch) < 1000:
            break
        time.sleep(DELAY_BINANCE_PAGE)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_localize(None)
    return df.drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)


def rolling_turbulence_proxy(close: pd.Series, window: int = 60) -> float:
    """
  Simplified single-asset turbulence proxy inspired by FinRL calculate_turbulence.
  Mahalanobis-style distance collapses to normalized return z-score for one asset.
    """
    ret = close.pct_change().dropna()
    if len(ret) < window + 5:
        return 0.0
    recent = ret.iloc[-window:]
    mu, sigma = recent.mean(), recent.std()
    if sigma <= 1e-12:
        return 0.0
    z = abs((ret.iloc[-1] - mu) / sigma)
    return float(min(z / 4.0, 1.0))


def fetch_vix_close(days_back: int = 30) -> float | None:
    """FinRL FeatureEngineer.add_vix — ^VIX level for macro regime (optional)."""
    try:
        import yfinance as yf
        end = datetime.now()
        start = end - timedelta(days=days_back)
        hist = yf.Ticker("^VIX").history(start=start, end=end, interval="1d")
        if hist is None or hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception:
        return None


def build_finrl_regime_extras(close: pd.Series, vix_level: float | None = None) -> dict:
    """Extra regime fields for feature_builder / ML dataset (FinRL-inspired)."""
    extras = {"turbulence_norm": rolling_turbulence_proxy(close)}
    if vix_level is not None:
        extras["vix_level"] = vix_level
        extras["vix_norm"] = min(max((vix_level - 12) / 28, 0.0), 1.0)
    return extras
