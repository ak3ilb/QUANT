import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))

from intelligence.context.session_engine import get_session_context
from intelligence.context.event_calendar import get_event_context
from intelligence.nlp.headline_tagger import tag_headline
from intelligence.nlp.sentiment_engine import score_headline
from intelligence.context_builder import build_context, context_to_regime, context_is_stale, resolve_context
from intelligence.validation.price_validator import is_plausible_reference, validate_symbol


class IntelligenceLayerTests(unittest.TestCase):
    def test_session_engine_gold_peak(self):
        peak = datetime(2024, 6, 3, 14, 0, tzinfo=timezone.utc)
        ctx = get_session_context("XAUUSD", peak)
        self.assertEqual(ctx["session"], "london_ny_overlap")
        self.assertGreater(ctx["session_quality"], 0.9)

    def test_session_engine_btc_us_hours(self):
        us = datetime(2024, 6, 3, 15, 0, tzinfo=timezone.utc)
        ctx = get_session_context("BTCUSD", us)
        self.assertEqual(ctx["session"], "us_active")

    def test_headline_tagger_btc(self):
        symbols = tag_headline("Bitcoin ETF approval drives BTC higher", [])
        self.assertIn("BTCUSD", symbols)

    def test_headline_tagger_gold(self):
        symbols = tag_headline("Gold prices rise on Fed outlook", [])
        self.assertIn("XAUUSD", symbols)

    def test_vader_sentiment_scores(self):
        result = score_headline("test-id-1", "Bitcoin rallies strongly on bullish momentum")
        self.assertIn("ensemble_score", result)
        self.assertIn(result["label"], ("bullish", "neutral", "bearish"))

    def test_context_to_regime_maps_fields(self):
        ctx = {
            "symbol": "BTCUSD",
            "session_quality": 0.8,
            "event_risk": 0.5,
            "sentiment_1h": 0.2,
            "price_divergence": 0.001,
            "data_quality": "ok",
            "trade_allowed": True,
        }
        regime = context_to_regime(ctx)
        self.assertEqual(regime["session_quality"], 0.8)
        self.assertEqual(regime["btc_sentiment_1h"], 0.2)

    @patch("intelligence.context_builder.validate_symbol")
    @patch("intelligence.context_builder.rolling_sentiment")
    @patch("intelligence.context_builder.get_macro_features")
    @patch("intelligence.context_builder.get_event_context")
    @patch("intelligence.context_builder.get_session_context")
    def test_build_context_unified(
        self, mock_session, mock_events, mock_macro, mock_sent, mock_validate
    ):
        mock_session.return_value = {"session": "us_active", "session_quality": 0.9, "is_weekend": False}
        mock_events.return_value = {"event_risk": 0.0, "in_pre_event_window": False, "surprise_zscore": 0.0}
        mock_macro.return_value = {"fear_greed_norm": 0.5, "dxy_momentum": 0.0, "funding_rate_norm": 0.5, "funding_rate": 0.0, "fear_greed": 50}
        mock_sent.return_value = {"score": 0.1, "label": "neutral", "count": 1}
        mock_validate.return_value = {"divergence_pct": 0.001, "data_quality": "ok", "trade_allowed": True, "reference_price": 100.0, "reference_source": "binance_spot"}

        ctx = build_context("BTCUSD", 100000.0)
        self.assertEqual(ctx["symbol"], "BTCUSD")
        self.assertEqual(ctx["data_quality"], "ok")

    @patch("intelligence.validation.price_validator.fetch_spot_ticker")
    def test_price_validator_btc(self, mock_ticker):
        mock_ticker.return_value = {"mid": 65000.0, "bid": 64990.0, "ask": 65010.0, "source": "binance_spot"}
        result = validate_symbol("BTCUSD", 65005.0)
        self.assertEqual(result["data_quality"], "ok")
        self.assertLess(result["divergence_pct"], 0.003)

    def test_plausible_reference_rejects_test_prices(self):
        self.assertFalse(is_plausible_reference("BTCUSD", 100.0))
        self.assertTrue(is_plausible_reference("BTCUSD", 65000.0))

    @patch("intelligence.context_builder.build_context")
    @patch("intelligence.context_builder.get_latest_context")
    def test_resolve_context_rebuilds_stale_cache(self, mock_cached, mock_build):
        mock_cached.return_value = {
            "symbol": "BTCUSD",
            "reference_price": 100.0,
            "checked_at": "2020-01-01T00:00:00+00:00",
        }
        mock_build.return_value = {"symbol": "BTCUSD", "reference_price": 65000.0}
        ctx = resolve_context("BTCUSD")
        mock_build.assert_called_once()
        self.assertEqual(ctx["reference_price"], 65000.0)


if __name__ == "__main__":
    unittest.main()
