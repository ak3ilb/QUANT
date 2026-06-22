"""Persist study events and cached historical evaluations."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

import duckdb

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "quant_vault.duckdb")


def _connect(read_only: bool = False):
    return duckdb.connect(database=DB_PATH, read_only=read_only)


def init_study_tables():
    con = _connect(read_only=False)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS study_events (
                id VARCHAR PRIMARY KEY,
                event_type VARCHAR,
                symbol VARCHAR,
                payload VARCHAR,
                created_at TIMESTAMP
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS study_cache (
                cache_key VARCHAR PRIMARY KEY,
                payload VARCHAR,
                updated_at TIMESTAMP
            )
            """
        )
    finally:
        con.close()


def append_event(event_type: str, symbol: str, payload: dict) -> str:
    init_study_tables()
    eid = f"evt_{uuid.uuid4().hex[:12]}"
    con = _connect(read_only=False)
    try:
        con.execute(
            "INSERT INTO study_events (id, event_type, symbol, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            [eid, event_type, symbol.upper(), json.dumps(payload), datetime.now()],
        )
    finally:
        con.close()
    return eid


def recent_events(limit: int = 50, symbol: str | None = None) -> list[dict]:
    init_study_tables()
    con = _connect(read_only=True)
    try:
        if symbol:
            rows = con.execute(
                """
                SELECT id, event_type, symbol, payload, created_at
                FROM study_events WHERE symbol = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                [symbol.upper(), limit],
            ).fetchall()
        else:
            rows = con.execute(
                """
                SELECT id, event_type, symbol, payload, created_at
                FROM study_events
                ORDER BY created_at DESC LIMIT ?
                """,
                [limit],
            ).fetchall()
        out = []
        for rid, etype, sym, payload, created_at in rows:
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                data = {}
            out.append({
                "id": rid,
                "event_type": etype,
                "symbol": sym,
                "payload": data,
                "created_at": str(created_at),
            })
        return out
    finally:
        con.close()


def save_cache(key: str, payload: dict):
    init_study_tables()
    con = _connect(read_only=False)
    try:
        con.execute(
            """
            INSERT INTO study_cache (cache_key, payload, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT (cache_key) DO UPDATE SET
              payload = excluded.payload,
              updated_at = excluded.updated_at
            """,
            [key, json.dumps(payload), datetime.now()],
        )
    finally:
        con.close()


def load_cache(key: str) -> dict | None:
    init_study_tables()
    con = _connect(read_only=True)
    try:
        row = con.execute("SELECT payload, updated_at FROM study_cache WHERE cache_key = ?", [key]).fetchone()
        if not row:
            return None
        data = json.loads(row[0])
        data["_cached_at"] = str(row[1])
        return data
    finally:
        con.close()
