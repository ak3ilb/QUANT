# Economic Calendar — High-Impact Events

Events that move markets and create **pattern discord** or **regime breaks**. Times in UTC unless noted.

## XAUUSD (Gold)

| Event | Frequency | Typical UTC | Impact |
|-------|-----------|-------------|--------|
| FOMC rate decision | 8×/year | 19:00 | Very high |
| US CPI | Monthly | 13:30 | Very high |
| US NFP | Monthly (1st Fri) | 13:30 | High |
| US PPI | Monthly | 13:30 | Medium |
| 10Y Treasury auction | Weekly | 17:00 | Medium |
| London gold fix AM | Daily | 10:30 | Medium |
| London gold fix PM | Daily | 15:00 | Medium |
| Geopolitical headlines | Ad hoc | Any | High (gaps) |

**Pattern note:** Run BOCPD around FOMC/CPI; mine pre-event accumulation motifs separately from post-event spike motifs.

## BTC (Bitcoin)

| Event | Frequency | Typical UTC | Impact |
|-------|-----------|-------------|--------|
| FOMC / CPI / NFP | Same as gold | 13:30–19:00 | High (macro correlation) |
| BTC ETF flow reports | Daily | US market hours | Medium–high |
| Funding rate settlement | Every 8h | 00:00, 08:00, 16:00 | Medium |
| Halving | ~4 years | — | Structural (diminishing) |
| Exchange outage / hack | Ad hoc | Any | Very high |
| CME BTC futures expiry | Monthly | 16:00 (last Fri) | Medium |

**Pattern note:** Tag motifs by funding rate percentile; extreme funding often precedes mean-reversion discord.

## Nifty 50

| Event | Frequency | Typical UTC | Impact |
|-------|-----------|-------------|--------|
| Nifty open | Daily (Mon–Fri) | 03:45 | High (overnight gap) |
| RBI MPC decision | 6×/year | ~06:00–08:00 | Very high |
| India CPI / WPI | Monthly | ~06:30 | High |
| FII flow data | Daily (lagged) | ~12:00 (prev day) | Medium |
| US market close | Daily | 21:00 | High (next day gap) |
| Union Budget | Annual (Feb) | ~06:30 | Very high |
| Nifty weekly expiry | Every Tuesday | 10:00 | High (gamma) |
| IndiaVIX spike | Ad hoc | — | Regime signal |

**Pattern note:** Separate motif libraries for expiry Tuesday vs normal Tuesday vs gap days.

## Bank Nifty

| Event | Frequency | Typical UTC | Impact |
|-------|-----------|-------------|--------|
| RBI MPC | 6×/year | ~06:00–08:00 | **Extreme** |
| Bank earnings season | Quarterly | 10:00–12:00 | High |
| Credit policy / liquidity ops | Ad hoc | — | High |
| Bank Nifty monthly expiry | Last Tuesday | 10:00 | **Extreme** (gamma) |
| NPA / asset quality news | Ad hoc | — | High |

**Pattern note:** RBI day motifs are distinct from normal days — never mix in same TS-K-means cluster without tagging.

## Cross-Market Events

| Event | Affects all four? |
|-------|-------------------|
| US recession fear | Gold ↑, BTC ↓, Nifty ↓, BankNifty ↓↓ |
| USD surge (DXY) | Gold ↓, BTC ↓, Nifty ↓ (FII outflow) |
| Global risk-off | Gold ↑, BTC mixed, India ↓ |

Use [session-calendar.md](../docs/cross-market/session-calendar.md) for timing.
