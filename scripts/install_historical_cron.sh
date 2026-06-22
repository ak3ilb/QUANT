#!/usr/bin/env bash
# Install crontab entries for QUANT historical data sync.
# - Every 5 min: watchdog auto-retries errors
# - Every 15 min: one job (rate-limit safe)
# - Every hour: status health check (+ auto-recovery)
# - Daily 03:00 UTC: ML training if data complete
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT}/backend/venv/bin/python"
LOG_DIR="${ROOT}/logs"
mkdir -p "${LOG_DIR}"

WATCHDOG_CRON="*/5 * * * * cd ${ROOT}/backend && ${PY} sync_watchdog.py"
TICK_CRON="*/15 * * * * cd ${ROOT}/backend && ${PY} historical_sync_cron.py --mode tick"
STATUS_CRON="0 * * * * cd ${ROOT}/backend && ${PY} historical_sync_cron.py --mode status"
ML_CRON="0 3 * * * cd ${ROOT}/backend && ${PY} historical_sync_cron.py --mode ml"

install_line() {
  local pattern="$1"
  local line="$2"
  if ! crontab -l 2>/dev/null | grep -qF "$pattern"; then
    (crontab -l 2>/dev/null; echo "$line") | crontab -
    echo "Installed: $line"
  else
    echo "Already installed: $pattern"
  fi
}

install_line "sync_watchdog.py" "$WATCHDOG_CRON"
install_line "historical_sync_cron.py --mode tick" "$TICK_CRON"
install_line "historical_sync_cron.py --mode status" "$STATUS_CRON"
install_line "historical_sync_cron.py --mode ml" "$ML_CRON"

echo ""
echo "Cron schedule:"
echo "  */5 * * * *   — watchdog: auto-retry errors immediately"
echo "  */15 * * * *  — download ONE symbol/interval (45-90s delay between jobs)"
echo "  0 * * * *     — status check + auto-recovery trigger"
echo "  0 3 * * *     — ML training when data complete"
echo ""
echo "When data + ML finish, cron entries are REMOVED automatically."
echo "To run again: python historical_sync_cron.py --reset && ./scripts/install_historical_cron.sh"
echo ""
echo "Logs:"
echo "  ${LOG_DIR}/historical_sync.log"
echo "  ${LOG_DIR}/historical_sync_errors.log"
echo "  ${LOG_DIR}/historical_sync_status.json"
echo ""
echo "Manual commands:"
echo "  cd ${ROOT}/backend && ${PY} sync_watchdog.py"
echo "  cd ${ROOT}/backend && ${PY} historical_sync_cron.py --status"
echo "  cd ${ROOT}/backend && ${PY} historical_sync_cron.py --mode full"
echo "  ${ROOT}/scripts/check_sync_logs.sh"
