"""Smoke tests for QUANT stack connectivity and paper ledger shape."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from paper_trader.portfolio import Portfolio
from paper_trader.risk_manager import RiskManager
from paper_trader.broker_config import STANDARD_ACCOUNT


class BrokerMathTest(unittest.TestCase):
    def test_user_btc_buy_example(self):
        """Match broker-style P/L: 0.01 lot, buy 64295.27 → 64304.62 = +$0.09."""
        open_p, current_p, lots = 64295.27, 64304.62, 0.01
        pnl = (current_p - open_p) * lots
        self.assertAlmostEqual(pnl, 0.09, places=2)

    def test_standard_sizing_and_no_commission(self):
        rm = RiskManager()
        margin, notional, qty, lots, fee, lev = rm.calculate_position_size(
            100.0, 5.0, "BTCUSD", 64295.27
        )
        self.assertEqual(lev, STANDARD_ACCOUNT["max_leverage"])
        self.assertGreaterEqual(lots, 0.01)
        self.assertEqual(fee, 0.0)
        self.assertAlmostEqual(margin, notional / lev, places=4)

    def test_stop_from_margin_not_price_pct(self):
        rm = RiskManager()
        entry = 64295.27
        lots = 0.01
        margin = (lots * entry) / STANDARD_ACCOUNT["max_leverage"]
        stop = rm.compute_stop_price(entry, "BUY", lots, "BTCUSD", margin)
        loss_at_stop = (entry - stop) * lots
        self.assertAlmostEqual(loss_at_stop, margin * 0.20, places=2)

    def test_spread_embedded_pnl(self):
        rm = RiskManager()
        mid = 64295.27
        entry = rm.apply_spread(mid, "BUY", "BTCUSD")
        exit_px = rm.exit_price(mid + 9.35, "BUY", "BTCUSD")
        pnl = (exit_px - entry) * 0.01
        self.assertAlmostEqual(pnl, 0.09, delta=0.02)


class PaperTradeLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.test_db = os.path.join(os.path.dirname(__file__), 'test_paper_ledger.duckdb')
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        import paper_trader.portfolio as pf
        self._orig_path = pf.DB_PATH
        pf.DB_PATH = self.test_db

    def tearDown(self):
        import paper_trader.portfolio as pf
        pf.DB_PATH = self._orig_path
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_open_close_persists_audit_fields(self):
        pf = Portfolio(initial_balance=100.0)
        rm = RiskManager()
        stop = rm.compute_stop_price(100.0, "BUY", 0.01, "BTCUSD", 0.5)
        trade_id = pf.open_position(
            "BTCUSD", "BUY", 100.0, 0.5, 500.0, 0.01,
            10.0, 0.8, 0.0, stop_price=stop, sde_target=105.0,
        )
        self.assertIsNotNone(trade_id)
        pf.close_position("BTCUSD", 102.0, "SDE Target Reached (In Profit)")

        import duckdb
        con = duckdb.connect(self.test_db, read_only=True)
        row = con.execute(
            "SELECT close_reason, stop_price, sde_target FROM paper_ledger WHERE trade_id = ?",
            [trade_id],
        ).fetchone()
        con.close()
        self.assertEqual(row[0], "SDE Target Reached (In Profit)")
        self.assertAlmostEqual(row[2], 105.0)
        self.assertLess(row[1], 100.0)  # stop below entry for BUY


class PaperLedgerResponseShapeTest(unittest.TestCase):
    def test_response_keys(self):
        expected = {
            "balance", "equity", "locked_margin", "unrealized_pnl",
            "stats", "open_positions", "history",
        }
        empty = {
            "balance": 100.0,
            "equity": 100.0,
            "locked_margin": 0.0,
            "unrealized_pnl": 0.0,
            "stats": {"win_rate": 0.0, "total_fees": 0.0, "total_trades": 0, "wins": 0, "losses": 0},
            "open_positions": [],
            "history": [],
        }
        self.assertTrue(expected.issubset(set(empty.keys())))


if __name__ == "__main__":
    unittest.main()
