# Instrument Comparison

Side-by-side specs for the four core instruments. Accurate as of **June 2026**.

| Dimension | XAUUSD | BTC | Nifty 50 | Bank Nifty |
|-----------|--------|-----|----------|------------|
| **Market type** | OTC spot/CFD | Crypto perp/spot | NSE index F&O | NSE banking F&O |
| **Hours** | Mon–Fri ~24h | 24/7/365 | IST 9:15–15:30 | IST 9:15–15:30 |
| **Best session (UTC)** | 13:00–17:00 | 24/7 | 03:45–10:00 | 03:45–10:00 |
| **Lot / contract** | 100 oz (std) | Perp / 5 BTC (CME) | 65 units | 30 units |
| **P&L per point** | $1/pip (std lot) | $1 per $1 BTC | ₹65/point | ₹30/point |
| **Typical daily range** | $20–40 | 3–8% | 80–150 pts | 150–300 pts |
| **Vol vs Nifty** | — | Higher fat tails | 1.0× | 1.5–2.0× |
| **Weekly expiry** | N/A | N/A | Every Tuesday | None (monthly) |
| **Monthly expiry** | N/A | CME only | Last Tuesday | Last Tuesday |
| **Primary driver** | Real yields, DXY | Macro, funding, ETF | FII flows | RBI, bank earnings |
| **FinRL native** | No | **Yes** | No | No |
| **Pattern library** | Session motifs | 24/7 motifs | Expiry/gap motifs | RBI/expiry motifs |

## Data API Summary

| Instrument | Primary API | Backup |
|------------|-------------|--------|
| XAUUSD | OANDA, MT5 | Dukascopy |
| BTC | Binance, CCXT | Coinbase |
| Nifty 50 | Kite Connect | TrueData |
| Bank Nifty | Kite Connect | TrueData |

## Cost Comparison (round-trip estimate)

| Instrument | Typical cost |
|------------|--------------|
| XAUUSD | Spread 15–30 pts |
| BTC perp | 0.08–0.20% (fees + funding) |
| Nifty futures | ~0.02–0.04% + STT |
| Bank Nifty futures | ~0.02–0.04% + STT |

## Correlation (approximate, regime-dependent)

| Pair | Normal | Crisis |
|------|--------|--------|
| Gold / DXY | −0.6 to −0.8 | Breaks down |
| BTC / S&P | +0.3 to +0.6 | +0.8+ |
| Nifty / S&P | +0.4 to +0.6 | +0.7+ |
| BankNifty / Nifty | +0.85 to +0.95 | +0.95+ |
| Gold / BTC | Low | Both risk-off bid |

See [correlation-regime.md](correlation-regime.md).

## Pattern Methodology Fit

| Technique | XAUUSD | BTC | Nifty | Bank Nifty |
|-----------|--------|-----|-------|------------|
| DTW | High | High | High | High |
| Matrix Profile | High | High | High | Medium |
| BOCPD | Medium | High | High | High |
| HMM regimes | Medium | Medium | High | High |
| Shapelets | Medium | Medium | High | Medium |
| FinRL | Custom | **Native** | Custom | Custom |
