# Pattern-Based Trading — Non-Static Methodology

This is the **core methodology** for this knowledge base. The goal is **real pattern recognition**, not static timing backtests.

## Why Static Timing Fails

| Static approach | Problem | Pattern alternative |
|-----------------|---------|---------------------|
| "Enter every Tuesday 9:15" | Ignores market structure | DTW match to known motif |
| Fixed 20-bar lookback | Pattern completes in 12 or 35 bars | VALMOD, SLIM variable-length |
| Single train/test split | Regime change breaks model | BOCPD + walk-forward per regime |
| Euclidean distance | Misses time-warped same shape | DTW warping path |
| RSI cross at bar N | Lagging, not shape-aware | Shapelet or Matrix Profile discord |

## The 6-Layer Research Stack

### Layer 1 — Distance Foundations

| Paper | File | Key idea |
|-------|------|----------|
| Berndt & Clifford 1994 — DTW | [PDF](../research/papers/L1-foundations/1994-berndt-clifford-dtw.pdf) | Warping path: `DTW(S,T) = min Σ δ(w_i)` |
| INFORMS DTW explainer | [Link](https://www.informs.org/Publications/OR-MS-Tomorrow/A-measure-of-distance-between-time-series-Dynamic-Time-Warping) | Cost matrix, Sakoe-Chiba window |
| SAX — Lin & Keogh | [PDF](../research/papers/L1-foundations/sax-lin-keogh.pdf) | Symbolic discretization for fast search |
| CID — Batista & Keogh | [PDF](../research/papers/L1-foundations/2011-batista-keogh-cid.pdf) | Complexity-invariant distance |

**DTW cost matrix:** Build `n×m` grid of pairwise distances. Recursive cumulative cost:

```
D(i,j) = δ(i,j) + min(D(i-1,j), D(i,j-1), D(i-1,j-1))
```

Warping path = path from (1,1) to (n,m) minimizing cumulative cost.

### Layer 2 — Mechanism Clustering

| Paper | File | Key idea |
|-------|------|----------|
| **TS-K-means + ANM-MM** | [PDF](../research/papers/L2-clustering/2202.03146-ts-kmeans-anm-mm.pdf) | Cluster by **generative mechanism**, not calendar |
| k-medoids + IDTW (TOPIX) | [Link](https://doi.org/10.1002/ecj.12140) | Representative fluctuation patterns |

**Your Paper 1** replaces Euclidean K-means with DTW-based TS-K-means inside ANM-MM for causal mechanism clustering on financial returns.

### Layer 3 — Motif Discovery

| Paper | File | Key idea |
|-------|------|----------|
| Matrix Profile I | [PDF](../research/papers/L3-motifs/2016-matrix-profile-I.pdf) | All-pairs nearest neighbor subsequence distances |
| STOMP (DMKD 2018) | [PDF](../research/papers/L3-motifs/2018-stomp-dmkd.pdf) | O(n²) scalable exact computation |
| VALMOD (financial) | [PDF](../research/papers/L3-motifs/valmod-financial-chapter.pdf) | Variable-length motifs |
| SLIM | [Link](https://www.mdpi.com/1999-4893/4/1/13) | Side-length-independent motifs |
| FX motif forecasting | [PDF](../research/papers/L6-trading-applications/jmest-fx-motif-forecasting.pdf) | CID + adaptive dissimilarity for FX |

**Motif** = most similar non-trivial subsequence pair. **Discord** = most anomalous subsequence.

```python
import stumpy
import numpy as np

# T = z-normalized price series, m = motif length
mp = stumpy.stump(T, m)
motif_idx = np.argmin(mp[:, 0])  # best match location
discord_idx = np.argmax(mp[:, 0])  # anomaly location
```

### Layer 4 — Regime Detection

| Paper | File | Key idea |
|-------|------|----------|
| BOCPD — Adams & MacKay | [PDF](../research/papers/L4-regimes/2007-adams-mackay-bocpd.pdf) | Online run-length posterior |
| BOCPD order flow | [PDF](../research/papers/L4-regimes/2307.02375-bocpd-order-flow.pdf) | Score-driven regime breaks |
| HMM regime factors | [Link](https://www.mdpi.com/1911-8074/13/12/311) | Route strategy by hidden state |

**Use regimes as controllers**, not predictors. HMM/BOCPD tells you *which pattern library is active*, not the next tick.

### Layer 5 — Classification & ML

| Paper | File | Key idea |
|-------|------|----------|
| Shapelets — Ye & Keogh | [Link](https://link.springer.com/article/10.1007/s10618-010-0179-5) | Interpretable discriminative subsequences |
| JISC-Net (2025) | [PDF](../research/papers/L5-shapelets-ml/2509.15040-jisc-net.pdf) | DTW + multivariate shapelets for finance |
| FinRL | [PDF](../research/papers/L5-shapelets-ml/2011.09607-finrl.pdf) | DRL learns when to act on pattern features |

### Layer 6 — Trading Application

| Paper | File | Key idea |
|-------|------|----------|
| DTW pattern matching trading | [Link](https://www.mdpi.com/2071-1050/10/12/4641) | Template matching for futures |
| FX motif forecasting | [PDF](../research/papers/L6-trading-applications/jmest-fx-motif-forecasting.pdf) | Event-driven FX prediction |

## Event-Driven Backtest Design

```
ENTRY:  DTW(current_window, motif_template) < threshold
        AND BOCPD_regime in favorable_set
        AND spread < max_spread

EXIT:   DTW match to opposing motif
        OR Matrix Profile discord detected
        OR regime change (BOCPD alert)
        OR stop-loss (ATR-scaled)

SIZE:   f(DTW_confidence, regime_probability, account_risk%)
```

**No clock triggers.** Signals fire when pattern conditions are met.

## Python Toolchain

| Library | Function |
|---------|----------|
| `tslearn` | `TimeSeriesKMeans(metric='dtw')`, `dtw` |
| `stumpy` | Matrix Profile, motifs, discords, shapelets |
| `hmmlearn` | `GaussianHMM` regime detection |
| `ruptures` | Offline PELT, BinSeg changepoints |
| `finrl` | DRL layer on top of pattern features |

```python
from tslearn.clustering import TimeSeriesKMeans
model = TimeSeriesKMeans(n_clusters=5, metric="dtw", max_iter=10)
labels = model.fit_predict(time_series_array)
```

## Per-Instrument Pattern Notes

### XAUUSD
- Session-segment before mining (London/NY only)
- DTW on dollar moves, not pip counts
- Motifs: pre-fix accumulation, FOMC spike, London open drive
- BOCPD on real-yield correlation breaks

### BTC
- 24/7 — no session filter
- Log returns + z-norm
- Motifs: funding-extreme reversal, liquidation cascade
- Matrix Profile on M15/H1

### Nifty 50
- IST session only (9:15–15:30)
- Shapelets for opening gap (first 15 min)
- Tuesday expiry gamma motifs
- Tag motifs by days-to-expiry

### Bank Nifty
- Higher vol → wider DTW Sakoe-Chiba window
- RBI announcement reaction templates
- BankNifty/Nifty ratio motifs
- Monthly expiry only — separate motif library

## Static vs Pattern Backtest

| Dimension | Static | Pattern-native |
|-----------|--------|----------------|
| Entry trigger | Clock / bar count | Motif similarity score |
| Window size | Fixed N | Variable (VALMOD, SLIM) |
| Train period | One block | Walk-forward per regime |
| Validation | Sharpe on full sample | Hit rate + regime-conditional expectancy |
| Overfitting risk | Time parameters | K, DTW window, motif length |

## Reading Order

1. Berndt & Clifford DTW → understand warping
2. arXiv:2202.03146 → mechanism clustering
3. Matrix Profile I + STOMP → automatic motif discovery
4. BOCPD → regime breaks
5. JISC-Net or DTW trading paper → application
6. FinRL → RL layer on pattern features

Full index: [research/papers-index.md](../research/papers-index.md)
