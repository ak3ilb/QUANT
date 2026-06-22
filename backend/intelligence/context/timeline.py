"""Session timeline metadata — when sessions change and quality windows."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from intelligence.context.session_engine import get_session_context

_SESSION_BOUNDARIES = [0, 7, 13, 16, 17, 22]


def _minutes_until_next_boundary(hour: int, now: datetime) -> int:
    for boundary in _SESSION_BOUNDARIES:
        if hour < boundary:
            target = now.replace(hour=boundary, minute=0, second=0, microsecond=0)
            return max(0, int((target - now).total_seconds() // 60))
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(0, int((tomorrow - now).total_seconds() // 60))


def get_timeline_context(symbol: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    session = get_session_context(symbol, now)
    hour = session.get("utc_hour", now.hour)
    weekday = now.weekday()
    return {
        "utc_time": now.isoformat(),
        "utc_hour": hour,
        "weekday": weekday,
        "weekday_name": now.strftime("%A"),
        "active_session": session.get("session", "unknown"),
        "session_quality": session.get("session_quality", 0.5),
        "is_weekend": session.get("is_weekend", weekday >= 5),
        "minutes_until_session_change": _minutes_until_next_boundary(hour, now),
        "london_ny_overlap": 13 <= hour < 17 and weekday < 5,
        "asia_session": 0 <= hour < 8,
        "europe_session": 7 <= hour < 16,
        "us_session": 13 <= hour < 22,
    }
