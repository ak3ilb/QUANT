import duckdb
import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
conn = duckdb.connect('quant_vault.duckdb', read_only=True)
df = conn.execute('''
    SELECT 
        trade_id, 
        symbol, 
        direction, 
        entry_time,
        exit_time,
        entry_price,
        exit_price,
        pnl_usd,
        status,
        confidence
    FROM paper_ledger 
    ORDER BY entry_time DESC
''').df()

for i, row in df.iterrows():
    pnl = f"${row['pnl_usd']:.2f}" if pd.notna(row['pnl_usd']) else "N/A"
    exit_px = f"{row['exit_price']:.2f}" if pd.notna(row['exit_price']) else "N/A"
    print(f"{row['trade_id']} | {row['direction']} {row['symbol']} | Entry: {row['entry_time']} @ {row['entry_price']:.2f} | Exit: {row['exit_time']} @ {exit_px} | PnL: {pnl} | Conf: {row['confidence']} | Status: {row['status']}")
