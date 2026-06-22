"""Free historical OHLCV fetchers — no API keys, rate-limit aware."""
import time
from datetime import datetime, timedelta, timezone

import pandas as pd

from data.rate_limiter import (
    DELAY_BINANCE_PAGE,
    DELAY_KRAKEN_PAGE,
    DELAY_YFINANCE,
    request_with_retry,
)
from data.sync_logger import log_event

BINANCE_URL = "https://api.binance.com/api/v3/klines"
KRAKEN_URL = "https://api.kraken.com/0/public/OHLC"

BINANCE_INTERVALS = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m",
    "1h": "1h", "4h": "4h", "1d": "1d",
}
KRAKEN_INTERVALS = {
    "1m": 1, "3m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440,
}
YF_TICKERS = {"XAUUSD": "GC=F", "BTCUSD": "BTC-USD"}
YF_INTERVALS = {
    "1m": "1m", "3m": "1m", "5m": "5m", "15m": "15m",
    "1h": "1h", "4h": "1h", "1d": "1d",
}


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _finalize_df(df: pd.DataFrame, source: str, actual_symbol: str, resolution: str) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)
    df.attrs["source"] = source
    df.attrs["actual_symbol"] = actual_symbol
    df.attrs["actual_resolution"] = resolution
    df.attrs["extracted_at"] = int(time.time() * 1000)
    return df


def fetch_binance_klines(symbol: str = "BTCUSDT", interval: str = "1h", days_back: int = 365) -> pd.DataFrame:
    bi_interval = BINANCE_INTERVALS.get(interval, interval)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    cursor = _ms(start)
    end_ms = _ms(end)
    rows = []
    page = 0

    while cursor < end_ms:
        page += 1
        resp = request_with_retry(
            BINANCE_URL,
            params={"symbol": symbol, "interval": bi_interval, "startTime": cursor, "endTime": end_ms, "limit": 1000},
            source="binance",
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Binance HTTP {resp.status_code}: {resp.text[:200]}")
        batch = resp.json()
        if not batch:
            break
        rows.extend(batch)
        cursor = batch[-1][0] + 1
        if len(batch) < 1000:
            break
        time.sleep(DELAY_BINANCE_PAGE)
        if page % 10 == 0:
            log_event("debug", "binance_pagination", page=page, rows=len(rows))

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "q", "n", "tb", "tq", "ig",
    ])
    df["time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True).dt.tz_localize(None)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return _finalize_df(df[["time", "open", "high", "low", "close", "volume"]].dropna(), "binance_public", symbol, bi_interval)


def fetch_kraken_ohlc(pair: str = "XBTUSD", interval: str = "1h", days_back: int = 365) -> pd.DataFrame:
    kr_interval = KRAKEN_INTERVALS.get(interval, 60)
    since = int((datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp())
    rows = []
    cursor = since
    page = 0

    for _ in range(200):
        page += 1
        resp = request_with_retry(
            KRAKEN_URL,
            params={"pair": pair, "interval": kr_interval, "since": cursor},
            source="kraken",
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Kraken HTTP {resp.status_code}")
        data = resp.json()
        if data.get("error"):
            raise RuntimeError(f"Kraken error: {data['error']}")
        result = data.get("result", {})
        key = [k for k in result if k != "last"]
        if not key:
            break
        batch = result[key[0]]
        if not batch:
            break
        rows.extend(batch)
        last = result.get("last")
        if last is None or last == cursor:
            break
        cursor = last
        time.sleep(DELAY_KRAKEN_PAGE)
        if page % 5 == 0:
            log_event("debug", "kraken_pagination", page=page, rows=len(rows))
        if len(batch) < 720:
            break

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "vwap", "volume", "count"])
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.tz_localize(None)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return _finalize_df(df[["time", "open", "high", "low", "close", "volume"]].dropna(), "kraken_public", pair, str(kr_interval))


def fetch_yfinance_history(symbol: str, interval: str, days_back: int = 365) -> pd.DataFrame:
    from data.finrl_patterns import fetch_yfinance_day_chunks

    ticker = YF_TICKERS.get(symbol, symbol)
    yf_interval = YF_INTERVALS.get(interval, "1d")

    # FinRL pattern: day-chunked downloads for intraday (yfinance ~7d cap per request)
    if yf_interval in ("1m", "5m", "15m"):
        time.sleep(DELAY_YFINANCE)
        df = fetch_yfinance_day_chunks(ticker, yf_interval, days_back=min(days_back, 60))
        if not df.empty:
            return _finalize_df(df, "yfinance_chunked", ticker, yf_interval)

    time.sleep(DELAY_YFINANCE)
    period = "60d" if yf_interval in ("1m", "5m", "15m") else ("730d" if yf_interval == "1h" else f"{days_back}d")

    import yfinance as yf
    hist = yf.Ticker(ticker).history(period=period, interval=yf_interval, auto_adjust=True)
    if hist is None or hist.empty:
        return pd.DataFrame()

    df = hist.reset_index()
    time_col = "Datetime" if "Datetime" in df.columns else "Date"
    df = df.rename(columns={time_col: "time"})
    if hasattr(df["time"].dt, "tz") and df["time"].dt.tz is not None:
        df["time"] = df["time"].dt.tz_localize(None)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})
    df["volume"] = df["Volume"] if "Volume" in df.columns else 0.0
    return _finalize_df(df[["time", "open", "high", "low", "close", "volume"]].dropna(), "yfinance_free", ticker, yf_interval)


