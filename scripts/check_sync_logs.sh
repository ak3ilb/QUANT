#!/usr/bin/env bash
# Quick helper to inspect historical sync logs and errors.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${ROOT}/logs"
BACKEND="${ROOT}/backend"
PY="${BACKEND}/venv/bin/python"

echo "=== Sync Status (manifest) ==="
cd "${BACKEND}" && "${PY}" historical_sync_cron.py --status 2>/dev/null || true

echo ""
echo "=== Latest status snapshot ==="
if [[ -f "${LOG_DIR}/historical_sync_status.json" ]]; then
  python3 -m json.tool "${LOG_DIR}/historical_sync_status.json" 2>/dev/null | head -60
else
  echo "(no snapshot yet — run sync first)"
fi

echo ""
echo "=== Last 15 errors (log file) ==="
if [[ -f "${LOG_DIR}/historical_sync_errors.log" ]]; then
  tail -n 15 "${LOG_DIR}/historical_sync_errors.log"
else
  echo "(no error log yet)"
fi

echo ""
echo "=== Last 20 sync events (main log) ==="
if [[ -f "${LOG_DIR}/historical_sync.log" ]]; then
  tail -n 20 "${LOG_DIR}/historical_sync.log"
else
  echo "(no main log yet)"
fi

echo ""
echo "=== Pipeline completion ==="
if [[ -f "${LOG_DIR}/historical_sync_pipeline_complete.json" ]]; then
  python3 -m json.tool "${LOG_DIR}/historical_sync_pipeline_complete.json" 2>/dev/null
  echo "(cron should be stopped — no more spinning)"
else
  echo "(pipeline still running or not started)"
fi

echo ""
echo "=== Recent DB errors (sync_run_log) ==="
cd "${BACKEND}" && "${PY}" -c "
from data.sync_manifest import get_recent_errors
for e in get_recent_errors(10):
    print(f\"{e.get('created_at')} | {e.get('symbol')} {e.get('interval')} | {e.get('message', '')[:120]}\")
" 2>/dev/null || echo "(DB not ready)"
