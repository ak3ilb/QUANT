import numpy as np
import pandas as pd

def chern_simons_gauge(df: pd.DataFrame) -> dict:
    """
    Market curvature heuristic inspired by Chern-Simons forms.

    The cited Chern-Simons sources concern connection 1-forms and curvature
    forms on manifolds. Here, close-to-close returns are used only as a
    practical proxy for local market curvature.
    """
    if len(df) < 20:
        return {
            "cs_1d": 0.0,
            "cs_3d": 0.0,
            "cs_5d": 0.0,
            "curvature_value": 0.0,
            "curvature_signal": "HOLD",
            "model_status": "heuristic_analogy",
        }
        
    A = df['close'].pct_change().replace([np.inf, -np.inf], np.nan).fillna(0).values
    A = np.clip(A, -0.05, 0.05)
    dA = np.diff(A, prepend=0)
    
    # 1D Form: A mod Z (We'll use modulo 1 for fractional part proxy)
    cs_1d = np.mean(A % 1.0)
    
    # 3D Form: Tr(dA^A + 2/3 A^3)
    cs_3d_arr = (dA * A) + (2/3 * (A**3))
    cs_3d = np.mean(cs_3d_arr)
    
    # 5D Form: Tr(A^(dA)^2 + 3/2 A^3 ^ dA + 3/5 A^5)
    cs_5d_arr = (A * (dA**2)) + (1.5 * (A**3) * dA) + (0.6 * (A**5))
    # Multiply by 1e12 to scale the infinitesimal topological invariant into a human-readable number
    cs_5d = np.mean(cs_5d_arr) * 1e12
    
    signal = "BUY" if cs_5d > 0 else "SELL" if cs_5d < 0 else "HOLD"
    
    return {
        "cs_1d": float(cs_1d),
        "cs_3d": float(cs_3d),
        "cs_5d": float(cs_5d),
        "curvature_value": float(cs_5d),
        "curvature_signal": signal,
        "model_status": "heuristic_analogy",
    }
