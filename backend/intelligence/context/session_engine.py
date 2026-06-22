"""UTC session flags per instrument (from session-calendar.md)."""
from datetime import datetime, timezone


def _hour_utc(now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    return now.hour


def get_session_context(symbol: str, now: datetime | None = None) -> dict:
    symbol = symbol.upper()
    now = now or datetime.now(timezone.utc)
    hour = _hour_utc(now)
    weekday = now.weekday()

    if symbol == "BTCUSD":
        if 13 <= hour < 22:
            session = "us_active"
            quality = 0.9
        elif 7 <= hour < 16:
            session = "europe_active"
            quality = 0.75
        elif 0 <= hour < 8:
            session = "asia_active"
            quality = 0.6
        else:
            session = "off_peak"
            quality = 0.55
        return {
            "session": session,
            "session_quality": quality,
            "is_weekend": weekday >= 5,
            "utc_hour": hour,
        }

    if symbol == "XAUUSD":
        if weekday >= 5:
            return {"session": "weekend", "session_quality": 0.3, "is_weekend": True, "utc_hour": hour}
        if 13 <= hour < 17:
            session, quality = "london_ny_overlap", 1.0
        elif 7 <= hour < 16:
            session, quality = "london", 0.85
        elif 17 <= hour < 22:
            session, quality = "new_york", 0.7
        elif 0 <= hour < 7:
            session, quality = "asia_thin", 0.35
        else:
            session, quality = "off_hours", 0.45
        return {
            "session": session,
            "session_quality": quality,
            "is_weekend": False,
            "utc_hour": hour,
        }

    return {"session": "unknown", "session_quality": 0.5, "is_weekend": False, "utc_hour": hour}
