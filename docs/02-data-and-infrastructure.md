# Data & Infrastructure

## Timezone Reference

| Market | Primary TZ | UTC offset | Market open (UTC) |
|--------|-----------|------------|-------------------|
| XAUUSD | UTC / ET | — | ~22:00 Sun (Sydney) |
| BTC | UTC | — | 24/7 |
| Nifty / Bank Nifty | IST (UTC+5:30) | +5:30 | 03:45 |
| US equities | ET (UTC−4/−5) | −4/−5 | 13:30 |

**Always store timestamps in UTC.** Convert to local only for display and session filters.

## Data Sources by Instrument

### XAUUSD

| Provider | API | Granularity | Cost |
|----------|-----|-------------|------|
| OANDA v20 | REST + stream | Tick, M1–D1 | Free with account |
| MetaTrader 5 | Python `MetaTrader5` | Tick, M1–D1 | Broker-dependent |
| Dukascopy | HTTP tick API | Tick | Free (limited) |
| QuantConnect | Cloud | M1+ | Subscription |

### BTC

| Provider | API | Granularity | Cost |
|----------|-----|-------------|------|
| Binance | REST + WebSocket | Tick, trades, L2 | Free |
| CCXT | Unified wrapper | OHLCV multi-exchange | Free |
| Coinbase Advanced | REST + WS | Spot | Free |
| Kaiko | REST | Institutional tick | Paid |

### Nifty 50 / Bank Nifty

| Provider | API | Granularity | Cost |
|----------|-----|-------------|------|
| Zerodha Kite Connect | REST + WS | Tick, 1-min | ₹2k/month API |
| TrueData | Feed | Tick, 1-min | Paid |
| GDFL | Feed | Tick, 1-min | Paid |
| NSE datacenter | Direct | Tick | Institutional |

## Storage Recommendations

| Scale | Solution |
|-------|----------|
| Research (< 10 GB) | Parquet files on disk |
| Medium (10–100 GB) | TimescaleDB or DuckDB |
| Production | TimescaleDB + Redis for live state |

**Parquet schema (OHLCV):**
```
timestamp (UTC), open, high, low, close, volume, symbol, timeframe
```

## Data Quality Checks

- Missing bars (gaps) — flag or forward-fill with caution
- Duplicate timestamps — deduplicate
- Corporate actions (splits) — adjust for equities; N/A for indices/crypto
- Timezone errors — most common bug in multi-market systems
- Survivorship — use point-in-time index constituents for Nifty backtests

## Pattern Mining Data Prep

For DTW / Matrix Profile pipelines:

1. **Z-normalize** each subsequence: `(x - μ) / σ`
2. **Log returns** for BTC and indices (not raw prices)
3. **Session filter** before mining (XAUUSD: London/NY; Nifty: 9:15–15:30 IST)
4. **Remove outliers** > 5σ before clustering (optional)
5. Store motif library separately from raw OHLCV

## Python Toolchain

| Library | Purpose |
|---------|---------|
| `pandas` / `numpy` | Data manipulation |
| `tslearn` | DTW K-means, clustering |
| `stumpy` | Matrix Profile, motifs, discords |
| `hmmlearn` | HMM regime detection |
| `ruptures` | Offline change-point detection |
| `pykiteconnect` | NSE live/historical via Zerodha |
| `ccxt` / `python-binance` | Crypto data |

See [reference/broker-api-matrix.md](../reference/broker-api-matrix.md).
