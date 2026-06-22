# INFORMS — Dynamic Time Warping Summary

Companion note for [Paper #2](papers-index.md). Original: [Berndt & Clifford 1994](L1-foundations/1994-berndt-clifford-dtw.pdf).

Source explainer: [INFORMS OR/MS Tomorrow](https://www.informs.org/Publications/OR-MS-Tomorrow/A-measure-of-distance-between-time-series-Dynamic-Time-Warping)

## Problem

Euclidean distance fails when two time series have the **same shape** but different **speed** or **phase**. Financial patterns (rally, dump, consolidation) often repeat at different durations.

## Cost Matrix

For sequences S (length n) and T (length m), build an n×m grid where cell (i,j) = distance δ(s_i, t_j).

Common δ:
- |s_i − t_j| (L1)
- (s_i − t_j)² (L2)

## Warping Path

A path W = (w_1, ..., w_k) where each w_l = (i, j) maps elements of S to T.

Constraints:
- Starts at (1,1), ends at (n,m)
- Each step moves to (i+1,j), (i,j+1), or (i+1,j+1)
- Monotonicity: i and j never decrease

## DTW Distance

```
DTW(S,T) = min over all valid paths W of Σ δ(w_l)
```

Computed via dynamic programming:

```
D(i,j) = δ(i,j) + min(D(i-1,j), D(i,j-1), D(i-1,j-1))
DTW(S,T) = D(n,m)
```

## Sakoe-Chiba Band (Warping Window)

Restrict path to band of width r around diagonal:

```
|i - j| ≤ r
```

Prevents pathological warping (one point matching many). Typical r = 10% of sequence length for finance.

## Application to Trading

1. Extract current window W_t from live series
2. Compare DTW(W_t, template_k) for each motif template k
3. If min distance < threshold θ → pattern match → event trigger
4. Warping path shows **which bars align** — useful for interpretability

## Python

```python
from tslearn.metrics import dtw
distance = dtw(subsequence_a, subsequence_b)
```

See [06-pattern-based-trading.md](../docs/06-pattern-based-trading.md).
