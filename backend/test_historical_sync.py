import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from data.sync_manifest import required_bars, upsert_manifest, init_manifest_tables
from data.free_historical_fetcher import fetch_binance_klines


class HistoricalSyncTests(unittest.TestCase):
    def test_required_bars_btc_1h(self):
        self.assertGreater(required_bars("BTCUSD", "1h"), 7000)

    def test_required_bars_xau_1m_lower(self):
        self.assertLess(required_bars("XAUUSD", "1m"), required_bars("BTCUSD", "1m"))

    @patch("data.free_historical_fetcher.request_with_retry")
    def test_binance_klines_pagination(self, mock_get):
        batch1 = [
            [1_700_000_000_000, "100", "101", "99", "100.5", "10"] + [0] * 6,
            [1_700_003_600_000, "100.5", "102", "100", "101", "12"] + [0] * 6,
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = [batch1, []]
        mock_get.return_value = mock_resp

        df = fetch_binance_klines("BTCUSDT", "1h", days_back=1)
        self.assertEqual(len(df), 2)
        self.assertEqual(df.attrs["source"], "binance_public")

    def test_manifest_upsert(self):
        init_manifest_tables()
        upsert_manifest("BTCUSD", "1d", 300, None, None, "test", "partial", None, 1)
        from data.sync_manifest import get_manifest
        rows = [r for r in get_manifest("BTCUSD") if r["interval"] == "1d"]
        self.assertTrue(len(rows) >= 1)


if __name__ == "__main__":
    unittest.main()
