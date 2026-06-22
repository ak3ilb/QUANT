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
            active_patterns VARCHAR,
            source VARCHAR,
            actual_symbol VARCHAR,
            actual_resolution VARCHAR,
            extracted_at TIMESTAMP,
            PRIMARY KEY (symbol, interval, time)
        )
    ''')
    for column_name, column_type in [
        ("active_patterns", "VARCHAR"),
        ("source", "VARCHAR"),
        ("actual_symbol", "VARCHAR"),
        ("actual_resolution", "VARCHAR"),
        ("extracted_at", "TIMESTAMP"),
    ]:
        try:
            conn.execute(f'ALTER TABLE market_data ADD COLUMN {column_name} {column_type}')
        except Exception:
            pass # Column already exists
    conn.close()

def store_ohlcv(symbol: str, interval: str, df: pd.DataFrame):
    """
    Ingest a pandas DataFrame into DuckDB.
    Expected columns: time, open, high, low, close, volume, [active_patterns].
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
    
    if 'active_patterns' not in df.columns:
        df['active_patterns'] = ''
    if 'source' not in df.columns:
        df['source'] = df.attrs.get('source', 'unknown')
    if 'actual_symbol' not in df.columns:
        df['actual_symbol'] = df.attrs.get('actual_symbol', symbol)
    if 'actual_resolution' not in df.columns:
        df['actual_resolution'] = df.attrs.get('actual_resolution', interval)
    if 'extracted_at' not in df.columns:
        extracted_at = df.attrs.get('extracted_at')
        df['extracted_at'] = pd.to_datetime(extracted_at, unit='ms') if extracted_at else pd.Timestamp.utcnow()
        
    # Ensure types
    df['time'] = pd.to_datetime(df['time'])
    df['extracted_at'] = pd.to_datetime(df['extracted_at'])
    
    conn = get_connection()
    # Use DuckDB's ON CONFLICT DO UPDATE to ensure live candles are actually updated
    conn.execute('''
        INSERT INTO market_data (
            symbol, interval, time, open, high, low, close, volume, active_patterns,
            source, actual_symbol, actual_resolution, extracted_at
        )
        SELECT
            symbol, interval, time, open, high, low, close, volume, active_patterns,
            source, actual_symbol, actual_resolution, extracted_at
        FROM df
        ON CONFLICT (symbol, interval, time) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            active_patterns = EXCLUDED.active_patterns,
            source = EXCLUDED.source,
            actual_symbol = EXCLUDED.actual_symbol,
            actual_resolution = EXCLUDED.actual_resolution,
            extracted_at = EXCLUDED.extracted_at
    ''')
    conn.close()

def get_ohlcv(symbol: str, interval: str, bars: int = 1000) -> pd.DataFrame:
    """
    Ultra-fast query returning pandas DataFrame.
    """
    conn = get_connection(read_only=True)
    df = conn.execute(f'''
        SELECT time, open, high, low, close, volume, active_patterns, source, actual_symbol, actual_resolution, extracted_at
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
