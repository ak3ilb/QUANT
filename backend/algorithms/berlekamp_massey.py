import numpy as np
import pandas as pd

def berlekamp_massey(df: pd.DataFrame) -> dict:
    if len(df) < 50:
        return {"lfsr_length": 0, "prediction": 0}
        
    returns = df['close'].pct_change().dropna().values
    seq = (returns > 0).astype(int)
    
    n = len(seq)
    c = np.zeros(n, dtype=int)
    b = np.zeros(n, dtype=int)
    c[0] = 1
    b[0] = 1
    l = 0
    m = -1
    
    for i in range(n):
        d = 0
        for j in range(l + 1):
            d ^= (c[j] * seq[i - j])
        if d == 1:
            t = np.copy(c)
            p = i - m
            for j in range(n - p):
                c[j + p] ^= b[j]
            if 2 * l <= i:
                l = i + 1 - l
                m = i
                b = t
                
    next_val = 0
    if l > 0:
        for j in range(1, l + 1):
            next_val ^= (c[j] * seq[-j])
            
    return {
        "lfsr_length": int(l),
        "prediction_binary": int(next_val),
        "prediction_label": "UP" if next_val == 1 else "DOWN",
        "complexity_ratio": float(l / n)
    }
