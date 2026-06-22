# FinRL — Deep Reinforcement Learning for Trading

Source: [AI4Finance-Foundation/FinRL](https://github.com/AI4Finance-Foundation/FinRL) (MIT, ~15.5k stars, v0.3.8 Mar 2026)

## FinRL vs FinRL-X

| | FinRL (this repo) | FinRL-X / FinRL-Trading |
|--|-------------------|-------------------------|
| Purpose | Education, research | Production deployment |
| Paradigm | DRL only | ML + DRL + LLM-ready |
| Backtesting | Custom loops | `bt` library |
| Live trading | Basic Alpaca | Multi-account + risk controls |
| **Use FinRL for** | Learning, prototyping | Live production systems |

## Ecosystem

| Repo | Role |
|------|------|
| [FinRL](https://github.com/AI4Finance-Foundation/FinRL) | Train-test-trade pipeline |
| [FinRL-Meta](https://github.com/AI4Finance-Foundation/FinRL-Meta) | Gym environments & benchmarks |
| [ElegantRL](https://github.com/AI4Finance-Foundation/ElegantRL) | DRL algorithms |
| [FinRL-Trading](https://github.com/AI4Finance-Foundation/FinRL-Trading) | Production stack (FinRL-X) |
| [FinGPT](https://github.com/AI4Finance-Foundation/FinGPT) | Financial LLMs |

## Architecture

```
Data Processors → Gym Environments → DRL Agents → train.py / test.py / trade.py
```

### Data Layer (`finrl/meta/data_processors/`)

14 processors: Yahoo, **Binance**, **CCXT**, Alpaca, Akshare, Baostock, Tushare, etc.

### Environment Layer (`finrl/meta/env_*`)

| Env | Use case |
|-----|----------|
| `env_stock_trading` | Multi-stock allocation |
| `env_cryptocurrency_trading` | **BTC** — native |
| `env_portfolio_allocation` | Portfolio weights |
| HFT env | High-frequency (research) |

### Agent Layer (`finrl/agents/`)

| Backend | Algorithms |
|---------|------------|
| stablebaseline3 | A2C, DDPG, PPO, SAC, TD3 |
| elegantrl | Custom DRL |
| rllib | Distributed RL |

### Default Features (`meta_config.py`)

Indicators: `macd`, `boll_ub`, `boll_lb`, `rsi_30`, `dx_30`, `close_30_sma`, `close_60_sma`

Plus VIX and turbulence index in stock tutorials.

## 2026 Tutorial Workflow

```bash
git clone https://github.com/AI4Finance-Foundation/FinRL.git
cd FinRL && python3 -m venv venv && source venv/bin/activate
pip install -e .

python examples/FinRL_StockTrading_2026_1_data.py   # DOW 30 data
python examples/FinRL_StockTrading_2026_2_train.py  # Train 5 agents
python examples/FinRL_StockTrading_2026_3_Backtest.py # Backtest vs MVO
```

## Environment Anatomy

| Component | Description |
|-----------|-------------|
| **State** | OHLCV + indicators + portfolio state (+ custom features) |
| **Action** | Buy/sell/hold or continuous position sizing |
| **Reward** | PnL, Sharpe, or risk-adjusted return |
| **Done** | End of episode (day, session, or max steps) |

## Agent Comparison for Trading

| Agent | Strength | Weakness |
|-------|----------|----------|
| PPO | Stable, good default | Sample inefficient |
| SAC | Continuous actions | Sensitive to reward scale |
| A2C | Fast training | High variance |
| DDPG | Continuous control | Overestimates Q |
| TD3 | Reduced overestimation | Slower than PPO |

## Instrument Fit

| Instrument | Native? | Path |
|------------|---------|------|
| **BTC** | Yes | `cryptocurrency_trading` + Binance/CCXT |
| XAUUSD | No | Custom processor (OANDA/MT5) + new env |
| Nifty 50 | No | Kite Connect processor + fork stock env |
| Bank Nifty | No | Same as Nifty; lot 30, higher vol scaling |

## Custom Env Checklist (XAUUSD / Nifty / Bank Nifty)

- [ ] Data processor for broker API
- [ ] Session boundaries in `done` flag
- [ ] Transaction costs in reward (spread, STT, brokerage)
- [ ] Lot/pip sizing in action space
- [ ] Expiry day flags in state (Nifty/BankNifty)
- [ ] Walk-forward train/test splits (not single period)
- [ ] **Pattern features**: DTW distance to motif cluster as state dimension

## Pattern + FinRL Integration (Phase 2)

```python
# Conceptual state extension
state = [
    ...indicators,
    dtw_distance_to_bull_motif,
    dtw_distance_to_bear_motif,
    bocpd_regime_probability,
    motif_match_confidence,
]
```

Agent learns **when** to act on a pattern, not on a clock.

## DRL Pitfalls

- Overfitting to train period — use walk-forward
- Reward design matters — Sharpe reward ≠ PnL reward
- Transaction costs often understated in default envs
- Non-stationarity — 2014–2020 policy may fail 2022+
- DOW 30 tickers in config are 2019 snapshot (survivorship)
- No options/Greeks in default envs
- **Not financial advice** — MIT license disclaimer

## Papers

- FinRL: [arXiv:2011.09607](../research/papers/L5-shapelets-ml/2011.09607-finrl.pdf)
- FinRL-Meta: [arXiv:2211.03107](../research/papers/L5-shapelets-ml/2211.03107-finrl-meta.pdf)

See [reference/finrl-ecosystem.md](../reference/finrl-ecosystem.md).
