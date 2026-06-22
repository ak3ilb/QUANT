"""Crypto Fear & Greed Index from alternative.me."""
import requests


def fetch_fear_greed() -> dict | None:
    try:
        resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=8)
        if resp.status_code != 200:
            return None
        data = resp.json().get("data", [])
        if not data:
            return None
        item = data[0]
        return {
            "value": int(item.get("value", 50)),
            "classification": item.get("value_classification", "Neutral"),
            "timestamp": item.get("timestamp"),
            "source": "alternative_me",
        }
    except Exception:
        return None
