# Nifty 50 — NSE Index F&O

## Contract Specifications (Jan 2026)

| Spec | Value |
|------|-------|
| Lot size | **65 units** (revised from 75) |
| Tick size | 0.05 index points |
| P&L per point | **₹65 per lot** |
| Contract notional | ~₹16–17 lakh (SEBI band ₹5–15 lakh) |
| Index type | Free-float market-cap weighted, 50 stocks |

### P&L Math

```
P&L (₹) = (exit_index - entry_index) × 65 × num_lots

Example: Long 1 lot, Nifty 24000 → 24100 = 100 pts × ₹65 = ₹6,500
```

## Session Schedule

| Phase | IST | UTC | Notes |
|-------|-----|-----|-------|
| Pre-open | 9:00–9:08 | 3:30–3:38 | Order collection, random close |
| Normal market | **9:15–15:30** | **3:45–10:00** | Cash + F&O |
| F&O extension | 9:15–**15:40** (from Aug 3, 2026) | 3:45–10:10 | Closing Auction Session |
| Trade modification | Until 16:15 IST | — | — |

**No overnight intraday** without carry/margin for F&O positions.

## Expiry Rules (effective Sep 1, 2025)

| Type | Day |
|------|-----|
| Weekly options | Every **Tuesday** |
| Monthly futures/options | Last **Tuesday** of month |
| Holiday rule | Expiry shifts to **previous working day** |

Nifty 50 is the **only index with weekly options on NSE** (SEBI: one weekly index per exchange).

## Index Composition (approximate weights)

| Sector | Weight |
|--------|--------|
| Financials | ~33% |
| IT | ~13% |
| Oil & Gas | ~10% |
| FMCG, Auto, others | Balance |

Heavyweights: HDFC Bank, Reliance, ICICI Bank, Infosys, TCS.

## Volatility Profile

- IndiaVIX: options-implied vol index for Nifty
- Intraday ATR: typically 80–150 index points on trend days
- **Expiry Tuesdays:** elevated gamma 14:00–15:30 IST
- Opening gap from US close (S&P 500 overnight effect at 9:15)

## Primary Price Drivers

| Driver | Impact |
|--------|--------|
| FII / DII flows | Dominates short-term direction |
| RBI MPC, India CPI/WPI | Rate-sensitive sectors |
| US markets (overnight) | Gap at 9:15 open |
| Crude oil (INR) | Import sensitivity |
| Union Budget | Annual structural shock |
| IndiaVIX | Vol regime for options strategies |

## Transaction Costs (model in backtests)

| Charge | Approximate |
|--------|-------------|
| STT (futures sell) | 0.0125% on sell side |
| STT (options sell) | 0.0625% on premium |
| Exchange charges | Variable |
| Brokerage + GST | ~₹20–40/order flat or % |
| **Total round-trip** | ~0.02–0.05% for futures; higher for options |

## Data Sources

| Source | Granularity | Notes |
|--------|-------------|-------|
| Zerodha Kite Connect | Tick, 1-min | REST + WebSocket; primary for algo |
| TrueData / GDFL | Tick, 1-min | Paid historical |
| NSE datacenter | Tick | Institutional |
| Angel One SmartAPI | Tick, 1-min | Alternative broker API |

## Regulatory Notes

- SEBI: proof of income/experience for F&O retail
- Peak margin reporting (intraday + EOD)
- Algo trading requires exchange-approved API
- Cash-settled index options (no physical delivery)
- Lot size revised periodically per SEBI notional mandate

## Strategy Archetypes (Caveats Only)

| Archetype | Caveat |
|-----------|--------|
| Opening gap fade | US correlation not stable |
| Expiry-day straddle | Vol crush post-15:30 |
| FII flow momentum | Data lagged by 1 day |
| Mean reversion intraday | Fails on trend days |

## FinRL Integration

**Not native.** Custom path:

1. Kite Connect `data_processor` for Nifty OHLCV
2. Fork `env_stock_trading` → single-asset index env
3. State: indicators + minutes_to_close + expiry_day_flag + IndiaVIX
4. Reward: PnL minus STT + brokerage
5. `done` at 15:30 IST (or 15:40 from Aug 2026)
6. Lot size 65 in position math

## Pattern Recognition Notes

| Technique | Application |
|-----------|-------------|
| **Shapelets** | Opening gap patterns (first 15 min shape) |
| **DTW** | Match pre-expiry gamma ramp patterns (variable speed) |
| **Matrix Profile** | Recurring Tuesday expiry day motifs |
| **BOCPD** | Detect FII-flow regime breaks |
| **Session segmentation** | Mine patterns only within 9:15–15:30 IST windows |

**Anti-pattern:** "Buy every Tuesday 9:15" — use DTW match to known expiry-week opening motif instead.

**Expiry filter:** Tag motifs by days-to-expiry (0, 1, 2, 3+) — same shape behaves differently.

**US gap feature:** Include overnight S&P return as exogenous variable in multivariate DTW.

See [06-pattern-based-trading.md](../06-pattern-based-trading.md).
