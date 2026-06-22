"""Standard CFD account profile (no commission, spread-only execution)."""

STANDARD_ACCOUNT = {
    "name": "Standard",
    "min_deposit_usd": 10.0,
    "initial_balance_usd": 100.0,
    "max_leverage": 2000,
    "commission_rate": 0.0,  # no commission
    "swap_rate": 0.0,
}

# Total bid-ask width in price units (not forex pip math for crypto)
SPREAD_WIDTH = {
    "BTCUSD": 0.20,
    "XAUUSD": 0.20,
}

# 1 lot = contract_size units of the base asset (Exness-style micro lots)
CONTRACT_SIZE = {
    "BTCUSD": 1.0,
    "XAUUSD": 1.0,
}

MIN_LOT = {
    "BTCUSD": 0.01,
    "XAUUSD": 0.01,
}

LOT_STEP = {
    "BTCUSD": 0.01,
    "XAUUSD": 0.01,
}


STOP_LOSS_MARGIN_PCT = 0.20  # max loss as fraction of margin (Standard CFD style)


def lots_to_qty(symbol: str, lots: float) -> float:
    return lots * CONTRACT_SIZE.get(symbol.upper(), 1.0)


def qty_to_lots(symbol: str, qty: float) -> float:
    cs = CONTRACT_SIZE.get(symbol.upper(), 1.0)
    return qty / cs if cs else qty


def spread_half(symbol: str) -> float:
    return SPREAD_WIDTH.get(symbol.upper(), 0.20) / 2.0
