"""Cross-source price validation: TV primary vs Binance/OANDA reference."""
from datetime import datetime, timezone

from intelligence.ingestion.binance_client import fetch_spot_ticker
from intelligence.ingestion.oanda_client import fetch_xau_quote
from intelligence_store import store_price_quote, get_latest_quotes

DIVERGENCE_WARN_PCT = 0.003
DIVERGENCE_FAIL_PCT = 0.01
MIN_REFERENCE = {"BTCUSD": 1000.0, "XAUUSD": 500.0}


def is_plausible_reference(symbol: str, price: float | None) -> bool:
    if price is None or price <= 0:
        return False
    floor = MIN_REFERENCE.get(symbol.upper())
    return price >= floor if floor else True


def _vault_reference_price(symbol: str) -> tuple[float | None, str | None]:
    try:
        from data_vault import get_ohlcv

        df = get_ohlcv(symbol.upper(), "1h", bars=2)
        if df is None or df.empty:
            return None, None
        close = float(df["close"].iloc[-1])
        if is_plausible_reference(symbol, close):
            return close, "vault_close"
    except Exception:
        pass
    return None, None


def validate_symbol(symbol: str, primary_price: float | None) -> dict:
    symbol = symbol.upper()
    reference = None
    ref_source = None

    if symbol == "BTCUSD":
        quote = fetch_spot_ticker("BTCUSDT")
        if quote and is_plausible_reference(symbol, quote["mid"]):
            reference = quote["mid"]
            ref_source = "binance_spot"
            store_price_quote("BTCUSD", ref_source, reference, quote["bid"], quote["ask"])
    elif symbol == "XAUUSD":
        quote = fetch_xau_quote("XAU_USD")
        if quote and is_plausible_reference(symbol, quote["mid"]):
            reference = quote["mid"]
            ref_source = "oanda"
            store_price_quote("XAUUSD", ref_source, reference, quote["bid"], quote["ask"])

    if reference is None:
        reference, ref_source = _vault_reference_price(symbol)
        if reference is not None:
            store_price_quote(symbol, ref_source, reference, None, None)

    if primary_price and reference:
        store_price_quote(symbol, "tradingview", primary_price, None, None)

    divergence_pct = 0.0
    quality = "unknown"
    if primary_price and reference and primary_price > 0:
        divergence_pct = abs(primary_price - reference) / primary_price
        if divergence_pct >= DIVERGENCE_FAIL_PCT:
            quality = "fail"
        elif divergence_pct >= DIVERGENCE_WARN_PCT:
            quality = "warn"
        else:
            quality = "ok"
    elif primary_price:
        quality = "primary_only"
    elif reference:
        quality = "reference_only"

    return {
        "symbol": symbol,
        "primary_price": primary_price,
        "reference_price": reference,
        "reference_source": ref_source,
        "divergence_pct": float(divergence_pct),
        "data_quality": quality,
        "trade_allowed": quality in ("ok", "warn", "primary_only", "unknown"),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "quotes": get_latest_quotes(symbol),
    }


def get_data_quality_summary() -> dict:
    summary = {}
    for symbol in ("BTCUSD", "XAUUSD"):
        quotes = get_latest_quotes(symbol)
        tv = quotes.get("tradingview", {})
        ref_key = "binance_spot" if symbol == "BTCUSD" else "oanda"
        ref = quotes.get(ref_key, {})
        primary = tv.get("mid")
        reference = ref.get("mid")
        div = 0.0
        quality = "unknown"
        if primary and reference and primary > 0:
            div = abs(primary - reference) / primary
            quality = "fail" if div >= DIVERGENCE_FAIL_PCT else ("warn" if div >= DIVERGENCE_WARN_PCT else "ok")
        summary[symbol] = {
            "primary_price": primary,
            "reference_price": reference,
            "divergence_pct": div,
            "data_quality": quality,
        }
    return summary
