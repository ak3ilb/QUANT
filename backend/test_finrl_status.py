"""Tests for FinRL status and paper bridge."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from ml.finrl.status import auto_date_splits, get_finrl_status, vault_stats


class FinrlStatusTests(unittest.TestCase):
    def test_vault_stats_btc(self):
        s = vault_stats("BTCUSD", "1h")
        self.assertIn("bars", s)
        self.assertIn("trainable", s)

    def test_auto_splits_keys(self):
        splits = auto_date_splits("BTCUSD", "1h")
        if splits:
            self.assertIn("train_start", splits)
            self.assertIn("train_end", splits)

    def test_get_finrl_status_shape(self):
        st = get_finrl_status()
        self.assertEqual(st["status"], "ok")
        self.assertIn("rl_dependencies", st)
        self.assertIn("vault", st)
        self.assertIn("auto_splits", st)


if __name__ == "__main__":
    unittest.main()
