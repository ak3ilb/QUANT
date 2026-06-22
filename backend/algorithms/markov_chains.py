import numpy as np
import pandas as pd


def markov_analysis(df: pd.DataFrame) -> dict:
    returns = df["close"].pct_change().dropna()

    if len(returns) < 5:
        return {
            "current_state": "Flat",
            "transitions": {},
            "prob_next_up": 0.5,
            "prob_next_down": 0.5,
            "prob_next_flat": 0.0,
        }

    std = returns.std()
    if std == 0 or np.isnan(std):
        std = 1e-6

    states = []
    for r in returns:
        if r > 0.5 * std:
            states.append("Up")
        elif r < -0.5 * std:
            states.append("Down")
        else:
            states.append("Flat")

    transitions = {
        "Up": {"Up": 0, "Down": 0, "Flat": 0},
        "Down": {"Up": 0, "Down": 0, "Flat": 0},
        "Flat": {"Up": 0, "Down": 0, "Flat": 0},
    }

    for i in range(len(states) - 1):
        transitions[states[i]][states[i + 1]] += 1

    for state, targets in transitions.items():
        total = sum(targets.values())
        if total > 0:
            for target in targets:
                targets[target] = targets[target] / total

    current_state = states[-1]
    row = transitions.get(current_state, {"Up": 0.33, "Down": 0.33, "Flat": 0.34})

    return {
        "current_state": current_state,
        "transitions": transitions,
        "prob_next_up": float(row.get("Up", 0.33)),
        "prob_next_down": float(row.get("Down", 0.33)),
        "prob_next_flat": float(row.get("Flat", 0.34)),
    }
