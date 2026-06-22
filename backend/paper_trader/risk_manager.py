from paper_trader.broker_config import (
    LOT_STEP,
    MIN_LOT,
    STANDARD_ACCOUNT,
    STOP_LOSS_MARGIN_PCT,
    lots_to_qty,
    spread_half,
)


class RiskManager:
    def __init__(self, kelly_fraction=0.5):
        self.kelly_fraction = kelly_fraction
        self.leverage = STANDARD_ACCOUNT["max_leverage"]

    def calculate_position_size(self, balance, raw_kelly_pct, symbol, price):
        """
        Standard account sizing: lots → margin = notional / max_leverage.
        Returns (margin_usd, notional_usd, qty, lots, fee_usd, leverage).
        fee_usd is always 0 — spread is embedded in execution prices only.
        """
        symbol = symbol.upper()
        min_lot = MIN_LOT.get(symbol, 0.01)
        step = LOT_STEP.get(symbol, 0.01)
        leverage = self.leverage

        kelly = max(0.0, min(1.0, raw_kelly_pct / 100.0))
        margin_budget = balance * max(kelly * self.kelly_fraction, 0.01)

        target_lots = (margin_budget * leverage) / price if price > 0 else 0.0
        lots = max(min_lot, round(target_lots / step) * step)
        lots = round(lots, 2)

        qty = lots_to_qty(symbol, lots)
        notional = qty * price
        margin = notional / leverage

        while margin > balance and lots > min_lot:
            lots = round(lots - step, 2)
            qty = lots_to_qty(symbol, lots)
            notional = qty * price
            margin = notional / leverage

        if margin > balance or lots < min_lot:
            return 0.0, 0.0, 0.0, 0.0, 0.0, leverage

        return margin, notional, qty, lots, 0.0, leverage

    def apply_spread(self, mid_price, direction, symbol):
        """BUY at ask (mid + half spread), SELL at bid (mid - half spread)."""
        half = spread_half(symbol)
        if direction == "BUY":
            return mid_price + half
        return mid_price - half

    def apply_slippage(self, price, direction, volatility_atr=None, symbol="BTCUSD"):
        return self.apply_spread(price, direction, symbol)

    def exit_price(self, mid_price, position_direction, symbol):
        """Price you'd get if closing now (opposite side of book)."""
        close_side = "SELL" if position_direction == "BUY" else "BUY"
        return self.apply_spread(mid_price, close_side, symbol)

    def compute_stop_price(self, entry_price, direction, lots, symbol, margin_usd):
        """
        Stop where loss equals STOP_LOSS_MARGIN_PCT of margin.
        Example: 0.01 lot BTC, margin ~$3.22, 20% risk → ~$0.64 max loss → ~$64 price move.
        """
        qty = lots_to_qty(symbol, lots)
        if qty <= 0 or margin_usd <= 0:
            return entry_price
        max_loss_usd = margin_usd * STOP_LOSS_MARGIN_PCT
        price_delta = max_loss_usd / qty
        if direction == "BUY":
            return round(entry_price - price_delta, 2)
        return round(entry_price + price_delta, 2)

    def unrealized_pnl(self, position, mid_price, symbol):
        exit_px = self.exit_price(mid_price, position["direction"], symbol)
        qty = position["qty"]
        entry = position["entry_price"]
        if position["direction"] == "BUY":
            return (exit_px - entry) * qty
        return (entry - exit_px) * qty

    def check_stop_loss(self, position, mid_price, current_confidence, symbol):
        if current_confidence < 0.50:
            return True, "Confidence Decay < 50%"

        exit_px = self.exit_price(mid_price, position["direction"], symbol)
        stop_price = position.get("stop_price")
        direction = position["direction"]

        if stop_price is not None:
            if direction == "BUY" and exit_px <= stop_price:
                return True, "Stop Loss Hit"
            if direction == "SELL" and exit_px >= stop_price:
                return True, "Stop Loss Hit"

        unrealized = self.unrealized_pnl(position, mid_price, symbol)
        max_loss = position["size_usd"] * STOP_LOSS_MARGIN_PCT
        if unrealized <= -max_loss:
            return True, f"Stop Loss Hit (-{int(STOP_LOSS_MARGIN_PCT * 100)}% margin)"

        return False, None

    def check_take_profit(self, position, mid_price, symbol):
        """TP at stored SDE target; must be in profit after spread on exit."""
        sde_target = position.get("sde_target")
        if sde_target is None:
            return False, None

        exit_px = self.exit_price(mid_price, position["direction"], symbol)
        unrealized = self.unrealized_pnl(position, mid_price, symbol)
        if unrealized <= 0:
            return False, None

        direction = position["direction"]
        if direction == "BUY" and exit_px >= float(sde_target):
            return True, "SDE Target Reached (In Profit)"
        if direction == "SELL" and exit_px <= float(sde_target):
            return True, "SDE Target Reached (In Profit)"
        return False, None
