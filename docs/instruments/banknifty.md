# Bank Nifty — NSE Banking Index F&O

## Contract Specifications (Jan 2026)

| Spec | Value |
|------|-------|
| Lot size | **30 units** (revised from 35) |
| Tick size | 0.05 index points |
| P&L per point | **₹30 per lot** |
| Constituents | 12 largest NSE banking stocks |
| Weekly expiry | **Discontinued Nov 2024** — monthly only |
| Monthly expiry | Last **Tuesday** of month |

### P&L Math

```
P&L (₹) = (exit_index - entry_index) × 30 × num_lots

Example: Long 1 lot, BankNifty 48000 → 48150 = 150 pts × ₹30 = ₹4,500
```

## Constituents (12 banks)

HDFC Bank, ICICI Bank, SBI, Kotak Mahindra, Axis Bank, IndusInd, AU Small Finance, Federal Bank, IDFC First, PNB, Bank of Baroda, Bandhan Bank (weights change on rebalance).

**100% banking/finance sector** — no diversification vs Nifty 50.

## vs Nifty 50

| Dimension | Nifty 50 | Bank Nifty |
|-----------|----------|------------|
| Lot size | 65 | 30 |
| P&L/point | ₹65 | ₹30 |
| Volatility | Lower | **~1.5–2× Nifty ATR** |
| Beta to Nifty | 1.0 | ~1.2–1.4 |
| Weekly options | Yes (Tuesdays) | **No** (monthly only) |
| Expiry gamma | High | **Extreme** on monthly expiry |
| RBI sensitivity | Moderate | **Very high** |
| Correlation to Nifty | — | ~0.85–0.95 |

## Session Schedule

Same as Nifty 50: **9:15–15:30 IST** (F&O to 15:40 from Aug 3, 2026).

## Volatility Profile

- Intraday ATR: often **150–300 index points** on RBI days
- Monthly expiry: highest retail participation; vol crush post-expiry
- Earnings season (bank results): sector-wide moves
- Mean-reversion less reliable than Nifty on trend days

## Primary Price Drivers

| Driver | Impact |
|--------|--------|
| RBI repo rate / MPC | **Primary** — immediate sector move |
| CRR, SLR, liquidity operations | Banking system liquidity |
| Credit growth data | NIM outlook |
| NPA trends | Asset quality sentiment |
| Bond yield curve | Bank NIM sensitivity |
| Quarterly bank earnings | Heavyweight earnings seasonality |
| Nifty correlation | Diverges on banking-specific news |

## Transaction Costs

Same structure as Nifty 50 (STT, exchange charges, brokerage). Higher **margin requirement** due to vol.

## Data Sources

Same as Nifty 50 — Kite Connect, TrueData, GDFL, NSE datacenter. Symbol: `BANKNIFTY` on NSE F&O.

## Strategy Archetypes (Caveats Only)

| Archetype | Caveat |
|-----------|--------|
| RBI straddle | Vol crush after announcement |
| BankNifty/Nifty ratio spread | Correlation breakdown in crisis |
| Monthly expiry strangle | Extreme gamma risk |
| Momentum on RBI day | Whipsaw common |

## FinRL Integration

Same custom path as Nifty 50 with adjustments:

- Lot size **30**
- Higher vol → scale reward/risk normalization
- No weekly expiry roll logic
- Add RBI_event_flag to state
- Monthly expiry only — expiry_day_flag on last Tuesday

## Pattern Recognition Notes

| Technique | Application |
|-----------|-------------|
| **DTW** | RBI announcement reaction patterns (warp speed of rate decision) |
| **Discord detection** | Unusual pre-RBI positioning (MP anomaly) |
| **BOCPD** | Detect when BankNifty/Nifty correlation regime shifts |
| **TS-K-means** | Cluster banking-specific mechanism regimes separately from Nifty |
| **Vol-adjusted motifs** | Z-norm with higher bandwidth due to 2× ATR |

**Pair trade patterns:** Mine BankNifty/Nifty ratio motifs — divergence often precedes sector rotation.

**RBI calendar:** Tag all motifs with `days_to_rbi` — patterns 0–1 days before MPC differ from normal.

**Monthly expiry only:** Build separate motif library for last-Tuesday vs non-expiry days.

See [06-pattern-based-trading.md](../06-pattern-based-trading.md) and [nifty50.md](nifty50.md) for shared NSE mechanics.
