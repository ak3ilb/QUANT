# FinRL Ecosystem Reference

## Git submodule in QUANT

FinRL is vendored for learning only (not imported by QUANT production code):

```bash
# From QUANT repo root (after clone)
git submodule update --init --recursive

# Path
reference/FinRL/
```

Optional isolated venv to run FinRL tutorials:

```bash
cd reference/FinRL
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

### QUANT mapping (what to study vs what we build)

| FinRL | QUANT equivalent |
|-------|------------------|
| `finrl/meta/env_cryptocurrency_trading/` | `backend/ml/finrl/env_crypto.py` |
| `finrl/train.py` → `test.py` → `trade.py` | `ml/finrl/train.py` → `test.py` → `trade.py` (+ supervised `ml/train/runner.py`) |
| `finrl/meta/data_processors/` | `ml/finrl/processor.py` + `data_vault` + `free_historical_fetcher` |
| Technical indicators in meta_config | `ml/finrl/preprocessor.py` (stockstats) + `algorithms/feature_builder.py` |
| DRL agents (PPO/SAC) | `ml/finrl/agent_sb3.py` |

**Do not** add FinRL to `backend/requirements.txt` or import from `reference/FinRL` in live trading code.

## News & sentiment: FinRL vs QUANT

FinRL **does not ship** a news or NLP pipeline. Their FAQ (`docs/source/faq.rst`) states sentiment must be BYO — paid feeds or scrape + deep NLP.

| Capability | FinRL | QUANT |
|------------|-------|-------|
| News ingestion | None | `intelligence/rss_fetcher.py`, `ai/worker.py` |
| Sentiment scoring | None (points to FinGPT repo) | FinBERT / VADER in `intelligence/nlp/` |
| Headline → trade impact | None | `ai/nlp/impact_scorer.py` + `news_impact` table |
| API / UI | None | `/api/intelligence/headlines`, `NewsFeedPanel` |

**Takeaway:** Keep FinRL for DRL/env/data-fetch patterns; QUANT already leads on news intelligence. Optional later: [FinGPT](https://github.com/AI4Finance-Foundation/FinGPT) for LLM headline summarization (separate repo, not in FinRL core).

## Data fetching: FinRL patterns integrated in QUANT

| FinRL source | Pattern | QUANT implementation |
|--------------|---------|----------------------|
| `processor_yahoofinance.py` | Day-by-day yfinance for 1m (7-day API cap) | `data/finrl_patterns.fetch_yfinance_day_chunks` → `free_historical_fetcher.fetch_yfinance_history` |
| `processor_ccxt.py` | CCXT window pagination for crypto | `data/finrl_patterns.fetch_ccxt_ohlcv_optional` → BTC fallback chain |
| `preprocessors.py` | `^VIX` merge + 252-day turbulence (multi-asset Mahalanobis) | `fetch_vix_close`, `rolling_turbulence_proxy` → `ml/data/dataset_builder` + `feature_builder` (`vix_norm`, `turbulence_norm`) |
| `FeatureEngineer` | MACD/RSI via `stockstats` | Already in `algorithms/feature_builder` (RSI, momentum, vol) |
| `DataProcessor` facade | Single entry for Alpaca/Yahoo/WRDS | `free_historical_fetcher.fetch_historical` (Binance→Kraken→CCXT→yfinance) |

Production code lives in `backend/data/finrl_patterns.py` and `backend/ml/finrl/` — **reimplemented**, not `import finrl`.

## Full FinRL DRL stack (`backend/ml/finrl/`)

```bash
cd backend
pip install -r requirements-rl.txt   # gymnasium, stable-baselines3, ccxt

