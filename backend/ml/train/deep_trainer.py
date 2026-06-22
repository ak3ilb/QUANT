"""Deep / ML training pipeline."""
import json
import os
import pickle
from datetime import datetime, timezone

import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from data.sync_manifest import record_ml_run
from ml.data.dataset_builder import build_direction_dataset, train_test_split_time_series
from ml.data.readiness import get_trainable_pairs

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saved_models")
os.makedirs(MODEL_DIR, exist_ok=True)


def _train_mlp(x_train, y_train, x_test, y_test) -> dict:
    scaler = StandardScaler()
    x_tr = scaler.fit_transform(x_train)
    x_te = scaler.transform(x_test)
    model = MLPClassifier(
        hidden_layer_sizes=(128, 64, 32),
        activation="relu",
        max_iter=300,
        early_stopping=True,
        validation_fraction=0.1,
        random_state=42,
    )
    model.fit(x_tr, y_train)
    proba = model.predict_proba(x_te)[:, 1]
    pred = model.predict(x_te)
    metrics = {
        "accuracy": float(accuracy_score(y_test, pred)),
        "auc": float(roc_auc_score(y_test, proba)) if len(np.unique(y_test)) > 1 else 0.5,
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "model_type": "mlp_sklearn",
    }
    return {"model": model, "scaler": scaler, "metrics": metrics}


def train_pair(symbol: str, interval: str) -> dict:
    x, y, feature_names = build_direction_dataset(symbol, interval)
    x_train, x_test, y_train, y_test = train_test_split_time_series(x, y)
    mlp_result = _train_mlp(x_train, y_train, x_test, y_test)
    key = f"{symbol}_{interval}_mlp"
    model_path = os.path.join(MODEL_DIR, f"{key}.pkl")
    with open(model_path, "wb") as f:
        pickle.dump({
            "model": mlp_result["model"],
            "scaler": mlp_result["scaler"],
            "feature_names": feature_names,
            "symbol": symbol,
            "interval": interval,
        }, f)
    return {"key": key, "metrics": mlp_result["metrics"]}


def run_training_pipeline(run_id: str | None = None, pairs: list[tuple[str, str]] | None = None) -> dict:
    run_id = run_id or f"train_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    all_metrics = {}
    pairs = pairs or get_trainable_pairs()
    trained_keys = []

    for symbol, interval in pairs:
        try:
            print(f"[ML] Training {symbol} {interval}...")
            result = train_pair(symbol, interval)
            all_metrics[result["key"]] = result["metrics"]
            trained_keys.append(result["key"])
            print(f"[ML] {result['key']} acc={result['metrics']['accuracy']:.3f}")
        except Exception as e:
            all_metrics[f"{symbol}_{interval}"] = {"error": str(e)}
            print(f"[ML] Skip {symbol} {interval}: {e}")

    status = "complete" if trained_keys else "failed"
    record_ml_run(run_id, status, all_metrics, MODEL_DIR)
    summary_path = os.path.join(MODEL_DIR, "latest_metrics.json")
    with open(summary_path, "w") as f:
        json.dump({"run_id": run_id, "metrics": all_metrics, "status": status}, f, indent=2)

    from ml.evaluate.report import write_eval_report
    eval_report = write_eval_report(run_id, trained_keys)
    return {"run_id": run_id, "status": status, "metrics": all_metrics, "eval": eval_report}


if __name__ == "__main__":
    run_training_pipeline()
