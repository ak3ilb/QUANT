#!/usr/bin/env python3
"""
Auto-recovery watchdog for historical sync.

Runs on a short cron (every 5 min). When errors or stalled jobs are detected:
  1. Clears backoff on retryable failed jobs
  2. Auto-triggers sync tick(s) with rate-limit delays
  3. Logs recovery actions for debugging

This is the "auto trigger when something goes wrong" layer — no manual intervention.
"""
import argparse
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from data.rate_limiter import job_delay
from data.sync_logger import log_event, write_status_snapshot
from data.sync_manifest import (
    MAX_ATTEMPTS,
    all_complete,
    build_status_summary,
    get_manifest,
    log_run_event,
    pending_jobs,
    upsert_manifest,
)
from historical_sync_cron import _acquire_lock, _release_lock, run_ml_if_ready, sync_job


def find_recoverable_errors() -> list[tuple[str, str, dict]]:
    """Jobs with error status that can still be retried."""
    recoverable = []
    for row in get_manifest():
        if row.get("status") != "error" and not row.get("last_error"):
            continue
        attempts = int(row.get("attempts") or 0)
        if attempts >= MAX_ATTEMPTS:
            continue
        symbol, interval = row["symbol"], row["interval"]
        recoverable.append((symbol, interval, row))
    return recoverable


def clear_backoff(symbol: str, interval: str, row: dict, run_id: str):
    """Reset next_retry_at so job is eligible immediately."""
    upsert_manifest(
        symbol, interval,
        int(row.get("stored_bars") or 0),
        row.get("first_time"), row.get("last_time"),
        row.get("source") or "error",
        "retry_pending",
        row.get("last_error"),
        int(row.get("attempts") or 0),
        None,
    )
    log_event("info", "watchdog_clear_backoff", run_id=run_id, symbol=symbol, interval=interval)
    log_run_event(run_id, "watchdog_clear_backoff", "INFO",
                  f"Cleared backoff for {symbol} {interval}", symbol, interval)


def run_watchdog(max_retries: int = 2, days_back: int = 365, train_if_done: bool = True) -> int:
    from data.sync_completion import exit_if_pipeline_complete

    if exit_if_pipeline_complete("watchdog"):
        return 0

    run_id = f"watchdog_{uuid.uuid4().hex[:8]}"
    summary = build_status_summary()

    if summary["complete"]:
        log_event("info", "watchdog_data_done", run_id=run_id, message="Data complete, handing off to ML")
        write_status_snapshot({**summary, "watchdog": "data_complete", "run_id": run_id})
        if train_if_done:
            return run_ml_if_ready(run_id)
        return 0

    recoverable = find_recoverable_errors()
    blocked = summary.get("blocked_by_backoff", 0)

    log_event(
        "info", "watchdog_scan",
        run_id=run_id,
        pending=summary["pending_jobs"],
        errors=summary["error_jobs"],
        recoverable=len(recoverable),
        blocked_backoff=blocked,
    )

    if not recoverable and summary["pending_jobs"] == 0 and blocked > 0:
        log_event("info", "watchdog_waiting_backoff", run_id=run_id, blocked=blocked)
        write_status_snapshot({**summary, "watchdog": "waiting_backoff", "run_id": run_id})
        return 0

    if not _acquire_lock():
        log_event("warning", "watchdog_lock_busy", run_id=run_id)
        return 0

    try:
        triggered = 0
        for symbol, interval, row in recoverable[:max_retries]:
            clear_backoff(symbol, interval, row, run_id)
            log_event("info", "watchdog_auto_retry", run_id=run_id, symbol=symbol, interval=interval)
            sync_job(symbol, interval, run_id, days_back=days_back)
            triggered += 1
            if triggered < max_retries:
                job_delay()

        if triggered == 0 and summary["pending_jobs"] > 0:
            jobs = pending_jobs(respect_backoff=True)
            if jobs:
                symbol, interval = jobs[0]
                log_event("info", "watchdog_forward_tick", run_id=run_id, symbol=symbol, interval=interval)
                sync_job(symbol, interval, run_id, days_back=days_back)
                triggered = 1

        fresh = build_status_summary()
        fresh["watchdog"] = {
            "run_id": run_id,
            "triggered": triggered,
            "recoverable_remaining": len(find_recoverable_errors()),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        write_status_snapshot(fresh)

        log_event(
            "info", "watchdog_done",
            run_id=run_id, triggered=triggered,
            pending=fresh["pending_jobs"], complete=fresh["complete"],
        )
        log_run_event(run_id, "watchdog_done", "INFO", f"Triggered {triggered} recovery job(s)",
                      details={"triggered": triggered, "pending": fresh["pending_jobs"]})

        if fresh["complete"] and train_if_done:
            return run_ml_if_ready(run_id)
        return 0
    finally:
        _release_lock()


def main():
    parser = argparse.ArgumentParser(description="QUANT sync auto-recovery watchdog")
    parser.add_argument("--max-retries", type=int, default=2, help="Max jobs to retry per watchdog run")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--no-train", action="store_true")
    args = parser.parse_args()
    sys.exit(run_watchdog(
        max_retries=args.max_retries,
        days_back=args.days,
        train_if_done=not args.no_train,
    ))


if __name__ == "__main__":
    main()
