"""Model artifact registry — list and load saved MLP models (offline inference stub)."""
import pickle
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent.parent / "saved_models"


def list_models() -> list[dict]:
    if not MODEL_DIR.exists():
        return []
    out = []
    for path in sorted(MODEL_DIR.glob("*_mlp.pkl")):
        name = path.stem
        base = name.replace("_mlp", "")
        parts = base.rsplit("_", 1)
        symbol = parts[0] if len(parts) == 2 else name
        interval = parts[1] if len(parts) == 2 else "?"
        out.append({
            "key": name,
            "path": str(path),
            "symbol": symbol,
            "interval": interval,
            "size_bytes": path.stat().st_size,
        })
    return out


def load_mlp(symbol: str, interval: str) -> dict | None:
    path = MODEL_DIR / f"{symbol}_{interval}_mlp.pkl"
    if not path.exists():
        return None
    with open(path, "rb") as f:
        data = pickle.load(f)
    if not isinstance(data, dict) or "model" not in data:
        return None
    return data


def predict_proba(symbol: str, interval: str, features: list[float]) -> float | None:
    import numpy as np

    bundle = load_mlp(symbol, interval)
    if not bundle:
        return None
    model = bundle["model"]
    scaler = bundle.get("scaler")
    x = np.array(features, dtype=float).reshape(1, -1)
    if scaler is not None:
        x = scaler.transform(x)
    if hasattr(model, "predict_proba"):
        return float(model.predict_proba(x)[0, 1])
    return None
