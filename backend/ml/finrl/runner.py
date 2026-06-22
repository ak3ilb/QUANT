#!/usr/bin/env python3
"""CLI: python -m ml.finrl.runner train|test|trade|arrays"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ml.finrl import config
from ml.finrl.processor import QuantDataProcessor


def cmd_arrays(args):
    dp = QuantDataProcessor(use_vix=not args.no_vix, use_turbulence=args.turbulence)
    price, tech, turb, df = dp.build_arrays(
        args.symbol, args.interval, args.start, args.end, days_back=args.days_back
    )
    print(json.dumps({
        "symbol": args.symbol,
        "interval": args.interval,
        "bars": len(price),
        "n_assets": price.shape[1],
        "tech_dim": tech.shape[1],
        "rows_df": len(df),
    }, indent=2))
    if args.save:
        path = dp.save_dataset(df, f"{args.symbol}_{args.interval}")
        print(f"Saved dataset: {path}")


def cmd_train(args):
    from ml.finrl.status import auto_date_splits
    from ml.finrl.train import train

    start, end = args.start, args.end
    if args.auto_dates:
        splits = auto_date_splits(args.symbol, args.interval)
        if splits:
            start, end = splits["train_start"], splits["train_end"]
            print(f"Auto dates: {start} → {end} ({splits['bars']} bars)", flush=True)

    result = train(
        symbol=args.symbol,
        interval=args.interval,
        start_date=start,
        end_date=end,
        model_name=args.model,
        total_timesteps=args.timesteps,
        data_source=args.source,
        use_vix=not args.no_vix,
        use_turbulence=args.turbulence,
        cwd=args.cwd,
    )
    print(json.dumps(result, indent=2))


def cmd_test(args):
    from ml.finrl.test import test
    result = test(
        model_path=args.model_path,
        model_name=args.model,
        symbol=args.symbol,
        interval=args.interval,
        start_date=args.start,
        end_date=args.end,
        use_vix=not args.no_vix,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "assets"}, indent=2, default=str))
    if args.save:
        from ml.finrl.trade import save_results
        print(f"Saved: {save_results(result, 'test')}")


def cmd_trade(args):
    from ml.finrl.trade import backtest, paper_trade_signal, save_results
    if args.paper:
        result = paper_trade_signal(args.model_path, args.model, args.symbol, args.interval)
    else:
        result = backtest(
            args.model_path, args.model, args.symbol, args.interval, args.start, args.end
        )
    print(json.dumps({k: v for k, v in result.items() if k != "assets"}, indent=2, default=str))
    if args.save:
        print(f"Saved: {save_results(result, 'trade')}")


def main():
    parser = argparse.ArgumentParser(description="QUANT FinRL DRL runner")
    sub = parser.add_subparsers(dest="command", required=True)

    p_arr = sub.add_parser("arrays", help="Build FinRL arrays from vault (no SB3)")
    p_arr.add_argument("--symbol", default=config.DEFAULT_SYMBOL)
    p_arr.add_argument("--interval", default=config.DEFAULT_INTERVAL)
    p_arr.add_argument("--start", default=config.TRAIN_START_DATE)
    p_arr.add_argument("--end", default=config.TRAIN_END_DATE)
    p_arr.add_argument("--days-back", type=int, default=730)
    p_arr.add_argument("--no-vix", action="store_true")
    p_arr.add_argument("--turbulence", action="store_true")
    p_arr.add_argument("--save", action="store_true")
    p_arr.set_defaults(func=cmd_arrays)

    p_train = sub.add_parser("train", help="Train SB3 agent (requires requirements-rl.txt)")
    p_train.add_argument("--symbol", default=config.DEFAULT_SYMBOL)
    p_train.add_argument("--interval", default=config.DEFAULT_INTERVAL)
    p_train.add_argument("--auto-dates", action="store_true", help="Use vault-derived train window")
    p_train.add_argument("--start", default=config.TRAIN_START_DATE)
    p_train.add_argument("--end", default=config.TRAIN_END_DATE)
    p_train.add_argument("--model", default="ppo", choices=["ppo", "sac", "a2c", "ddpg", "td3"])
    p_train.add_argument("--timesteps", type=int, default=config.DEFAULT_TIMESTEPS)
    p_train.add_argument("--source", default="vault_then_fetch", choices=["vault", "fetch", "vault_then_fetch"])
    p_train.add_argument("--no-vix", action="store_true")
    p_train.add_argument("--turbulence", action="store_true")
    p_train.add_argument("--cwd", default=None)
    p_train.set_defaults(func=cmd_train)

    p_test = sub.add_parser("test", help="Evaluate trained model")
    p_test.add_argument("model_path")
    p_test.add_argument("--model", default="ppo")
    p_test.add_argument("--symbol", default=config.DEFAULT_SYMBOL)
    p_test.add_argument("--interval", default=config.DEFAULT_INTERVAL)
    p_test.add_argument("--start", default=config.TEST_START_DATE)
    p_test.add_argument("--end", default=config.TEST_END_DATE)
    p_test.add_argument("--save", action="store_true")
    p_test.add_argument("--no-vix", action="store_true")
    p_test.set_defaults(func=cmd_test)

    p_trade = sub.add_parser("trade", help="Backtest or paper signal")
    p_trade.add_argument("model_path")
    p_trade.add_argument("--model", default="ppo")
    p_trade.add_argument("--symbol", default=config.DEFAULT_SYMBOL)
    p_trade.add_argument("--interval", default=config.DEFAULT_INTERVAL)
    p_trade.add_argument("--start", default=config.TRADE_START_DATE)
    p_trade.add_argument("--end", default=config.TRADE_END_DATE)
    p_trade.add_argument("--paper", action="store_true", help="Latest action for paper trader")
    p_trade.add_argument("--save", action="store_true")
    p_trade.set_defaults(func=cmd_trade)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
