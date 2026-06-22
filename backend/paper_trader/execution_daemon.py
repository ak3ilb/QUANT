import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from portfolio import Portfolio
from risk_manager import RiskManager
from learning_engine import get_learning_engine
from price_resolver import resolve_mark_price

SYMBOLS = ["BTCUSD", "XAUUSD"]
TIMEFRAME = "1h"
ENTRY_CONFIDENCE = 0.65  # aligned with signal_engine action threshold


def run_execution_engine():
    print("Initializing Medallion Paper Trading Execution Daemon...")
    portfolio = Portfolio(initial_balance=100.0)
    risk_manager = RiskManager(kelly_fraction=0.5)
    learner = get_learning_engine()

    print(f"Starting Balance: ${portfolio.get_balance():.2f}")
    print(f"Learning engine: online_active={learner.online_active} drift={learner.drift.severity()}")

    study_tick = 0
    while True:
        try:
            for symbol in SYMBOLS:
                json_path = f"/tmp/latest_matrix_{symbol}.json"
                if not os.path.exists(json_path):
                    continue

                with open(json_path, "r") as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        continue

                matrix = data.get("matrix", {})
                tf_data = matrix.get(TIMEFRAME, {})
                if not tf_data:
                    continue

                current_price = tf_data.get("current_price")
                sde_forecast = tf_data.get("sde_forecast")
                if current_price is None:
                    continue

                current_price = resolve_mark_price(symbol, current_price, TIMEFRAME)
                tf_data = {**tf_data, "current_price": current_price}

                portfolio.update_mark_price(symbol, current_price)

                signals = tf_data.get("signals", {})
                # FinRL PPO policy signal (optional overlay)
                try:
                    from ml.finrl.status import get_paper_signal
                    finrl_sig = get_paper_signal(symbol, TIMEFRAME)
                    if (
                        finrl_sig.get("status") == "ok"
                        and finrl_sig.get("model_reliable")
                        and finrl_sig.get("action") in ("BUY", "SELL")
                    ):
                        signals["finrl_ppo"] = {
                            "action": finrl_sig["action"],
                            "confidence": finrl_sig["confidence"],
                            "strength": finrl_sig.get("strength", 0.0),
                            "model_path": finrl_sig.get("model_path"),
                        }
                except Exception:
                    pass

                fused = None
                try:
                    from ai.context_fusion import fuse_context
                    fused = fuse_context(symbol, tf_data, TIMEFRAME)
                    tf_data = {**tf_data, "context": fused.get("intelligence") or tf_data.get("context")}
                except Exception:
                    pass

                strategy_name, signal, bandit_samples = learner.select_strategy(signals)

                action = signal.get("action", "HOLD")
                confidence = signal.get("confidence", 0.5)
                raw_kelly = tf_data.get("kelly_recommended_pct", 0.0) * learner.size_multiplier()

                position = portfolio.get_position(symbol)

                if position:
                    should_close, reason = risk_manager.check_stop_loss(
                        position, current_price, confidence, symbol
                    )

                    if not should_close:
                        should_close, reason = risk_manager.check_take_profit(
                            position, current_price, symbol
                        )

                    if not should_close:
                        if position['direction'] == "BUY" and action == "SELL" and confidence > 0.6:
                            should_close = True
                            reason = "Signal Flipped to SELL"
                        elif position['direction'] == "SELL" and action == "BUY" and confidence > 0.6:
                            should_close = True
                            reason = "Signal Flipped to BUY"

                    if should_close:
                        executed_price = risk_manager.apply_spread(
                            current_price,
                            "SELL" if position['direction'] == "BUY" else "BUY",
                            symbol,
                        )
                        outcome = portfolio.close_position(symbol, executed_price, reason)
                        if outcome:
                            learner.on_trade_closed(outcome)
                            print(
                                f"[TRADE CLOSE] {symbol} {position['direction']} | "
                                f"exit={executed_price:.2f} | pnl=${outcome['pnl_usd']:.2f} | "
                                f"strategy={outcome.get('strategy')} | reason={reason} | "
                                f"{datetime.now().isoformat()}"
                            )

                else:
                    ctx = tf_data.get("context") or {}
                    if ctx.get("data_quality") == "fail" or ctx.get("trade_allowed") is False:
                        continue
                    if learner.should_block_entry():
                        continue

                    if action in ["BUY", "SELL"] and confidence >= ENTRY_CONFIDENCE:
                        expected_move_pct = abs(sde_forecast - current_price) / current_price

                        if expected_move_pct > 0.003:
                            valid_entry = (
                                (action == "BUY" and sde_forecast > current_price)
                                or (action == "SELL" and sde_forecast < current_price)
                            )
                            if valid_entry:
                                margin_usd, leveraged_size_usd, qty, lots, fee_usd, leverage = risk_manager.calculate_position_size(
                                    portfolio.get_balance(), raw_kelly, symbol, current_price
                                )
                                if margin_usd > 0:
                                    executed_price = risk_manager.apply_spread(current_price, action, symbol)
                                    stop_price = risk_manager.compute_stop_price(
                                        executed_price, action, lots, symbol, margin_usd
                                    )
                                    entry_features = learner.build_entry_features(tf_data, fused=fused)
                                    context_snapshot = fused or (tf_data.get("context") or {})
                                    trade_id = portfolio.open_position(
                                        symbol, action, executed_price, margin_usd, leveraged_size_usd,
                                        qty, raw_kelly, confidence, fee_usd,
                                        stop_price=stop_price, sde_target=sde_forecast,
                                        strategy=strategy_name, entry_features=entry_features,
                                        context_snapshot=context_snapshot,
                                        lots=lots, leverage=leverage,
                                    )
                                    if trade_id:
                                        print(
                                            f"[TRADE OPEN] {symbol} {action} @ {executed_price:.2f} | "
                                            f"lots={lots:.2f} lev=1:{leverage:.0f} | "
                                            f"strategy={strategy_name} | sample={bandit_samples.get(strategy_name, 0):.3f} | "
                                            f"stop={stop_price:.2f} | sde={sde_forecast:.2f} | "
                                            f"conf={confidence * 100:.0f}% | margin=${margin_usd:.2f} | "
                                            f"{datetime.now().isoformat()}"
                                        )

            time.sleep(1)
            study_tick += 1
            if study_tick % 900 == 0:
                try:
                    from ai.study.engine import get_study_engine
                    for sym in SYMBOLS:
                        get_study_engine().run_historical_study(sym, TIMEFRAME, force=True)
                except Exception:
                    pass

        except Exception as e:
            print(f"[ERROR] Execution Engine Error: {e}")
            time.sleep(1)


if __name__ == "__main__":
    run_execution_engine()
