import requests
import os
import time
import pandas as pd
from datetime import datetime, timedelta
from data_vault import store_ohlcv

TV_SYMBOLS = {"BTCUSD": "BINANCE:BTCUSD", "XAUUSD": "OANDA:XAUUSD", "NIFTY": "NSE:NIFTY"}

class TradingViewHistorySyncer:
    def __init__(self, cdp_url="http://localhost:3001"):
        self.cdp_url = cdp_url
        self.symbols = ["BTCUSD"] # Focus only on BTCUSD for backtesting as requested
        self.timeframes = {
            "1m": "1",
            "3m": "3",
            "5m": "5",
            "15m": "15",
            "1h": "60",
            "4h": "240",
            "1d": "1D"
        }
        
    def sync_all(self):
        print(f"[{datetime.now()}] Starting TV History Sync for {self.symbols}")
        
        for symbol in self.symbols:
            print(f"\n--- Syncing {symbol} ---")
            tv_symbol = TV_SYMBOLS.get(symbol, symbol)
                
            for tf_label, tv_tf in self.timeframes.items():
                print(f"  -> Extracting {tf_label}...")
                    
                # Extract Data
                try:
                    resp = requests.get(
                        f"{self.cdp_url}/extract/history",
                        params={
                            "symbol": tv_symbol,
                            "resolution": tv_tf,
                            "maxBars": 5000,
                            "settleMs": 2000,
                        },
                        timeout=30,
                    )
                    data = resp.json()
                    
                    if data.get("actualSymbol") != tv_symbol:
                        print(f"     ❌ Symbol mismatch: requested {tv_symbol}, got {data.get('actualSymbol')}")
                        continue
                    if data.get("actualResolution") != tv_tf:
                        print(f"     ❌ Timeframe mismatch: requested {tv_tf}, got {data.get('actualResolution')}")
                        continue
                    
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
                            
                        # Store in Vault
                        store_ohlcv(symbol, tf_label, df)
                        print(f"     ✅ Stored {len(df)} bars for {symbol} {tf_label} ({data.get('firstTime')} -> {data.get('lastTime')})")
                    else:
                        print(f"     ❌ No bars returned: {data}")
                        
                except Exception as e:
                    print(f"     ❌ Error extracting {tf_label}: {e}")
                    
        print("\nSync cycle complete!")

def run_sync_once():
    syncer = TradingViewHistorySyncer()
    
    try:
        # Create lock file to pause matrix_worker
        with open("/tmp/history_sync.lock", "w") as f:
            f.write("locked")
        
        syncer.sync_all()
        
    except Exception as e:
        print(f"Critical sync error: {e}")
    finally:
        # Remove lock file when done
        if os.path.exists("/tmp/history_sync.lock"):
            os.remove("/tmp/history_sync.lock")
        
    print(f"[{datetime.now()}] One-time sync complete. Exiting.")

if __name__ == "__main__":
    run_sync_once()
