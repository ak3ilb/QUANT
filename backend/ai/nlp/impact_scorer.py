"""Per-headline AI impact scoring — maps sentiment to trading impact."""
from intelligence_store import get_impact, store_impact


def score_headline_impact(
    headline_id: str,
    ensemble_score: float,
    label: str,
    symbols: list[str],
    context: dict | None = None,
) -> dict:
    context = context or {}
    session_quality = float(context.get("session_quality", 0.5))
    event_risk = float(context.get("event_risk", 0.0))
    in_pre_event = bool(context.get("in_pre_event_window", False))
    data_quality = str(context.get("data_quality", "ok"))
    trade_allowed = bool(context.get("trade_allowed", True))

    # Same nudge magnitude as signal_engine sentiment gate
    prob_bull_delta = 0.0
    if ensemble_score > 0.15:
        prob_bull_delta = 0.04
    elif ensemble_score < -0.15:
        prob_bull_delta = -0.04
    else:
        prob_bull_delta = ensemble_score * 0.1

    prob_bull_delta *= session_quality

    abs_score = abs(ensemble_score)
    if abs_score >= 0.35:
        strength = "high"
    elif abs_score >= 0.15:
        strength = "medium"
    else:
        strength = "low"

    if data_quality == "fail" or not trade_allowed:
        trade_gate = "block"
    elif in_pre_event and event_risk >= 0.6:
        trade_gate = "warn"
    else:
        trade_gate = "allow"

    impact_direction = label if label in ("bullish", "bearish", "neutral") else "neutral"

    result = {
        "headline_id": headline_id,
        "impact_direction": impact_direction,
        "prob_bull_delta": round(prob_bull_delta, 4),
        "impact_strength": strength,
        "affected_symbols": symbols or [],
        "session_modifier": round(session_quality, 3),
        "trade_gate": trade_gate,
        "ml_confidence": None,
    }
    store_impact(headline_id, result)
    return result


def enrich_headline_with_impact(headline: dict, context: dict | None = None) -> dict:
    existing = get_impact(headline.get("id", ""))
    if existing:
        return {**headline, "impact": existing}
    score = headline.get("ensemble_score")
    if score is None:
        return {**headline, "impact": None}
    impact = score_headline_impact(
        headline["id"],
        float(score),
        headline.get("label") or "neutral",
        headline.get("symbols") or [],
        context,
    )
    return {**headline, "impact": impact}
