"""Finnhub economic calendar client with JSON fallback."""
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

import requests

from intelligence_store import store_economic_event, get_upcoming_events

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")
FALLBACK_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "economic_calendar_fallback.json")

HIGH_IMPACT_KEYWORDS = ("cpi", "fomc", "nonfarm", "payroll", "ppi", "gdp", "rate decision")


def _tag_symbols(event_name: str) -> list[str]:
    name = event_name.lower()
    symbols = []
    if any(k in name for k in ("btc", "bitcoin", "crypto", "etf")):
        symbols.append("BTCUSD")
    if any(k in name for k in ("gold", "xau")):
        symbols.append("XAUUSD")
    if any(k in name for k in HIGH_IMPACT_KEYWORDS):
        symbols.extend(["BTCUSD", "XAUUSD"])
    return list(dict.fromkeys(symbols)) or ["BTCUSD", "XAUUSD"]


def _impact_level(raw: str) -> str:
    raw = (raw or "").lower()
    if raw in ("3", "high"):
        return "high"
    if raw in ("2", "medium"):
        return "medium"
    return "low"


def fetch_finnhub_calendar(days_ahead: int = 7) -> list[dict]:
    if not FINNHUB_API_KEY:
        return []
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        end = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        resp = requests.get(
            "https://finnhub.io/api/v1/calendar/economic",
            params={"from": today, "to": end, "token": FINNHUB_API_KEY},
            timeout=12,
        )
        if resp.status_code != 200:
            return []
        events = []
        for row in resp.json().get("economicCalendar", []):
            name = row.get("event", "Unknown")
            event_time = datetime.strptime(
                f"{row.get('date')} {row.get('time', '00:00')}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=timezone.utc)
            event_id = hashlib.md5(f"{name}_{event_time.isoformat()}".encode()).hexdigest()
            forecast = row.get("estimate")
            actual = row.get("actual")
            surprise = None
            if forecast is not None and actual is not None:
                try:
                    surprise = float(actual) - float(forecast)
                except (TypeError, ValueError):
                    surprise = None
            ev = {
                "event_id": event_id,
                "event_time": event_time,
                "name": name,
                "impact": _impact_level(str(row.get("impact", ""))),
                "symbols": _tag_symbols(name),
                "forecast": float(forecast) if forecast is not None else None,
                "actual": float(actual) if actual is not None else None,
                "surprise": surprise,
                "country": row.get("country", "US"),
                "source": "finnhub",
            }
            events.append(ev)
            store_economic_event(ev)
        return events
    except Exception:
        return []


def load_fallback_calendar() -> list[dict]:
    if not os.path.exists(FALLBACK_PATH):
        return []
    with open(FALLBACK_PATH) as f:
        templates = json.load(f)
    now = datetime.now(timezone.utc)
    events = []
    for tpl in templates:
        event_time = now.replace(
            hour=int(tpl.get("typical_utc_hour", 13)),
            minute=int(tpl.get("typical_utc_minute", 30)),
            second=0,
            microsecond=0,
        )
        if event_time < now:
            event_time += timedelta(days=1)
        event_id = hashlib.md5(f"{tpl['name']}_{event_time.date()}".encode()).hexdigest()
        ev = {
            "event_id": event_id,
            "event_time": event_time,
            "name": tpl["name"],
            "impact": tpl.get("impact", "medium"),
            "symbols": tpl.get("symbols", ["BTCUSD", "XAUUSD"]),
            "forecast": None,
            "actual": None,
            "surprise": None,
            "country": tpl.get("country", "US"),
            "source": "fallback",
        }
        events.append(ev)
        store_economic_event(ev)
    return events


def refresh_calendar() -> list[dict]:
    events = fetch_finnhub_calendar()
    if not events:
        events = load_fallback_calendar()
    return events
