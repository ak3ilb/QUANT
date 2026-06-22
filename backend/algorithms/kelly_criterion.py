import os

import numpy as np
import pandas as pd
import duckdb

DEFAULT_WIN_RATE = 0.5075
_MIN_CLOSED_TRADES = 5


def _win_rate_from_ledger() -> float | None:
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quant_vault.duckdb")
    if not os.path.exists(db_path):
        return None

    try:
        con = duckdb.connect(database=db_path, read_only=True)
        tables = con.execute("SHOW TABLES").df()
        if "paper_ledger" not in tables["name"].values:
            con.close()
            return None

        closed = con.execute(
            """
            SELECT pnl_usd
            FROM paper_ledger
            WHERE status = 'CLOSED' AND pnl_usd IS NOT NULL
            """
        ).df()
        con.close()

        if len(closed) < _MIN_CLOSED_TRADES:
            return None

        wins = (closed["pnl_usd"] > 0).sum()
        return float(wins / len(closed))
    except Exception:
        return None


def kelly_sizing(df: pd.DataFrame, strategy: str = "medallion") -> dict:
    """
    Kelly Criterion position sizing with adaptive win rate from closed paper trades.
    """
    ledger_win_rate = _win_rate_from_ledger()
    w = ledger_win_rate if ledger_win_rate is not None else DEFAULT_WIN_RATE
    win_rate_source = "paper_ledger" if ledger_win_rate is not None else "default"

    if len(df) < 10:
        return {
            "win_rate": w,
            "win_rate_source": win_rate_source,
            "win_loss_ratio": 1.0,
            "full_kelly": 0.0,
            "fractional_kelly": 0.0,
            "recommended_size_pct": 0.0,
        }

    returns = df["close"].pct_change().dropna()
    avg_win = returns[returns > 0].mean()
    avg_loss = abs(returns[returns < 0].mean())

    if pd.isna(avg_win) or pd.isna(avg_loss) or avg_loss == 0:
        r = 1.0
    else:
        r = float(avg_win / avg_loss)

    f_star = w - ((1 - w) / r) if r > 0 else 0.0
    f_star = max(0.0, min(1.0, f_star))
    fractional_kelly = f_star * 0.5

    return {
        "win_rate": float(w),
        "win_rate_source": win_rate_source,
        "win_loss_ratio": r,
        "full_kelly": float(f_star),
        "fractional_kelly": float(fractional_kelly),
        "recommended_size_pct": float(fractional_kelly * 100),
    }
