"""FinRL FeatureEngineer, data_split, GroupByScaler — reimplemented for QUANT."""
from __future__ import annotations

import datetime

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import MaxAbsScaler

from ml.finrl import config


def data_split(df: pd.DataFrame, start: str, end: str, target_date_col: str = "date") -> pd.DataFrame:
    """Split dataset by date range (FinRL preprocessors.data_split)."""
    data = df.copy()
    data[target_date_col] = pd.to_datetime(data[target_date_col])
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    data = data[(data[target_date_col] >= start_ts) & (data[target_date_col] < end_ts)]
    data[target_date_col] = data[target_date_col].dt.strftime("%Y-%m-%d %H:%M:%S")
    data = data.sort_values([target_date_col, "tic"], ignore_index=True)
    data.index = data[target_date_col].factorize()[0]
    return data


class GroupByScaler(BaseEstimator, TransformerMixin):
    """Per-ticker sklearn scaler (FinRL GroupByScaler)."""

    def __init__(self, by: str, scaler=MaxAbsScaler, columns=None, scaler_kwargs=None):
        self.scalers = {}
        self.by = by
        self.scaler = scaler
        self.columns = columns
        self.scaler_kwargs = {} if scaler_kwargs is None else scaler_kwargs

    def fit(self, X, y=None):
        if self.columns is None:
            self.columns = X.select_dtypes(exclude=["object"]).columns
        for value in X[self.by].unique():
            X_group = X.loc[X[self.by] == value, self.columns]
            self.scalers[value] = self.scaler(**self.scaler_kwargs).fit(X_group)
        return self

    def transform(self, X, y=None):
        X = X.copy()
        for value in X[self.by].unique():
            mask = X[self.by] == value
            X.loc[mask, self.columns] = self.scalers[value].transform(X.loc[mask, self.columns])
        return X


def _add_indicators_stockstats(df: pd.DataFrame, indicators: list[str]) -> pd.DataFrame:
    from stockstats import StockDataFrame as Sdf

    out = df.copy().sort_values(by=["tic", "date"])
    stock = Sdf.retype(out.copy())
    for indicator in indicators:
        parts = []
        for tic in stock.tic.unique():
            sub = stock[stock.tic == tic]
            temp = pd.DataFrame({indicator: sub[indicator].values})
            temp["tic"] = tic
            temp["date"] = out.loc[out.tic == tic, "date"].values
            parts.append(temp)
        indicator_df = pd.concat(parts, ignore_index=True)
        out = out.merge(indicator_df[["tic", "date", indicator]], on=["tic", "date"], how="left")
    return out.sort_values(by=["date", "tic"])


def _add_indicators_pandas(df: pd.DataFrame, indicators: list[str]) -> pd.DataFrame:
    """Fallback when stockstats is not installed."""
    out = df.copy().sort_values(by=["tic", "date"])
    for tic in out.tic.unique():
        mask = out.tic == tic
        close = out.loc[mask, "close"].astype(float)
        high = out.loc[mask, "high"].astype(float)
        low = out.loc[mask, "low"].astype(float)
        idx = out.loc[mask].index

        if "macd" in indicators:
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            out.loc[idx, "macd"] = ema12 - ema26
        if "boll_ub" in indicators or "boll_lb" in indicators:
            sma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            if "boll_ub" in indicators:
                out.loc[idx, "boll_ub"] = sma20 + 2 * std20
            if "boll_lb" in indicators:
                out.loc[idx, "boll_lb"] = sma20 - 2 * std20
        if "rsi_30" in indicators:
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(30).mean()
            loss = (-delta.clip(upper=0)).rolling(30).mean()
            rs = gain / loss.replace(0, np.nan)
            out.loc[idx, "rsi_30"] = 100 - (100 / (1 + rs))
        if "cci_30" in indicators:
            tp = (high + low + close) / 3
            sma = tp.rolling(30).mean()
            mad = tp.rolling(30).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
            out.loc[idx, "cci_30"] = (tp - sma) / (0.015 * mad)
        if "dx_30" in indicators:
            up = high.diff()
            down = -low.diff()
            plus_dm = np.where((up > down) & (up > 0), up, 0.0)
            minus_dm = np.where((down > up) & (down > 0), down, 0.0)
            tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
            atr = tr.rolling(30).mean()
            plus_di = 100 * pd.Series(plus_dm, index=close.index).rolling(30).mean() / atr
            minus_di = 100 * pd.Series(minus_dm, index=close.index).rolling(30).mean() / atr
            dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
            out.loc[idx, "dx_30"] = dx
        if "close_30_sma" in indicators:
            out.loc[idx, "close_30_sma"] = close.rolling(30).mean()
        if "close_60_sma" in indicators:
            out.loc[idx, "close_60_sma"] = close.rolling(60).mean()

    return out.sort_values(by=["date", "tic"])


