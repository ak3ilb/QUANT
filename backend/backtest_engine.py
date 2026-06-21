import pandas as pd
from backtesting import Strategy, Backtest

class NovaStrategy(Strategy):
    """
    Nova: Momentum Breakout strategy based on EMA crossover and RSI
    """
    n1 = 9
    n2 = 21
    rsi_period = 14
    
    def init(self):
        # Already calculated by indicator_engine, just access them
        self.ema_fast = self.data.EMA_9
        self.ema_slow = self.data.EMA_21
        self.rsi = self.data.RSI_14
        
    def next(self):
        # Bullish cross and not overbought
        if self.ema_fast[-1] > self.ema_slow[-1] and self.ema_fast[-2] <= self.ema_slow[-2] and self.rsi[-1] < 70:
            if not self.position.is_long:
                self.buy()
                
        # Bearish cross or overbought
        elif self.ema_fast[-1] < self.ema_slow[-1] or self.rsi[-1] > 80:
            if self.position.is_long:
                self.position.close()

class PiggyBasketStrategy(Strategy):
    """
    Piggy Basket: Mean Reversion based on Bollinger Bands
    """
    def init(self):
        # We need the lower/upper bands from pandas_ta
        # Assuming BB_LOWER and BB_UPPER are available
        self.lower = self.data.BBL_20_2_0
        self.upper = self.data.BBU_20_2_0
        
    def next(self):
        # Buy when price crosses below lower band
        if self.data.Close[-1] < self.lower[-1] and self.data.Close[-2] >= self.lower[-2]:
            if not self.position.is_long:
                self.buy()
                
        # Sell when price crosses above upper band
        elif self.data.Close[-1] > self.upper[-1]:
            if self.position.is_long:
                self.position.close()

class BacktestEngine:
    def __init__(self):
        pass
        
    def run(self, df: pd.DataFrame, strategy_name: str, cash: float, commission: float, params: dict = None) -> dict:
        """
        Runs the backtest using Backtesting.py
        """
        # Rename columns for Backtesting.py
        bt_df = df.copy()
        bt_df = bt_df.rename(columns={
            "open": "Open", "high": "High", "low": "Low", 
            "close": "Close", "volume": "Volume"
        })
        
        # Map strategy string to class
        strategy_class = NovaStrategy
        if strategy_name == "piggy":
            strategy_class = PiggyBasketStrategy
            
        bt = Backtest(bt_df, strategy_class, cash=cash, commission=commission)
        stats = bt.run()
        
        # Extract trades
        trades = []
        if hasattr(stats, "_trades") and len(stats._trades) > 0:
            trades_df = stats._trades
            for _, row in trades_df.iterrows():
                trades.append({
                    "size": int(row["Size"]),
                    "entry_time": str(row["EntryTime"]),
                    "entry_price": float(row["EntryPrice"]),
                    "exit_time": str(row["ExitTime"]) if pd.notna(row["ExitTime"]) else None,
                    "exit_price": float(row["ExitPrice"]) if pd.notna(row["ExitPrice"]) else None,
                    "pnl": float(row["PnL"]) if pd.notna(row["PnL"]) else None,
                    "return_pct": float(row["ReturnPct"]) if pd.notna(row["ReturnPct"]) else None
                })
        
        # Extract equity curve
        equity_curve = []
        if hasattr(stats, "_equity_curve"):
            eq_df = stats._equity_curve
            for idx, row in eq_df.iterrows():
                equity_curve.append({
                    "time": str(idx),
                    "equity": float(row["Equity"])
                })
                
        # Clean stats for JSON serialization
        clean_stats = {}
        for k, v in stats.items():
            if k.startswith("_"): continue
            if pd.isna(v): clean_stats[k] = None
            elif isinstance(v, (int, float, str, bool)): clean_stats[k] = v
            else: clean_stats[k] = str(v)
            
        return {
            "metrics": clean_stats,
            "equity_curve": equity_curve,
            "trades": trades
        }

class StrategyRunner:
    def __init__(self):
        pass
