import json
from typing import Any

import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler

from algorithms.feature_builder import FEATURE_NAMES, features_to_vector

_MIN_SAMPLES = 8
_BLEND_WEIGHT = 0.4


class OnlineLogisticModel:
  """Incremental logistic model updated from closed trade outcomes."""

  def __init__(self):
    self.model = SGDClassifier(
      loss="log_loss",
      penalty="l2",
      alpha=1e-4,
      max_iter=1000,
      tol=1e-3,
      random_state=42,
    )
    self.scaler = StandardScaler()
    self._fitted = False
    self.n_samples = 0

  def partial_update(self, features: dict, label: int) -> None:
    x = features_to_vector(features).reshape(1, -1)
    y = np.array([int(label)])

    if not self._fitted:
      self.scaler.partial_fit(x)
      x_scaled = self.scaler.transform(x)
      self.model.partial_fit(x_scaled, y, classes=np.array([0, 1]))
      self._fitted = True
    else:
      self.scaler.partial_fit(x)
      x_scaled = self.scaler.transform(x)
      self.model.partial_fit(x_scaled, y)

    self.n_samples += 1

  def predict_prob(self, features: dict) -> float | None:
    if not self._fitted or self.n_samples < _MIN_SAMPLES:
      return None

    x = features_to_vector(features).reshape(1, -1)
    x_scaled = self.scaler.transform(x)
    prob = float(self.model.predict_proba(x_scaled)[0][1])
    return max(0.01, min(0.99, prob))

  def to_dict(self) -> dict:
    if not self._fitted:
      return {"fitted": False, "n_samples": self.n_samples}

    return {
      "fitted": True,
      "n_samples": self.n_samples,
      "coef": self.model.coef_.tolist(),
      "intercept": self.model.intercept_.tolist(),
      "classes": self.model.classes_.tolist(),
      "scaler_mean": self.scaler.mean_.tolist() if hasattr(self.scaler, "mean_") and self.scaler.mean_ is not None else None,
      "scaler_scale": self.scaler.scale_.tolist() if hasattr(self.scaler, "scale_") and self.scaler.scale_ is not None else None,
      "scaler_n_samples_seen": int(getattr(self.scaler, "n_samples_seen_", 0)),
    }

  @classmethod
  def from_dict(cls, data: dict) -> "OnlineLogisticModel":
    online = cls()
    if not data or not data.get("fitted"):
      online.n_samples = int(data.get("n_samples", 0)) if data else 0
      return online

    online.n_samples = int(data.get("n_samples", 0))
    online.model.coef_ = np.array(data["coef"])
    online.model.intercept_ = np.array(data["intercept"])
    online.model.classes_ = np.array(data.get("classes", [0, 1]))
    online._fitted = True

    if data.get("scaler_mean") and data.get("scaler_scale"):
      online.scaler.mean_ = np.array(data["scaler_mean"])
      online.scaler.scale_ = np.array(data["scaler_scale"])
      online.scaler.n_samples_seen_ = int(data.get("scaler_n_samples_seen", online.n_samples))
      online.scaler.n_features_in_ = len(FEATURE_NAMES)

    return online


def blend_probabilities(walk_forward_prob: float, online_prob: float | None, online_active: bool) -> float:
  if online_prob is None or not online_active:
    return walk_forward_prob
  return max(0.01, min(0.99, (1.0 - _BLEND_WEIGHT) * walk_forward_prob + _BLEND_WEIGHT * online_prob))


def regime_to_features(regime: dict) -> dict:
  """Build feature dict from matrix regime snapshot (no OHLCV required)."""
  from algorithms.feature_builder import build_features
  import pandas as pd

  close = float(regime.get("current_price", regime.get("close", 100.0)))
  df = pd.DataFrame(
    {
      "close": [close] * 60,
      "open": [close] * 60,
      "volume": [float(regime.get("volume", 1000.0))] * 60,
    }
  )
  return build_features(df, regime)


def serialize_state(model: OnlineLogisticModel) -> str:
  return json.dumps(model.to_dict())


def deserialize_state(raw: str | None) -> OnlineLogisticModel:
  if not raw:
    return OnlineLogisticModel()
  try:
    return OnlineLogisticModel.from_dict(json.loads(raw))
  except (json.JSONDecodeError, KeyError, TypeError):
    return OnlineLogisticModel()
