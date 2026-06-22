"""FinRL DataProcessor facade — DuckDB vault + free fetchers."""
from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd

from data.free_historical_fetcher import fetch_historical
from data_vault import get_ohlcv
from ml.finrl import config
from ml.finrl.preprocessor import FeatureEngineer, add_technical_indicator, add_turbulence, add_vix


def vault_to_finrl_df(symbol: str, interval: str, bars: int = 500_000) -> pd.DataFrame:
    """Convert QUANT DuckDB OHLCV → FinRL long format (date, tic, OHLCV)."""
    raw = get_ohlcv(symbol, interval, bars=bars)
    if raw.empty:
        return raw
    tic = config.SYMBOL_TO_TIC.get(symbol.upper(), symbol.upper())
    df = raw.copy()
    df["date"] = pd.to_datetime(df["time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    df["tic"] = tic
    return df[["date", "tic", "open", "high", "low", "close", "volume"]]


def fetch_to_finrl_df(symbol: str, interval: str, days_back: int = 365) -> pd.DataFrame:
    raw = fetch_historical(symbol, interval, days_back)
    if raw.empty:
        return raw
    tic = config.SYMBOL_TO_TIC.get(symbol.upper(), symbol.upper())
    df = raw.copy()
    df["date"] = pd.to_datetime(df["time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    df["tic"] = tic
    return df[["date", "tic", "open", "high", "low", "close", "volume"]]


def df_to_arrays(
    df: pd.DataFrame,
    tech_indicator_list: list[str] | None = None,
    if_vix: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    FinRL df_to_array: (price_array, tech_array, turbulence_array).
    price_array shape: (T, n_assets)
    tech_array shape: (T, n_assets * n_indicators [+ vix])
    """
    tech_indicator_list = tech_indicator_list or config.INDICATORS
    df = df.sort_values(["date", "tic"]).copy()
    dates = sorted(df.date.unique())
    tics = sorted(df.tic.unique())
    n_t = len(dates)
    n_assets = len(tics)

    price_array = np.zeros((n_t, n_assets), dtype=np.float32)
    n_ind = len(tech_indicator_list) + (1 if if_vix and "vix" in df.columns else 0)
    tech_array = np.zeros((n_t, n_assets * n_ind), dtype=np.float32)
    turbulence_array = np.zeros(n_t, dtype=np.float32)

    if "turbulence" in df.columns:
        turb_by_date = df.groupby("date")["turbulence"].first()
        for i, d in enumerate(dates):
            turbulence_array[i] = float(turb_by_date.get(d, 0.0))

    for j, tic in enumerate(tics):
        sub = df[df.tic == tic].set_index("date").reindex(dates)
        price_array[:, j] = sub["close"].astype(float).ffill().bfill().values
        cols = list(tech_indicator_list)
        if if_vix and "vix" in sub.columns:
            cols = cols + ["vix"]
        block = sub[cols].astype(float).ffill().bfill().values
        tech_array[:, j * n_ind : (j + 1) * n_ind] = block

    tech_array = np.nan_to_num(tech_array, nan=0.0, posinf=0.0, neginf=0.0)
    price_array = np.nan_to_num(price_array, nan=0.0, posinf=0.0, neginf=0.0)
    return price_array, tech_array, turbulence_array


class QuantDataProcessor:
    """
    FinRL DataProcessor facade for QUANT.
    data_source: 'vault' | 'fetch' | 'vault_then_fetch'
    """

    def __init__(
        self,
        data_source: str = "vault",
        tech_indicator: list[str] | None = None,
        use_vix: bool = True,
        use_turbulence: bool = False,
    ):
        self.data_source = data_source
        self.tech_indicator_list = tech_indicator or config.INDICATORS
        self.use_vix = use_vix
        self.use_turbulence = use_turbulence
        self._engineer = FeatureEngineer(
            tech_indicator_list=self.tech_indicator_list,
            use_vix=use_vix,
            use_turbulence=use_turbulence,
        )

    def download_data(
        self,
        ticker_list: list[str],
        start_date: str,
        end_date: str,
        time_interval: str,
        days_back: int = 730,
    ) -> pd.DataFrame:
        frames = []
        for sym in ticker_list:
            sym = sym.upper()
            if self.data_source == "fetch":
                df = fetch_to_finrl_df(sym, time_interval, days_back)
            elif self.data_source == "vault_then_fetch":
                df = vault_to_finrl_df(sym, time_interval)
                if df.empty:
                    df = fetch_to_finrl_df(sym, time_interval, days_back)
            else:
                df = vault_to_finrl_df(sym, time_interval)
            if not df.empty:
                frames.append(df)
        if not frames:
            raise ValueError(f"No data for {ticker_list} {time_interval}")
        out = pd.concat(frames, ignore_index=True)
        out["date"] = pd.to_datetime(out["date"])
        mask = (out["date"] >= pd.Timestamp(start_date)) & (out["date"] < pd.Timestamp(end_date))
        out = out.loc[mask].copy()
        out["date"] = out["date"].dt.strftime("%Y-%m-%d %H:%M:%S")
        return out

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        return FeatureEngineer.clean_data(df)

    def add_technical_indicator(self, df: pd.DataFrame, tech_indicator_list: list[str] | None = None) -> pd.DataFrame:
        self.tech_indicator_list = tech_indicator_list or self.tech_indicator_list
        return add_technical_indicator(df, self.tech_indicator_list)

    def add_vix(self, df: pd.DataFrame) -> pd.DataFrame:
        return add_vix(df)

    def add_turbulence(self, df: pd.DataFrame) -> pd.DataFrame:
        return add_turbulence(df)

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._engineer.preprocess_data(df)

    def df_to_array(self, df: pd.DataFrame, if_vix: bool | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if_vix = self.use_vix if if_vix is None else if_vix
        return df_to_arrays(df, self.tech_indicator_list, if_vix=if_vix)

    def build_arrays(
        self,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: str,
        days_back: int = 730,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
        """Full pipeline: download → preprocess → arrays."""
        df = self.download_data([symbol], start_date, end_date, interval, days_back)
        df = self.preprocess(df)
        price, tech, turb = self.df_to_array(df, if_vix=self.use_vix)
        return price, tech, turb, df

    def save_dataset(self, df: pd.DataFrame, name: str) -> str:
        os.makedirs(config.DATA_SAVE_DIR, exist_ok=True)
        path = os.path.join(config.DATA_SAVE_DIR, f"{name}.csv")
        df.to_csv(path, index=False)
        return path
