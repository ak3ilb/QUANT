"""Check which symbol/interval pairs have enough bars to train."""
from data.sync_manifest import SYMBOLS, TIMEFRAMES, count_stored_bars

DEFAULT_MIN_ROWS = 500
MIN_ROWS_OVERRIDE = {"BTCUSD": {"1d": 300}}


def min_rows_for(symbol: str, interval: str) -> int:
    return MIN_ROWS_OVERRIDE.get(symbol, {}).get(interval, DEFAULT_MIN_ROWS)


def assess_readiness(min_rows: int | None = None) -> list[dict]:
    rows = []
    for symbol in SYMBOLS:
        for interval in TIMEFRAMES:
            need = min_rows or min_rows_for(symbol, interval)
            n, first_t, last_t = count_stored_bars(symbol, interval)
            trainable = n >= need
            rows.append({
                "symbol": symbol,
                "interval": interval,
                "bars": n,
                "min_rows": need,
                "trainable": trainable,
                "reason": "ok" if trainable else f"need>={need}, have={n}",
                "first_time": str(first_t) if first_t else None,
                "last_time": str(last_t) if last_t else None,
            })
    return rows


def get_trainable_pairs(min_rows: int | None = None) -> list[tuple[str, str]]:
    return [(r["symbol"], r["interval"]) for r in assess_readiness(min_rows) if r["trainable"]]


def readiness_summary() -> dict:
    rows = assess_readiness()
    trainable = [r for r in rows if r["trainable"]]
    return {"total_pairs": len(rows), "trainable_count": len(trainable), "trainable": trainable, "all": rows}


if __name__ == "__main__":
    import json
    print(json.dumps(readiness_summary(), indent=2))
