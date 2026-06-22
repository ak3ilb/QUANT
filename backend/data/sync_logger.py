"""Structured logging for historical sync cron — file + console, error tracking."""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # project root (QUANT/)
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

MAIN_LOG = LOG_DIR / "historical_sync.log"
ERROR_LOG = LOG_DIR / "historical_sync_errors.log"
STATUS_JSON = LOG_DIR / "historical_sync_status.json"

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 5

_logger: logging.Logger | None = None


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger("quant.historical_sync")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    main_handler = RotatingFileHandler(
        MAIN_LOG, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8",
    )
    main_handler.setFormatter(fmt)
    main_handler.setLevel(logging.DEBUG)

    err_handler = RotatingFileHandler(
        ERROR_LOG, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8",
    )
    err_handler.setFormatter(fmt)
    err_handler.setLevel(logging.ERROR)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    console.setLevel(logging.INFO)

    logger.addHandler(main_handler)
    logger.addHandler(err_handler)
    logger.addHandler(console)
    _logger = logger
    return logger


def log_event(level: str, event: str, **fields):
    logger = get_logger()
    payload = {"ts": _utcnow_iso(), "event": event, **fields}
    msg = f"{event} | {json.dumps({k: v for k, v in fields.items() if k != 'traceback'}, default=str)}"
    if level == "error":
        logger.error(msg)
    elif level == "warning":
        logger.warning(msg)
    elif level == "debug":
        logger.debug(msg)
    else:
        logger.info(msg)
    return payload


def write_status_snapshot(snapshot: dict):
    snapshot["updated_at"] = _utcnow_iso()
    with open(STATUS_JSON, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, default=str)


def read_status_snapshot() -> dict | None:
    if not STATUS_JSON.exists():
        return None
    try:
        with open(STATUS_JSON, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
