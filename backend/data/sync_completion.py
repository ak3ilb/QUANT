"""Pipeline completion gate — stop cron/watchdog when data + ML are done."""
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "logs"
COMPLETE_FLAG = LOG_DIR / "historical_sync_pipeline_complete.json"
QUIET_LOG_MARKER = LOG_DIR / ".sync_complete_last_logged"

# Patterns removed from crontab when pipeline finishes
CRON_PATTERNS = (
    "sync_watchdog.py",
    "historical_sync_cron.py --mode tick",
    "historical_sync_cron.py --mode status",
    "historical_sync_cron.py --mode ml",
)


def _load_flag() -> dict | None:
    if not COMPLETE_FLAG.exists():
        return None
    try:
        with open(COMPLETE_FLAG, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def get_latest_ml_success() -> dict | None:
    from data.sync_manifest import _connect

    con = _connect(read_only=True)
    try:
        row = con.execute(
            """
            SELECT run_id, finished_at, status, metrics, model_path
            FROM ml_training_runs
            WHERE status = 'complete'
            ORDER BY finished_at DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        con.close()
    if not row:
        return None
    return {
        "run_id": row[0],
        "finished_at": str(row[1]),
        "status": row[2],
        "model_path": row[4],
    }


def is_pipeline_complete() -> bool:
    """True when 1yr data is stored AND ML training succeeded at least once."""
    flag = _load_flag()
    if flag and flag.get("complete"):
        return True

    from data.sync_manifest import all_complete

    if not all_complete():
        return False
    ml = get_latest_ml_success()
    if not ml:
        return False

    # Persist flag so future runs exit instantly without DB hits
    mark_pipeline_complete(
        data_complete=True,
        ml_run_id=ml["run_id"],
        auto_uninstall_cron=False,
        quiet=True,
    )
    return True


def _log_complete_once(mode: str, flag: dict | None = None):
    """Avoid log spam — at most one info line per calendar day."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        if QUIET_LOG_MARKER.exists() and QUIET_LOG_MARKER.read_text(encoding="utf-8").strip() == today:
            return
        QUIET_LOG_MARKER.write_text(today, encoding="utf-8")
    except OSError:
        pass

    from data.sync_logger import log_event

    log_event(
        "info", "pipeline_complete_skip",
        mode=mode,
        completed_at=(flag or {}).get("completed_at"),
        message="Pipeline finished — cron/watchdog will not run again",
    )


def exit_if_pipeline_complete(mode: str) -> bool:
    """
    Call at start of tick/watchdog/status/ml.
    Returns True if caller should exit immediately (no work, no spinning).
    """
    if not is_pipeline_complete():
        return False
    _log_complete_once(mode, _load_flag())
    return True


def uninstall_sync_cron() -> bool:
    """Remove historical sync lines from user crontab."""
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return False
        lines = result.stdout.splitlines()
        kept = [ln for ln in lines if not any(p in ln for p in CRON_PATTERNS)]
        if len(kept) == len(lines):
            return False
        subprocess.run(["crontab", "-"], input="\n".join(kept) + ("\n" if kept else ""), text=True, check=True)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def mark_pipeline_complete(
    data_complete: bool = True,
    ml_run_id: str | None = None,
    auto_uninstall_cron: bool = True,
    quiet: bool = False,
):
    """Write completion flag and optionally remove cron entries."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "complete": True,
        "data_complete": data_complete,
        "ml_run_id": ml_run_id,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "cron_removed": False,
    }

    if auto_uninstall_cron:
        payload["cron_removed"] = uninstall_sync_cron()

    with open(COMPLETE_FLAG, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    if not quiet:
        from data.sync_logger import log_event

        log_event(
            "info", "pipeline_complete",
            ml_run_id=ml_run_id,
            cron_removed=payload["cron_removed"],
            message="Historical sync pipeline finished — stopping scheduled jobs",
        )


def reset_pipeline_complete():
    """Clear completion flag so sync can run again (manual re-backfill)."""
    if COMPLETE_FLAG.exists():
        COMPLETE_FLAG.unlink()
    if QUIET_LOG_MARKER.exists():
        QUIET_LOG_MARKER.unlink()
