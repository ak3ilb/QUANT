#!/usr/bin/env python3
"""Train ML models on all currently-ready symbol/interval pairs."""
import argparse
import sys
import uuid

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__file__)))

from ml.data.readiness import get_trainable_pairs, readiness_summary
from ml.train.deep_trainer import run_training_pipeline


def main():
    parser = argparse.ArgumentParser(description="QUANT ML train runner")
    parser.add_argument("--now", action="store_true", help="Train all trainable pairs")
    parser.add_argument("--symbol", type=str, default=None)
    parser.add_argument("--interval", type=str, default=None)
    args = parser.parse_args()

    if args.symbol and args.interval:
        pairs = [(args.symbol.upper(), args.interval)]
    elif args.now:
        pairs = get_trainable_pairs()
        if not pairs:
            print("No trainable pairs. Check: python -m ml.data.readiness")
            sys.exit(1)
    else:
        print(readiness_summary())
        parser.print_help()
        sys.exit(0)

    result = run_training_pipeline(run_id=f"run_{uuid.uuid4().hex[:8]}", pairs=pairs)
    print(f"Done: status={result['status']} trained={len([k for k in result['metrics'] if k.endswith('_mlp')])}")
    sys.exit(0 if result["status"] == "complete" else 1)


if __name__ == "__main__":
    main()
