"""Binance public REST client for BTC cross-check and futures metrics."""
import requests

SPOT_URL = "https://api.binance.com/api/v3"
FUTURES_URL = "https://fapi.binance.com/fapi/v1"


def fetch_spot_ticker(symbol: str = "BTCUSDT") -> dict | None:
    try:
        resp = requests.get(f"{SPOT_URL}/ticker/bookTicker", params={"symbol": symbol}, timeout=8)
        if resp.status_code != 200:
            return None
        data = resp.json()
        bid = float(data.get("bidPrice", 0))
        ask = float(data.get("askPrice", 0))
        if bid <= 0 or ask <= 0:
            return None
        return {"symbol": symbol, "bid": bid, "ask": ask, "mid": (bid + ask) / 2.0, "source": "binance_spot"}
    except Exception:
        return None


def fetch_funding_rate(symbol: str = "BTCUSDT") -> dict | None:
    try:
        resp = requests.get(f"{FUTURES_URL}/premiumIndex", params={"symbol": symbol}, timeout=8)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return {
            "symbol": symbol,
            "funding_rate": float(data.get("lastFundingRate", 0)),
            "mark_price": float(data.get("markPrice", 0)),
            "source": "binance_futures",
        }
    except Exception:
        return None


def fetch_open_interest(symbol: str = "BTCUSDT") -> dict | None:
    try:
        resp = requests.get(f"{FUTURES_URL}/openInterest", params={"symbol": symbol}, timeout=8)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return {"symbol": symbol, "open_interest": float(data.get("openInterest", 0)), "source": "binance_futures"}
    except Exception:
        return None
