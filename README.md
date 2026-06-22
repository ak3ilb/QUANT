# QUANT — Trader Knowledge Base

Structured reference for quantitative trading across **XAUUSD**, **BTC**, **Nifty 50**, and **Bank Nifty**, with emphasis on **pattern-native** methodology (DTW, motifs, regimes) rather than static timing backtests.

**Last updated:** June 2026

---

## Quick Reference

| Instrument | Market | Lot / Contract | Best Session (UTC) | Weekly Expiry |
|------------|--------|----------------|--------------------|---------------|
| [XAUUSD](docs/instruments/xauusd-gold.md) | Forex / OTC gold | 100 oz/std lot, $1/pip | 13:00–17:00 (London/NY) | N/A (Mon–Fri) |
| [BTC](docs/instruments/btc-bitcoin.md) | Crypto 24/7 | Perp / CME 5 BTC | 24/7 | N/A |
| [Nifty 50](docs/instruments/nifty50.md) | NSE F&O | 65 units, ₹65/point | 03:45–10:00 UTC | Every **Tuesday** |
| [Bank Nifty](docs/instruments/banknifty.md) | NSE F&O | 30 units, ₹30/point | 03:45–10:00 UTC | Monthly only |

---

## Documentation Map

### Core Quant

| Doc | Topic |
|-----|-------|
| [01 — Quant Fundamentals](docs/01-quant-fundamentals.md) | Workflow, metrics, backtest hygiene |
| [02 — Data & Infrastructure](docs/02-data-and-infrastructure.md) | APIs, timezones, storage |
| [03 — Risk & Position Sizing](docs/03-risk-and-position-sizing.md) | Kelly, VaR, drawdown rules |
| [04 — Strategy Frameworks](docs/04-strategy-frameworks.md) | Mean reversion, momentum, vol, Greeks |

### AI / Pattern Trading

| Doc | Topic |
|-----|-------|
| [05 — FinRL Deep RL](docs/05-finrl-deep-reinforcement-learning.md) | DRL train-test-trade pipeline |
| [06 — Pattern-Based Trading](docs/06-pattern-based-trading.md) | DTW → motifs → regimes (non-static BT) |

### Instruments

- [XAUUSD / Gold](docs/instruments/xauusd-gold.md)
- [BTC / Bitcoin](docs/instruments/btc-bitcoin.md)
- [Nifty 50](docs/instruments/nifty50.md)
- [Bank Nifty](docs/instruments/banknifty.md)

### Cross-Market

- [Session Calendar](docs/cross-market/session-calendar.md)
- [Instrument Comparison](docs/cross-market/instrument-comparison.md)
- [Correlation & Regimes](docs/cross-market/correlation-regime.md)

### Regulations

- [India — SEBI / NSE](docs/regulations/india-sebi-nse.md)
- [Global — Crypto & Forex](docs/regulations/global-crypto-forex.md)

### Research Papers

- [Papers Index](research/papers-index.md) — 22-paper bibliography with download status
- [PDF Library](research/papers/) — L1 (foundations) through L6 (trading apps)

### Reference

- [Glossary](reference/glossary.md)
- [Economic Calendar](reference/economic-calendar.md)
- [Broker / API Matrix](reference/broker-api-matrix.md)
- [FinRL Ecosystem](reference/finrl-ecosystem.md)

---

## Recommended Reading Order (Pattern-Native Quant)

1. **L1 Foundations** — DTW (Berndt & Clifford 1994), SAX, CID
2. **L2 Clustering** — TS-K-means + ANM-MM ([arXiv:2202.03146](research/papers/L2-clustering/2202.03146-ts-kmeans-anm-mm.pdf))
3. **L3 Motifs** — Matrix Profile, STOMP, VALMOD, SLIM
4. **L4 Regimes** — BOCPD, HMM regime switching
5. **L5 ML** — Shapelets, JISC-Net, FinRL
6. **L6 Trading** — DTW pattern matching, FX motif forecasting

See [06-pattern-based-trading.md](docs/06-pattern-based-trading.md) for the full stack.

---

## Phase 2 (Not Yet Built)

- Clone [FinRL](https://github.com/AI4Finance-Foundation/FinRL) + wire DTW/motif features as RL state
- Event-driven backtester (pattern trigger, not clock trigger)
- STUMPY + tslearn pipeline on historical BTC / Nifty data

---

## Disclaimer

This knowledge base is for **education and research** only. Nothing herein constitutes financial advice. Consult a qualified professional before deploying capital.
