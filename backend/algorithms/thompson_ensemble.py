import numpy as np

STRATEGIES = ["nova", "piggy", "limroy", "dejavu", "medallion", "finrl_ppo"]


def _default_bandit_state() -> dict:
  return {strategy: {"alpha": 1.0, "beta": 1.0, "trades": 0} for strategy in STRATEGIES}


def thompson_select_strategy(
  signals: dict,
  bandit_state: dict | None = None,
  rng: np.random.Generator | None = None,
) -> tuple[str, dict, dict]:
  """
  Thompson sampling over strategies with actionable BUY/SELL signals.
  Falls back to medallion HOLD when nothing is actionable.
  """
  bandit_state = bandit_state or _default_bandit_state()
  rng = rng or np.random.default_rng()

  samples = {}
  for strategy in STRATEGIES:
    state = bandit_state.get(strategy, {"alpha": 1.0, "beta": 1.0})
    alpha = max(1e-3, float(state.get("alpha", 1.0)))
    beta = max(1e-3, float(state.get("beta", 1.0)))
    samples[strategy] = float(rng.beta(alpha, beta))

  actionable = {
    strategy: signals[strategy]
    for strategy in signals
    if strategy in signals and signals[strategy].get("action") in ("BUY", "SELL")
  }

  if not actionable:
    fallback = signals.get("medallion", {"action": "HOLD", "confidence": 0.5, "strategy": "medallion"})
    return "medallion", fallback, samples

  best_strategy = max(actionable.keys(), key=lambda s: samples[s])
  return best_strategy, actionable[best_strategy], samples


def update_bandit(bandit_state: dict, strategy: str, won: bool) -> dict:
  bandit_state = bandit_state or _default_bandit_state()
  state = bandit_state.setdefault(strategy, {"alpha": 1.0, "beta": 1.0, "trades": 0})
  if won:
    state["alpha"] = float(state.get("alpha", 1.0)) + 1.0
  else:
    state["beta"] = float(state.get("beta", 1.0)) + 1.0
  state["trades"] = int(state.get("trades", 0)) + 1
  return bandit_state


def bandit_summary(bandit_state: dict) -> dict:
  bandit_state = bandit_state or _default_bandit_state()
  summary = {}
  all_strategies = list(dict.fromkeys([*STRATEGIES, *bandit_state.keys()]))
  for strategy in all_strategies:
    state = bandit_state.get(strategy, {"alpha": 1.0, "beta": 1.0, "trades": 0})
    alpha = float(state.get("alpha", 1.0))
    beta = float(state.get("beta", 1.0))
    summary[strategy] = {
      "alpha": alpha,
      "beta": beta,
      "trades": int(state.get("trades", 0)),
      "expected_win_rate": alpha / (alpha + beta),
    }
  return summary
