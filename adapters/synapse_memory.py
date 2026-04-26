"""Synapse memory adapter — persistent cross-session memory layer for CTS.

Synapse v2.0 is the user's local memory engine (~/.synapse/brain.db, hybrid
FTS5 + vec0, ~8ms hybrid via Unix socket /tmp/synapse.sock). 147k docs at
deploy time. CTS now optionally backs its long-term context store with
Synapse rather than re-implementing memory.

Three operations:
  remember(text, title=, kind=)  — write a memory
  recall(query, k=8)             — hybrid FTS5 + vector retrieval
  forget(query)                  — delete matches (used cautiously)

Falls back to local SQLite (~/.claude/cache/cts-memory/store.db) if Synapse
socket is not running. Behaviour stays identical to caller.
"""

from __future__ import annotations

import os
import socket
import sqlite3
import time
from pathlib import Path
from typing import Iterable

SOCK = os.environ.get("SYNAPSE_SOCK", "/tmp/synapse.sock")
FALLBACK_DB = Path.home() / ".claude" / "cache" / "cts-memory" / "store.db"
FALLBACK_DB.parent.mkdir(parents=True, exist_ok=True)


def _synapse_alive() -> bool:
    if not Path(SOCK).exists():
        return False
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(SOCK)
        s.close()
        return True
    except OSError:
        return False


def _send(cmd: str, *fields: str) -> str:
    """Synapse socket protocol: tab-separated <cmd>\\t<f1>\\t<f2>\\n, response same."""
    payload = ("\t".join([cmd] + list(fields)) + "\n").encode()
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(2.0)
    s.connect(SOCK)
    s.sendall(payload)
    chunks: list[bytes] = []
    while True:
        b = s.recv(8192)
        if not b:
            break
        chunks.append(b)
    s.close()
    return b"".join(chunks).decode("utf-8", errors="replace")


def _fb_init() -> sqlite3.Connection:
    c = sqlite3.connect(FALLBACK_DB)
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS mem(id INTEGER PRIMARY KEY, ts INTEGER,
            kind TEXT, title TEXT, text TEXT);
        CREATE INDEX IF NOT EXISTS idx_mem_kind ON mem(kind, ts);
        CREATE VIRTUAL TABLE IF NOT EXISTS mem_fts USING fts5(title, text,
            content='mem', content_rowid='id');
        """
    )
    return c


def remember(text: str, title: str = "", kind: str = "cts-note") -> dict:
    if _synapse_alive():
        out = _send("put", title or text[:60], text)
        return {"backend": "synapse", "raw": out.strip()}
    c = _fb_init()
    c.execute(
        "INSERT INTO mem(ts,kind,title,text) VALUES(?,?,?,?)",
        (int(time.time()), kind, title, text),
    )
    rid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("INSERT INTO mem_fts(rowid,title,text) VALUES(?,?,?)", (rid, title, text))
    c.commit()
    return {"backend": "fallback-sqlite", "id": rid}


def recall(query: str, k: int = 8) -> list[dict]:
    if _synapse_alive():
        raw = _send("hybrid", query, str(k))
        results = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            results.append({"score": parts[0] if parts else "", "text": parts[-1]})
        return results
    c = _fb_init()
    rows = c.execute(
        """
        SELECT m.id, m.ts, m.kind, m.title, snippet(mem_fts, 1, '«', '»', '…', 12)
        FROM mem_fts JOIN mem m ON m.id = mem_fts.rowid
        WHERE mem_fts MATCH ? ORDER BY rank LIMIT ?
        """,
        (query, k),
    ).fetchall()
    return [
        {"id": r[0], "ts": r[1], "kind": r[2], "title": r[3], "snippet": r[4]}
        for r in rows
    ]


def forget(query: str) -> dict:
    """Delete matches. Synapse path is intentionally unsupported until a
    confirmed-delete tool exists upstream — refuse to silently drop memory."""
    if _synapse_alive():
        return {"backend": "synapse", "deleted": 0, "note": "use `syn rm` directly"}
    c = _fb_init()
    rows = c.execute(
        "SELECT rowid FROM mem_fts WHERE mem_fts MATCH ?", (query,)
    ).fetchall()
    ids = [r[0] for r in rows]
    if ids:
        qmarks = ",".join("?" * len(ids))
        c.execute(f"DELETE FROM mem WHERE id IN ({qmarks})", ids)
        c.execute(f"DELETE FROM mem_fts WHERE rowid IN ({qmarks})", ids)
        c.commit()
    return {"backend": "fallback-sqlite", "deleted": len(ids)}


__all__: Iterable[str] = ("remember", "recall", "forget")
