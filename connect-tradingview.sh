#!/usr/bin/env bash
# Connect TradingView Desktop to QUANT CDP bridge (run in macOS Terminal)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
CDP_PORT="${CDP_PORT:-9222}"
API_PORT="${API_PORT:-3001}"

echo "=== QUANT TradingView CDP Connector ==="

# Quit any existing TradingView so debug port can bind
if pgrep -x TradingView >/dev/null 2>&1; then
  echo "[1/4] Quitting existing TradingView..."
  osascript -e 'quit app "TradingView"' || true
  sleep 3
fi

echo "[2/4] Launching TradingView with remote debugging on port ${CDP_PORT}..."

# Method A: open with args (preferred on macOS)
if ! open -na "TradingView" --args --remote-debugging-port="${CDP_PORT}" 2>/dev/null; then
  # Method B: direct binary
  TV_BIN="/Applications/TradingView.app/Contents/MacOS/TradingView"
  if [[ -x "$TV_BIN" ]]; then
    "$TV_BIN" --remote-debugging-port="${CDP_PORT}" &
  else
    echo "ERROR: TradingView not found in /Applications"
    exit 1
  fi
fi

echo "      Waiting for CDP on http://localhost:${CDP_PORT} ..."
READY=0
for i in $(seq 1 45); do
  if curl -sf "http://127.0.0.1:${CDP_PORT}/json/version" >/dev/null 2>&1; then
    READY=1
    echo "      CDP ready (${i}s)"
    break
  fi
  sleep 1
done

if [[ "$READY" -ne 1 ]]; then
  echo ""
  echo "WARNING: CDP port ${CDP_PORT} did not open."
  echo "Some TradingView Mac builds block --remote-debugging-port."
  echo ""
  echo "Try manually:"
  echo "  1. Quit TradingView completely (Cmd+Q)"
  echo "  2. In Terminal, run:"
  echo "       open -na TradingView --args --remote-debugging-port=${CDP_PORT}"
  echo "  3. Open a chart tab (BTCUSD or XAUUSD)"
  echo "  4. Re-run: ./connect-tradingview.sh"
  echo ""
  read -r -p "Press Enter after you have a chart open, or Ctrl+C to abort..."
fi

# Ensure chart is open
if ! curl -sf "http://127.0.0.1:${CDP_PORT}/json/list" 2>/dev/null | grep -q '/chart/'; then
  echo "[3/4] Opening default BTCUSD chart..."
  open "https://www.tradingview.com/chart/?symbol=BINANCE:BTCUSD"
  sleep 5
fi

echo "[4/4] Starting CDP bridge on port ${API_PORT}..."
cd "$ROOT/cdp-bridge"
if lsof -i :"${API_PORT}" >/dev/null 2>&1; then
  echo "      CDP bridge already running on :${API_PORT}"
else
  echo "      Run in a separate terminal: ./start.sh cdp"
  echo "      Or: cd cdp-bridge && npm start"
fi

echo ""
echo "Verify:"
echo "  curl http://localhost:${CDP_PORT}/json/version"
echo "  curl http://localhost:${API_PORT}/health"
echo ""
echo "Then start matrix worker: ./start.sh matrix"
