# Risk & Position Sizing

## Fixed-Fractional Sizing

Risk a fixed percentage of account per trade:

```
Position Size = (Account × Risk%) / (Stop Distance × Point Value)

XAUUSD example:
  Account = $10,000, Risk = 1%, Stop = 200 pts ($2.00 move)
  Lot size = ($100) / (200 × $1.00) = 0.50 lots (standard)
```

## Instrument-Specific Sizing

| Instrument | Point value | Typical stop | 1% risk on $10k |
|------------|-------------|--------------|-----------------|
| XAUUSD (0.10 lot) | $0.10/pip | 150–300 pips | 0.03–0.07 lots |
| BTC (0.01 BTC) | $1/point | $500–2000 | 0.005–0.02 BTC |
| Nifty (1 lot) | ₹65/point | 50–100 pts | 1–2 lots on ₹5L account |
| Bank Nifty (1 lot) | ₹30/point | 100–200 pts | 1 lot on ₹5L account |

## Kelly Criterion

```
f* = (p × b - q) / b

p = win probability, q = 1-p, b = win/loss ratio
```

**Half-Kelly** is standard in practice — full Kelly is too aggressive and assumes known edge.

Kelly requires accurate edge estimates. With overfitted backtests, Kelly will oversize.

## Value at Risk (VaR)

- **Historical VaR**: 5th percentile of last N days of returns
- **Parametric VaR**: assumes normal distribution (underestimates tails)
- **Regime-conditional VaR**: compute VaR separately per BOCPD regime

For fat-tailed assets (BTC, Bank Nifty), use **CVaR (Expected Shortfall)** instead.

## Drawdown Rules

| Rule | Action |
|------|--------|
| Daily loss limit (2%) | Stop trading for day |
| Weekly loss limit (5%) | Reduce size 50% |
| Max drawdown (15%) | Halt strategy; review |
| Consecutive losses (5+) | Pause; check regime change |

## Pattern-Native Risk

When using motif-triggered entries:

- Size by **motif match confidence** (DTW distance inverse)
- Reduce size when BOCPD signals recent regime change
- Widen stops proportionally to subsequence ATR at match point
- Exit on **discord** (Matrix Profile anomaly) not fixed time

## Portfolio-Level Risk

Multi-asset desk (XAUUSD + BTC + Nifty + Bank Nifty):

- Correlation spikes in crisis — reduce gross exposure
- Three session regimes — max concurrent positions may be 2–3
- Margin: NSE peak margin reporting; crypto liquidation risk

See [cross-market/correlation-regime.md](cross-market/correlation-regime.md).
