#!/usr/bin/env python3
"""
Cron-friendly historical data sync with rate limits, structured logs, and recovery.

Modes:
  --mode tick   Run ONE pending job then exit (safe for frequent cron, default)
  --mode status Log manifest + errors snapshot (hourly health check)
  --mode full   Retry loop until complete (manual / overnight)
  --mode ml     Train ML if all data complete

Logs:
  logs/historical_sync.log         — all events (rotating 5MB x5)
  logs/historical_sync_errors.log  — errors only
  logs/historical_sync_status.json — latest status snapshot
  DuckDB sync_run_log              — queryable error history
"""
import argparse
import os
import sys
import traceback
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))

from data.free_historical_fetcher import fetch_historical
from data.rate_limiter import backoff_seconds, job_delay, round_delay
from data.sync_logger import get_logger, log_event, write_status_snapshot
from data.sync_manifest import (
    MAX_ATTEMPTS,
    all_complete,
    build_status_summary,
    count_stored_bars,
    get_manifest,
    get_recent_errors,
    log_run_event,
    pending_jobs,
    required_bars,
    upsert_manifest,
)
from data.sync_completion import exit_if_pipeline_complete, mark_pipeline_complete, reset_pipeline_complete
from data_vault import store_ohlcv

LOCK_FILE = "/tmp/history_sync.lock"
MAX_ROUNDS_FULL = 50


def _acquire_lock() -> bool:
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as f:
                content = f.read()
            if "started=" in content:
                return False
        except OSError:
            return False
    with open(LOCK_FILE, "w") as f:
        f.write(f"pid={os.getpid()} started={datetime.now(timezone.utc).isoformat()}\n")
    return True


def _release_lock():
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
        except OSError:
            pass


def sync_job(symbol: str, interval: str, run_id: str, days_back: int = 365) -> bool:
    target = required_bars(symbol, interval)
    prev_count, _, _ = count_stored_bars(symbol, interval)
    manifest_rows = {f"{r['symbol']}_{r['interval']}": r for r in get_manifest(symbol)}
    key = f"{symbol}_{interval}"
    attempts = int(manifest_rows.get(key, {}).get("attempts") or 0) + 1

    log_event(
        "info", "job_start",
        run_id=run_id, symbol=symbol, interval=interval,
        attempt=attempts, need=target, have=prev_count,
    )
    log_run_event(run_id, "job_start", "INFO", f"Starting {symbol} {interval}", symbol, interval,
                  {"attempt": attempts, "target": target, "stored": prev_count})

    try:
        df = fetch_historical(symbol, interval, days_back=days_back)
        if df.empty:
            raise RuntimeError("Fetcher returned empty DataFrame")

        store_ohlcv(symbol, interval, df)
        stored, first_t, last_t = count_stored_bars(symbol, interval)
        source = df.attrs.get("source", "unknown")
        status = "complete" if stored >= target else "partial"
        upsert_manifest(symbol, interval, stored, first_t, last_t, source, status, None, attempts, None)

        log_event(
            "info", "job_done",
            run_id=run_id, symbol=symbol, interval=interval,
            stored=stored, status=status, source=source,
        )
        log_run_event(run_id, "job_done", "INFO", f"Stored {stored} bars", symbol, interval,
                      {"status": status, "source": source})
        return stored >= target

    except Exception as e:
        stored, first_t, last_t = count_stored_bars(symbol, interval)
        err_msg = str(e)[:500]
        retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds(attempts))
        upsert_manifest(
            symbol, interval, stored, first_t, last_t, "error",
            "error", err_msg, attempts, retry_at,
        )
        log_event(
            "error", "job_failed",
            run_id=run_id, symbol=symbol, interval=interval,
            error=err_msg, attempt=attempts, next_retry=retry_at.isoformat(),
        )
        log_run_event(run_id, "job_failed", "ERROR", err_msg, symbol, interval,
                      {"attempt": attempts, "traceback": traceback.format_exc()[-800:]})
        return False


