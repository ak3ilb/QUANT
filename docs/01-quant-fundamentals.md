# Quant Fundamentals

## Research → Production Workflow

```
Hypothesis → Data → Clean/Align → Features → Backtest → Risk → Paper → Live
```

Each stage has failure modes. Skipping validation at any step compounds error downstream.

## Backtesting Hygiene

| Bias | Description | Mitigation |
|------|-------------|------------|
| Look-ahead | Using future data in features | Point-in-time data; lag all indicators |
| Survivorship | Only testing stocks that still exist | Use historical index constituents |
| Overfitting | Tuning on same data you test | Walk-forward; out-of-sample holdout |
| Data snooping | Testing many strategies, reporting best | Deflated Sharpe ratio; Bonferroni correction |
| Regime change | Model trained on bull, tested in bear | BOCPD splits; regime-conditional metrics |

## Performance Metrics

| Metric | Formula / Meaning | When to use |
|--------|-------------------|-------------|
| Sharpe | (Return − Rf) / σ | Risk-adjusted comparison |
| Sortino | Return / downside σ | Penalizes only bad vol |
| Calmar | CAGR / max drawdown | Tail risk focus |
| Max drawdown | Peak-to-trough | Worst-case loss |
| Profit factor | Gross profit / gross loss | >1.5 often meaningful |
| Expectancy | (Win% × avg win) − (Loss% × avg loss) | Per-trade edge |
| Turnover | Trades / capital / period | Cost sensitivity |

**Win rate alone is misleading.** A 40% win rate with 3:1 reward/risk beats 70% win rate with 1:3.

## Statistical Validation

- **t-test** on daily returns vs zero
- **Monte Carlo**: shuffle trade sequence 1000× — is real Sharpe in top 5%?
- **Deflated Sharpe** (Bailey & López de Prado): adjust for number of trials
- **Minimum track record length**: how long before Sharpe is statistically significant?

## Execution Realism

Always model in backtests:

| Cost | XAUUSD | BTC | Nifty/BankNifty |
|------|--------|-----|-----------------|
| Spread | 15–30 pts | 0.01–0.05% | Tick spread |
| Commission | Broker-dependent | 0.04–0.10% taker | ₹20–40/order |
| Slippage | 1–5 pts on news | Higher weekends | 0.5–2 ticks |
| Funding (perp) | N/A | Every 8h | N/A |
| STT | N/A | N/A | 0.0125–0.0625% |
| Roll cost | N/A | N/A | Futures roll |

## Regime Awareness

Markets are non-stationary. A strategy's edge may exist only in specific regimes:

- **Trend vs range** — momentum fails in chop; mean reversion fails in trends
- **Vol clustering** — GARCH effects; size down in high-vol regimes
- **Correlation breakdown** — gold/BTC/Nifty correlations shift in crisis (2020, 2022)

Use HMM or BOCPD to tag regimes before evaluating strategy performance.

## Pattern-Native vs Static Backtesting

This knowledge base emphasizes **pattern-native** evaluation. See [06-pattern-based-trading.md](06-pattern-based-trading.md).

| Static (avoid) | Pattern-native (prefer) |
|----------------|-------------------------|
| Enter at fixed clock time | Enter on DTW motif match |
| Fixed N-bar window | Variable-length motifs |
| Single train period | Walk-forward per regime |
| Indicator cross at bar N | Shapelet / Matrix Profile trigger |

## Key References

- [03-risk-and-position-sizing.md](03-risk-and-position-sizing.md)
- [06-pattern-based-trading.md](06-pattern-based-trading.md)
- [research/papers-index.md](../research/papers-index.md)
