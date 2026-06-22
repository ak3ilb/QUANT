"""DuckDB sync manifest: track 1-year historical fetch progress per symbol/interval."""
import json
import os
from datetime import datetime, timezone

import duckdb

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quant_vault.duckdb")

SYMBOLS = ["BTCUSD", "XAUUSD"]
TIMEFRAMES = ["1m", "3m", "5m", "15m", "1h", "4h", "1d"]

EXPECTED_BARS_YEAR = {
    "1m": 470_000,
    "3m": 157_000,
    "5m": 94_000,
    "15m": 31_000,
    "1h": 7_800,
    "4h": 1_950,
    "1d": 330,
}

XAU_INTRADAY_LIMITS = {
    "1m": 5_000,
    "3m": 5_000,
    "5m": 5_000,
    "15m": 12_000,
    "1h": 7_800,
    "4h": 1_950,
    "1d": 330,
}

MAX_ATTEMPTS = 20
_CONNECT_RETRIES = 5
_CONNECT_RETRY_SLEEP = 2.0


def _connect(read_only: bool = False):
    import time

    last_err = None
    for attempt in range(1, _CONNECT_RETRIES + 1):
        try:
            return duckdb.connect(database=DB_PATH, read_only=read_only)
        except Exception as e:
            last_err = e
            if "lock" not in str(e).lower() and attempt == 1:
                raise
            time.sleep(_CONNECT_RETRY_SLEEP * attempt)
    raise last_err


