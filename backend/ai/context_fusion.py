"""Fuse news, sessions, forecasts, broker state, and FinRL into one trade-time bundle."""
from __future__ import annotations

from datetime import datetime, timezone

from intelligence.context.timeline import get_timeline_context
from intelligence.context_builder import context_to_regime, resolve_context
from paper_trader.broker_config import STANDARD_ACCOUNT


def _news_summary(symbol: str, hours: int = 4) -> dict:
    try:
        from intelligence_store import get_headlines
        from intelligence.nlp.sentiment_engine import rolling_sentiment

        headlines = get_headlines([symbol], hours=hours, limit=30)
        sent = rolling_sentiment([symbol], hours=hours)
        impacts = [h for h in headlines if h.get("impact")]
        gates = {h.get("impact", {}).get("trade_gate") for h in impacts if h.get("impact")}
        return {
            "status": "ok" if headlines else "stale",
            "count": len(headlines),
            "avg_sentiment": sent.get("score", 0.0),
            "sentiment_label": sent.get("label", "neutral"),
            "impact_gates": sorted(g for g in gates if g),
            "top_headline": headlines[0].get("headline") if headlines else None,
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)[:120], "count": 0}


def _finrl_summary(symbol: str, interval: str = "1h") -> dict:
    try:
        from ml.finrl.status import get_paper_signal, vault_stats

        sig = get_paper_signal(symbol, interval)
        vs = vault_stats(symbol, interval)
        return {
            "action": sig.get("action", "HOLD"),
            "model_reliable": sig.get("model_reliable", False),
            "confidence": sig.get("confidence", 0.0),
            "confidence_kind": sig.get("confidence_kind", "action_strength"),
            "vault_bars": vs.get("bars", 0),
            "status": sig.get("status", "unknown"),
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)[:120]}


def _ohlcv_micro(symbol: str, interval: str = "1h", bars: int = 5) -> dict:
    try:
        from data_vault import get_ohlcv

        df = get_ohlcv(symbol.upper(), interval, bars=bars)
        if df is None or df.empty:
            return {"bars": 0}
        closes = df["close"].astype(float).tolist()
        ret = (closes[-1] - closes[0]) / closes[0] if closes[0] else 0.0
        return {"bars": len(closes), "last_close": closes[-1], "micro_return_pct": round(ret * 100, 4)}
    except Exception:
        return {"bars": 0}


def fuse_context(symbol: str, matrix_tf_data: dict | None = None, interval: str = "1h") -> dict:
    """Assemble full context bundle for learning, UI, and trade snapshots."""
    symbol = symbol.upper()
    matrix_tf_data = matrix_tf_data or {}
    now = datetime.now(timezone.utc)

    intel = resolve_context(symbol)
    timeline = get_timeline_context(symbol, now)
    news = _news_summary(symbol)
    finrl = _finrl_summary(symbol, interval)
    micro = _ohlcv_micro(symbol, interval)

    current_price = matrix_tf_data.get("current_price")
    sde_forecast = matrix_tf_data.get("sde_forecast")
    sde_div = 0.0
    if current_price and sde_forecast and current_price > 0:
        sde_div = (float(sde_forecast) - float(current_price)) / float(current_price)

    broker = {
        "account_type": STANDARD_ACCOUNT["name"],
        "initial_deposit_usd": STANDARD_ACCOUNT["initial_balance_usd"],
        "max_leverage": STANDARD_ACCOUNT["max_leverage"],
        "commission_rate": STANDARD_ACCOUNT["commission_rate"],
        "min_spread": 0.20,
    }

    bundle = {
        "symbol": symbol,
        "interval": interval,
        "fused_at": now.isoformat(),
        "intelligence": intel,
        "timeline": timeline,
        "news": news,
        "finrl": finrl,
        "ohlcv_micro": micro,
        "matrix": {
            "current_price": current_price,
            "sde_forecast": sde_forecast,
            "sde_divergence_pct": round(sde_div, 6),
            "regime": matrix_tf_data.get("regime"),
            "signals": matrix_tf_data.get("signals", {}),
            "kelly_recommended_pct": matrix_tf_data.get("kelly_recommended_pct"),
        },
        "broker": broker,
        "regime_features": context_to_regime(intel),
    }
    return bundle
