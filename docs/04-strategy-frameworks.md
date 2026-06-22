# Strategy Frameworks

## Mean Reversion

**Idea:** Price deviates from fair value, reverts.

| Instrument | Fit | Caveat |
|------------|-----|--------|
| XAUUSD | Moderate (session ranges) | Fails on FOMC trend days |
| BTC | Moderate (funding extremes) | Liquidation cascades break reversion |
| Nifty | Moderate (intraday) | Gap days break mean reversion |
| Bank Nifty | Weak on trend days | RBI days are momentum |

**Pattern-native:** Use DTW to match "overextension" motif, not RSI > 70 at fixed bar.

## Momentum / Trend Following

**Idea:** Price continues in direction of established trend.

| Instrument | Fit | Caveat |
|------------|-----|--------|
| XAUUSD | Good (London/NY) | Session-filter required |
| BTC | Good (macro trends) | Weekend gaps |
| Nifty | Good (FII flow days) | Expiry gamma distorts |
| Bank Nifty | Strong on RBI days | Whipsaw on range days |

**Pattern-native:** Match "breakout continuation" shapelet; enter on DTW confirmation.

## Volatility Strategies

| Strategy | Instrument | Notes |
|----------|------------|-------|
| Straddle/strangle | Nifty, Bank Nifty | Expiry vol crush |
| Vol selling | Nifty weekly | Tail risk on gap days |
| Funding arb | BTC perp | Mean reversion on extreme funding |

Model **IndiaVIX** for Nifty vol strategies; **realized vs implied** spread.

## Options Greeks (Nifty / Bank Nifty)

| Greek | Meaning | Expiry relevance |
|-------|---------|------------------|
| Delta | Directional exposure | High near ATM on expiry |
| Gamma | Delta change rate | **Extreme** 14:00–15:30 on expiry |
| Theta | Time decay | Accelerates into expiry |
| Vega | Vol sensitivity | RBI/MPC announcements |

Bank Nifty monthly expiry has **higher gamma** than Nifty weekly due to vol.

## Pairs / Spread

| Pair | Idea |
|------|------|
| BankNifty / Nifty | Sector rotation |
| BTC / ETH | Crypto beta |
| Gold / DXY | Inverse macro |

**Pattern-native:** Mine ratio-series motifs with multivariate DTW.

## Regime-Switching

Route strategy by detected regime (HMM / BOCPD):

```
IF regime == low_vol_trend → momentum
IF regime == high_vol_chop → mean reversion or flat
IF regime == crisis → reduce exposure 80%
```

See [06-pattern-based-trading.md](06-pattern-based-trading.md) Layer 4.

## What NOT to Do

- Optimize indicator periods on full sample (overfit)
- Backtest without transaction costs
- Use static clock entries ("buy 9:15 every day")
- Ignore regime changes between train and test periods
