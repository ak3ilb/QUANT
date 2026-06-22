"""Unified intelligence context per symbol."""
from datetime import datetime, timezone

from intelligence.context.event_calendar import get_event_context
from intelligence.context.macro_features import get_macro_features
from intelligence.context.session_engine import get_session_context
from intelligence.nlp.sentiment_engine import rolling_sentiment
from intelligence.validation.price_validator import is_plausible_reference, validate_symbol
from intelligence_store import get_latest_context, store_context_snapshot

CONTEXT_MAX_AGE_S = 300


def build_context(symbol: str, primary_price: float | None = None) -> dict:
    symbol = symbol.upper()
    session = get_session_context(symbol)
    events = get_event_context(symbol)
    macro = get_macro_features(symbol)
    validation = validate_symbol(symbol, primary_price)
    sentiment = rolling_sentiment([symbol], hours=4)

    ctx = {
        "symbol": symbol,
        "session": session["session"],
        "session_quality": session["session_quality"],
        "is_weekend": session.get("is_weekend", False),
        "minutes_to_event": events.get("minutes_to_event"),
        "next_event": events.get("next_event"),
        "event_risk": events.get("event_risk", 0.0),
        "in_pre_event_window": events.get("in_pre_event_window", False),
        "surprise_zscore": events.get("surprise_zscore", 0.0),
        "fear_greed_norm": macro.get("fear_greed_norm", 0.5),
        "fear_greed": macro.get("fear_greed", 50),
        "dxy_momentum": macro.get("dxy_momentum", 0.0),
        "yields_momentum": macro.get("yields_momentum", 0.0),
        "funding_rate": macro.get("funding_rate", 0.0),
        "funding_rate_norm": macro.get("funding_rate_norm", 0.5),
        "open_interest": macro.get("open_interest"),
        "sentiment_1h": sentiment.get("score", 0.0),
        "sentiment_label": sentiment.get("label", "neutral"),
        "sentiment_count": sentiment.get("count", 0),
        "price_divergence": validation.get("divergence_pct", 0.0),
        "data_quality": validation.get("data_quality", "unknown"),
        "trade_allowed": validation.get("trade_allowed", True),
        "reference_price": validation.get("reference_price"),
        "reference_source": validation.get("reference_source"),
        "checked_at": validation.get("checked_at"),
    }

    store_context_snapshot(symbol, ctx)
    return ctx


def _context_age_s(ctx: dict) -> float | None:
    checked = ctx.get("checked_at")
    if not checked:
        return None
    try:
        ts = datetime.fromisoformat(str(checked).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - ts).total_seconds()
    except (TypeError, ValueError):
        return None


def context_is_stale(ctx: dict, symbol: str, max_age_s: int = CONTEXT_MAX_AGE_S) -> bool:
    if not ctx:
        return True
    ref = ctx.get("reference_price")
    if not is_plausible_reference(symbol, ref):
        return True
    age = _context_age_s(ctx)
    return age is None or age > max_age_s


def resolve_context(symbol: str, primary_price: float | None = None, max_age_s: int = CONTEXT_MAX_AGE_S) -> dict:
    """Return fresh context — rebuild when cached snapshot is stale or has implausible prices."""
    symbol = symbol.upper()
    cached = get_latest_context(symbol)
    if cached and not context_is_stale(cached, symbol, max_age_s=max_age_s):
        return cached
    return build_context(symbol, primary_price)


def context_to_regime(ctx: dict) -> dict:
    """Map intelligence context into regime dict for feature_builder / signal_engine."""
    return {
        "session_quality": ctx.get("session_quality", 0.5),
        "session": ctx.get("session", "unknown"),
        "minutes_to_event": ctx.get("minutes_to_event"),
        "event_risk": ctx.get("event_risk", 0.0),
        "in_pre_event_window": ctx.get("in_pre_event_window", False),
        "surprise_zscore": ctx.get("surprise_zscore", 0.0),
        "fear_greed_norm": ctx.get("fear_greed_norm", 0.5),
        "dxy_momentum": ctx.get("dxy_momentum", 0.0),
        "funding_rate_norm": ctx.get("funding_rate_norm", 0.5),
        "btc_sentiment_1h": ctx.get("sentiment_1h", 0.0) if ctx.get("symbol") == "BTCUSD" else 0.0,
        "gold_sentiment_1h": ctx.get("sentiment_1h", 0.0) if ctx.get("symbol") == "XAUUSD" else 0.0,
        "sentiment_1h": ctx.get("sentiment_1h", 0.0),
        "price_divergence": ctx.get("price_divergence", 0.0),
        "data_quality": ctx.get("data_quality", "unknown"),
        "trade_allowed": ctx.get("trade_allowed", True),
    }
