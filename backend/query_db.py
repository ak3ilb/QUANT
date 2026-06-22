import duckdb
import pandas as pd
from datetime import datetime, timedelta

con = duckdb.connect("quant_vault.duckdb", read_only=True)

print("=== BTCUSD Last 10 Minutes ===")
df = con.execute("""
    SELECT time, open, high, low, close, volume, active_patterns 
    FROM market_data 
    WHERE symbol='BTCUSD' AND interval='1m' 
    ORDER BY time DESC LIMIT 10
""").df()
print(df)

print("\n=== XAUUSD Last 10 Minutes ===")
df = con.execute("""
    SELECT time, open, high, low, close, volume, active_patterns 
    FROM market_data 
    WHERE symbol='XAUUSD' AND interval='1m' 
    ORDER BY time DESC LIMIT 10
""").df()
print(df)

