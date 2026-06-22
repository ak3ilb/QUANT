"""Macro proxies: DXY, yields, funding, fear/greed."""
from intelligence.ingestion.binance_client import fetch_funding_rate, fetch_open_interest
from intelligence.ingestion.fear_greed_client import fetch_fear_greed


def _yfinance_change(ticker: str, period: str = "5d") -> float | None:
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period=period)
        if hist is None or len(hist) < 2:
            return None
        close = hist["Close"]
        return float((close.iloc[-1] - close.iloc[0]) / close.iloc[0])
    except Exception:
        return None


def get_macro_features(symbol: str) -> dict:
    symbol = symbol.upper()
    fear = fetch_fear_greed()
    fear_val = int(fear["value"]) if fear else 50
    fear_norm = fear_val / 100.0

    dxy_chg = _yfinance_change("DX-Y.NYB") or 0.0
    yields_chg = _yfinance_change("^TNX") or 0.0

    funding_rate = 0.0
    funding_norm = 0.5
    open_interest = None
    if symbol == "BTCUSD":
        fr = fetch_funding_rate("BTCUSDT")
        if fr:
            funding_rate = float(fr.get("funding_rate", 0))
            funding_norm = max(0.0, min(1.0, 0.5 + funding_rate * 500))
        oi = fetch_open_interest("BTCUSDT")
        if oi:
            open_interest = oi.get("open_interest")

    return {
        "fear_greed": fear_val,
        "fear_greed_norm": fear_norm,
        "fear_greed_label": fear.get("classification", "Neutral") if fear else "Neutral",
        "dxy_momentum": float(dxy_chg),
        "yields_momentum": float(yields_chg),
        "funding_rate": funding_rate,
        "funding_rate_norm": funding_norm,
        "open_interest": open_interest,
    }
