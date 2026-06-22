"""Resolve best available mark price for paper trading (vault fallback when matrix is stale)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def _vault_mark(symbol: str) -> float | None:
    try:
        from data_vault import get_ohlcv
        for tf in ("1m", "5m", "1h"):
            df = get_ohlcv(symbol.upper(), tf, bars=2)
            if df is not None and not df.empty:
                return float(df["close"].iloc[-1])
    except Exception:
        pass
    return None


def _matrix_mark(symbol: str, interval: str = "1h") -> tuple[float | None, str | None]:
    path = f"/tmp/latest_matrix_{symbol.upper()}.json"
    if not os.path.exists(path):
        return None, None
    try:
        with open(path) as f:
            data = json.load(f)
        price = data.get("matrix", {}).get(interval, {}).get("current_price")
        updated = data.get("last_updated")
        return (float(price) if price else None), updated
    except Exception:
        return None, None


def _is_stale(updated_iso: str | None, max_age_sec: int = 300) -> bool:
    if not updated_iso:
        return True
    try:
        ts = datetime.fromisoformat(updated_iso.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        return age > max_age_sec
    except Exception:
        return True


def resolve_mark_price(symbol: str, matrix_price: float | None = None, interval: str = "1h") -> float:
    """
    Prefer fresh vault tick; use matrix when within 0.5% of vault.
    Matrix worker can freeze when history_sync.lock is held — vault stays current via CDP.
    """
    symbol = symbol.upper()
    vault = _vault_mark(symbol)
    matrix, updated = _matrix_mark(symbol, interval)
    mid = matrix_price if matrix_price is not None else matrix

    if vault is None and mid is not None:
        return mid
    if vault is not None and mid is None:
        return vault
    if vault is None and mid is None:
        return 0.0

    stale = _is_stale(updated)
    if stale:
        return vault

    if mid and mid > 0:
        divergence = abs(vault - mid) / mid
        if divergence > 0.005:
            return vault
    return mid if mid else vault
