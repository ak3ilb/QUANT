import numpy as np
import pandas as pd


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _price_features(df: pd.DataFrame) -> dict:
    close = pd.to_numeric(df["close"], errors="coerce").dropna()
    if len(close) < 5:
        return {
            "momentum_5": 0.0,
            "momentum_20": 0.0,
            "volatility_20": 0.0,
            "rsi_norm": 0.5,
        }

    returns = close.pct_change().dropna()
    momentum_5 = _safe_float(returns.tail(5).mean(), 0.0)
    momentum_20 = _safe_float(returns.tail(20).mean(), 0.0) if len(returns) >= 20 else momentum_5
    volatility_20 = _safe_float(returns.tail(20).std(), 0.0) if len(returns) >= 5 else 0.0

    if "RSI_14" in df.columns:
        rsi = _safe_float(df["RSI_14"].iloc[-1], 50.0)
    else:
        rsi = 50.0

    return {
        "momentum_5": momentum_5,
        "momentum_20": momentum_20,
        "volatility_20": volatility_20,
        "rsi_norm": max(0.0, min(1.0, rsi / 100.0)),
    }


def build_features(df: pd.DataFrame, regime: dict | None = None) -> dict:
    """Build a named feature dict from OHLCV and matrix regime enrichment."""
    regime = regime or {}
    price_feats = _price_features(df)

    current_close = _safe_float(df["close"].iloc[-1], 0.0) if len(df) else 0.0
    sde_forecast = _safe_float(regime.get("sde_forecast", current_close), current_close)
    sde_divergence_pct = 0.0
    if current_close > 0:
        sde_divergence_pct = ((sde_forecast - current_close) / current_close) * 100.0

    curvature = _safe_float(regime.get("curvature_value", regime.get("cs_5d", 0.0)), 0.0)
    cheeger = _safe_float(regime.get("cheeger_invariant", 0.5), 0.5)
    kernel_p = _safe_float(regime.get("kernel_p_value", 1.0), 1.0)
    markov_p_up = _safe_float(regime.get("markov_p_up", 0.5), 0.5)
    kde_distance_pct = _safe_float(regime.get("kde_distance_pct", 0.0), 0.0)

    regime_state = str(regime.get("current_regime", "Unknown"))
    regime_conf = _safe_float(regime.get("confidence", 0.5), 0.5)
    if regime_state == "Bull":
        regime_bull_bias = regime_conf
    elif regime_state == "Bear":
        regime_bull_bias = 1.0 - regime_conf
    else:
        regime_bull_bias = 0.5

    berlekamp_up = int(regime.get("berlekamp_up", 0))
    structural_break = 1.0 if regime.get("structural_break", False) else 0.0
    hyper_instability = 1.0 if regime.get("hyper_instability", False) else 0.0

    volume_imbalance = _safe_float(regime.get("volume_imbalance", 0.0), 0.0)
    buy_pressure = _safe_float(regime.get("buy_pressure", 0.5), 0.5)
    changepoint_prob = _safe_float(regime.get("changepoint_prob", 0.0), 0.0)
    kalman_z = _safe_float(regime.get("kalman_z", 0.0), 0.0)
    spread_zscore = _safe_float(regime.get("spread_zscore", 0.0), 0.0)

    session_quality = _safe_float(regime.get("session_quality", 0.5), 0.5)
    event_risk = _safe_float(regime.get("event_risk", 0.0), 0.0)
    minutes_to_event = regime.get("minutes_to_event")
    minutes_norm = 1.0
    if minutes_to_event is not None:
        minutes_norm = max(0.0, min(1.0, float(minutes_to_event) / 120.0))
    surprise_z = _safe_float(regime.get("surprise_zscore", 0.0), 0.0)
    fear_greed_norm = _safe_float(regime.get("fear_greed_norm", 0.5), 0.5)
    dxy_momentum = _safe_float(regime.get("dxy_momentum", 0.0), 0.0)
    funding_rate_norm = _safe_float(regime.get("funding_rate_norm", 0.5), 0.5)
    sentiment_1h = _safe_float(
        regime.get("sentiment_1h", regime.get("btc_sentiment_1h", regime.get("gold_sentiment_1h", 0.0))),
        0.0,
    )
    price_divergence = _safe_float(regime.get("price_divergence", 0.0), 0.0)
    turbulence_norm = _safe_float(regime.get("turbulence_norm", 0.0), 0.0)
    vix_norm = _safe_float(regime.get("vix_norm", 0.5), 0.5)

    return {
        **price_feats,
        "curvature_norm": float(np.tanh(curvature / 500.0)),
        "structural_break": structural_break,
        "berlekamp_up": float(berlekamp_up),
        "cheeger_invariant": max(0.0, min(1.0, cheeger)),
        "hyper_instability": hyper_instability,
        "kernel_confidence": max(0.0, min(1.0, 1.0 - kernel_p)),
        "sde_divergence_pct": float(np.tanh(sde_divergence_pct / 2.0)),
        "markov_p_up": max(0.0, min(1.0, markov_p_up)),
        "kde_proximity": max(0.0, min(1.0, 1.0 - (kde_distance_pct / 5.0))),
        "regime_bull_bias": regime_bull_bias,
        "volume_imbalance": float(np.tanh(volume_imbalance * 3.0)),
        "buy_pressure": max(0.0, min(1.0, buy_pressure)),
        "changepoint_prob": max(0.0, min(1.0, changepoint_prob)),
        "kalman_z_norm": float(np.tanh(kalman_z / 2.5)),
        "spread_z_norm": float(np.tanh(spread_zscore / 2.5)),
        "session_quality": max(0.0, min(1.0, session_quality)),
        "event_risk": max(0.0, min(1.0, event_risk)),
        "minutes_to_event_norm": minutes_norm,
        "surprise_z_norm": float(np.tanh(surprise_z / 2.0)),
        "fear_greed_norm": max(0.0, min(1.0, fear_greed_norm)),
        "dxy_momentum_norm": float(np.tanh(dxy_momentum * 20.0)),
        "funding_rate_norm": max(0.0, min(1.0, funding_rate_norm)),
        "sentiment_1h_norm": float(np.tanh(sentiment_1h * 2.0)),
        "price_divergence_norm": max(0.0, min(1.0, price_divergence * 100.0)),
        "turbulence_norm": max(0.0, min(1.0, turbulence_norm)),
        "vix_norm": max(0.0, min(1.0, vix_norm)),
    }


