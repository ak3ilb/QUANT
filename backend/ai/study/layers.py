"""Algorithm layer taxonomy for the AI study dashboard."""
from __future__ import annotations

LAYER_ORDER = [
    "L1_regime",
    "L2_forecast",
    "L3_microstructure",
    "L4_signal",
    "L5_geometry",
    "L6_sequence",
    "L7_ml",
    "L8_nlp",
    "L9_execution",
]

LAYER_META = {
    "L1_regime": {"name": "Regime Detection", "description": "HMM, Markov, changepoint — market state"},
    "L2_forecast": {"name": "SDE Forecast", "description": "OU/GBM Monte Carlo price targets"},
    "L3_microstructure": {"name": "Microstructure", "description": "Volume flow, Kalman fair value, cointegration"},
    "L4_signal": {"name": "Signal Scoring", "description": "Logistic walk-forward, online model, strategy ensemble"},
    "L5_geometry": {"name": "Geometry Heuristics", "description": "Chern-Simons, Cheeger, Simons volatility proxies"},
    "L6_sequence": {"name": "Sequence", "description": "Berlekamp-Massey return sign patterns"},
    "L7_ml": {"name": "Machine Learning", "description": "Offline MLP + FinRL PPO policies"},
    "L8_nlp": {"name": "NLP / Intelligence", "description": "News sentiment, session context, impact scoring"},
    "L9_execution": {"name": "Execution Learning", "description": "Thompson bandit, drift detector, Kelly sizing"},
}

# Map registry / runtime ids → layer
ALGORITHM_LAYERS: dict[str, str] = {
    "hmm_baum_welch": "L1_regime",
    "bocpd_break": "L1_regime",
    "markov_chains": "L1_regime",
    "markov_chains": "L1_regime",
    "ornstein_uhlenbeck_sde": "L2_forecast",
    "geometric_brownian_motion_sde": "L2_forecast",
    "kernel_regression": "L2_forecast",
    "signed_volume_imbalance": "L3_microstructure",
    "kalman_fair_value": "L3_microstructure",
    "engle_granger_spread": "L3_microstructure",
    "logistic_scorer": "L4_signal",
    "medallion_signal": "L4_signal",
    "online_logistic": "L4_signal",
    "thompson_ensemble": "L4_signal",
    "chern_simons_gauge": "L5_geometry",
    "cheeger_simons_characters": "L5_geometry",
    "simons_hypersurface": "L5_geometry",
    "berlekamp_massey": "L6_sequence",
    "ml_mlp": "L7_ml",
    "finrl_ppo": "L7_ml",
    "intelligence_layer": "L8_nlp",
    "learning_engine": "L9_execution",
    "kelly_sizing": "L9_execution",
    "drift_detector": "L9_execution",
}

STRATEGY_LAYER = "L4_signal"
