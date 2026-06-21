import ccxt
import time
import pandas as pd
from datetime import datetime, timedelta
import asyncio
from data_vault import store_ohlcv

class HistorySyncer:
    def __init__(self, symbol="BTC/USDT", exchange_id="kraken"):
        self.exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True,
        })
        self.symbol = symbol

    def sync_timeframe(self, timeframe="1m", years=1):
        print(f"Starting deep historical sync for {self.symbol} ({timeframe}) - {years} year(s)")
        
        # Calculate timestamps
        end_time = self.exchange.milliseconds()
        start_time = end_time - int(years * 365 * 24 * 60 * 60 * 1000)
        
        current_since = start_time
        total_fetched = 0
        
        while current_since < end_time:
            try:
                # Fetch up to 720 candles (Kraken max)
                ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, since=current_since, limit=720)
                if not ohlcv:
                    break
                    
                # Convert to DataFrame
                df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                df['time'] = pd.to_datetime(df['time'], unit='ms')
                
                # Store in DuckDB
                # Mapping BTC/USDT to BTCUSD for internal consistency
                internal_symbol = self.symbol.replace("/", "").replace("USDT", "USD")
                store_ohlcv(internal_symbol, timeframe, df)
                
                total_fetched += len(df)
                
                # Update current_since for next pagination (add 1 millisecond to avoid duplicate)
                current_since = ohlcv[-1][0] + 1
                
                # Print progress
                current_date = datetime.fromtimestamp(ohlcv[-1][0]/1000).strftime('%Y-%m-%d')
                print(f"[{timeframe}] Fetched {len(df)} bars. Progress: {current_date}. Total: {total_fetched}")
                
                # Minimal sleep to respect rate limits
                time.sleep(self.exchange.rateLimit / 1000)
                
            except Exception as e:
                print(f"Error fetching data: {e}")
                time.sleep(5) # Backoff
                
        print(f"Sync complete for {timeframe}. Total bars fetched: {total_fetched}")

if __name__ == "__main__":
    syncer = HistorySyncer(symbol="BTC/USDT")
    
    # The user requested exactly 3 months of data (0.25 years) for all timeframes
    syncer.sync_timeframe("1m", years=0.25)
    syncer.sync_timeframe("5m", years=0.25) 
    syncer.sync_timeframe("15m", years=0.25)
    syncer.sync_timeframe("1h", years=0.25)
    syncer.sync_timeframe("4h", years=0.25)
    syncer.sync_timeframe("1d", years=0.25)
