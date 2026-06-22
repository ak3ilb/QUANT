import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from algorithms.feature_builder import (
    FEATURE_NAMES,
    build_features,
    features_to_vector,
    historical_feature_row,
)

from algorithms.online_logistic import blend_probabilities

_MIN_TRAIN_ROWS = 30
_DEFAULT_PROB = 0.5


def _walk_forward_prob(df: pd.DataFrame, regime: dict | None) -> float:
    """
    Walk-forward logistic model: price history + regime features -> P(next bar up).
    """
    regime = regime or {}
    if len(df) < 55:
        return _DEFAULT_PROB

    close = pd.to_numeric(df["close"], errors="coerce").dropna()
    if len(close) < 55:
        return _DEFAULT_PROB

    start = max(50, len(close) - 220)
    x_rows = []
    y_rows = []

    for i in range(start, len(close) - 1):
        x_rows.append(historical_feature_row(df, i))
        y_rows.append(1 if close.iloc[i + 1] > close.iloc[i] else 0)

    if len(x_rows) < _MIN_TRAIN_ROWS:
        return _DEFAULT_PROB

    x_train = np.vstack(x_rows)
    y_train = np.array(y_rows, dtype=int)

    if len(np.unique(y_train)) < 2:
        return _DEFAULT_PROB

    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x_train)

    model = LogisticRegression(max_iter=300, C=0.8, solver="lbfgs")
    model.fit(x_scaled, y_train)

    current_features = build_features(df, regime)
    x_current = features_to_vector(current_features).reshape(1, -1)
    x_current_scaled = scaler.transform(x_current)

    prob = float(model.predict_proba(x_current_scaled)[0][1])
    return max(0.01, min(0.99, prob))


def predict_prob_bull(df: pd.DataFrame, regime: dict | None = None) -> float:
    """Blend walk-forward logistic with online model when learning engine is active."""
    regime = regime or {}
    walk_forward = _walk_forward_prob(df, regime)

    try:
        from learning_engine import get_learning_engine
        engine = get_learning_engine()
        engine.reload_if_stale()
        features = build_features(df, regime)
        online = engine.online_prob_bull(features)
        return blend_probabilities(walk_forward, online, engine.online_active)
    except Exception:
        return walk_forward


def score_details(df: pd.DataFrame, regime: dict | None = None) -> dict:
    """Return probability plus the feature vector used for scoring."""
    regime = regime or {}
    features = build_features(df, regime)
    return {
        "prob_bull": predict_prob_bull(df, regime),
        "features": features,
        "feature_names": FEATURE_NAMES,
    }
