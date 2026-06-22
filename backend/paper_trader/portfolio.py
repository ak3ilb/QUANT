import duckdb
import os
import json
import uuid
import time
from datetime import datetime

# Shared vault with the main backend
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'quant_vault.duckdb')

class Portfolio:
    def __init__(self, initial_balance=100.0):
        self.balance = initial_balance
        self.positions = {}
        
        self._init_db()
        self._load_state()

    def _execute(self, query, params=None, fetch_df=False):
        conn = duckdb.connect(database=DB_PATH, read_only=False)
        try:
            if params:
                result = conn.execute(query, params)
            else:
                result = conn.execute(query)
            
            if fetch_df:
                df = result.df()
                return df
        finally:
            conn.close()

    def _init_db(self):
        # Create paper_ledger table if not exists
        self._execute('''
            CREATE TABLE IF NOT EXISTS paper_ledger (
                trade_id VARCHAR PRIMARY KEY,
                symbol VARCHAR,
                direction VARCHAR,
                entry_time TIMESTAMP,
                entry_price DOUBLE,
                size_usd DOUBLE,
                qty DOUBLE,
                status VARCHAR,
                exit_time TIMESTAMP,
                exit_price DOUBLE,
                pnl_usd DOUBLE,
                pnl_pct DOUBLE,
                kelly_pct DOUBLE,
                confidence DOUBLE,
                fees_paid DOUBLE,
                leveraged_size DOUBLE
            )
        ''')
        
    def _load_state(self):
        # Load active positions and calculate current balance
        df = self._execute("SELECT * FROM paper_ledger", fetch_df=True)
        if not df.empty:
            closed_trades = df[df['status'] == 'CLOSED']
            if not closed_trades.empty:
                # Add realized PNL to initial balance
                realized_pnl = closed_trades['pnl_usd'].sum()
                self.balance += realized_pnl
                
            open_trades = df[df['status'] == 'OPEN']
            for _, row in open_trades.iterrows():
                self.positions[row['symbol']] = {
                    "trade_id": row['trade_id'],
                    "direction": row['direction'],
                    "entry_time": row['entry_time'],
                    "entry_price": row['entry_price'],
                    "size_usd": row['size_usd'],
                    "qty": row['qty'],
                    "kelly_pct": row['kelly_pct'],
                    "confidence": row['confidence'],
                    "fees_paid": row['fees_paid'],
                    "leveraged_size": row['leveraged_size']
                }

    def open_position(self, symbol, direction, price, margin_usd, leveraged_size_usd, qty, kelly_pct, confidence, fee_usd):
        if symbol in self.positions:
            print(f"[PORTFOLIO] Already holding {symbol}. Ignoring open request.")
            return None
            
        now = datetime.now().isoformat()
        trade_id = f"TRD_{int(time.time()*1000)}"
        
        # Deduction is handled later
        
        self.positions[symbol] = {
            "trade_id": trade_id,
            "direction": direction,
            "entry_time": now,
            "entry_price": price,
            "size_usd": margin_usd,
            "leveraged_size": leveraged_size_usd,
            "qty": qty,
            "kelly_pct": kelly_pct,
            "confidence": confidence,
            "fees_paid": fee_usd
        }
        
        # Deduct margin and entry fee
        self.balance -= (margin_usd + fee_usd)
        
        self._execute('''
            INSERT INTO paper_ledger 
            (trade_id, symbol, direction, entry_time, entry_price, size_usd, qty, status, kelly_pct, confidence, fees_paid, leveraged_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?)
        ''', (trade_id, symbol, direction, now, price, margin_usd, qty, kelly_pct, confidence, fee_usd, leveraged_size_usd))
        
        print(f"[PORTFOLIO] OPEN {direction} {symbol} | LevSize: ${leveraged_size_usd:.2f} (Margin: ${margin_usd:.2f}) | Price: ${price:.2f} | Fee: ${fee_usd:.2f} | Bal: ${self.balance:.2f}")
        return trade_id

    def close_position(self, symbol, price, reason="Signal Flip"):
        if symbol not in self.positions:
            return None
            
        pos = self.positions[symbol]
        direction = pos['direction']
        entry_price = pos['entry_price']
        qty = pos['qty']
        leveraged_size = pos['leveraged_size']
        total_fees = pos['fees_paid']
        
        # Exit fee based on current execution value
        exit_value = qty * price
        exit_fee = exit_value * 0.001
        total_fees += exit_fee
        
        # Calculate Leveraged PNL
        if direction == "BUY":
            gross_pnl_usd = (price - entry_price) * qty
        else: # SELL (Short)
            gross_pnl_usd = (entry_price - price) * qty
            
        # Net PNL explicitly subtracts the combined fees
        net_pnl_usd = gross_pnl_usd - total_fees
        pnl_pct = net_pnl_usd / pos['size_usd'] # Return on Margin
            
        now = datetime.now()
        
        # Free margin + Net PNL
        self.balance += (pos['size_usd'] + net_pnl_usd)
        
        self._execute('''
            UPDATE paper_ledger
            SET status = 'CLOSED', exit_time = ?, exit_price = ?, pnl_usd = ?, pnl_pct = ?, fees_paid = ?
            WHERE trade_id = ?
        ''', (now, price, net_pnl_usd, pnl_pct, total_fees, pos['trade_id']))
        
        del self.positions[symbol]
        
        print(f"[PORTFOLIO] CLOSE {direction} {symbol} ({reason}) | Net PNL: ${net_pnl_usd:.2f} (Fees: ${total_fees:.2f}) | Bal: ${self.balance:.2f}")
        return net_pnl_usd

    def get_position(self, symbol):
        return self.positions.get(symbol)
        
    def get_balance(self):
        return self.balance