FEATURE_NAMES = [
    "momentum_5",
    "momentum_20",
    "volatility_20",
    "rsi_norm",
    "curvature_norm",
    "structural_break",
    "berlekamp_up",
    "cheeger_invariant",
    "hyper_instability",
    "kernel_confidence",
    "sde_divergence_pct",
    "markov_p_up",
    "kde_proximity",
    "regime_bull_bias",
    "volume_imbalance",
    "buy_pressure",
    "changepoint_prob",
    "kalman_z_norm",
    "spread_z_norm",
    "session_quality",
    "event_risk",
    "minutes_to_event_norm",
    "surprise_z_norm",
    "fear_greed_norm",
    "dxy_momentum_norm",
    "funding_rate_norm",
    "sentiment_1h_norm",
    "price_divergence_norm",
    "turbulence_norm",
    "vix_norm",
]


def features_to_vector(features: dict) -> np.ndarray:
    return np.array([_safe_float(features.get(name, 0.0), 0.0) for name in FEATURE_NAMES], dtype=float)


def historical_feature_row(df: pd.DataFrame, index: int) -> np.ndarray:
    """Price-only features for walk-forward logistic training."""
    slice_df = df.iloc[: index + 1]
    feats = build_features(slice_df, regime={})
    return features_to_vector(feats)
