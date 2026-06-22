import pandas as pd
import requests

TV_SYMBOLS = {"BTCUSD": "BINANCE:BTCUSD", "XAUUSD": "OANDA:XAUUSD", "NIFTY": "NSE:NIFTY"}
TV_RESOLUTIONS = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "1D"}

class DataFetcher:
    def __init__(self, cdp_url="http://localhost:3001"):
        self.cdp_url = cdp_url
        self._last_live_fetch = {}
        
    async def fetch(self, symbol: str, interval: str, bars: int = 365, source: str = "auto"):
        """Fetch OHLCV data. Tries validated TradingView CDP data, then DuckDB."""
        from data_vault import get_ohlcv

        if source == "auto":
            db_df = get_ohlcv(symbol, interval, bars)
            if len(db_df) >= bars:
                db_df.set_index('time', inplace=True)
                return db_df

        if source == "auto" or source == "tradingview":
            try:
                cdp_data = self._fetch_from_cdp(symbol, interval, bars)
                if cdp_data is not None and len(cdp_data) >= bars:
                    # Save to Vault
                    from data_vault import store_ohlcv
                    store_ohlcv(symbol, interval, cdp_data.reset_index())
                    return cdp_data
            except Exception as e:
                if source == "tradingview":
                    raise
                print(f"CDP fetch failed: {e}. Falling back to DuckDB.")
                
        # Try local DuckDB Vault first
        db_df = get_ohlcv(symbol, interval, bars)
        if not db_df.empty:
            db_df.set_index('time', inplace=True)
            return db_df
                
        # If we reach here, we don't have enough data in DuckDB.
        # We ripped out yfinance because it's inaccurate and drops ticks.
        # The user must run backend/history_sync.py to populate the DuckDB vault.
        raise ValueError(f"Insufficient deep history for {symbol} on {interval}. Please run history_sync.py to populate DuckDB Vault via Binance API.")

    async def fetch_live_from_tradingview(self):
        """Fetch current live OHLCV from TradingView CDP."""
        try:
            resp = requests.get(f"{self.cdp_url}/extract/ohlcv", timeout=5)
            if resp.status_code == 200:
                return resp.json()
            return None
        except:
            return None
            
    async def change_tv_symbol(self, symbol: str):
        """Change symbol on TradingView app."""
        resp = requests.post(f"{self.cdp_url}/control/symbol", json={"symbol": symbol})
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
                "settleMs": 1500,
            },
            timeout=20,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("error"):
                raise ValueError(data["error"])
            if data.get("actualSymbol") != tv_symbol:
                raise ValueError(f"TradingView symbol mismatch: requested {tv_symbol}, got {data.get('actualSymbol')}")
            if data.get("actualResolution") != tv_resolution:
                raise ValueError(f"TradingView resolution mismatch: requested {tv_resolution}, got {data.get('actualResolution')}")
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
