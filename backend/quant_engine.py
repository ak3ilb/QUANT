import pandas as pd

from algorithms.hmm_baum_welch import HMMBaumWelch
from algorithms.kelly_criterion import kelly_sizing
from algorithms.kernel_regression import kernel_regression
from algorithms.stochastic_diff_eq import ornstein_uhlenbeck_sde
from algorithms.markov_chains import markov_analysis
from algorithms.berlekamp_massey import berlekamp_massey
from algorithms.chern_simons import chern_simons_gauge
from algorithms.ax_kochen import ax_kochen_break
from algorithms.kde_liquidity import kde_liquidity_nodes
from algorithms.simons_equation import simons_hypersurface
from algorithms.cheeger_simons import cheeger_simons_characters

class QuantEngine:
    def __init__(self):
        self.hmm = HMMBaumWelch()
        
    def detect_regime(self, df: pd.DataFrame) -> dict:
        return self.hmm.detect_regime(df)
            
    def kelly_sizing(self, df: pd.DataFrame, strategy: str) -> dict:
        return kelly_sizing(df, strategy)
        
    def kernel_regression(self, df: pd.DataFrame) -> dict:
        return kernel_regression(df)

    def monte_carlo(self, df: pd.DataFrame, simulations: int = 1000, forecast_bars: int = 30) -> dict:
        return ornstein_uhlenbeck_sde(df, simulations, forecast_bars)

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
