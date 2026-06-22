import duckdb
import os
import time
from datetime import datetime

# Shared vault with the main backend
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'quant_vault.duckdb')

LEDGER_COLUMNS = [
    ("close_reason", "VARCHAR"),
    ("stop_price", "DOUBLE"),
    ("sde_target", "DOUBLE"),
    ("current_price", "DOUBLE"),
    ("strategy", "VARCHAR"),
    ("entry_features", "VARCHAR"),
    ("context_snapshot", "VARCHAR"),
    ("lots", "DOUBLE"),
    ("leverage", "DOUBLE"),
]


class Portfolio:
    def __init__(self, initial_balance=100.0):
        self.initial_balance = initial_balance
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
                return result.df()
        finally:
            conn.close()

    def _init_db(self):
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
                leveraged_size DOUBLE,
                close_reason VARCHAR,
                stop_price DOUBLE,
                sde_target DOUBLE,
                current_price DOUBLE
            )
        ''')
        for col, col_type in LEDGER_COLUMNS:
            try:
                self._execute(f"ALTER TABLE paper_ledger ADD COLUMN IF NOT EXISTS {col} {col_type}")
            except Exception:
                pass

    def _load_state(self):
        df = self._execute("SELECT * FROM paper_ledger", fetch_df=True)
        if df.empty:
            return

        closed_trades = df[df['status'] == 'CLOSED']
        if not closed_trades.empty:
            self.balance += float(closed_trades['pnl_usd'].sum())

        open_trades = df[df['status'] == 'OPEN']
        for _, row in open_trades.iterrows():
            margin = float(row['size_usd'])
            fees = float(row['fees_paid'])
            self.balance -= margin
            stop_price = None
            sde_target = None
            if 'stop_price' in df.columns and row['stop_price'] == row['stop_price']:
                stop_price = float(row['stop_price'])
            if 'sde_target' in df.columns and row['sde_target'] == row['sde_target']:
                sde_target = float(row['sde_target'])
            entry_features = None
            if 'entry_features' in df.columns and isinstance(row.get('entry_features'), str):
                try:
                    import json
                    entry_features = json.loads(row['entry_features'])
                except (json.JSONDecodeError, TypeError):
                    entry_features = None
            self.positions[row['symbol']] = {
                "trade_id": row['trade_id'],
                "direction": row['direction'],
                "entry_time": row['entry_time'],
                "entry_price": float(row['entry_price']),
                "size_usd": margin,
                "qty": float(row['qty']),
                "lots": float(row['lots']) if 'lots' in df.columns and row['lots'] == row['lots'] else float(row['qty']),
                "leverage": float(row['leverage']) if 'leverage' in df.columns and row['leverage'] == row['leverage'] else 100.0,
                "kelly_pct": float(row['kelly_pct']) if row['kelly_pct'] is not None else 0.0,
                "confidence": float(row['confidence']) if row['confidence'] is not None else 0.5,
                "fees_paid": fees,
                "leveraged_size": float(row['leveraged_size']),
                "stop_price": stop_price,
                "sde_target": sde_target,
                "strategy": row['strategy'] if 'strategy' in df.columns else "medallion",
                "entry_features": entry_features,
            }

    def open_position(
        self,
        symbol,
        direction,
        price,
        margin_usd,
        leveraged_size_usd,
        qty,
        kelly_pct,
        confidence,
        fee_usd,
        stop_price=None,
        sde_target=None,
        strategy="medallion",
        entry_features=None,
        context_snapshot=None,
        lots=None,
        leverage=None,
    ):
        if symbol in self.positions:
            print(f"[PORTFOLIO] Already holding {symbol}. Ignoring open request.")
            return None

        now = datetime.now()
        trade_id = f"TRD_{int(time.time() * 1000)}"

        import json
        features_json = json.dumps(entry_features) if entry_features else None
        context_json = json.dumps(context_snapshot) if context_snapshot else None

        self.positions[symbol] = {
            "trade_id": trade_id,
            "direction": direction,
            "entry_time": now,
            "entry_price": price,
            "size_usd": margin_usd,
            "leveraged_size": leveraged_size_usd,
            "qty": qty,
            "lots": lots if lots is not None else qty,
            "leverage": leverage if leverage is not None else 100.0,
            "kelly_pct": kelly_pct,
            "confidence": confidence,
            "fees_paid": 0.0,
            "stop_price": stop_price,
            "sde_target": sde_target,
            "strategy": strategy,
            "entry_features": entry_features,
            "context_snapshot": context_snapshot,
        }

        self.balance -= margin_usd

        self._execute('''
            INSERT INTO paper_ledger
            (trade_id, symbol, direction, entry_time, entry_price, size_usd, qty, status,
             kelly_pct, confidence, fees_paid, leveraged_size, stop_price, sde_target,
             current_price, strategy, entry_features, context_snapshot, lots, leverage)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_id, symbol, direction, now, price, margin_usd, qty,
            kelly_pct, confidence, 0.0, leveraged_size_usd,
            stop_price, sde_target, price, strategy, features_json, context_json,
            lots if lots is not None else qty, leverage if leverage is not None else 100.0,
        ))

        print(
            f"[PORTFOLIO] OPEN {direction} {symbol} | LevSize: ${leveraged_size_usd:.2f} "
            f"(Margin: ${margin_usd:.2f}) | Price: ${price:.2f} | Stop: ${stop_price:.2f} "
            f"| SDE: ${sde_target:.2f} | Bal: ${self.balance:.2f}"
        )
        return trade_id

    def update_mark_price(self, symbol, current_price):
        if symbol not in self.positions:
            return
        self._execute(
            "UPDATE paper_ledger SET current_price = ? WHERE trade_id = ? AND status = 'OPEN'",
            (current_price, self.positions[symbol]['trade_id']),
        )

    def close_position(self, symbol, price, reason="Signal Flip"):
        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]
        direction = pos['direction']
        entry_price = pos['entry_price']
        qty = pos['qty']

        if direction == "BUY":
            gross_pnl_usd = (price - entry_price) * qty
        else:
            gross_pnl_usd = (entry_price - price) * qty

        net_pnl_usd = gross_pnl_usd  # Standard: no commission; spread already in entry/exit prices
        pnl_pct = net_pnl_usd / pos['size_usd'] if pos['size_usd'] else 0.0

        now = datetime.now()
        self.balance += (pos['size_usd'] + net_pnl_usd)

        self._execute('''
            UPDATE paper_ledger
            SET status = 'CLOSED', exit_time = ?, exit_price = ?, pnl_usd = ?, pnl_pct = ?,
                fees_paid = ?, close_reason = ?, current_price = ?
            WHERE trade_id = ?
        ''', (now, price, net_pnl_usd, pnl_pct, 0.0, reason, price, pos['trade_id']))

        del self.positions[symbol]

        print(
            f"[PORTFOLIO] CLOSE {direction} {symbol} ({reason}) | "
            f"Net PNL: ${net_pnl_usd:.2f} | Bal: ${self.balance:.2f}"
        )
        return {
            "symbol": symbol,
            "pnl_usd": net_pnl_usd,
            "pnl_pct": pnl_pct,
            "trade_id": pos['trade_id'],
            "direction": direction,
            "strategy": pos.get("strategy", "medallion"),
            "entry_features": pos.get("entry_features"),
            "context_snapshot": pos.get("context_snapshot"),
            "lots": pos.get("lots"),
            "leverage": pos.get("leverage"),
            "won": net_pnl_usd > 0,
        }

    def get_position(self, symbol):
        return self.positions.get(symbol)

    def get_balance(self):
        return self.balance

    def get_equity(self, mark_prices=None):
        """Cash balance plus unrealized PnL on open positions."""
        mark_prices = mark_prices or {}
        equity = self.balance
        for symbol, pos in self.positions.items():
            mark = mark_prices.get(symbol, pos.get('entry_price', 0))
            if pos['direction'] == "BUY":
                unrealized = (mark - pos['entry_price']) * pos['qty']
            else:
                unrealized = (pos['entry_price'] - mark) * pos['qty']
            equity += pos['size_usd'] + unrealized
        return equity
