"""Runtime AI verification CLI — checks learning loop, context fusion, news."""
from __future__ import annotations

import json
import sys


def main() -> int:
    errors: list[str] = []
    checks: list[str] = []

    # 1. Learning engine singleton
    try:
        from learning_engine import get_learning_engine
        e1 = get_learning_engine()
        e2 = get_learning_engine()
        if e1 is not e2:
            errors.append("get_learning_engine() is not a singleton")
        else:
            checks.append("learning_singleton: ok")
        e1.reload_if_stale()
        stats = e1.get_stats()
        checks.append(f"learning_stats: trades={stats['walk_forward']['trade_count']}")
    except Exception as exc:
        errors.append(f"learning_engine: {exc}")

    # 2. Context fusion
    try:
        from ai.context_fusion import fuse_context
        bundle = fuse_context("BTCUSD", {"current_price": 100000, "sde_forecast": 100500})
        required = ("intelligence", "timeline", "news", "finrl", "matrix", "broker", "regime_features")
        missing = [k for k in required if k not in bundle]
        if missing:
            errors.append(f"context_fusion missing keys: {missing}")
        else:
            checks.append(f"context_fusion: ok (news_count={bundle['news'].get('count', 0)})")
    except Exception as exc:
        errors.append(f"context_fusion: {exc}")

    # 3. Timeline
    try:
        from intelligence.context.timeline import get_timeline_context
        tl = get_timeline_context("BTCUSD")
        if "active_session" not in tl:
            errors.append("timeline missing active_session")
        else:
            checks.append(f"timeline: session={tl['active_session']}")
    except Exception as exc:
        errors.append(f"timeline: {exc}")

    # 4. RSS ingest (non-fatal if network blocked)
    try:
        from intelligence.ingestion.rss_ingestor import RSS_FEEDS
        if "kitco" not in RSS_FEEDS:
            errors.append("kitco feed missing from RSS_FEEDS")
        else:
            url = RSS_FEEDS["kitco"][0]
            if "kitco-news.xml" in url:
                errors.append(f"kitco still uses stale URL: {url}")
            else:
                checks.append(f"kitco_rss_url: {url}")
    except Exception as exc:
        errors.append(f"rss_config: {exc}")

    # 5. FinRL gating
    try:
        from ml.finrl.status import get_paper_signal
        sig = get_paper_signal("BTCUSD", "1h")
        checks.append(
            f"finrl_signal: action={sig.get('action')} reliable={sig.get('model_reliable')} "
            f"status={sig.get('status')}"
        )
    except Exception as exc:
        errors.append(f"finrl_signal: {exc}")

    # 6. Overlay merge
    try:
        from learning_engine import LearningEngine
        eng = LearningEngine()
        entry = {"session_quality": 0.5, "sentiment_1h_norm": 0.0}
        ctx = {
            "symbol": "BTCUSD",
            "timeline": {"session_quality": 0.9},
            "news": {"avg_sentiment": 0.3},
            "regime_features": {"session_quality": 0.9, "btc_sentiment_1h": 0.3},
        }
        merged = eng._overlay_context_features(entry, ctx)
        if merged.get("session_quality", 0) < 0.8:
            errors.append("context overlay did not update session_quality")
        else:
            checks.append("context_overlay: ok")
    except Exception as exc:
        errors.append(f"context_overlay: {exc}")

    print("=== Runtime AI Verification ===")
    for c in checks:
        print(f"  PASS  {c}")
    for e in errors:
        print(f"  FAIL  {e}")

    if errors:
        print(json.dumps({"status": "fail", "errors": errors, "checks": checks}, indent=2))
        return 1
    print(json.dumps({"status": "ok", "checks": checks}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
