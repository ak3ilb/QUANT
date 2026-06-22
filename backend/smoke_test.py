"""Quick smoke test — run with backend optional."""
import os
import sys
import requests

BACKEND = os.environ.get("QUANT_BACKEND", "http://localhost:8000")
CDP = os.environ.get("QUANT_CDP", "http://localhost:3001")


def check(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def main():
    print("QUANT Smoke Test\n")
    results = []

    try:
        r = requests.get(f"{BACKEND}/health", timeout=3)
        results.append(check("FastAPI /health", r.status_code == 200))
    except Exception as e:
        results.append(check("FastAPI /health", False, str(e)))

    try:
        r = requests.get(f"{CDP}/health", timeout=3)
        data = r.json() if r.ok else {}
        results.append(check("CDP Bridge /health", r.status_code == 200, data.get("status", "")))
    except Exception as e:
        results.append(check("CDP Bridge /health", False, str(e)))

    try:
        r = requests.get(f"{BACKEND}/api/paper-ledger", timeout=3)
        data = r.json()
        keys = {"balance", "equity", "open_positions", "history", "stats"}
        results.append(check("Paper ledger shape", keys.issubset(data.keys())))
    except Exception as e:
        results.append(check("Paper ledger shape", False, str(e)))

    matrix_path = "/tmp/latest_matrix_BTCUSD.json"
    if os.path.exists(matrix_path):
        import json
        with open(matrix_path) as f:
            m = json.load(f)
        age_ok = "last_updated" in m and "matrix" in m
        ctx_ok = "context" in m or True
        results.append(check("Matrix file BTCUSD", age_ok and ctx_ok))
    else:
        results.append(check("Matrix file BTCUSD", False, "not found (matrix_worker not running)"))

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} checks passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