def fetch_btc_history(interval: str, days_back: int = 365) -> pd.DataFrame:
    """Try Binance → Kraken → CCXT (FinRL pattern) → yfinance."""
    from data.finrl_patterns import fetch_ccxt_ohlcv_optional

    errors = []
    ccxt_interval = {
        "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m",
        "1h": "1h", "4h": "4h", "1d": "1d",
    }.get(interval, "1h")
    for name, fn, kwargs in [
        ("binance", fetch_binance_klines, {"symbol": "BTCUSDT", "interval": interval, "days_back": days_back}),
        ("kraken", fetch_kraken_ohlc, {"pair": "XBTUSD", "interval": interval, "days_back": days_back}),
        ("ccxt", fetch_ccxt_ohlcv_optional, {"pair": "BTC/USDT", "interval": ccxt_interval, "days_back": days_back}),
        ("yfinance", fetch_yfinance_history, {"symbol": "BTCUSD", "interval": interval, "days_back": days_back}),
    ]:
        try:
            log_event("info", "fetch_attempt", symbol="BTCUSD", interval=interval, source=name)
            df = fn(**kwargs)
            if not df.empty:
                if name == "ccxt":
                    df = _finalize_df(df, "ccxt_public", "BTC/USDT", ccxt_interval)
                source = df.attrs.get("source", name)
                log_event("info", "fetch_success", symbol="BTCUSD", interval=interval, source=source, bars=len(df))
                if source == "unknown" or not df.attrs.get("source"):
                    df.attrs["source"] = f"{name}_public"
                return df
            errors.append(f"{name}: empty")
        except Exception as e:
            log_event("warning", "fetch_source_failed", symbol="BTCUSD", interval=interval, source=name, error=str(e)[:200])
            errors.append(f"{name}: {e}")
    raise RuntimeError("; ".join(errors))


def fetch_historical(symbol: str, interval: str, days_back: int = 365) -> pd.DataFrame:
    symbol = symbol.upper()
    if symbol == "BTCUSD":
        return fetch_btc_history(interval, days_back)
    if symbol == "XAUUSD":
        log_event("info", "fetch_attempt", symbol="XAUUSD", interval=interval, source="yfinance")
        df = fetch_yfinance_history("XAUUSD", interval, days_back)
        if not df.empty:
            log_event("info", "fetch_success", symbol="XAUUSD", interval=interval, source="yfinance", bars=len(df))
        return df
    raise ValueError(f"Unsupported symbol: {symbol}")
