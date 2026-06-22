import numpy as np
import pandas as pd


def _student_t_predictive(x: np.ndarray, mu0: float = 0.0, kappa0: float = 1.0, alpha0: float = 1.0, beta0: float = 1.0) -> float:
    """Log predictive density under Normal-Inverse-Gamma prior."""
    n = len(x)
    if n == 0:
        return 0.0

    x_bar = float(np.mean(x))
    kappa_n = kappa0 + n
    alpha_n = alpha0 + n / 2.0
    beta_n = beta0 + 0.5 * np.sum((x - x_bar) ** 2) + (kappa0 * n / (2.0 * kappa_n)) * (x_bar - mu0) ** 2

    # Predictive for next point uses Student-t with these params
    nu = 2.0 * alpha_n
    scale = np.sqrt(beta_n * (kappa_n + 1.0) / (alpha_n * kappa_n))
    if scale <= 0 or not np.isfinite(scale):
        return 0.0

    z = (x[-1] - x_bar) / scale if n == 1 else 0.0
    return float(-0.5 * (nu + 1.0) * np.log1p((z ** 2) / nu) - np.log(scale))


def bocpd_break(
    df: pd.DataFrame,
    hazard_rate: float = 1 / 100,
    break_threshold: float = 0.55,
) -> dict:
    """
    Bayesian Online Changepoint Detection on returns (Adams & MacKay style).
    """
    returns = pd.to_numeric(df["close"], errors="coerce").pct_change().dropna().values
    if len(returns) < 40:
        return {
            "structural_break": False,
            "changepoint_prob": 0.0,
            "run_length": len(returns),
            "model": "bocpd",
        }

    hazard_rate = max(1e-5, min(0.5, float(hazard_rate)))
    max_run = min(len(returns), 250)

    # Run-length posterior: R[t, r] = P(run_length=r at t)
    R = np.zeros((len(returns), max_run + 1))
    R[0, 0] = 1.0

    for t in range(1, len(returns)):
        x = returns[max(0, t - max_run) : t + 1]
        pred_probs = np.zeros(max_run + 1)

        for r in range(min(t, max_run) + 1):
            segment = returns[t - r : t + 1]
            log_p = _student_t_predictive(segment)
            pred_probs[r] = np.exp(log_p) if np.isfinite(log_p) else 1e-12

        growth = R[t - 1] * pred_probs * (1.0 - hazard_rate)
        cp = np.sum(R[t - 1] * pred_probs) * hazard_rate

        new_R = np.zeros(max_run + 1)
        new_R[1 : len(growth)] = growth[:-1]
        new_R[0] = cp

        total = new_R.sum()
        if total > 0:
            R[t] = new_R / total
        else:
            R[t, 0] = 1.0

    changepoint_prob = float(R[-1, 0])
    run_length = int(np.argmax(R[-1]))

    return {
        "structural_break": bool(changepoint_prob >= break_threshold),
        "changepoint_prob": changepoint_prob,
        "run_length": run_length,
        "model": "bocpd",
    }
