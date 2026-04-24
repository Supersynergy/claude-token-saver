"""Session cost ledger — records per-call usage so Layer 5 claims stay honest.

SQLite at ~/.cts/usage.db. Schema is deliberately tiny so dashboards can
materialize whatever they need via `duckdb ATTACH`.
"""

from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass

DEFAULT_DB = os.path.expanduser("~/.cts/usage.db")


@dataclass
class UsageRow:
    ts: int
    model: str
    reason: str
    input_tokens: int
    output_tokens: int
    cache_read: int
    cache_create: int


class UsageLogger:
    def __init__(self, db_path: str = DEFAULT_DB):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._db = sqlite3.connect(db_path)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                ts INTEGER NOT NULL,
                model TEXT NOT NULL,
                reason TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                cache_read INTEGER,
                cache_create INTEGER
            )
        """)
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_calls_ts ON calls(ts)")
        self._db.commit()

    def record(self, row: UsageRow) -> None:
        self._db.execute(
            "INSERT INTO calls VALUES (?, ?, ?, ?, ?, ?, ?)",
            (row.ts, row.model, row.reason, row.input_tokens,
             row.output_tokens, row.cache_read, row.cache_create),
        )
        self._db.commit()

    def summary(self, since_seconds: int = 86400) -> dict:
        cutoff = int(time.time()) - since_seconds
        rows = self._db.execute(
            """SELECT model, COUNT(*), SUM(input_tokens), SUM(output_tokens),
                      SUM(cache_read)
               FROM calls WHERE ts >= ? GROUP BY model""",
            (cutoff,),
        ).fetchall()
        return {
            m: {"calls": c, "input": i or 0, "output": o or 0, "cache_read": cr or 0}
            for m, c, i, o, cr in rows
        }

    def close(self) -> None:
        self._db.close()
