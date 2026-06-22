# India — SEBI & NSE Regulations

Applies to **Nifty 50** and **Bank Nifty** F&O trading.

## Retail F&O Eligibility

- SEBI requires proof of income and trading experience for F&O access
- Periodic review of eligibility criteria

## Margin & Reporting

- **Peak margin reporting** — broker must report intraday peak margin
- **SPAN + Exposure margin** — exchange-calculated; Bank Nifty typically higher than Nifty
- EOD margin must be maintained or positions squared off

## Algo Trading

- Automated trading requires **exchange-approved API** (e.g., Kite Connect with exchange registration)
- Colocation for HFT — institutional only
- Order tagging and audit trail requirements

## Transaction Taxes (STT)

| Instrument | STT rate | Side |
|------------|----------|------|
| Futures (sell) | 0.0125% | Sell only |
| Options (sell) | 0.0625% | On premium, sell only |
| Options (exercise) | 0.125% | On intrinsic value |

Plus exchange transaction charges, SEBI fees, GST on brokerage.

## Contract Specifications (2026)

| Index | Lot size | Effective |
|-------|----------|-----------|
| Nifty 50 | 65 | Jan 2026 series |
| Bank Nifty | 30 | Jan 2026 series |
| FINNIFTY | 60 | Jan 2026 series |
| MIDCPNIFTY | 120 | Jan 2026 series |

SEBI mandates lot size revisions to keep notional value in ₹5–15 lakh band.

## Expiry Rules (from Sep 1, 2025)

- All NSE F&O expiries moved to **Tuesday** (from Thursday)
- Nifty 50: weekly + monthly on Tuesday
- Bank Nifty: **monthly only** (weekly discontinued Nov 2024)
- Holiday: expiry shifts to previous working day

## Trading Hours

- Cash: 9:15–15:30 IST
- F&O: 9:15–15:30 IST (extends to **15:40 IST from Aug 3, 2026**)
- Pre-open: 9:00–9:08 IST

## Index Options

- Cash-settled (no physical delivery of index)
- Only **one weekly index** per exchange (Nifty 50 on NSE; Sensex on BSE)

## Risk Warnings

- ~90%+ retail F&O participants lose money (SEBI disclosure)
- Lot size changes require strategy recalibration
- Expiry day gamma risk — especially Bank Nifty monthly

See [nifty50.md](../instruments/nifty50.md) and [banknifty.md](../instruments/banknifty.md).
