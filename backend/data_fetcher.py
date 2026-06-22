import pandas as pd
import requests

from cdp_lock import cdp_lock, jittered_settle_ms

TV_SYMBOLS = {"BTCUSD": "BINANCE:BTCUSD", "XAUUSD": "OANDA:XAUUSD", "NIFTY": "NSE:NIFTY"}
TV_RESOLUTIONS = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "1D"}


class DataFetcher:
    def __init__(self, cdp_url="http://localhost:3001"):
        self.cdp_url = cdp_url
        self._last_live_fetch = {}

    def _cdp_healthy(self):
        try:
            resp = requests.get(f"{self.cdp_url}/health", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    async def fetch(self, symbol: str, interval: str, bars: int = 365, source: str = "auto"):
        """Fetch OHLCV. TV-first when bridge is healthy, DuckDB as cache/fallback."""
        from data_vault import get_ohlcv, store_ohlcv

        if source == "duckdb":
            db_df = get_ohlcv(symbol, interval, bars)
            if db_df.empty:
                raise ValueError(f"No DuckDB data for {symbol} on {interval}")
            db_df.set_index('time', inplace=True)
            return db_df

        cdp_data = None
        if source in ("auto", "tradingview") and self._cdp_healthy():
            try:
                with cdp_lock():
                    cdp_data = self._fetch_from_cdp(symbol, interval, bars)
                if cdp_data is not None and len(cdp_data) > 0:
                    store_ohlcv(symbol, interval, cdp_data.reset_index())
                    if len(cdp_data) >= bars or source == "tradingview":
                        return cdp_data
            except Exception as e:
                if source == "tradingview":
                    raise
                print(f"CDP fetch failed: {e}. Falling back to DuckDB.")

        db_df = get_ohlcv(symbol, interval, bars)
        if not db_df.empty:
            db_df.set_index('time', inplace=True)
            return db_df

        if cdp_data is not None and len(cdp_data) > 0:
            return cdp_data

        raise ValueError(
            f"Insufficient data for {symbol} on {interval}. "
            "Ensure TradingView CDP bridge is running or run history_sync.py."
        )

    async def fetch_live_from_tradingview(self):
        """Fetch current live OHLCV from TradingView CDP."""
        try:
            with cdp_lock():
                resp = requests.get(f"{self.cdp_url}/extract/ohlcv", timeout=5)
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception:
            return None

    async def change_tv_symbol(self, symbol: str):
        """Change symbol on TradingView app."""
        tv_symbol = TV_SYMBOLS.get(symbol.upper(), symbol)
        with cdp_lock():
            resp = requests.post(f"{self.cdp_url}/control/symbol", json={"symbol": tv_symbol})
        return resp.json()

    def _fetch_from_cdp(self, symbol: str, interval: str, bars: int):
        """Fetch validated history from the TradingView CDP bridge."""
        tv_symbol = TV_SYMBOLS.get(symbol.upper(), symbol)
        tv_resolution = TV_RESOLUTIONS.get(interval, interval)
        resp = requests.get(
            f"{self.cdp_url}/extract/history",
            params={
                "symbol": tv_symbol,
                "resolution": tv_resolution,
                "maxBars": bars,
                "settleMs": jittered_settle_ms(),
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("error"):
                raise ValueError(data["error"])
            if data.get("actualSymbol") != tv_symbol:
                raise ValueError(
                    f"TradingView symbol mismatch: requested {tv_symbol}, got {data.get('actualSymbol')}"
                )
            if data.get("actualResolution") != tv_resolution:
                raise ValueError(
                    f"TradingView resolution mismatch: requested {tv_resolution}, got {data.get('actualResolution')}"
                )
            if "bars" in data and len(data["bars"]) > 0:
                df = pd.DataFrame(data["bars"])
                unit = "ms" if df["time"].iloc[-1] > 20000000000 else "s"
                df['time'] = pd.to_datetime(df['time'], unit=unit)
                df.set_index('time', inplace=True)
                df.attrs["source"] = data.get("source", "tradingview_cdp")
                df.attrs["actual_symbol"] = data.get("actualSymbol")
                df.attrs["actual_resolution"] = data.get("actualResolution")
                df.attrs["extracted_at"] = data.get("extractedAt")
                return df
        return None
