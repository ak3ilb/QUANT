"""Offline evaluation report after ML training."""
import json
import os
from datetime import datetime, timezone

import numpy as np

from ml.data.dataset_builder import build_direction_dataset, train_test_split_time_series
from ml.models.registry import MODEL_DIR, load_mlp

EVAL_PATH = MODEL_DIR / "latest_eval.json"


def evaluate_model(symbol: str, interval: str) -> dict:
    bundle = load_mlp(symbol, interval)
    if not bundle:
        return {"symbol": symbol, "interval": interval, "error": "model_not_found"}
    try:
        x, y, _ = build_direction_dataset(symbol, interval)
        _, x_test, _, y_test = train_test_split_time_series(x, y)
        model = bundle["model"]
        scaler = bundle.get("scaler")
        x_te = scaler.transform(x_test) if scaler else x_test
        pred = model.predict(x_te)
        proba = model.predict_proba(x_te)[:, 1] if hasattr(model, "predict_proba") else pred.astype(float)
        return {
            "symbol": symbol,
            "interval": interval,
            "test_rows": int(len(y_test)),
            "accuracy": float(np.mean(y_test == pred)),
            "mean_proba": float(np.mean(proba)),
            "bull_rate_actual": float(np.mean(y_test)),
        }
    except Exception as e:
        return {"symbol": symbol, "interval": interval, "error": str(e)}


def write_eval_report(run_id: str, trained_keys: list[str]) -> dict:
    os.makedirs(MODEL_DIR, exist_ok=True)
    results = {}
    for key in trained_keys:
        if not key.endswith("_mlp"):
            continue
        base = key.replace("_mlp", "")
        parts = base.rsplit("_", 1)
        if len(parts) != 2:
            continue
        results[key] = evaluate_model(parts[0], parts[1])
    payload = {
        "run_id": run_id,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "models": results,
    }
    with open(EVAL_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    return payload


def read_eval_report() -> dict | None:
    if not EVAL_PATH.exists():
        return None
    with open(EVAL_PATH) as f:
        return json.load(f)
