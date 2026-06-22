#!/usr/bin/env bash
# Start QUANT services. Run each in a separate terminal, or use: ./start.sh all
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="${ROOT}/backend/venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi

start_tv() {
  cd "$ROOT/backend"
  "$PY" tv_launcher.py
}

start_backend() {
  cd "$ROOT/backend"
  source venv/bin/activate 2>/dev/null || true
  # Use PORT=8001 if Apache or another service occupies 8000
  PORT="${PORT:-8000}" python main.py
}

start_frontend() {
  cd "$ROOT/frontend"
  # Set NEXT_PUBLIC_API_BASE if backend is not on :8000
  NEXT_PUBLIC_API_BASE="${NEXT_PUBLIC_API_BASE:-http://localhost:8001/api}" npm run dev
}

start_cdp() {
  cd "$ROOT/cdp-bridge"
  npm start
}

start_matrix() {
  cd "$ROOT/backend"
  source venv/bin/activate 2>/dev/null || true
  python matrix_worker.py
}

start_trader() {
  cd "$ROOT/backend/paper_trader"
  source ../venv/bin/activate 2>/dev/null || true
  python execution_daemon.py
}

start_intelligence() {
  cd "$ROOT/backend"
  source venv/bin/activate 2>/dev/null || true
  python intelligence_worker.py
}

start_ai() {
  cd "$ROOT/backend"
  source venv/bin/activate 2>/dev/null || true
  python ai/worker.py
}

start_historical_sync() {
  cd "$ROOT/backend"
  source venv/bin/activate 2>/dev/null || true
  python historical_sync_cron.py "$@"
}

start_sync_watchdog() {
  cd "$ROOT/backend"
  source venv/bin/activate 2>/dev/null || true
  python sync_watchdog.py "$@"
}

case "${1:-}" in
  tv)       start_tv ;;
  backend)  start_backend ;;
  frontend) start_frontend ;;
  cdp)      start_cdp ;;
  matrix)   start_matrix ;;
  trader)   start_trader ;;
  intelligence) start_intelligence ;;
  ai) start_ai ;;
  historical-sync) shift; start_historical_sync "$@" ;;
  sync-watchdog) shift; start_sync_watchdog "$@" ;;
  all)
    echo "Start each service in its own terminal (in this order):"
    echo "  0. ./start.sh historical-sync --mode full   # overnight full sync + ML"
    echo "     ./start.sh historical-sync --mode tick  # one API-safe job"
    echo "  1. ./start.sh tv"
    echo "  2. ./start.sh cdp"
    echo "  3. ./start.sh matrix"
    echo "  4. ./start.sh intelligence"
    echo "  5. ./start.sh trader"
    echo "  6. ./start.sh backend"
    echo "  7. ./start.sh frontend"
    echo ""
    echo "Then open http://localhost:3000"
    ;;
  *)
    echo "Usage: ./start.sh {tv|cdp|matrix|intelligence|ai|historical-sync|sync-watchdog|trader|backend|frontend|all}"
    exit 1
    ;;
esac
