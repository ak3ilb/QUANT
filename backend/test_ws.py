import asyncio
import ccxt.pro as ccxtpro
import pandas as pd
from algorithms.candlestick_patterns import detect_candlestick_patterns
from data_vault import store_ohlcv

async def test():
    kraken = ccxtpro.kraken({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    print("Watching 1m...")
    try:
        live_ohlcv = await asyncio.wait_for(kraken.watch_ohlcv('BTC/USDT', '1m'), timeout=10)
        print("Got:", len(live_ohlcv), "candles")
        live_df = pd.DataFrame(live_ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        live_df['time'] = pd.to_datetime(live_df['time'], unit='ms')
        print(live_df.tail(2))
        
        target_df = detect_candlestick_patterns(live_df.tail(10).copy())
        target_df = target_df.iloc[[-1]]
        
        print(f"Writing tick: {target_df['time'].iloc[-1]} active_patterns: {target_df['active_patterns'].iloc[-1]}")
        store_ohlcv("BTCUSD", "1m", target_df)
        print("Stored successfully.")
    except Exception as e:
        print("Error:", e)
    finally:
        await kraken.close()

asyncio.run(test())