def run_tick(days_back: int = 365) -> int:
    """One job per cron invocation — API-safe."""
    if exit_if_pipeline_complete("tick"):
        return 0

    run_id = f"tick_{uuid.uuid4().hex[:8]}"
    jobs = pending_jobs(respect_backoff=True)
    if not jobs:
        log_event("info", "tick_idle", run_id=run_id, message="All jobs complete or waiting backoff")
        _write_status(run_id)
        if all_complete():
            return run_ml_if_ready(run_id)
        return 0

    symbol, interval = jobs[0]
    log_event("info", "tick_start", run_id=run_id, pending=len(jobs), job=f"{symbol}/{interval}")
    sync_job(symbol, interval, run_id, days_back=days_back)
    _write_status(run_id)
    return 0  # never fail cron — errors are logged and retried next tick


def run_status() -> int:
    if exit_if_pipeline_complete("status"):
        return 0

    run_id = f"status_{uuid.uuid4().hex[:8]}"
    summary = _write_status(run_id)
    logger = get_logger()
    logger.info("=== Sync Status Check ===")
    logger.info(
        "complete=%s jobs=%s/%s pending=%s blocked_backoff=%s errors=%s",
        summary["complete"], summary["complete_jobs"], summary["total_jobs"],
        summary["pending_jobs"], summary["blocked_by_backoff"], summary["error_jobs"],
    )
    for row in summary.get("manifest", []):
        err = row.get("last_error") or ""
        logger.info(
            "%s %s %s/%s %s %s %s",
            row["symbol"], row["interval"], row["stored_bars"], row["target_bars"],
            row.get("status", ""), row.get("source", ""), err[:80],
        )
    recent = get_recent_errors(5)
    if recent:
        logger.warning("Recent errors (%d):", len(recent))
        for e in recent:
            logger.warning("  %s %s %s: %s", e.get("symbol"), e.get("interval"), e.get("created_at"), e.get("message", "")[:120])

    # Auto-trigger recovery when errors detected (no manual intervention)
    if summary.get("error_jobs", 0) > 0 or summary.get("pending_jobs", 0) > 0:
        logger.info("Auto-triggering watchdog recovery...")
        try:
            from sync_watchdog import run_watchdog
            run_watchdog(max_retries=1, train_if_done=False)
        except Exception as e:
            logger.error("Watchdog auto-recovery failed: %s", e)

    return 0


def run_full(days_back: int = 365, max_rounds: int = MAX_ROUNDS_FULL, train_on_complete: bool = True) -> int:
    if exit_if_pipeline_complete("full"):
        return 0

    run_id = f"full_{uuid.uuid4().hex[:8]}"
    log_event("info", "full_sync_start", run_id=run_id, max_rounds=max_rounds)

    for round_num in range(1, max_rounds + 1):
        jobs = pending_jobs(respect_backoff=True)
        if not jobs:
            log_event("info", "full_sync_done", run_id=run_id, rounds=round_num - 1)
            break

        log_event("info", "full_round", run_id=run_id, round=round_num, pending=len(jobs))
        any_failed = False
        for symbol, interval in jobs:
            ok = sync_job(symbol, interval, run_id, days_back=days_back)
            if not ok:
                manifest = {f"{r['symbol']}_{r['interval']}": r for r in get_manifest()}
                att = int(manifest.get(f"{symbol}_{interval}", {}).get("attempts", 0))
                if att < MAX_ATTEMPTS:
                    any_failed = True
            delay = job_delay()
            log_event("debug", "job_delay", seconds=round(delay, 1))

        _write_status(run_id)
        if not any_failed and all_complete():
            break
        if any_failed:
            rd = round_delay()
            log_event("info", "round_retry_wait", seconds=round(rd, 1))

    _write_status(run_id)
    if all_complete() and train_on_complete:
        return run_ml_if_ready(run_id)
    if not all_complete():
        log_event("warning", "full_sync_incomplete", run_id=run_id)
        return 0  # don't exit 1 — cron will keep ticking
    return 0


