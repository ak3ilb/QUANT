"""Tag headlines with symbol and event entity labels."""

BTC_KEYWORDS = ("bitcoin", "btc", "crypto", "etf", "binance", "sec", "halving", "ethereum")
GOLD_KEYWORDS = ("gold", "xau", "bullion", "precious metal", "kitco")
MACRO_KEYWORDS = ("fed", "fomc", "cpi", "inflation", "nfp", "payroll", "rate", "treasury", "dxy", "yield")


def tag_headline(headline: str, default_symbols: list | None = None) -> list[str]:
    text = headline.lower()
    symbols = list(default_symbols or [])
    if any(k in text for k in BTC_KEYWORDS):
        if "BTCUSD" not in symbols:
            symbols.append("BTCUSD")
    if any(k in text for k in GOLD_KEYWORDS):
        if "XAUUSD" not in symbols:
            symbols.append("XAUUSD")
    if any(k in text for k in MACRO_KEYWORDS):
        for s in ("BTCUSD", "XAUUSD"):
            if s not in symbols:
                symbols.append(s)
    return symbols or ["BTCUSD", "XAUUSD"]


def tag_event_type(headline: str) -> list[str]:
    text = headline.lower()
    tags = []
    for kw in ("cpi", "fomc", "nfp", "ppi", "gdp", "war", "geopolit"):
        if kw in text:
            tags.append(kw)
    return tags