def init_manifest_tables():
    con = _connect(read_only=False)
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS data_sync_manifest (
                symbol VARCHAR,
                interval VARCHAR,
                target_bars INTEGER,
                stored_bars INTEGER,
                first_time TIMESTAMP,
                last_time TIMESTAMP,
                source VARCHAR,
                status VARCHAR,
                last_error VARCHAR,
                attempts INTEGER,
                next_retry_at TIMESTAMP,
                updated_at TIMESTAMP,
                PRIMARY KEY (symbol, interval)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS sync_run_log (
                id INTEGER PRIMARY KEY,
                run_id VARCHAR,
                event VARCHAR,
                symbol VARCHAR,
                interval VARCHAR,
                level VARCHAR,
                message VARCHAR,
                details VARCHAR,
                created_at TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS ml_training_runs (
                run_id VARCHAR PRIMARY KEY,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                status VARCHAR,
                metrics VARCHAR,
                model_path VARCHAR
            )
        """)
        try:
            con.execute("ALTER TABLE data_sync_manifest ADD COLUMN next_retry_at TIMESTAMP")
        except Exception:
            pass
        try:
            con.execute("CREATE SEQUENCE IF NOT EXISTS sync_run_log_id_seq START 1")
        except Exception:
            pass
    finally:
        con.close()


def required_bars(symbol: str, interval: str) -> int:
    if symbol == "XAUUSD" and interval in XAU_INTRADAY_LIMITS:
        return XAU_INTRADAY_LIMITS[interval]
    return EXPECTED_BARS_YEAR.get(interval, 1000)


def upsert_manifest(
    symbol: str,
    interval: str,
    stored_bars: int,
    first_time,
    last_time,
    source: str,
    status: str,
    last_error: str | None = None,
    attempts: int = 0,
    next_retry_at=None,
):
    con = _connect(read_only=False)
    try:
        con.execute(
            """
            INSERT INTO data_sync_manifest
            (symbol, interval, target_bars, stored_bars, first_time, last_time,
             source, status, last_error, attempts, next_retry_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (symbol, interval) DO UPDATE SET
                target_bars = EXCLUDED.target_bars,
                stored_bars = EXCLUDED.stored_bars,
                first_time = EXCLUDED.first_time,
                last_time = EXCLUDED.last_time,
                source = EXCLUDED.source,
                status = EXCLUDED.status,
                last_error = EXCLUDED.last_error,
                attempts = EXCLUDED.attempts,
                next_retry_at = EXCLUDED.next_retry_at,
                updated_at = EXCLUDED.updated_at
            """,
            [
                symbol, interval, required_bars(symbol, interval), stored_bars,
                first_time, last_time, source, status, last_error, attempts,
                next_retry_at, datetime.now(timezone.utc),
            ],
        )
    finally:
        con.close()


def log_run_event(run_id: str, event: str, level: str, message: str,
                  symbol: str | None = None, interval: str | None = None, details: dict | None = None):
    con = _connect(read_only=False)
    try:
        con.execute(
            """
            INSERT INTO sync_run_log (id, run_id, event, symbol, interval, level, message, details, created_at)
            VALUES (nextval('sync_run_log_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [run_id, event, symbol, interval, level, message, json.dumps(details or {}), datetime.now(timezone.utc)],
        )
    except Exception:
        try:
            con.execute(
                """
                INSERT INTO sync_run_log (run_id, event, symbol, interval, level, message, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [run_id, event, symbol, interval, level, message, json.dumps(details or {}), datetime.now(timezone.utc)],
            )
        except Exception:
            pass
    finally:
        con.close()


def get_recent_errors(limit: int = 20) -> list[dict]:
    con = _connect(read_only=True)
    try:
        df = con.execute(
            """
            SELECT run_id, event, symbol, interval, level, message, details, created_at
            FROM sync_run_log
            WHERE level IN ('ERROR', 'error')
            ORDER BY created_at DESC
            LIMIT ?
            """,
            [limit],
        ).df()
    finally:
        con.close()
    if df.empty:
        return []
    return df.to_dict(orient="records")


def get_manifest(symbol: str | None = None) -> list[dict]:
    con = _connect(read_only=True)
    try:
        if symbol:
            df = con.execute(
                "SELECT * FROM data_sync_manifest WHERE symbol = ? ORDER BY interval", [symbol],
            ).df()
        else:
            df = con.execute("SELECT * FROM data_sync_manifest ORDER BY symbol, interval").df()
    finally:
        con.close()
    if df.empty:
        return []
    return df.to_dict(orient="records")


def count_stored_bars(symbol: str, interval: str) -> tuple[int, object, object]:
    con = _connect(read_only=True)
    try:
        row = con.execute(
            """
            SELECT COUNT(*) AS n, MIN(time) AS first_time, MAX(time) AS last_time
            FROM market_data WHERE symbol = ? AND interval = ?
            """,
            [symbol, interval],
        ).fetchone()
    finally:
        con.close()
    return int(row[0]), row[1], row[2]


def all_complete() -> bool:
    return len(pending_jobs()) == 0


def pending_jobs(respect_backoff: bool = True) -> list[tuple[str, str]]:
    now = datetime.now(timezone.utc)
    manifest = {f"{r['symbol']}_{r['interval']}": r for r in get_manifest()}
    jobs = []
    for symbol in SYMBOLS:
        for interval in TIMEFRAMES:
            n, _, _ = count_stored_bars(symbol, interval)
            if n >= required_bars(symbol, interval):
                continue
            key = f"{symbol}_{interval}"
            row = manifest.get(key, {})
            if respect_backoff and row.get("next_retry_at"):
                retry_at = row["next_retry_at"]
                if hasattr(retry_at, "tzinfo") and retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                if retry_at > now:
                    continue
            jobs.append((symbol, interval))
    return jobs


def build_status_summary() -> dict:
    manifest = get_manifest()
    pending = pending_jobs(respect_backoff=True)
    blocked = pending_jobs(respect_backoff=False)
    total = len(SYMBOLS) * len(TIMEFRAMES)
    complete = total - len(blocked)
    errors = [r for r in manifest if r.get("status") == "error" or r.get("last_error")]
    return {
        "complete": all_complete(),
        "total_jobs": total,
        "complete_jobs": complete,
        "pending_jobs": len(pending),
        "blocked_by_backoff": len(blocked) - len(pending),
        "error_jobs": len(errors),
        "manifest": manifest,
        "pending": [{"symbol": s, "interval": i} for s, i in pending],
        "recent_errors": get_recent_errors(10),
    }


def record_ml_run(run_id: str, status: str, metrics: dict, model_path: str | None = None):
    con = _connect(read_only=False)
    try:
        con.execute(
            """
            INSERT INTO ml_training_runs (run_id, started_at, finished_at, status, metrics, model_path)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (run_id) DO UPDATE SET
                finished_at = EXCLUDED.finished_at,
                status = EXCLUDED.status,
                metrics = EXCLUDED.metrics,
                model_path = EXCLUDED.model_path
            """,
            [run_id, datetime.now(timezone.utc), datetime.now(timezone.utc), status, json.dumps(metrics), model_path],
        )
    finally:
        con.close()


init_manifest_tables()
