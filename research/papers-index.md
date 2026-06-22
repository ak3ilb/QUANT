# Research Papers Index

22-paper bibliography for pattern-native quant trading. PDFs in [papers/](papers/) where open access.

**Reading order:** L1 → L2 → L3 → L4 → L5 → L6. See [06-pattern-based-trading.md](../docs/06-pattern-based-trading.md).

---

## Tier 0 — Must-Read (User Requested)

| # | Paper | ID | PDF | Why read |
|---|-------|-----|-----|----------|
| 1 | Time-Series K-means in Causal Inference and Mechanism Clustering for Financial Data | [arXiv:2202.03146](https://arxiv.org/abs/2202.03146) | [✓ L2](papers/L2-clustering/2202.03146-ts-kmeans-anm-mm.pdf) | TS-K-means + DTW + ANM-MM clusters recurring generative mechanisms |
| 2 | A measure of distance between time series: Dynamic Time Warping | [INFORMS](https://www.informs.org/Publications/OR-MS-Tomorrow/A-measure-of-distance-between-time-series-Dynamic-Time-Warping) | Summary in [06-pattern](../docs/06-pattern-based-trading.md) | Cost matrix, warping path, Sakoe-Chiba window |
| 2b | Using Dynamic Time Warping to Find Patterns in Time Series | Berndt & Clifford, KDD 1994 | [✓ L1](papers/L1-foundations/1994-berndt-clifford-dtw.pdf) | Original DTW: `DTW(S,T) = min Σ δ(w_i)` |

---

## L1 — Foundations

| # | Paper | PDF | Why read |
|---|-------|-----|----------|
| 3 | Experiencing SAX: A Novel Symbolic Representation of Time Series | [✓ L1](papers/L1-foundations/sax-lin-keogh.pdf) | Discretize OHLCV; fast motif search with lower-bound distance |
| 4 | A Complexity-Invariant Distance Measure for Time Series (CID) | [✓ L1](papers/L1-foundations/2011-batista-keogh-cid.pdf) | Corrects complexity bias across vol regimes |
| 5 | iSAX: Indexing and mining massive time series | [Link](https://www.cs.ucr.edu/~eamonn/iSAX.htm) | Scalable symbolic indexing |

---

## L2 — Clustering

| # | Paper | PDF | Why read |
|---|-------|-----|----------|
| 6 | Stock price prediction using k-medoids with indexing DTW | [DOI](https://doi.org/10.1002/ecj.12140) | Paywalled — IDTW clusters TOPIX patterns as momentum/reversal |
| 7 | Using DTW to Cluster Stocks | [Medium](https://lixiaoguang.medium.com/using-dynamic-time-warping-dtw-to-cluster-stocks-a2e50ad43480) | tslearn `TimeSeriesKMeans(metric='dtw')` tutorial |

---

## L3 — Motifs

| # | Paper | PDF | Why read |
|---|-------|-----|----------|
| 8 | Matrix Profile I: All Pairs Similarity Joins | [✓ L3](papers/L3-motifs/2016-matrix-profile-I.pdf) | Foundational motif/discord via matrix profile |
| 9 | STOMP — motifs, discords, shapelets unifying view | [✓ L3](papers/L3-motifs/2018-stomp-dmkd.pdf) | O(n²) scalable exact algorithm |
| 10 | Financial Time Series: Matrix Profile Techniques | [MDPI](https://www.mdpi.com/2673-4591/5/1/45) | Direct financial MP application |
| 11 | SLIM: Side-Length-Independent Motif | [MDPI](https://www.mdpi.com/1999-4893/4/1/13) | Same shape at different speeds |
| 12 | Motif Discovery Using VALMOD (financial) | [✓ L3](papers/L3-motifs/valmod-financial-chapter.pdf) | Variable-length financial motifs |
| 13 | FX Forecasting Based on Motif Discovery | [✓ L6](papers/L6-trading-applications/jmest-fx-motif-forecasting.pdf) | CID + motif for FX prediction |

---

## L4 — Regimes

| # | Paper | PDF | Why read |
|---|-------|-----|----------|
| 14 | Bayesian Online Changepoint Detection | [✓ L4](papers/L4-regimes/2007-adams-mackay-bocpd.pdf) | Online run-length posterior for regime breaks |
| 15 | BOCPD for Financial Time Series | [ACM 2025](https://dl.acm.org/doi/10.1145/3795154.3795291) | S&P 500 / CSI 300; beats GLR and KS |
| 16 | Regime-Switching Factor Investing with HMM | [MDPI](https://www.mdpi.com/1911-8074/13/12/311) | Route strategy by detected regime |
| 17 | BOCPD for Order Flow | [✓ L4](papers/L4-regimes/2307.02375-bocpd-order-flow.pdf) | Score-driven microstructure regimes |

---

## L5 — Shapelets & ML

| # | Paper | PDF | Why read |
|---|-------|-----|----------|
| 18 | Time Series Shapelets | [Springer](https://link.springer.com/article/10.1007/s10618-010-0179-5) | Interpretable subsequence classifiers |
| 19 | JISC-Net: Shapelet Framework for Finance | [✓ L5](papers/L5-shapelets-ml/2509.15040-jisc-net.pdf) | DTW + multivariate shapelets (2025) |
| 20 | FinRL: DRL library for stock trading | [✓ L5](papers/L5-shapelets-ml/2011.09607-finrl.pdf) | Pattern features as RL state |
| 21 | FinRL-Meta: Market Environments | [✓ L5](papers/L5-shapelets-ml/2211.03107-finrl-meta.pdf) | Custom Gym envs |

---

## L6 — Trading Applications

| # | Paper | PDF | Why read |
|---|-------|-----|----------|
| 22 | Pattern Matching Trading System Based on DTW | [MDPI](https://www.mdpi.com/2071-1050/10/12/4641) | Direct DTW template matching for futures |

---

## Download Status

| Status | Count |
|--------|-------|
| PDF downloaded | 13 |
| Link only (paywall or MDPI fetch failed) | 9 |

### Downloaded PDFs

```
papers/L1-foundations/1994-berndt-clifford-dtw.pdf
papers/L1-foundations/sax-lin-keogh.pdf
papers/L1-foundations/2011-batista-keogh-cid.pdf
papers/L2-clustering/2202.03146-ts-kmeans-anm-mm.pdf
papers/L3-motifs/2016-matrix-profile-I.pdf
papers/L3-motifs/2018-stomp-dmkd.pdf
papers/L3-motifs/valmod-financial-chapter.pdf
papers/L4-regimes/2007-adams-mackay-bocpd.pdf
papers/L4-regimes/2307.02375-bocpd-order-flow.pdf
papers/L5-shapelets-ml/2509.15040-jisc-net.pdf
papers/L5-shapelets-ml/2011.09607-finrl.pdf
papers/L5-shapelets-ml/2211.03107-finrl-meta.pdf
papers/L6-trading-applications/jmest-fx-motif-forecasting.pdf
```

### Key Equations Reference

**DTW (Berndt & Clifford 1994):**
```
DTW(S,T) = min over warping paths W of Σ δ(w_i)
D(i,j) = δ(s_i, t_j) + min(D(i-1,j), D(i,j-1), D(i-1,j-1))
```

**CID (Batista & Keogh 2011):**
```
CID(Q,C) = ED(Q,C) × CF(Q,C)
CF = complexity correction factor based on arc length
```

**Matrix Profile:**
```
MP[i] = min distance from subsequence T[i:i+m] to any other subsequence
Motif = argmin(MP)  |  Discord = argmax(MP)
```
