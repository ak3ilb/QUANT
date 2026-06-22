"""AI Study Engine — live trade learning + historical algorithm evaluation."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from ai.study.historical_eval import evaluate_algorithms
from ai.study.layers import LAYER_META, LAYER_ORDER, STRATEGY_LAYER
from ai.study.store import append_event, load_cache, recent_events, save_cache
from algorithm_registry import get_algorithm_registry


_CACHE_TTL_S = 900  # 15 min historical re-eval


class StudyEngine:
    def record_trade_closed(self, trade: dict):
        symbol = str(trade.get("symbol", "BTCUSD")).upper()
        ctx = trade.get("context_snapshot") or {}
        if isinstance(ctx, str):
            import json
            try:
                ctx = json.loads(ctx)
            except json.JSONDecodeError:
                ctx = {}
        append_event("trade_closed", symbol, {
            "strategy": trade.get("strategy"),
            "won": trade.get("won"),
            "pnl_pct": trade.get("pnl_pct"),
            "pnl_usd": trade.get("pnl_usd"),
            "direction": trade.get("direction"),
            "trade_id": trade.get("trade_id"),
            "lots": trade.get("lots"),
            "leverage": trade.get("leverage"),
            "session": (ctx.get("timeline") or {}).get("active_session"),
            "news_count": (ctx.get("news") or {}).get("count"),
            "finrl_action": (ctx.get("finrl") or {}).get("action"),
            "sde_divergence_pct": (ctx.get("matrix") or {}).get("sde_divergence_pct"),
        })

    def run_historical_study(self, symbol: str = "BTCUSD", interval: str = "1h", force: bool = False) -> dict:
        key = f"hist_{symbol.upper()}_{interval}"
        cached = load_cache(key)
        if cached and not force:
            age = time.time() - cached.get("evaluated_at", 0)
            if age < _CACHE_TTL_S:
                return cached
        result = evaluate_algorithms(symbol, interval)
        save_cache(key, result)
        append_event("historical_eval", symbol.upper(), {"interval": interval, "bars": result.get("bars", 0)})
        return result

    def get_live_strategy_stats(self) -> dict:
        from learning_engine import get_learning_engine

        engine = get_learning_engine()
        engine._load_state()
        stats = engine.get_stats()
        bandit = stats.get("bandit", {})
        trades = engine.trade_history

        per_strategy: dict[str, dict] = {}
        for t in trades:
            s = t.get("strategy", "medallion")
            bucket = per_strategy.setdefault(s, {"wins": 0, "losses": 0, "pnl_sum": 0.0, "trades": 0})
            bucket["trades"] += 1
            if t.get("won"):
                bucket["wins"] += 1
            else:
                bucket["losses"] += 1
            bucket["pnl_sum"] += float(t.get("pnl_pct", 0.0))

        strategies = []
        for name, b in bandit.items():
            live = per_strategy.get(name, {"wins": 0, "losses": 0, "pnl_sum": 0.0, "trades": 0})
            strategies.append({
                "strategy": name,
                "layer": STRATEGY_LAYER,
                "bandit_alpha": b.get("alpha"),
                "bandit_beta": b.get("beta"),
                "expected_win_rate": round(b.get("expected_win_rate", 0.5), 4),
                "live_trades": live["trades"],
                "live_wins": live["wins"],
                "live_losses": live["losses"],
                "live_pnl_pct_sum": round(live["pnl_sum"], 4),
                "working": b.get("expected_win_rate", 0.5) >= 0.5 or live["trades"] < 3,
            })

        return {
            "strategies": sorted(strategies, key=lambda x: x["expected_win_rate"], reverse=True),
            "online_model": stats.get("online_model"),
            "walk_forward": stats.get("walk_forward"),
            "drift": stats.get("drift"),
            "entry_blocked": stats.get("entry_blocked"),
            "size_multiplier": stats.get("size_multiplier"),
        }

    def get_dashboard(self, symbol: str = "BTCUSD", interval: str = "1h") -> dict:
        historical = self.run_historical_study(symbol, interval)
        live = self.get_live_strategy_stats()
        events = recent_events(limit=30, symbol=symbol)
        registry = get_algorithm_registry()

        # Decode registry into layers
        registry_by_layer: dict[str, list] = {lid: [] for lid in LAYER_ORDER}
        for entry in registry:
            aid = entry["id"]
            from ai.study.layers import ALGORITHM_LAYERS
            layer = ALGORITHM_LAYERS.get(aid, "L5_geometry")
            hist = next((a for a in historical.get("algorithms", []) if a["algorithm_id"] == aid), None)
            registry_by_layer.setdefault(layer, []).append({
                "id": aid,
                "name": entry["name"],
                "category": entry["category"],
                "implementation_status": entry["implementation_status"],
                "historical_score": hist["historical_score"] if hist else None,
                "score_kind": hist.get("score_kind") if hist else None,
                "status": hist["status"] if hist else "not_evaluated",
            })

        layers = []
        for lid in LAYER_ORDER:
            hist_layer = next((l for l in historical.get("layer_summary", []) if l["layer_id"] == lid), None)
            layers.append({
                "layer_id": lid,
                **LAYER_META.get(lid, {}),
                "avg_historical_score": hist_layer["avg_score"] if hist_layer else None,
                "avg_accuracy_score": hist_layer.get("avg_accuracy_score") if hist_layer else None,
                "avg_readiness_score": hist_layer.get("avg_readiness_score") if hist_layer else None,
                "best_algorithm": hist_layer["best_algorithm"] if hist_layer else None,
                "best_accuracy_algorithm": hist_layer.get("best_accuracy_algorithm") if hist_layer else None,
                "registry_algorithms": registry_by_layer.get(lid, []),
                "evaluated_algorithms": hist_layer["algorithms"] if hist_layer else [],
            })

        recommendations = []
        for algo in historical.get("algorithms", []):
            if algo.get("score_kind") == "accuracy" and algo["status"] == "poor":
                recommendations.append(f"Consider tuning or disabling `{algo['algorithm_id']}` (accuracy {algo['historical_score']:.2f})")
        for s in live.get("strategies", []):
            if s["live_trades"] >= 5 and not s["working"]:
                recommendations.append(f"Strategy `{s['strategy']}` underperforming in live paper trades")

        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "interval": interval,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "layers": layers,
            "live_learning": live,
            "historical": {
                "bars": historical.get("bars"),
                "evaluated_at": historical.get("evaluated_at"),
                "cached_at": historical.get("_cached_at"),
                "status": historical.get("status", "ok"),
                "min_recommended_bars": 400,
                "low_data": int(historical.get("bars") or 0) < 400,
            },
            "recent_events": events,
            "recommendations": recommendations[:8],
            "study_active": True,
        }


_engine: StudyEngine | None = None


def get_study_engine() -> StudyEngine:
    global _engine
    if _engine is None:
        _engine = StudyEngine()
    return _engine
