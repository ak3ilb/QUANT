# BTC — Bitcoin

## Contract Specifications

| Venue | Symbol | Contract | Key Spec |
|-------|--------|----------|----------|
| Binance USDT-M Perp | BTCUSDT | Perpetual | No expiry; funding every 8h; up to 125x |
| CME BTC Futures | BTC | Regulated | 5 BTC/contract; monthly/quarterly; cash-settled to CME CF BRR |
| CME Micro BTC | MBT | Regulated | 0.10 BTC/contract; tick $0.50 |
| Spot | BTC/USD, BTC/USDT | — | Basis = futures − spot |

### Perp Funding Rate

- Charged every **8 hours** (00:00, 08:00, 16:00 UTC)
- Positive funding = longs pay shorts (bullish overcrowding)
- **Must model in backtests** as hidden carry cost
- Extreme funding (>0.1%/8h) often precedes mean reversion

### P&L Math (Spot / Perp)

```
P&L (USDT) = (exit - entry) × quantity_btc
Funding cost = position_value × funding_rate × periods_held
```

## Session Schedule

**24/7/365** — no market close. Weekend volatility is real.

| Period | UTC | Character |
|--------|-----|-----------|
| Asia active | 00:00–08:00 | Moderate; Korea/Japan flows |
| Europe | 07:00–16:00 | Moderate |
| US | 13:00–22:00 | Highest institutional volume |
| Weekend | Sat–Sun | Lower liquidity; gap risk on Sunday CME open |

Unlike gold, **do not filter out weekends** for BTC pattern mining.

## Volatility Profile

- Daily range: often **3–8%** in normal conditions; 10–20%+ in stress
- Fat tails stronger than equities
- Vol clustering (GARCH effects) pronounced
- Use **log returns** for modeling; price levels non-stationary

## Primary Price Drivers

| Driver | Signal type | Feature idea |
|--------|-------------|--------------|
| Fed / macro liquidity | Slow | DXY, real yields correlation (increasingly macro asset) |
| ETF flows (US spot ETFs) | Structural | Daily flow data as exogenous feature |
| Funding rate extremes | Fast | Contrarian when >95th percentile |
| On-chain (exchange flows, MVRV) | Slow | Regime filter, not entry trigger |
| Halving cycle | Very slow | Diminishing narrative impact post-ETF |
| Liquidation cascades | Fast | Non-linear; stop-clustering events |

## Microstructure & Execution

- Order book depth varies wildly by exchange
- Liquidation cascades create **non-linear** price moves
- Cross-exchange basis (Binance vs Coinbase vs CME) — arb opportunity
- Taker fees: ~0.04–0.10% depending on tier
- Model slippage on large orders in thin weekend books

## Data Sources

| Source | Granularity | Notes |
|--------|-------------|-------|
| Binance REST + WebSocket | Tick, trades, L2 book | Primary for perps |
| CCXT | Multi-exchange OHLCV | Unified wrapper |
| Coinbase Advanced | Spot | US-regulated |
| CME DataMine | Futures | Institutional |
| CryptoCompare / Kaiko | Aggregated | Paid institutional |

## Regulatory Notes

- CME = CFTC-regulated
- Binance = jurisdiction-dependent (geo-blocks)
- India: crypto taxation and exchange restrictions — check current SEBI/RBI rules
- US spot ETFs (2024+) changed structural flow dynamics

## Strategy Archetypes (Caveats Only)

| Archetype | Caveat |
|-----------|--------|
| Funding rate mean reversion | Works until trend accelerates |
| CME basis trade | Requires futures account + capital |
| Momentum on breakouts | Liquidation cascades amplify losses |
| On-chain lag signals | Too slow for intraday |

## FinRL Integration

**Best native fit** of all four instruments.

```
finrl/applications/cryptocurrency_trading
+ Binance or CCXT data processor
```

Extensions needed:
- Add funding rate to state vector
- Penalize holding through high-funding periods in reward
- Model 24/7 — no session `done` flag
- Separate spot vs perp env configs

Quick start:
```bash
git clone https://github.com/AI4Finance-Foundation/FinRL.git
pip install -e .
# See finrl/applications/cryptocurrency_trading/
```

## Pattern Recognition Notes

| Technique | Application |
|-----------|-------------|
| **Matrix Profile** | 24/7 motif library on log returns; no session filter |
| **DTW** | Match accumulation/distribution patterns at variable speed |
| **BOCPD** | Detect funding-regime breaks; vol regime shifts |
| **CID** | Compare patterns across halving cycles with different vol |
| **Discord detection** | Flag liquidation cascade precursors (volume spike + MP anomaly) |

**Recommended:** z-normalized log returns on M15/H1 for motif mining.

**Funding filter:** Only take long motifs when funding < 50th percentile; short motifs when funding > 50th.

**Pattern → FinRL state:** DTW distance to nearest bull/bear motif cluster as continuous state feature.

See [06-pattern-based-trading.md](../06-pattern-based-trading.md) and [05-finrl-deep-reinforcement-learning.md](../05-finrl-deep-reinforcement-learning.md).
