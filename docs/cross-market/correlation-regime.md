# Correlation & Regime Relationships

Correlations are **regime-dependent** and break down in stress. Use BOCPD/HMM to tag regimes before relying on correlation for pairs trading.

## Normal Regime (approximate)

| Pair | Correlation | Notes |
|------|-------------|-------|
| XAUUSD / DXY | −0.6 to −0.8 | Inverse dollar |
| XAUUSD / Real yields | −0.7+ | Primary gold driver |
| BTC / S&P 500 | +0.3 to +0.6 | Increasingly "macro asset" |
| BTC / DXY | −0.2 to −0.4 | Weaker than gold |
| Nifty / S&P 500 | +0.4 to +0.6 | Overnight gap driver |
| BankNifty / Nifty | +0.85 to +0.95 | Sector beta |
| Gold / BTC | +0.1 to +0.3 | Both alternative assets |

## Crisis Regime (2020, 2022 examples)

- **March 2020:** Everything sold off together (liquidity crunch); correlations → +1
- **2022 rate hikes:** Gold and BTC diverged (gold held, BTC fell)
- **India stress:** BankNifty often falls harder than Nifty (sector concentration)

## Regime Detection Approach

1. **BOCPD** on rolling 60-day correlation matrix — alert when correlation structure shifts
2. **HMM** on [returns, vol, correlation_to_benchmark] — 3–4 hidden states
3. **TS-K-means (DTW)** on return windows — cluster mechanism regimes (Paper 1)

## Multi-Asset Pattern Implications

| Scenario | Action |
|----------|--------|
| Correlation spike (all → +0.9) | Reduce gross exposure; patterns less independent |
| Gold/BTC decorrelate | Run separate motif libraries |
| BankNifty/Nifty ratio discord | Sector rotation signal |
| BOCPD break on Nifty | Retrain Nifty motif library; pause BankNifty pair trades |

## Cross-Asset Motif Ideas

- **Multivariate DTW:** [Nifty return, S&P overnight return, IndiaVIX change]
- **Ratio motifs:** BankNifty/Nifty z-score shapelets
- **Macro motifs:** [Gold return, DXY return, 10Y yield change] for XAUUSD

See [06-pattern-based-trading.md](../06-pattern-based-trading.md).
