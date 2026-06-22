"""
Auto-launch TradingView Desktop with Chrome DevTools Protocol on macOS.
"""
import os
import subprocess
import time
import urllib.request
import urllib.error

CDP_PORT = int(os.environ.get("CDP_PORT", "9222"))
CDP_HOST = os.environ.get("CDP_HOST", "127.0.0.1")
TV_APP_PATHS = [
    "/Applications/TradingView.app/Contents/MacOS/TradingView",
    os.path.expanduser("~/Applications/TradingView.app/Contents/MacOS/TradingView"),
]
DEFAULT_CHART_URL = "https://www.tradingview.com/chart/?symbol=BINANCE:BTCUSD"


def cdp_url(path="/json/version"):
    return f"http://{CDP_HOST}:{CDP_PORT}{path}"


def is_cdp_alive():
    try:
        with urllib.request.urlopen(cdp_url(), timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def has_chart_target():
    try:
        with urllib.request.urlopen(cdp_url("/json/list"), timeout=3) as resp:
            import json
            targets = json.loads(resp.read().decode())
            return any(t.get("url", "").find("/chart/") >= 0 for t in targets)
    except Exception:
        return False


def find_tv_binary():
    for path in TV_APP_PATHS:
        if os.path.isfile(path):
            return path
    return None


def launch_tradingview(wait_seconds=45):
    if is_cdp_alive():
        print(f"[TV] CDP already running on port {CDP_PORT}")
        return True

    binary = find_tv_binary()
    if not binary:
        print("[TV] TradingView binary not found. Install TradingView Desktop or set TV_APP_PATH.")
        return False

    # Quit existing instance so debug port can bind
    subprocess.run(
        ["osascript", "-e", 'quit app "TradingView"'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)

    print(f"[TV] Launching TradingView with --remote-debugging-port={CDP_PORT}")

    # macOS: prefer `open -na` so Electron receives chrome flags
    opened = subprocess.run(
        ["open", "-na", "TradingView", "--args", f"--remote-debugging-port={CDP_PORT}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if opened.returncode != 0:
        subprocess.Popen(
            [binary, f"--remote-debugging-port={CDP_PORT}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if is_cdp_alive():
            print(f"[TV] CDP ready on port {CDP_PORT}")
            return True
        time.sleep(1)

    print(f"[TV] CDP did not become ready within {wait_seconds}s")
    print("[TV] Run ./connect-tradingview.sh in Terminal, or manually:")
    print(f'       open -na TradingView --args --remote-debugging-port={CDP_PORT}')
    return False


def ensure_chart_open():
    if not is_cdp_alive():
        if not launch_tradingview():
            return False

    if has_chart_target():
        return True

    binary = find_tv_binary()
    if binary:
        print("[TV] Opening default chart — open a chart tab in TradingView if this fails")
        subprocess.Popen(
            ["open", "-a", "TradingView", DEFAULT_CHART_URL],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(5)
    return has_chart_target()


def ensure_tradingview_ready():
    ok = launch_tradingview()
    if ok:
        ensure_chart_open()
    return ok


if __name__ == "__main__":
    success = ensure_tradingview_ready()
    raise SystemExit(0 if success else 1)
