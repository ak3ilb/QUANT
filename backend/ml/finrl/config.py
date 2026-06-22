"""FinRL-compatible configuration for QUANT crypto DRL."""
from __future__ import annotations

import os

# Paths (under backend/)
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_SAVE_DIR = os.path.join(_BASE, "ml", "finrl", "datasets")
TRAINED_MODEL_DIR = os.path.join(_BASE, "ml", "finrl", "trained_models")
TENSORBOARD_LOG_DIR = os.path.join(_BASE, "ml", "finrl", "tensorboard_log")
RESULTS_DIR = os.path.join(_BASE, "ml", "finrl", "results")

# Date splits (override per run)
TRAIN_START_DATE = "2024-01-01"
TRAIN_END_DATE = "2025-06-01"
TEST_START_DATE = "2025-06-01"
TEST_END_DATE = "2025-12-01"
TRADE_START_DATE = "2025-12-01"
TRADE_END_DATE = "2026-06-01"

# stockstats indicator names (FinRL default)
INDICATORS = [
    "macd",
    "boll_ub",
    "boll_lb",
    "rsi_30",
    "cci_30",
    "dx_30",
    "close_30_sma",
    "close_60_sma",
]

# QUANT symbol → FinRL tic / CCXT pair
SYMBOL_TO_TIC = {"BTCUSD": "BTCUSD", "XAUUSD": "XAUUSD"}
SYMBOL_TO_CCXT = {"BTCUSD": "BTC/USDT", "XAUUSD": None}

DEFAULT_SYMBOL = "BTCUSD"
DEFAULT_INTERVAL = "1h"
DEFAULT_TIMESTEPS = 50_000

# SB3 hyperparameters (from FinRL config.py)
A2C_PARAMS = {"n_steps": 5, "ent_coef": 0.01, "learning_rate": 0.0007}
PPO_PARAMS = {
    "n_steps": 2048,
    "ent_coef": 0.01,
    "learning_rate": 0.00025,
    "batch_size": 64,
}
DDPG_PARAMS = {"batch_size": 128, "buffer_size": 50000, "learning_rate": 0.001}
TD3_PARAMS = {"batch_size": 100, "buffer_size": 1000000, "learning_rate": 0.001}
SAC_PARAMS = {
    "batch_size": 64,
    "buffer_size": 100000,
    "learning_rate": 0.0001,
    "learning_starts": 100,
    "ent_coef": "auto_0.1",
}

MODEL_PARAMS = {
    "a2c": A2C_PARAMS,
    "ppo": PPO_PARAMS,
    "ddpg": DDPG_PARAMS,
    "td3": TD3_PARAMS,
    "sac": SAC_PARAMS,
}

# Env
INITIAL_CAPITAL = 1_000_000.0
BUY_COST_PCT = 0.001
SELL_COST_PCT = 0.001
LOOKBACK = 5
MIN_TRAIN_BARS = 2000
GAMMA = 0.99