def add_technical_indicator(df: pd.DataFrame, indicators: list[str] | None = None) -> pd.DataFrame:
    indicators = indicators or config.INDICATORS
    try:
        import stockstats  # noqa: F401
        return _add_indicators_stockstats(df, indicators)
    except ImportError:
        return _add_indicators_pandas(df, indicators)


def calculate_turbulence(df: pd.DataFrame) -> pd.DataFrame:
    """FinRL multi-asset Mahalanobis turbulence (252-day window)."""
    df_price_pivot = df.pivot(index="date", columns="tic", values="close").pct_change()
    unique_date = df.date.unique()
    start = 252
    turbulence_index = [0.0] * start
    count = 0
    for i in range(start, len(unique_date)):
        current_price = df_price_pivot[df_price_pivot.index == unique_date[i]]
        hist_price = df_price_pivot[
            (df_price_pivot.index < unique_date[i]) & (df_price_pivot.index >= unique_date[i - 252])
        ]
        filtered_hist_price = hist_price.iloc[hist_price.isna().sum().min() :].dropna(axis=1)
        if filtered_hist_price.shape[1] == 0:
            turbulence_index.append(0.0)
            continue
        cov_temp = filtered_hist_price.cov()
        current_temp = current_price[[x for x in filtered_hist_price]] - np.mean(filtered_hist_price, axis=0)
        try:
            temp = current_temp.values.dot(np.linalg.pinv(cov_temp)).dot(current_temp.values.T)
            if temp > 0:
                count += 1
                turbulence_temp = temp[0][0] if count > 2 else 0.0
            else:
                turbulence_temp = 0.0
        except Exception:
            turbulence_temp = 0.0
        turbulence_index.append(turbulence_temp)
    return pd.DataFrame({"date": df_price_pivot.index, "turbulence": turbulence_index})


def add_vix(df: pd.DataFrame) -> pd.DataFrame:
    from data.finrl_patterns import fetch_vix_close
    import yfinance as yf

    start = pd.Timestamp(df.date.min())
    end = pd.Timestamp(df.date.max()) + pd.Timedelta(days=1)
    try:
        vix_df = yf.Ticker("^VIX").history(start=start, end=end, interval="1d")
        if vix_df.empty:
            df["vix"] = fetch_vix_close() or 20.0
            return df
        vix = vix_df.reset_index()
        vix["date"] = pd.to_datetime(vix["Date"]).dt.strftime("%Y-%m-%d")
        vix = vix.rename(columns={"Close": "vix"})[["date", "vix"]]
        out = df.copy()
        out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
        out = out.merge(vix, on="date", how="left")
        out["vix"] = out["vix"].ffill().bfill()
        return out.sort_values(["date", "tic"]).reset_index(drop=True)
    except Exception:
        level = fetch_vix_close() or 20.0
        out = df.copy()
        out["vix"] = level
        return out


def add_turbulence(df: pd.DataFrame) -> pd.DataFrame:
    turb = calculate_turbulence(df)
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    turb["date"] = pd.to_datetime(turb["date"]).dt.strftime("%Y-%m-%d")
    return out.merge(turb, on="date", how="left").sort_values(["date", "tic"]).reset_index(drop=True)


class FeatureEngineer:
    """FinRL FeatureEngineer — preprocess OHLCV panel data."""

    def __init__(
        self,
        use_technical_indicator: bool = True,
        tech_indicator_list: list[str] | None = None,
        use_vix: bool = False,
        use_turbulence: bool = False,
        user_defined_feature: bool = False,
    ):
        self.use_technical_indicator = use_technical_indicator
        self.tech_indicator_list = tech_indicator_list or config.INDICATORS
        self.use_vix = use_vix
        self.use_turbulence = use_turbulence
        self.user_defined_feature = user_defined_feature

    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.clean_data(df)
        if self.use_technical_indicator:
            df = add_technical_indicator(df, self.tech_indicator_list)
        if self.use_vix:
            df = add_vix(df)
        if self.use_turbulence:
            df = add_turbulence(df)
        if self.user_defined_feature:
            df = df.copy()
            df["daily_return"] = df.groupby("tic")["close"].pct_change()
        return df.ffill().bfill().fillna(0)

    @staticmethod
    def clean_data(data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df = df.sort_values(["date", "tic"], ignore_index=True)
        df.index = df.date.factorize()[0]
        merged_closes = df.pivot_table(index="date", columns="tic", values="close")
        merged_closes = merged_closes.dropna(axis=1)
        tics = merged_closes.columns
        return df[df.tic.isin(tics)]
