import pandas as pd

from algorithms.hmm_baum_welch import HMMBaumWelch
from algorithms.kelly_criterion import kelly_sizing
from algorithms.kernel_regression import kernel_regression
from algorithms.stochastic_diff_eq import geometric_brownian_motion_sde, ornstein_uhlenbeck_sde
from algorithms.markov_chains import markov_analysis
from algorithms.berlekamp_massey import berlekamp_massey
from algorithms.chern_simons import chern_simons_gauge
from algorithms.ax_kochen import ax_kochen_break
from algorithms.kde_liquidity import kde_liquidity_nodes
from algorithms.simons_equation import simons_hypersurface
from algorithms.cheeger_simons import cheeger_simons_characters
from algorithms.logistic_scorer import predict_prob_bull, score_details
from algorithms.signed_volume import signed_volume_imbalance
from algorithms.bocpd import bocpd_break
from algorithms.kalman_fair_value import kalman_fair_value
from algorithms.cointegration import engle_granger_spread


class QuantEngine:
    def __init__(self):
        self.hmm = HMMBaumWelch()

    def detect_regime(self, df: pd.DataFrame) -> dict:
        return self.hmm.detect_regime(df)

    def kelly_sizing(self, df: pd.DataFrame, strategy: str) -> dict:
        return kelly_sizing(df, strategy)

    def kernel_regression(self, df: pd.DataFrame) -> dict:
        return kernel_regression(df)

    def monte_carlo(
        self,
        df: pd.DataFrame,
        simulations: int = 1000,
        forecast_bars: int = 30,
        seed: int | None = None,
    ) -> dict:
        """Trading SDE path: Ornstein-Uhlenbeck mean-reversion forecast."""
        return self.ornstein_uhlenbeck(df, simulations, forecast_bars, seed)

    def geometric_brownian_motion(
        self,
        df: pd.DataFrame,
        simulations: int = 1000,
        forecast_bars: int = 30,
        seed: int | None = None,
    ) -> dict:
        return geometric_brownian_motion_sde(df, simulations, forecast_bars, seed)

    def ornstein_uhlenbeck(
        self,
        df: pd.DataFrame,
        simulations: int = 1000,
        forecast_bars: int = 30,
        seed: int | None = None,
    ) -> dict:
        return ornstein_uhlenbeck_sde(df, simulations, forecast_bars, seed)

    def markov_analysis(self, df: pd.DataFrame) -> dict:
        return markov_analysis(df)

    def berlekamp_massey(self, df: pd.DataFrame) -> dict:
        return berlekamp_massey(df)

    def chern_simons_gauge(self, df: pd.DataFrame) -> dict:
        return chern_simons_gauge(df)

    def ax_kochen_break(self, df: pd.DataFrame) -> dict:
        return ax_kochen_break(df)

    def kde_liquidity_nodes(self, df: pd.DataFrame) -> list:
        return kde_liquidity_nodes(df)

    def simons_hypersurface(self, df: pd.DataFrame) -> dict:
        return simons_hypersurface(df)

    def cheeger_simons_characters(self, df: pd.DataFrame) -> dict:
        return cheeger_simons_characters(df)

    def logistic_prob_bull(self, df: pd.DataFrame, regime: dict) -> float:
        return predict_prob_bull(df, regime)

    def logistic_score_details(self, df: pd.DataFrame, regime: dict) -> dict:
        return score_details(df, regime)

    def signed_volume_imbalance(self, df: pd.DataFrame, window: int = 20) -> dict:
        return signed_volume_imbalance(df, window)

    def bocpd_break(self, df: pd.DataFrame, hazard_rate: float = 1 / 100) -> dict:
        return bocpd_break(df, hazard_rate=hazard_rate)

    def kalman_fair_value(self, df: pd.DataFrame) -> dict:
        return kalman_fair_value(df)

    def cointegration_spread(self, df_a: pd.DataFrame, df_b: pd.DataFrame) -> dict:
        return engle_granger_spread(df_a, df_b)