python -m ml.finrl.runner arrays --symbol BTCUSD --interval 1h --save
python -m ml.finrl.runner train --symbol BTCUSD --interval 1h --model ppo --timesteps 50000
python -m ml.finrl.runner test path/to/model.zip --model ppo
python -m ml.finrl.runner trade path/to/model.zip --paper
```

Supervised ML (`python -m ml.train.runner`) and DRL (`python -m ml.finrl.runner`) run in parallel.


| Repo | URL | Stars | Purpose |
|------|-----|-------|---------|
| FinRL | https://github.com/AI4Finance-Foundation/FinRL | ~15.5k | Classic train-test-trade DRL |
| FinRL-Meta | https://github.com/AI4Finance-Foundation/FinRL-Meta | — | Gym environments & benchmarks |
| ElegantRL | https://github.com/AI4Finance-Foundation/ElegantRL | — | Lightweight DRL algorithms |
| FinRL-Trading (FinRL-X) | https://github.com/AI4Finance-Foundation/FinRL-Trading | — | Production trading stack |
| FinGPT | https://github.com/AI4Finance-Foundation/FinGPT | — | Financial LLMs |

## When to Use Which

| User goal | Use |
|-----------|-----|
| Learn DRL for trading | FinRL |
| Custom Gym environments | FinRL-Meta |
| Algorithm research | ElegantRL |
| Live production deployment | FinRL-X / FinRL-Trading |
| NLP + finance | FinGPT |

## Installation

```bash
git clone https://github.com/AI4Finance-Foundation/FinRL.git
cd FinRL
python3 -m venv venv && source venv/bin/activate
pip install -e .
# Or: pip install finrl
```

Requirements: Python 3.6+, PyTorch, stable-baselines3.

## Key Config Files

| File | Purpose |
|------|---------|
| `finrl/config.py` | Main configuration |
| `finrl/config_tickers.py` | Ticker lists |
| `finrl/meta/meta_config.py` | Indicators, date ranges, DOW 30 list |
| `finrl/meta/meta_config_tickers.py` | Extended ticker configs |

Default indicators: `macd`, `boll_ub`, `boll_lb`, `rsi_30`, `dx_30`, `close_30_sma`, `close_60_sma`

## Folder Structure

```
finrl/
├── applications/
│   ├── stock_trading/
│   ├── cryptocurrency_trading/   ← BTC
│   ├── portfolio_allocation/
│   ├── high_frequency_trading/
│   └── imitation_learning/
├── agents/
│   ├── stablebaseline3/          ← A2C, PPO, SAC, DDPG, TD3
│   ├── elegantrl/
│   └── rllib/
├── meta/
│   ├── data_processors/          ← 14 data sources
│   ├── env_stock_trading/
│   ├── env_cryptocurrency_trading/
│   └── env_portfolio_allocation/
├── train.py
├── test.py
└── trade.py
```

## Papers (local PDFs)

- FinRL: [../research/papers/L5-shapelets-ml/2011.09607-finrl.pdf](../research/papers/L5-shapelets-ml/2011.09607-finrl.pdf)
- FinRL-Meta: [../research/papers/L5-shapelets-ml/2211.03107-finrl-meta.pdf](../research/papers/L5-shapelets-ml/2211.03107-finrl-meta.pdf)
- FinRL-X: [arXiv:2603.21330](https://arxiv.org/abs/2603.21330)

## Citation

```bibtex
@article{finrl2020,
    author  = {Liu, Xiao-Yang and Yang, Hongyang and others},
    title   = {{FinRL}: A deep reinforcement learning library for automated stock trading},
    journal = {Deep RL Workshop, NeurIPS 2020},
    year    = {2020}
}
```

## Community

- Discord: https://discord.gg/trsr8SXpW5
- Docs: https://finrl.readthedocs.io
- AI4Finance: https://ai4finance.org

## Integration with Pattern Stack

Phase 2: extend FinRL state vector with:
- `dtw_distance_bull_motif`
- `dtw_distance_bear_motif`
- `bocpd_regime_prob`
- `matrix_profile_discord_flag`

See [05-finrl-deep-reinforcement-learning.md](../docs/05-finrl-deep-reinforcement-learning.md).

## Disclaimer

MIT license. Not financial advice. Academic and research use.
