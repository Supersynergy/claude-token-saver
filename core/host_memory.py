"""Host escalation learner — SQLite-backed per-host fetch-stage memory.

Tracks success/failure per (host, stage). Picks cheapest stage likely to succeed.
Decays stale entries so one-off outages don't pin a host to expensive stages.

Generic and portable: no personal data, no external deps. Stage names are arbitrary
strings — callers provide their own hierarchy (e.g. curl → curl_cffi → browser).
"""

from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass
from urllib.parse import urlparse

DEFAULT_DB = os.path.expanduser("~/.cts/host_memory.db")
DECAY_SECONDS = 7 * 24 * 3600  # 7d — stale entries reset
PROMOTE_AFTER_FAILS = 3         # 3 fails → escalate
DEMOTE_AFTER_WINS = 10          # 10 cheap wins in a row → try cheaper next


@dataclass
class StageAdvice:
    stage: str
    confidence: float
    reason: str


class HostMemory:
    def __init__(self, db_path: str = DEFAULT_DB):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._db = sqlite3.connect(db_path)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS host_stats (
                host TEXT NOT NULL,
                stage TEXT NOT NULL,
                wins INTEGER DEFAULT 0,
                fails INTEGER DEFAULT 0,
                last_seen INTEGER DEFAULT 0,
                PRIMARY KEY (host, stage)
            )
        """)
        self._db.commit()

    @staticmethod
    def _host(url: str) -> str:
        p = urlparse(url if "://" in url else f"//{url}")
        return (p.hostname or url).lower()

    def record(self, url: str, stage: str, success: bool) -> None:
        host = self._host(url)
        now = int(time.time())
        col = "wins" if success else "fails"
        self._db.execute(
            f"""INSERT INTO host_stats (host, stage, {col}, last_seen)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(host, stage) DO UPDATE SET
                    {col} = {col} + 1,
                    last_seen = excluded.last_seen""",
            (host, stage, now),
        )
        self._db.commit()

    def advise(self, url: str, stages: list[str]) -> StageAdvice:
        """Pick cheapest stage (earliest in list) with no recent failure streak.

        stages is ordered cheapest → most expensive. Returns first viable stage.
        """
        host = self._host(url)
        now = int(time.time())
        rows = self._db.execute(
            "SELECT stage, wins, fails, last_seen FROM host_stats WHERE host = ?",
            (host,),
        ).fetchall()
        stats = {
            s: (w, f) for s, w, f, seen in rows if (now - seen) < DECAY_SECONDS
        }
        if not stats:
            return StageAdvice(stages[0], 0.5, "no-history")

        for stage in stages:
            wins, fails = stats.get(stage, (0, 0))
            if fails >= PROMOTE_AFTER_FAILS and wins == 0:
                continue  # burnt — escalate
            score = (wins + 1) / (wins + fails + 2)
            return StageAdvice(stage, score, f"{wins}w/{fails}f")
        return StageAdvice(stages[-1], 0.3, "all-escalated")

    def close(self) -> None:
        self._db.close()
