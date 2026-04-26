"""Layer 6 — Cache-replay for prompts/tasks.

Python port of `~/.claude/bin/lib-router.sh`. Same SQLite schema, so bash and
Python tools share one cache directory per tool.

Verified speedups in production: 91× on usearch, 199× on yt-transcript-batch.

Usage:
    from cts.cache_replay import CacheReplay
    cr = CacheReplay(tool="my-agent", ttl=3600)
    hit = cr.check(query, mode="default")
    if hit is not None:
        return hit
    result = expensive_call()
    cr.write(query, result, mode="default")
    cr.log_perf(query, "default", exit_code=0, duration_ms=t, bytes=len(result))
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional


class CacheReplay:
    SCHEMA_PERF = (
        "CREATE TABLE IF NOT EXISTS perf("
        "ts INTEGER, query TEXT, mode TEXT, "
        "duration_ms INTEGER, exit_code INTEGER, result_bytes INTEGER);"
        "CREATE INDEX IF NOT EXISTS idx_perf_mode ON perf(mode, ts);"
    )
    SCHEMA_CACHE = (
        "CREATE TABLE IF NOT EXISTS cache("
        "qhash TEXT PRIMARY KEY, ts INTEGER, payload BLOB)"
    )

    def __init__(self, tool: str, ttl: int = 3600, root: Optional[Path] = None):
        self.tool = tool
        self.ttl = ttl
        root = root or Path.home() / ".claude" / "cache" / tool
        root.mkdir(parents=True, exist_ok=True)
        self.perf_db = root / "perf.db"
        self.cache_db = root / "cache.db"
        with sqlite3.connect(self.perf_db) as c:
            c.executescript(self.SCHEMA_PERF)
        with sqlite3.connect(self.cache_db) as c:
            c.executescript(self.SCHEMA_CACHE)

    def _qhash(self, query: str, mode: str) -> str:
        return hashlib.sha256(f"{mode}|{query}".encode()).hexdigest()[:16]

    def check(self, query: str, mode: str = "") -> Optional[bytes]:
        if os.environ.get("ROUTER_NOCACHE"):
            return None
        h = self._qhash(query, mode)
        cutoff = int(time.time()) - self.ttl
        with sqlite3.connect(self.cache_db) as c:
            row = c.execute(
                "SELECT payload FROM cache WHERE qhash=? AND ts > ?",
                (h, cutoff),
            ).fetchone()
        return row[0] if row else None

    def write(self, query: str, payload: bytes | str, mode: str = "") -> None:
        if os.environ.get("ROUTER_NOCACHE") or not payload:
            return
        if isinstance(payload, str):
            payload = payload.encode()
        h = self._qhash(query, mode)
        with sqlite3.connect(self.cache_db) as c:
            c.execute(
                "INSERT OR REPLACE INTO cache VALUES(?, ?, ?)",
                (h, int(time.time()), payload),
            )

    def log_perf(
        self,
        query: str,
        mode: str,
        exit_code: int,
        duration_ms: int,
        result_bytes: int,
    ) -> None:
        with sqlite3.connect(self.perf_db) as c:
            c.execute(
                "INSERT INTO perf VALUES(?,?,?,?,?,?)",
                (
                    int(time.time()),
                    query[:200],
                    mode,
                    duration_ms,
                    exit_code,
                    result_bytes,
                ),
            )

    def best_mode(self, default: str, lookback_days: int = 7, min_samples: int = 5) -> str:
        cutoff = int(time.time()) - lookback_days * 86400
        with sqlite3.connect(self.perf_db) as c:
            rows = c.execute(
                """
                SELECT mode,
                       (AVG(duration_ms) * COALESCE(AVG(NULLIF(result_bytes,0)), 1000))
                       / (AVG(CASE WHEN exit_code=0 THEN 1.0 ELSE 0.1 END) * COUNT(*)) AS cost
                FROM perf WHERE ts > ?
                GROUP BY mode HAVING COUNT(*) >= ?
                ORDER BY cost ASC LIMIT 2
                """,
                (cutoff, min_samples),
            ).fetchall()
        if not rows:
            return default
        if len(rows) == 1:
            return rows[0][0]
        # confidence-gated: require winner ≥1.5× cheaper than runner-up
        return rows[0][0] if rows[1][1] / rows[0][1] >= 1.5 else default
