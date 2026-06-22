# Session Calendar — Multi-Market

All times in **UTC**. Convert for local scheduling.

## Daily Timeline (UTC)

| UTC Hour | XAUUSD | BTC | Nifty / Bank Nifty |
|----------|--------|-----|---------------------|
| 00:00–03:00 | Asia (thin) | Active | Closed |
| 03:30–03:45 | Asia | Active | Pre-open (IST 9:00) |
| **03:45–10:00** | London open | Active | **Market open (IST 9:15–15:30)** |
| 07:00–08:00 | London ramp | Active | Nifty active |
| 10:00–13:00 | London | Active | **Nifty closed** |
| **13:00–17:00** | **Peak (London/NY)** | Active | Closed |
| 17:00–22:00 | NY only | Active | Closed |
| 22:00–24:00 | Thin | Active | Closed |

## Session Overlap Map

```
UTC:  00    04    08    12    16    20    24
      |-----|-----|-----|-----|-----|-----|
BTC:  [========== 24/7 continuous ==========]
Gold:       [Asia][=== London ===][= NY =]
India:            [== Nifty 03:45-10:00 ==]
Gold peak:                  [***]
```

**Gold peak:** 13:00–17:00 UTC (London/NY overlap)

**Nifty window:** 03:45–10:00 UTC only (09:15–15:30 IST)

From **Aug 3, 2026:** NSE F&O extends to 10:10 UTC (15:40 IST).

## Timezone Quick Convert

| UTC | IST | ET (summer) |
|-----|-----|-------------|
| 03:45 | 09:15 | 23:45 (prev day) |
| 10:00 | 15:30 | 06:00 |
| 13:00 | 18:30 | 09:00 |
| 17:00 | 22:30 | 13:00 |

## Multi-Asset Desk Implications

A desk running all four instruments operates across **three session regimes**:

1. **24/7** — BTC (always on)
2. **FX hours** — XAUUSD (Mon–Fri, best 13:00–17:00 UTC)
3. **IST cash** — Nifty/BankNifty (03:45–10:00 UTC weekdays)

**No single "market open"** — pattern mining must be session-aware per instrument.

## Pattern Mining Windows

| Instrument | Mine patterns in | Skip |
|------------|------------------|------|
| XAUUSD | 07:00–22:00 UTC | 00:00–07:00 (thin Asia) |
| BTC | 24/7 | — |
| Nifty | 03:45–10:00 UTC | All other hours |
| Bank Nifty | 03:45–10:00 UTC | All other hours |

## Key Event Times (UTC)

| Event | Typical UTC | Affects |
|-------|-------------|---------|
| US NFP / CPI | 13:30 | XAUUSD, BTC, Nifty gap next day |
| FOMC decision | 19:00 | XAUUSD, BTC |
| London gold fix AM | 10:30 | XAUUSD |
| London gold fix PM | 15:00 | XAUUSD |
| Nifty open | 03:45 | Nifty, Bank Nifty |
| RBI MPC | ~06:00–08:00 | Bank Nifty, Nifty |
| BTC funding | 00:00, 08:00, 16:00 | BTC perp |

See [economic-calendar.md](../reference/economic-calendar.md).
