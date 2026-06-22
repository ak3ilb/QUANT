"""Economic event calendar: minutes_to_event, event_risk, surprise."""
from datetime import datetime, timezone

from intelligence_store import get_upcoming_events


def get_event_context(symbol: str, pre_event_minutes: int = 30) -> dict:
    symbol = symbol.upper()
    now = datetime.now(timezone.utc)
    events = get_upcoming_events(hours=48)

    relevant = []
    for ev in events:
        syms = ev.get("symbols") or []
        if symbol in syms or "BOTH" in syms:
            relevant.append(ev)

    minutes_to_event = None
    next_event = None
    event_risk = 0.0
    surprise_zscore = 0.0

    for ev in relevant:
        try:
            et = datetime.fromisoformat(str(ev["event_time"]).replace("Z", "+00:00"))
            if et.tzinfo is None:
                et = et.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        delta_min = (et - now).total_seconds() / 60.0
        if 0 <= delta_min <= 24 * 60:
            impact = ev.get("impact", "low")
            risk = {"high": 1.0, "medium": 0.6, "low": 0.2}.get(impact, 0.3)
            if minutes_to_event is None or delta_min < minutes_to_event:
                minutes_to_event = delta_min
                next_event = ev.get("name")
                event_risk = risk
        if ev.get("actual") is not None and ev.get("forecast") is not None:
            surprise = ev.get("surprise")
            if surprise is not None:
                surprise_zscore = max(-3.0, min(3.0, float(surprise)))

    in_pre_event_window = minutes_to_event is not None and 0 <= minutes_to_event <= pre_event_minutes

    return {
        "minutes_to_event": minutes_to_event,
        "next_event": next_event,
        "event_risk": event_risk,
        "in_pre_event_window": in_pre_event_window,
        "surprise_zscore": surprise_zscore,
        "upcoming_count": len(relevant),
    }
