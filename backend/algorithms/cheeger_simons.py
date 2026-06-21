import numpy as np
import pandas as pd

def cheeger_simons_characters(df: pd.DataFrame) -> dict:
    """
    Cheeger-Simons Differential Characters.
    Evaluates boundary integrals over cyclic price action.
    """
    if len(df) < 50:
        return {"cyclic_invariant": 0.0, "regime_boundary": 0.0}
        
    # We integrate price momentum over the boundary of the rolling window
    momentum = df['close'].diff().fillna(0).values
    
    # The integral of omega modulo Z
    integral_omega = np.cumsum(momentum)
    
    # Modulo Z character (fractional cycle progression)
    # We map price to a bounded lattice space by dividing by standard deviation
    std = np.std(momentum) if np.std(momentum) > 0 else 1
    lattice_integral = integral_omega / std
    
    differential_character = lattice_integral % 1.0
    
    current_char = np.mean(differential_character[-10:])
    
    return {
        "cyclic_invariant": float(current_char),
        "regime_boundary": float(lattice_integral[-1])
    }
