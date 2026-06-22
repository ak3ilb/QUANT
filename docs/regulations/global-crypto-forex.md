# Global — Crypto & Forex Regulations

Applies to **XAUUSD** and **BTC**.

## XAUUSD (Forex / Gold CFD)

| Jurisdiction | Key rules |
|--------------|-----------|
| EU (ESMA) | Retail leverage cap **1:30** on gold |
| UK (FCA) | Similar leverage restrictions |
| US | NFA-regulated brokers; no CFDs for US residents (use futures) |
| Australia (ASIC) | Leverage caps on CFDs |
| India | Retail forex trading via offshore brokers — legal gray area; consult local law |

**COMEX GC futures** (CME): CFTC-regulated; 100 oz/contract; US-accessible via futures brokers.

## BTC (Cryptocurrency)

| Jurisdiction | Key rules |
|--------------|-----------|
| US | CME BTC futures = CFTC; spot ETFs (2024+); exchange KYC/AML |
| EU | MiCA framework (phased) |
| India | 30% tax on crypto gains; 1% TDS on transfers; exchange restrictions evolve — check RBI/SEBI |
| Global | No unified regulation; venue selection critical |

## Venue Types

| Venue | Regulation | Instruments |
|-------|------------|-----------|
| Binance | Offshore; geo-blocks | Spot, perp |
| Coinbase | US-regulated | Spot |
| CME | CFTC | BTC futures, micro BTC |
| OANDA / IBKR | Multi-jurisdiction | XAUUSD CFD/spot |
| MetaTrader brokers | Varies by broker | XAUUSD CFD |

## Tax Considerations (general)

- Crypto: capital gains treatment varies by country
- India: 30% flat on crypto gains + 1% TDS
- Forex CFD: treatment varies; may be ordinary income
- **Consult a tax professional** — not covered in detail here

## Compliance for Algo Trading

- KYC on all regulated exchanges
- API rate limits and terms of service
- Market manipulation rules apply to order placement
- No guarantee of exchange solvency (use regulated venues for large capital)

## Pattern Trading Legal Notes

- Research and backtesting: generally unrestricted
- Live automated trading: must comply with broker/exchange API terms
- India F&O algo: exchange registration required
- No specific restriction on DTW/pattern methods — standard market rules apply

See [xauusd-gold.md](../instruments/xauusd-gold.md) and [btc-bitcoin.md](../instruments/btc-bitcoin.md).
