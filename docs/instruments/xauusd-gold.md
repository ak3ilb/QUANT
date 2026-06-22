# XAUUSD — Spot Gold vs USD

## Contract Specifications

| Spec | Value |
|------|-------|
| Quote | USD per troy ounce (typically 2 decimals) |
| 1 pip | $0.01 price move |
| Standard lot | 100 oz → **$1.00 per pip** |
| Mini (0.10 lot) | 10 oz → $0.10/pip |
| Micro (0.01 lot) | 1 oz → $0.01/pip |
| Typical daily range | ~$20–$40 (2,000–4,000 pips) |
| COMEX GC futures | 100 troy oz/contract |

### P&L Math

```
P&L ($) = (exit_price - entry_price) × 100 × lot_size
         = pip_move × $1.00 × lot_size   (per standard lot)
```

Example: Long 0.10 lot from 2650.00 to 2655.00 → 500 pips × $0.10 = **$50 profit**.

## Session Schedule

| Session | UTC | IST | ET | Liquidity |
|---------|-----|-----|-----|-----------|
| Asia | 00:00–08:00 | 05:30–13:30 | 19:00–03:00 | Thin, wide spreads |
| London | 07:00–16:00 | 12:30–21:30 | 02:00–11:00 | High |
| **London/NY overlap** | **13:00–17:00** | **18:30–22:30** | **08:00–12:00** | **Peak** |
| NY (post-London) | 17:00–22:00 | 22:30–03:30 | 12:00–17:00 | Moderate |

**Key fixes:** London AM ~10:30 UTC, PM ~15:00 UTC — institutional volume clusters.

Trading hours: Mon–Fri ~24h; Sunday open gaps common after weekend news.

## Volatility Profile

- ATR(14) on H1: typically **80–180 points** (vs EUR/USD 15–25 pips)
- Gold moves **2–4×** equivalent FX major volatility
- Same 1% risk → **5× smaller lot size** vs EUR/USD for equivalent stop distance

## Primary Price Drivers

| Driver | Relationship | Feature idea |
|--------|--------------|--------------|
| Real yields (10Y TIPS) | Inverse | TIPS yield as regime filter |
| DXY (USD index) | Inverse | Multi-variate motif with DXY |
| Fed / CPI / NFP / FOMC | Event shocks | Discord detection around releases |
| Geopolitical risk | Risk-off bid | VIX correlation spike motifs |
| Central bank buying | Structural bid | Slow-moving trend component |

## Microstructure & Execution

- Spreads: 15–30 pts typical; **2–5× wider** in Asia vs London/NY overlap
- Slippage spikes around US data (13:30 UTC NFP, CPI)
- No single exchange — OTC/ECN fragmentation
- Model spread cap in backtests (e.g., skip entry if spread > 25 pts)

## Data Sources

| Source | Granularity | Notes |
|--------|-------------|-------|
| OANDA v20 API | Tick, M1–D1 | REST + streaming |
| MetaTrader 5 | Tick, M1–D1 | Widely used for gold CFDs |
| Dukascopy | Tick historical | Free tick data (limited) |
| QuantConnect | CFD XAUUSD | Cloud backtest |
| Polygon / Refinitiv | Institutional | Paid |

## Regulatory Notes

- EU ESMA retail leverage cap: **1:30**
- US: NFA-regulated brokers (OANDA, IBKR)
- No India-specific gold spot on NSE for retail FX — trade via international brokers

## Strategy Archetypes (Caveats Only)

| Archetype | Caveat |
|-----------|--------|
| Session-filtered momentum | Only trade London/NY overlap |
| Mean reversion on overextension | Wide stops required; ATR-scaled |
| Event straddle | Gap risk on Sunday open |
| Gold/DXY pair | Correlation not stable in crisis |

## FinRL Integration

**Not native.** Custom path required:

1. Build `data_processor` for OANDA/MT5 OHLCV
2. Fork `env_stock_trading` → `env_gold_trading`
3. State: indicators + session flag + spread estimate
4. Reward: PnL minus spread penalty
5. Action: position size in lots (discretized)
6. Done: session close or max drawdown

## Pattern Recognition Notes

| Technique | Application |
|-----------|-------------|
| **DTW** | Match London-open spike patterns; warp speed of FOMC reaction |
| **Matrix Profile** | Find recurring pre-fix accumulation motifs |
| **BOCPD** | Detect regime shift when real-yield correlation breaks |
| **CID distance** | Compare patterns across different vol regimes |
| **Session segmentation** | Split series by session before motif mining |

**Anti-pattern:** Do not use fixed "enter at 13:30 UTC" rules — use DTW match to known CPI-reaction template instead.

**Recommended motif length:** 30–120 M5 bars for intraday; 20–60 H1 bars for swing.

**Z-normalize** subsequence before DTW to handle vol scaling.

See [06-pattern-based-trading.md](../06-pattern-based-trading.md).