def run_ml_if_ready(run_id: str) -> int:
    if exit_if_pipeline_complete("ml"):
        return 0

    from ml.data.readiness import get_trainable_pairs

    pairs = get_trainable_pairs()
    if not pairs:
        log_event("info", "ml_skip", run_id=run_id, reason="no_trainable_pairs")
        return 0

    log_event("info", "ml_start", run_id=run_id, pairs=len(pairs))
    try:
        from ml.train.deep_trainer import run_training_pipeline
        ml_run_id = f"cron_{uuid.uuid4().hex[:8]}"
        result = run_training_pipeline(run_id=ml_run_id, pairs=pairs)
        if result.get("status") == "complete":
            log_event("info", "ml_done", run_id=run_id, ml_run_id=ml_run_id)
            log_run_event(run_id, "ml_done", "INFO", "ML training completed")
            if all_complete():
                mark_pipeline_complete(ml_run_id=ml_run_id, auto_uninstall_cron=True)
            return 0
        log_event("warning", "ml_incomplete", run_id=run_id, status=result.get("status"))
        return 0
    except Exception as e:
        log_event("error", "ml_failed", run_id=run_id, error=str(e)[:300])
        log_run_event(run_id, "ml_failed", "ERROR", str(e)[:500])
        return 0


def _write_status(run_id: str | None = None) -> dict:
    try:
        summary = build_status_summary()
    except Exception as e:
        log_event("warning", "status_write_skipped", run_id=run_id, error=str(e)[:200])
        return {"complete": False, "pending_jobs": -1, "error": str(e)[:200]}
    summary["run_id"] = run_id
    write_status_snapshot(summary)
    if run_id:
        log_run_event(run_id, "status_snapshot", "INFO", "Status updated",
                      details={"complete": summary["complete"], "pending": summary["pending_jobs"]})
    return summary


def print_status():
    from data.sync_completion import is_pipeline_complete, _load_flag

    summary = build_status_summary()
    pipeline_done = is_pipeline_complete()
    flag = _load_flag()

    print("=== Data Sync Manifest ===")
    if pipeline_done:
        print(f"PIPELINE COMPLETE (since {flag.get('completed_at', '?') if flag else '?'})")
        print("Cron/watchdog are stopped — use --reset to run again.\n")
    if not summary.get("manifest"):
        print("(no manifest rows — run sync first)")
    for row in summary.get("manifest", []):
        print(
            f"{row['symbol']:8} {row['interval']:4} "
            f"{row['stored_bars']:>7}/{row['target_bars']:<7} "
            f"{row['status']:10} {row.get('source', '')} "
            f"{row.get('last_error') or ''}"
        )
    print(f"\nPending: {summary['pending_jobs']} | Complete: {summary['complete']}")
    print(f"Status JSON: logs/historical_sync_status.json")


def main():
    parser = argparse.ArgumentParser(description="QUANT historical sync cron (rate-limited, logged)")
    parser.add_argument("--mode", choices=["tick", "status", "full", "ml"], default="tick",
                        help="tick=one job (cron), status=health check, full=run all, ml=train only")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--max-rounds", type=int, default=MAX_ROUNDS_FULL)
    parser.add_argument("--status", action="store_true", help="Print manifest (alias for --mode status)")
    parser.add_argument("--no-train", action="store_true")
    parser.add_argument("--symbol", type=str, default=None)
    parser.add_argument("--interval", type=str, default=None)
    parser.add_argument("--force", action="store_true", help="Ignore lock file")
    parser.add_argument("--reset", action="store_true", help="Clear completion flag and re-enable sync")
    args = parser.parse_args()

    if args.reset:
        reset_pipeline_complete()
        log_event("info", "pipeline_reset", message="Completion flag cleared — sync can run again")
        print("[SYNC] Pipeline reset. Re-install cron: ./scripts/install_historical_cron.sh")
        return

    if args.status:
        print_status()
        return

    if not args.force and not _acquire_lock():
        log_event("warning", "lock_busy", message="Another sync is running; skipping")
        print("[SYNC] Lock held — another sync running. Use --force to override.")
        sys.exit(0)

    try:
        if args.symbol and args.interval:
            run_id = f"single_{uuid.uuid4().hex[:8]}"
            ok = sync_job(args.symbol.upper(), args.interval, run_id, days_back=args.days)
            _write_status(run_id)
            sys.exit(0 if ok else 0)

        if args.mode == "tick":
            sys.exit(run_tick(days_back=args.days))
        if args.mode == "status":
            sys.exit(run_status())
        if args.mode == "ml":
            sys.exit(run_ml_if_ready(f"ml_{uuid.uuid4().hex[:8]}"))
        sys.exit(run_full(days_back=args.days, max_rounds=args.max_rounds, train_on_complete=not args.no_train))
    finally:
        _release_lock()


if __name__ == "__main__":
    main()
