# Broker & API Matrix

For Phase 2 implementation. All require account registration and API keys.

## By Instrument

### XAUUSD

| Provider | API type | Data | Execution | Python lib |
|----------|----------|------|-----------|------------|
| OANDA | REST + stream | Tick, M1–D1 | Yes | `oandapyV20` |
| MetaTrader 5 | Terminal API | Tick, M1–D1 | Yes | `MetaTrader5` |
| Interactive Brokers | TWS API | Tick+ | Yes | `ib_insync` |
| Dukascopy | HTTP | Tick (hist) | No | Custom |
| QuantConnect | Cloud | M1+ | Yes (cloud) | LEAN |

### BTC

| Provider | API type | Data | Execution | Python lib |
|----------|----------|------|-----------|------------|
| Binance | REST + WS | Tick, L2, funding | Yes | `python-binance` |
| CCXT | Unified | OHLCV multi-ex | Yes | `ccxt` |
| Coinbase Advanced | REST + WS | Spot | Yes | `coinbase-advanced-py` |
| CME | DataMine | Futures | Via broker | — |

### Nifty 50 / Bank Nifty

| Provider | API type | Data | Execution | Python lib |
|----------|----------|------|-----------|------------|
| Zerodha Kite | REST + WS | Tick, 1-min | Yes | `pykiteconnect` |
| Angel One SmartAPI | REST + WS | Tick, 1-min | Yes | `smartapi-python` |
| Upstox | REST + WS | Tick, 1-min | Yes | `upstox-python-sdk` |
| TrueData | Feed | Tick, 1-min | No | Vendor SDK |
| GDFL | Feed | Tick, 1-min | No | Vendor SDK |

## Pattern Mining Stack (no broker needed)

| Library | Install | Purpose |
|---------|---------|---------|
| `stumpy` | `pip install stumpy` | Matrix Profile, motifs |
| `tslearn` | `pip install tslearn` | DTW K-means, clustering |
| `hmmlearn` | `pip install hmmlearn` | HMM regimes |
| `ruptures` | `pip install ruptures` | Offline changepoints |
| `finrl` | `pip install finrl` | DRL trading |

## FinRL Data Processor Mapping

| FinRL processor | Our instrument |
|-----------------|----------------|
| Binance | BTC |
| CCXT | BTC (multi-exchange) |
| Yahoo | Not our instruments |
| Alpaca | US only |
| Custom needed | XAUUSD, Nifty, Bank Nifty |

## Recommended Stack by Goal

| Goal | Stack |
|------|-------|
| BTC pattern research | Binance API + stumpy + tslearn |
| BTC live DRL | FinRL + Binance processor |
| Nifty pattern research | TrueData/Kite hist + stumpy |
| Nifty live algo | Kite Connect + custom engine |
| XAUUSD patterns | Dukascopy hist + tslearn DTW |
| Multi-asset regimes | hmmlearn + ruptures on combined features |

## API Rate Limits (approximate)

| API | Limit |
|-----|-------|
| Binance REST | 1200 weight/min |
| Kite Connect | 3 req/sec historical |
| OANDA | Varies by account |
| Yahoo (yfinance) | 2000/hour |

Always implement exponential backoff and caching for historical downloads.
