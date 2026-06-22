"""Tests for context fusion and timeline."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestContextFusion(unittest.TestCase):
    def test_fuse_context_structure(self):
        from ai.context_fusion import fuse_context

        bundle = fuse_context("BTCUSD", {"current_price": 95000, "sde_forecast": 96000})
        self.assertEqual(bundle["symbol"], "BTCUSD")
        self.assertIn("intelligence", bundle)
        self.assertIn("timeline", bundle)
        self.assertIn("news", bundle)
        self.assertIn("finrl", bundle)
        self.assertIn("broker", bundle)
        self.assertIn("regime_features", bundle)
        self.assertIn("fused_at", bundle)

    def test_sde_divergence(self):
        from ai.context_fusion import fuse_context

        bundle = fuse_context("BTCUSD", {"current_price": 100.0, "sde_forecast": 101.0})
        self.assertAlmostEqual(bundle["matrix"]["sde_divergence_pct"], 0.01, places=4)


class TestTimeline(unittest.TestCase):
    def test_timeline_session(self):
        from intelligence.context.timeline import get_timeline_context

        ctx = get_timeline_context("BTCUSD")
        self.assertIn("active_session", ctx)
        self.assertIn("session_quality", ctx)
        self.assertIn("minutes_until_session_change", ctx)


if __name__ == "__main__":
    unittest.main()
