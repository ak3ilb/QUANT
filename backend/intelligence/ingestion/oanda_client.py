"""OANDA v20 practice API client for XAU/USD cross-check."""
import os
import requests

OANDA_API_TOKEN = os.environ.get("OANDA_API_TOKEN", "")
OANDA_ACCOUNT_ID = os.environ.get("OANDA_ACCOUNT_ID", "")
OANDA_API_URL = os.environ.get("OANDA_API_URL", "https://api-fxpractice.oanda.com/v3")


def fetch_xau_quote(instrument: str = "XAU_USD") -> dict | None:
    if not OANDA_API_TOKEN:
        return None
    try:
        headers = {"Authorization": f"Bearer {OANDA_API_TOKEN}"}
        resp = requests.get(
            f"{OANDA_API_URL}/accounts/{OANDA_ACCOUNT_ID}/pricing"
            if OANDA_ACCOUNT_ID
            else f"{OANDA_API_URL}/accounts",
            params={"instruments": instrument} if OANDA_ACCOUNT_ID else None,
            headers=headers,
            timeout=8,
        )
        if not OANDA_ACCOUNT_ID:
            acct = resp.json().get("accounts", [{}])[0].get("id")
            if not acct:
                return None
            resp = requests.get(
                f"{OANDA_API_URL}/accounts/{acct}/pricing",
                params={"instruments": instrument},
                headers=headers,
                timeout=8,
            )
        if resp.status_code != 200:
            return None
        prices = resp.json().get("prices", [])
        if not prices:
            return None
        p = prices[0]
        bid = float(p["bids"][0]["price"])
        ask = float(p["asks"][0]["price"])
        return {"symbol": "XAUUSD", "bid": bid, "ask": ask, "mid": (bid + ask) / 2.0, "source": "oanda"}
    except Exception:
        return None
