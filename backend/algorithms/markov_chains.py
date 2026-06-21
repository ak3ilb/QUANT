import numpy as np
import pandas as pd

def markov_analysis(df: pd.DataFrame) -> dict:
    returns = df['close'].pct_change().dropna()
    
    std = returns.std()
    states = []
    for r in returns:
        if r > 0.5 * std: states.append("Up")
        elif r < -0.5 * std: states.append("Down")
        else: states.append("Flat")
        
    transitions = {"Up": {"Up": 0, "Down": 0, "Flat": 0},
                   "Down": {"Up": 0, "Down": 0, "Flat": 0},
                   "Flat": {"Up": 0, "Down": 0, "Flat": 0}}
                   
    for i in range(len(states)-1):
        transitions[states[i]][states[i+1]] += 1
        
    for k, v in transitions.items():
        total = sum(v.values())
        if total > 0:
            for target in v:
                v[target] = v[target] / total
                
    return {
        "current_state": states[-1],
        "transitions": transitions
    }
