import numpy as np
import pandas as pd

def ax_kochen_break(df: pd.DataFrame) -> dict:
    if len(df) < 60:
        return {"structural_break": False}
        
    returns = df['close'].pct_change().dropna().values
    recent = returns[-30:]
    older = returns[-60:-30]
    
    var_recent = np.var(recent)
    var_older = np.var(older)
    
    f_stat = var_recent / var_older if var_older > 0 else 1
    is_break = bool(f_stat > 2.5 or f_stat < 0.4)
    
    return {
        "f_statistic": float(f_stat),
        "structural_break": is_break
    }
