"""Background worker: polls feeds, builds context, updates matrix JSON."""
import asyncio
import json
import os
import time
from datetime import datetime

from intelligence.context_builder import build_context
from intelligence.ingestion.finnhub_client import refresh_calendar
from intelligence.ingestion.rss_ingestor import fetch_rss_headlines
from intelligence.nlp.sentiment_engine import score_headlines_batch
from intelligence.validation.price_validator import get_data_quality_summary

SYMBOLS = ["BTCUSD", "XAUUSD"]
MATRIX_DIR = "/tmp"


async def run_intelligence_worker():
    print("[INTELLIGENCE] Worker started", flush=True)
    loop = 0
    while True:
        try:
            loop += 1
            if loop == 1 or loop % 15 == 0:
                refresh_calendar()
            if loop == 1 or loop % 5 == 0:
                headlines = fetch_rss_headlines()
                if headlines:
                    try:
                        ctx = build_context("BTCUSD")
                    except Exception:
                        ctx = {}
                    score_headlines_batch(headlines, context=ctx)

            for symbol in SYMBOLS:
                json_path = f"{MATRIX_DIR}/latest_matrix_{symbol}.json"
                primary_price = None
                if os.path.exists(json_path):
                    try:
                        with open(json_path) as f:
                            data = json.load(f)
                        primary_price = (
                            data.get("matrix", {}).get("1h", {}).get("current_price")
                            or data.get("matrix", {}).get("5m", {}).get("current_price")
                        )
                    except Exception:
                        pass

                ctx = build_context(symbol, primary_price)

                if os.path.exists(json_path):
                    try:
                        with open(json_path) as f:
                            data = json.load(f)
                        data["context"] = ctx
                        data["intelligence_updated"] = datetime.now().isoformat()
                        tmp = f"{json_path}.intel.tmp"
                        with open(tmp, "w") as f:
                            json.dump(data, f)
                        os.replace(tmp, json_path)
                    except Exception as e:
                        print(f"[INTELLIGENCE] Matrix patch failed {symbol}: {e}", flush=True)

            if loop % 10 == 0:
                dq = get_data_quality_summary()
                print(f"[INTELLIGENCE] data_quality={dq}", flush=True)

            await asyncio.sleep(60)

        except Exception as e:
            print(f"[INTELLIGENCE] Error: {e}", flush=True)
            await asyncio.sleep(5)


def main():
    asyncio.run(run_intelligence_worker())


if __name__ == "__main__":
    main()
