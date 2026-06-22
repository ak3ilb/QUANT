"""DuckDB persistence for intelligence layer tables."""
import json
import os
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc)

import duckdb
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "quant_vault.duckdb")


def get_connection(read_only: bool = False):
    return duckdb.connect(database=DB_PATH, read_only=read_only)


def init_intelligence_tables():
    con = get_connection(read_only=False)
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS price_quotes (
                symbol VARCHAR,
                source VARCHAR,
                mid DOUBLE,
                bid DOUBLE,
                ask DOUBLE,
                ts TIMESTAMP,
                PRIMARY KEY (symbol, source, ts)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS news_headlines (
                id VARCHAR PRIMARY KEY,
                published_at TIMESTAMP,
                source VARCHAR,
                headline VARCHAR,
                url VARCHAR,
                symbols VARCHAR
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS news_sentiment (
                headline_id VARCHAR PRIMARY KEY,
                finbert_score DOUBLE,
                vader_score DOUBLE,
                ensemble_score DOUBLE,
                label VARCHAR,
                scored_at TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS economic_events (
                event_id VARCHAR PRIMARY KEY,
                event_time TIMESTAMP,
                name VARCHAR,
                impact VARCHAR,
                symbols VARCHAR,
                forecast DOUBLE,
                actual DOUBLE,
                surprise DOUBLE,
                country VARCHAR,
                source VARCHAR
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS context_snapshots (
                symbol VARCHAR,
                ts TIMESTAMP,
                payload VARCHAR,
                PRIMARY KEY (symbol, ts)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS news_impact (
                headline_id VARCHAR PRIMARY KEY,
                impact_direction VARCHAR,
                prob_bull_delta DOUBLE,
                impact_strength VARCHAR,
                affected_symbols VARCHAR,
                session_modifier DOUBLE,
                trade_gate VARCHAR,
                ml_confidence DOUBLE,
                scored_at TIMESTAMP
            )
        """)
    finally:
        con.close()


def store_price_quote(symbol: str, source: str, mid: float, bid: float | None, ask: float | None, ts: datetime | None = None):
    ts = ts or _utcnow()
    con = get_connection(read_only=False)
    try:
        con.execute(
            """
            INSERT INTO price_quotes (symbol, source, mid, bid, ask, ts)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (symbol, source, ts) DO UPDATE SET
                mid = EXCLUDED.mid, bid = EXCLUDED.bid, ask = EXCLUDED.ask
            """,
            [symbol, source, mid, bid, ask, ts],
        )
    finally:
        con.close()


def get_latest_quotes(symbol: str) -> dict:
    con = get_connection(read_only=True)
    try:
        df = con.execute(
            """
            SELECT source, mid, bid, ask, ts
            FROM price_quotes
            WHERE symbol = ?
            ORDER BY ts DESC
            LIMIT 10
            """,
            [symbol],
        ).df()
    finally:
        con.close()
    if df.empty:
        return {}
    out = {}
    for source in df["source"].unique():
        row = df[df["source"] == source].iloc[0]
        out[source] = {
            "mid": float(row["mid"]),
            "bid": float(row["bid"]) if row["bid"] == row["bid"] else None,
            "ask": float(row["ask"]) if row["ask"] == row["ask"] else None,
            "ts": str(row["ts"]),
        }
    return out


def store_headline(headline_id: str, published_at, source: str, headline: str, url: str, symbols: list):
    con = get_connection(read_only=False)
    try:
        con.execute(
            """
            INSERT INTO news_headlines (id, published_at, source, headline, url, symbols)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO NOTHING
            """,
            [headline_id, published_at, source, headline, url, json.dumps(symbols)],
        )
    finally:
        con.close()


def store_sentiment(headline_id: str, finbert: float, vader: float, ensemble: float, label: str):
    con = get_connection(read_only=False)
    try:
        con.execute(
            """
            INSERT INTO news_sentiment (headline_id, finbert_score, vader_score, ensemble_score, label, scored_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (headline_id) DO UPDATE SET
                finbert_score = EXCLUDED.finbert_score,
                vader_score = EXCLUDED.vader_score,
                ensemble_score = EXCLUDED.ensemble_score,
                label = EXCLUDED.label,
                scored_at = EXCLUDED.scored_at
            """,
            [headline_id, finbert, vader, ensemble, label, _utcnow()],
        )
    finally:
        con.close()


def store_economic_event(event: dict):
    con = get_connection(read_only=False)
    try:
        con.execute(
            """
            INSERT INTO economic_events
            (event_id, event_time, name, impact, symbols, forecast, actual, surprise, country, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (event_id) DO UPDATE SET
                forecast = EXCLUDED.forecast,
                actual = EXCLUDED.actual,
                surprise = EXCLUDED.surprise,
                impact = EXCLUDED.impact
            """,
            [
                event["event_id"],
                event["event_time"],
                event["name"],
                event.get("impact", "medium"),
                json.dumps(event.get("symbols", [])),
                event.get("forecast"),
                event.get("actual"),
                event.get("surprise"),
                event.get("country", "US"),
                event.get("source", "fallback"),
            ],
        )
    finally:
        con.close()


def get_upcoming_events(hours: int = 48) -> list[dict]:
    con = get_connection(read_only=True)
    try:
        df = con.execute(
            """
            SELECT * FROM economic_events
            WHERE event_time >= now() - INTERVAL '1 hour'
              AND event_time <= now() + INTERVAL ? HOUR
            ORDER BY event_time ASC
            """,
            [hours],
        ).df()
    except Exception:
        df = con.execute(
            """
            SELECT * FROM economic_events
            WHERE event_time >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
            ORDER BY event_time ASC
            LIMIT 50
            """
        ).df()
    finally:
        con.close()
    if df.empty:
        return []
    events = []
    for _, row in df.iterrows():
        events.append({
            "event_id": row["event_id"],
            "event_time": str(row["event_time"]),
            "name": row["name"],
            "impact": row["impact"],
            "symbols": json.loads(row["symbols"]) if row["symbols"] else [],
            "forecast": row["forecast"],
            "actual": row["actual"],
            "surprise": row["surprise"],
            "country": row.get("country", "US"),
            "source": row.get("source", ""),
        })
    return events


def store_context_snapshot(symbol: str, payload: dict, ts: datetime | None = None):
    ts = ts or _utcnow()
    con = get_connection(read_only=False)
    try:
        con.execute(
            """
            INSERT INTO context_snapshots (symbol, ts, payload)
            VALUES (?, ?, ?)
            ON CONFLICT (symbol, ts) DO UPDATE SET payload = EXCLUDED.payload
            """,
            [symbol, ts, json.dumps(payload)],
        )
    finally:
        con.close()


def get_latest_context(symbol: str) -> dict | None:
    con = get_connection(read_only=True)
    try:
        row = con.execute(
            """
            SELECT payload FROM context_snapshots
            WHERE symbol = ?
            ORDER BY ts DESC LIMIT 1
            """,
            [symbol],
        ).fetchone()
    finally:
        con.close()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except json.JSONDecodeError:
        return None


def get_recent_sentiment(symbols: list[str], hours: int = 4) -> list[dict]:
    con = get_connection(read_only=True)
    try:
        df = con.execute(
            """
            SELECT h.id, h.published_at, h.source, h.headline, h.url, h.symbols,
                   s.ensemble_score, s.label
            FROM news_headlines h
            LEFT JOIN news_sentiment s ON h.id = s.headline_id
            WHERE h.published_at >= CURRENT_TIMESTAMP - INTERVAL ? HOUR
            ORDER BY h.published_at DESC
            LIMIT 100
            """,
            [hours],
        ).df()
    except Exception:
        return []
    finally:
        con.close()
    if df.empty:
        return []
    results = []
    for _, row in df.iterrows():
        try:
            syms = json.loads(row["symbols"]) if row["symbols"] else []
        except json.JSONDecodeError:
            syms = []
        if symbols and not any(s in syms for s in symbols):
            continue
        results.append({
            "id": row["id"],
            "published_at": str(row["published_at"]),
            "source": row["source"],
            "headline": row["headline"],
            "url": row["url"],
            "symbols": syms,
            "ensemble_score": float(row["ensemble_score"]) if row["ensemble_score"] == row["ensemble_score"] else None,
            "label": row["label"],
        })
    return results


def store_impact(headline_id: str, impact: dict):
    con = get_connection(read_only=False)
    try:
        con.execute(
            """
            INSERT INTO news_impact
            (headline_id, impact_direction, prob_bull_delta, impact_strength,
             affected_symbols, session_modifier, trade_gate, ml_confidence, scored_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (headline_id) DO UPDATE SET
                impact_direction = EXCLUDED.impact_direction,
                prob_bull_delta = EXCLUDED.prob_bull_delta,
                impact_strength = EXCLUDED.impact_strength,
                affected_symbols = EXCLUDED.affected_symbols,
                session_modifier = EXCLUDED.session_modifier,
                trade_gate = EXCLUDED.trade_gate,
                ml_confidence = EXCLUDED.ml_confidence,
                scored_at = EXCLUDED.scored_at
            """,
            [
                headline_id,
                impact.get("impact_direction"),
                impact.get("prob_bull_delta"),
                impact.get("impact_strength"),
                json.dumps(impact.get("affected_symbols", [])),
                impact.get("session_modifier"),
                impact.get("trade_gate"),
                impact.get("ml_confidence"),
                _utcnow(),
            ],
        )
    finally:
        con.close()


def get_impact(headline_id: str) -> dict | None:
    con = get_connection(read_only=True)
    try:
        row = con.execute(
            "SELECT * FROM news_impact WHERE headline_id = ?", [headline_id]
        ).fetchone()
    finally:
        con.close()
    if not row:
        return None
    cols = [
        "headline_id", "impact_direction", "prob_bull_delta", "impact_strength",
        "affected_symbols", "session_modifier", "trade_gate", "ml_confidence", "scored_at",
    ]
    d = dict(zip(cols, row))
    try:
        d["affected_symbols"] = json.loads(d["affected_symbols"] or "[]")
    except json.JSONDecodeError:
        d["affected_symbols"] = []
    return d


def get_headlines(symbol: str | None = None, hours: int = 24, limit: int = 50) -> list[dict]:
    con = get_connection(read_only=True)
    try:
        df = con.execute(
            """
            SELECT h.id, h.published_at, h.source, h.headline, h.url, h.symbols,
                   s.ensemble_score, s.label, s.vader_score, s.finbert_score,
                   i.impact_direction, i.prob_bull_delta, i.impact_strength,
                   i.trade_gate, i.affected_symbols
            FROM news_headlines h
            LEFT JOIN news_sentiment s ON h.id = s.headline_id
            LEFT JOIN news_impact i ON h.id = i.headline_id
            WHERE h.published_at >= CURRENT_TIMESTAMP - INTERVAL ? HOUR
            ORDER BY h.published_at DESC
            LIMIT ?
            """,
            [hours, limit],
        ).df()
    except Exception:
        return []
    finally:
        con.close()
    if df.empty:
        return []
    out = []
    for _, row in df.iterrows():
        try:
            syms = json.loads(row["symbols"]) if row["symbols"] else []
        except json.JSONDecodeError:
            syms = []
        if symbol:
            sym_upper = symbol.upper()
            if syms and sym_upper not in [str(s).upper() for s in syms]:
                continue
        impact = None
        if row.get("impact_direction") == row.get("impact_direction"):
            try:
                aff = json.loads(row["affected_symbols"]) if row["affected_symbols"] else syms
            except (json.JSONDecodeError, TypeError):
                aff = syms
            impact = {
                "impact_direction": row["impact_direction"],
                "prob_bull_delta": float(row["prob_bull_delta"]) if row["prob_bull_delta"] == row["prob_bull_delta"] else 0.0,
                "impact_strength": row["impact_strength"],
                "trade_gate": row["trade_gate"],
                "affected_symbols": aff,
            }
        out.append({
            "id": row["id"],
            "published_at": str(row["published_at"]),
            "source": row["source"],
            "headline": row["headline"],
            "url": row["url"],
            "symbols": syms,
            "ensemble_score": float(row["ensemble_score"]) if row["ensemble_score"] == row["ensemble_score"] else None,
            "label": row["label"],
            "vader_score": float(row["vader_score"]) if row["vader_score"] == row["vader_score"] else None,
            "finbert_score": float(row["finbert_score"]) if row["finbert_score"] == row["finbert_score"] else None,
            "impact": impact,
        })
    return out


init_intelligence_tables()
