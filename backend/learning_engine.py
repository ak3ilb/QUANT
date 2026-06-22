import json
import logging
import os
from datetime import datetime

import duckdb
import numpy as np
import pandas as pd

from algorithms.feature_builder import build_features

from algorithms.drift_detector import PageHinkleyDetector
from algorithms.online_logistic import (
  OnlineLogisticModel,
  deserialize_state,
  regime_to_features,
  serialize_state,
)
from intelligence.context_builder import context_to_regime
from algorithms.thompson_ensemble import (
  STRATEGIES,
  _default_bandit_state,
  bandit_summary,
  thompson_select_strategy,
  update_bandit,
)

DB_PATH = os.path.join(os.path.dirname(__file__), "quant_vault.duckdb")
_WALK_FORWARD_WINDOW = 20
_PROMOTE_MIN_TRADES = 10
_CONTEXT_OVERLAY_KEYS = (
  "session_quality",
  "event_risk",
  "sentiment_1h_norm",
  "minutes_to_event_norm",
  "fear_greed_norm",
  "turbulence_norm",
  "vix_norm",
  "price_divergence_norm",
)

_log = logging.getLogger(__name__)


class LearningEngine:
  """Continuous learning loop: Thompson bandit, online logistic, drift detection."""

  def __init__(self, db_path: str | None = None):
    self.db_path = db_path or DB_PATH
    self.bandit_state = _default_bandit_state()
    self.online_model = OnlineLogisticModel()
    self.candidate_model = OnlineLogisticModel()
    self.drift = PageHinkleyDetector()
    self.trade_history: list[dict] = []
    self.production_sharpe = 0.0
    self.candidate_sharpe = 0.0
    self.online_active = False
    self._init_db()
    self._load_state()

  def _connect(self, read_only: bool = False):
    return duckdb.connect(database=self.db_path, read_only=read_only)

  def _init_db(self):
    con = self._connect(read_only=False)
    try:
      con.execute(
        """
        CREATE TABLE IF NOT EXISTS learning_state (
          key VARCHAR PRIMARY KEY,
          value VARCHAR,
          updated_at TIMESTAMP
        )
        """
      )
    finally:
      con.close()

  def _load_kv(self, key: str) -> str | None:
    if not os.path.exists(self.db_path):
      return None
    con = self._connect(read_only=True)
    try:
      row = con.execute("SELECT value FROM learning_state WHERE key = ?", [key]).fetchone()
      return row[0] if row else None
    finally:
      con.close()

  def _save_kv(self, key: str, value: str):
    con = self._connect(read_only=False)
    try:
      con.execute(
        """
        INSERT INTO learning_state (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        [key, value, datetime.now()],
      )
    finally:
      con.close()

  def _load_state(self):
    bandit_raw = self._load_kv("bandit_state")
    if bandit_raw:
      try:
        self.bandit_state = json.loads(bandit_raw)
      except json.JSONDecodeError:
        pass

    self.online_model = deserialize_state(self._load_kv("online_model"))
    self.candidate_model = deserialize_state(self._load_kv("candidate_model"))

    drift_raw = self._load_kv("drift_state")
    if drift_raw:
      try:
        self.drift = PageHinkleyDetector.from_dict(json.loads(drift_raw))
      except (json.JSONDecodeError, TypeError):
        pass

    meta_raw = self._load_kv("learning_meta")
    if meta_raw:
      try:
        meta = json.loads(meta_raw)
        self.trade_history = meta.get("trade_history", [])
        self.production_sharpe = float(meta.get("production_sharpe", 0.0))
        self.candidate_sharpe = float(meta.get("candidate_sharpe", 0.0))
        self.online_active = bool(meta.get("online_active", False))
      except json.JSONDecodeError:
        pass

  def _persist_state(self):
    self._save_kv("bandit_state", json.dumps(self.bandit_state))
    self._save_kv("online_model", serialize_state(self.online_model))
    self._save_kv("candidate_model", serialize_state(self.candidate_model))
    self._save_kv("drift_state", json.dumps(self.drift.as_dict()))
    self._save_kv(
      "learning_meta",
      json.dumps(
        {
          "trade_history": self.trade_history[-200:],
          "production_sharpe": self.production_sharpe,
          "candidate_sharpe": self.candidate_sharpe,
          "online_active": self.online_active,
          "updated_at": datetime.now().isoformat(),
        }
      ),
    )

  @staticmethod
  def _rolling_sharpe(trades: list[dict], window: int = _WALK_FORWARD_WINDOW) -> float:
    if len(trades) < 5:
      return 0.0
    returns = [float(t.get("pnl_pct", 0.0)) for t in trades[-window:]]
    std = float(np.std(returns))
    if std <= 1e-9:
      return 0.0
    return float(np.mean(returns) / std)

  def select_strategy(self, signals: dict) -> tuple[str, dict, dict]:
    return thompson_select_strategy(signals, self.bandit_state)

  def size_multiplier(self) -> float:
    return self.drift.size_multiplier()

  def should_block_entry(self) -> bool:
    return self.drift.severity() == "severe"

  def reload_if_stale(self) -> None:
    """Reload persisted state (e.g. after another process updated DuckDB)."""
    self._load_state()

  @staticmethod
  def _overlay_context_features(entry_features: dict, context_snapshot: dict) -> dict:
    merged = {**entry_features}
    if not context_snapshot:
      return merged

    regime = context_snapshot.get("regime_features")
    if not regime:
      intel = context_snapshot.get("intelligence") or context_snapshot
      regime = context_to_regime(intel)

    timeline = context_snapshot.get("timeline") or {}
    if timeline.get("session_quality") is not None:
      regime["session_quality"] = timeline["session_quality"]

    news = context_snapshot.get("news") or {}
    if news.get("avg_sentiment") is not None:
      sym = str(context_snapshot.get("symbol", "BTCUSD")).upper()
      if "XAU" in sym:
        regime["gold_sentiment_1h"] = news["avg_sentiment"]
      else:
        regime["btc_sentiment_1h"] = news["avg_sentiment"]

    matrix = context_snapshot.get("matrix") or {}
    if matrix.get("current_price"):
      regime["current_price"] = matrix["current_price"]
    if matrix.get("sde_forecast"):
      regime["sde_forecast"] = matrix["sde_forecast"]

    close = float(regime.get("current_price") or 100.0)
    df = pd.DataFrame({"close": [close] * 60, "open": [close] * 60, "volume": [1000.0] * 60})
    full = build_features(df, regime)
    for key in _CONTEXT_OVERLAY_KEYS:
      if key in full:
        merged[key] = full[key]
    return merged

  def build_entry_features(self, tf_data: dict, fused: dict | None = None) -> dict:
    ctx = (fused or {}).get("intelligence") or tf_data.get("context") or {}
    regime = {
      "current_regime": tf_data.get("regime", "Unknown"),
      "confidence": 0.5,
      "curvature_value": tf_data.get("curvature_value", 0.0),
      "structural_break": tf_data.get("break", False),
      "berlekamp_up": 0,
      "cheeger_invariant": tf_data.get("cheeger_invariant", 0.5),
      "hyper_instability": tf_data.get("hyper_instability", False),
      "markov_p_up": tf_data.get("markov_p_up", 0.5),
      "kde_distance_pct": tf_data.get("kde_distance_pct", 0.0),
      "sde_forecast": tf_data.get("sde_forecast", tf_data.get("current_price", 0.0)),
      "kernel_p_value": tf_data.get("kernel_p_value", 1.0),
      "volume_imbalance": tf_data.get("volume_imbalance", 0.0),
      "buy_pressure": tf_data.get("buy_pressure", 0.5),
      "changepoint_prob": tf_data.get("changepoint_prob", 0.0),
      "kalman_z": tf_data.get("kalman_z", 0.0),
      "spread_zscore": tf_data.get("spread_zscore", 0.0),
      "cointegration_ready": abs(float(tf_data.get("spread_zscore", 0.0))) > 0,
      "current_price": tf_data.get("current_price", 0.0),
    }
    regime.update((fused or {}).get("regime_features") or context_to_regime(ctx))
    return regime_to_features(regime)

  def online_prob_bull(self, features: dict) -> float | None:
    if not self.online_active:
      return None
    return self.online_model.predict_prob(features)

  def on_trade_closed(self, trade: dict):
    strategy = trade.get("strategy", "medallion")
    won = bool(trade.get("won", float(trade.get("pnl_usd", 0.0)) > 0))
    pnl_pct = float(trade.get("pnl_pct", 0.0))
    direction = trade.get("direction", "BUY")
    entry_features = trade.get("entry_features") or {}
    context_snapshot = trade.get("context_snapshot") or {}

    self.bandit_state = update_bandit(self.bandit_state, strategy, won)
    self.drift.update(1.0 if won else 0.0)

    label = 1 if won else 0
    if entry_features:
      merged = self._overlay_context_features(entry_features, context_snapshot)
      self.candidate_model.partial_update(merged, label)

    record = {
      "trade_id": trade.get("trade_id"),
      "strategy": strategy,
      "won": won,
      "pnl_pct": pnl_pct,
      "direction": direction,
      "closed_at": datetime.now().isoformat(),
    }
    self.trade_history.append(record)

    self.candidate_sharpe = self._rolling_sharpe(self.trade_history)
    if len(self.trade_history) >= _PROMOTE_MIN_TRADES:
      if self.candidate_sharpe >= self.production_sharpe:
        self.online_model = self.candidate_model
        self.production_sharpe = self.candidate_sharpe
        self.online_active = True
      else:
        self.online_active = self.online_model.n_samples >= _PROMOTE_MIN_TRADES

    if won and self.drift.is_active():
      self.drift.clear()

    try:
      from ai.study.engine import get_study_engine
      get_study_engine().record_trade_closed({
        **trade,
        "strategy": strategy,
        "won": won,
        "pnl_pct": pnl_pct,
      })
    except Exception as exc:
      _log.warning("study event failed: %s", exc)

    self._persist_state()

  def get_stats(self) -> dict:
    self._load_state()
    return {
      "bandit": bandit_summary(self.bandit_state),
      "drift": self.drift.to_dict(),
      "online_model": {
        "active": self.online_active,
        "n_samples": self.online_model.n_samples,
        "candidate_samples": self.candidate_model.n_samples,
      },
      "walk_forward": {
        "production_sharpe": self.production_sharpe,
        "candidate_sharpe": self.candidate_sharpe,
        "trade_count": len(self.trade_history),
        "promote_min_trades": _PROMOTE_MIN_TRADES,
      },
      "strategies": STRATEGIES,
      "size_multiplier": self.size_multiplier(),
      "entry_blocked": self.should_block_entry(),
    }


_shared_engine: LearningEngine | None = None


def get_learning_engine() -> LearningEngine:
  global _shared_engine
  if _shared_engine is None:
    _shared_engine = LearningEngine()
  return _shared_engine
