import duckdb
import pandas as pd
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'quant_vault.duckdb')

import time

def get_connection(read_only=False):
    # Use DuckDB for ultra-fast, columnar time-series storage
    retries = 20
    for i in range(retries):
        try:
            conn = duckdb.connect(database=DB_PATH, read_only=read_only)
            return conn
        except duckdb.IOException as e:
            if i == retries - 1:
                raise e
            time.sleep(0.5)

def init_db():
    conn = get_connection()
    # Create the master time-series table. 
    # DuckDB is columnar, so storing all timeframes in one massive table is extremely fast to query.
    conn.execute('''
        CREATE TABLE IF NOT EXISTS market_data (
            symbol VARCHAR,
            interval VARCHAR,
            time TIMESTAMP,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume DOUBLE,
            PRIMARY KEY (symbol, interval, time)
        )
    ''')
    conn.close()

def store_ohlcv(symbol: str, interval: str, df: pd.DataFrame):
    """
    Ingest a pandas DataFrame into DuckDB.
    Expected columns: time, open, high, low, close, volume.
    """
    if df.empty:
        return
    
    # Ensure standard column names
    if 'Datetime' in df.columns:
        df = df.rename(columns={'Datetime': 'time'})
    elif 'Date' in df.columns:
        df = df.rename(columns={'Date': 'time'})
    elif 'index' in df.columns:
        df = df.rename(columns={'index': 'time'})
        
    df['symbol'] = symbol
    df['interval'] = interval
    
    # Ensure types
    df['time'] = pd.to_datetime(df['time'])
    
    conn = get_connection()
    # Use DuckDB's fast INSERT OR IGNORE via pandas
    conn.execute('''
        INSERT OR IGNORE INTO market_data 
        SELECT symbol, interval, time, open, high, low, close, volume 
        FROM df
    ''')
    conn.close()

def get_ohlcv(symbol: str, interval: str, bars: int = 1000) -> pd.DataFrame:
    """
    Ultra-fast query returning pandas DataFrame.
    """
    conn = get_connection(read_only=True)
    df = conn.execute(f'''
        SELECT time, open, high, low, close, volume 
        FROM market_data 
        WHERE symbol = ? AND interval = ? 
        ORDER BY time DESC 
        LIMIT ?
    ''', [symbol, interval, bars]).df()
    conn.close()
    
    if not df.empty:
        df = df.sort_values('time').reset_index(drop=True)
    return df

# Initialize DB on load
init_db()
