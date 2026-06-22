"""Aggregate QUANT service health for the UI."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX_DIR = Path("/tmp")
LOCK_SYNC = "/tmp/history_sync.lock"


def _age_seconds(ts_str: str | None) -> float | None:
    if not ts_str:
        return None
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - ts).total_seconds()
    except (ValueError, TypeError):
        return None


def _matrix_status(symbol: str = "BTCUSD") -> dict:
    path = MATRIX_DIR / f"latest_matrix_{symbol}.json"
    if not path.exists():
        return {"status": "offline", "detail": "no matrix file"}
    try:
        with open(path) as f:
            data = json.load(f)
        age = _age_seconds(data.get("last_updated") or data.get("intelligence_updated"))
        intel_age = _age_seconds(data.get("intelligence_updated"))
        return {
            "status": "ok" if age is not None and age < 120 else "stale",
            "last_updated": data.get("last_updated"),
            "intelligence_updated": data.get("intelligence_updated"),
            "age_seconds": age,
            "intelligence_age_seconds": intel_age,
        }
    except (json.JSONDecodeError, OSError) as e:
        return {"status": "error", "detail": str(e)}


def get_services_status() -> dict:
    sync_status = {}
    status_json = ROOT.parent / "logs" / "historical_sync_status.json"
    if status_json.exists():
        try:
            with open(status_json) as f:
                sync_status = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    sync_running = os.path.exists(LOCK_SYNC)
    matrix_btc = _matrix_status("BTCUSD")
    matrix_xau = _matrix_status("XAUUSD")
    intel_age = matrix_btc.get("intelligence_age_seconds")
    intel_ok = intel_age is not None and intel_age < 180

    return {
        "fastapi": {"status": "ok"},
        "matrix_worker": {
            "status": matrix_btc.get("status", "unknown"),
            "btc": matrix_btc,
            "xau": matrix_xau,
        },
        "intelligence_worker": {
            "status": "ok" if intel_ok else "stale",
            "last_intelligence_update": matrix_btc.get("intelligence_updated"),
            "intelligence_age_seconds": intel_age,
        },
        "historical_sync": {
            "status": "running" if sync_running else "idle",
            "pipeline_complete": sync_status.get("complete", False),
            "pending_jobs": sync_status.get("pending_jobs"),
        },
        "paper_trader": {"status": "unknown", "note": "check paper-ledger API"},
        "finrl_drl": _finrl_status_brief(),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def _finrl_status_brief() -> dict:
    try:
        from ml.finrl.status import find_latest_model, vault_stats, _rl_deps_ok
        m = find_latest_model()
        btc = vault_stats("BTCUSD", "1h")
        return {
            "status": "ok" if m else "no_model",
            "latest_model": m,
            "btc_1h_bars": btc.get("bars", 0),
            "rl_deps": _rl_deps_ok()["installed"],
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)[:120]}
