import pandas as pd
import requests
from datetime import datetime, timedelta
import io

class DataFetcher:
    def __init__(self, cdp_url="http://localhost:3001"):
        self.cdp_url = cdp_url
        self._last_live_fetch = {}
        
    async def fetch(self, symbol: str, interval: str, bars: int = 365, source: str = "auto"):
        """Fetch OHLCV data. Tries CDP first, falls back to yfinance."""
        if source == "auto" or source == "tradingview":
            try:
                # Try to use CDP bridge
                cdp_data = self._fetch_from_cdp(symbol, interval, bars)
                if cdp_data is not None and len(cdp_data) >= bars:
                    # Save to Vault
                    from data_vault import store_ohlcv
                    store_ohlcv(symbol, interval, cdp_data.reset_index())
                    return cdp_data
            except Exception as e:
                print(f"CDP fetch failed: {e}. Falling back to yfinance.")
                
        # Try local DuckDB Vault first
        from data_vault import get_ohlcv
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
        """Try to fetch history from CDP."""
        resp = requests.get(f"{self.cdp_url}/extract/history")
        if resp.status_code == 200:
            data = resp.json()
            if "bars" in data and len(data["bars"]) > 0:
                df = pd.DataFrame(data["bars"])
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('time', inplace=True)
                return df
        return None
