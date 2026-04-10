#!/usr/bin/env bash
# team-sandbox: shared hyperstack cache backed by SQLite + FTS5.
# Zero-setup (built-in macOS sqlite3), no port conflicts, no auth.
# Enables multi-dev Claude teams to dedupe scraped output.

set -euo pipefail

DB="${CTS_TEAM_DB_PATH:-${HOME}/.cts/hyperstack.db}"
NS="${CTS_TEAM_NS:-default}"

mkdir -p "$(dirname "$DB")"

sqlite_init() {
  sqlite3 "$DB" <<'SQL'
CREATE TABLE IF NOT EXISTS fetch (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  team_ns TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  stage TEXT NOT NULL,
  bytes INTEGER NOT NULL DEFAULT 0,
  token_estimate INTEGER NOT NULL DEFAULT 0,
  summary TEXT,
  fetched_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
  fetched_by TEXT NOT NULL DEFAULT 'unknown',
  UNIQUE(url, team_ns)
);
CREATE INDEX IF NOT EXISTS idx_fetch_ns ON fetch(team_ns, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_fetch_hash ON fetch(content_hash);

CREATE TABLE IF NOT EXISTS agent_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload TEXT,
  team_ns TEXT NOT NULL,
  ts INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE INDEX IF NOT EXISTS idx_event_ns_ts ON agent_event(team_ns, ts DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS fetch_fts USING fts5(url, summary);
SQL
  echo "[team-sandbox] initialized: $DB"
}

sq_esc() { printf "%s" "$1" | sed "s/'/''/g"; }

lookup() {
  local url; url=$(sq_esc "$1")
  local max_age="${2:-3600}"
  sqlite3 -json "$DB" "SELECT url, stage, bytes, token_estimate, summary, fetched_at, fetched_by
    FROM fetch WHERE url='$url' AND team_ns='$(sq_esc "$NS")'
    AND fetched_at > strftime('%s','now') - $max_age LIMIT 1;"
}

record() {
  local url; url=$(sq_esc "$1")
  local stage; stage=$(sq_esc "$2")
  local bytes="$3" hash; hash=$(sq_esc "$4")
  local tokens="$5"
  local summary="${6:-}"
  summary=$(sq_esc "$summary")
  local who; who=$(sq_esc "${USER:-unknown}")
  sqlite3 "$DB" "INSERT INTO fetch(url, team_ns, content_hash, stage, bytes, token_estimate, summary, fetched_by)
    VALUES('$url','$(sq_esc "$NS")','$hash','$stage',$bytes,$tokens,'$summary','$who')
    ON CONFLICT(url, team_ns) DO UPDATE SET
      content_hash=excluded.content_hash,
      stage=excluded.stage,
      bytes=excluded.bytes,
      token_estimate=excluded.token_estimate,
      summary=excluded.summary,
      fetched_at=strftime('%s','now'),
      fetched_by=excluded.fetched_by;
    DELETE FROM fetch_fts WHERE url='$url';
    INSERT INTO fetch_fts(url, summary) VALUES('$url','$summary');"
}

stats() {
  sqlite3 -column -header "$DB" "
    SELECT
      COUNT(*) AS total_fetches,
      COALESCE(SUM(token_estimate),0) AS total_tokens_cached,
      COALESCE(SUM(bytes),0) AS total_bytes_cached,
      COUNT(DISTINCT fetched_by) AS unique_devs,
      COUNT(DISTINCT content_hash) AS unique_content,
      (SELECT COUNT(*) FROM fetch WHERE team_ns='$(sq_esc "$NS")') AS this_ns
    FROM fetch;"
  echo ""
  echo "-- per namespace --"
  sqlite3 -column -header "$DB" "
    SELECT team_ns, COUNT(*) AS fetches, SUM(token_estimate) AS tokens_cached
    FROM fetch GROUP BY team_ns ORDER BY fetches DESC LIMIT 10;"
}

broadcast() {
  local agent; agent=$(sq_esc "$1")
  local event; event=$(sq_esc "$2")
  local payload; payload=$(sq_esc "${3:-{\}}")
  sqlite3 "$DB" "INSERT INTO agent_event(agent_id, event_type, payload, team_ns)
    VALUES('$agent','$event','$payload','$(sq_esc "$NS")');"
}

tail_events() {
  local since="${1:-3600}"
  sqlite3 -column -header "$DB" "
    SELECT agent_id, event_type, payload, datetime(ts,'unixepoch','localtime') AS at
    FROM agent_event
    WHERE team_ns='$(sq_esc "$NS")' AND ts > strftime('%s','now') - $since
    ORDER BY ts DESC LIMIT 50;"
}

search() {
  local query; query=$(sq_esc "$1")
  sqlite3 -json "$DB" "
    SELECT f.url, f.stage, f.token_estimate, f.summary, f.fetched_by,
           datetime(f.fetched_at,'unixepoch','localtime') AS at
    FROM fetch f
    WHERE f.url IN (SELECT url FROM fetch_fts WHERE fetch_fts MATCH '$query')
      AND f.team_ns='$(sq_esc "$NS")'
    ORDER BY f.fetched_at DESC LIMIT 20;"
}

purge() {
  local older_than="${1:-86400}"
  sqlite3 "$DB" "DELETE FROM fetch WHERE fetched_at < strftime('%s','now') - $older_than;"
  sqlite3 "$DB" "DELETE FROM agent_event WHERE ts < strftime('%s','now') - $older_than;"
  echo "[team-sandbox] purged entries older than ${older_than}s"
}

case "${1:-help}" in
  init) sqlite_init ;;
  lookup) shift; lookup "$@" ;;
  record) shift; record "$@" ;;
  stats) stats ;;
  broadcast) shift; broadcast "$@" ;;
  tail) shift; tail_events "$@" ;;
  search) shift; search "$@" ;;
  purge) shift; purge "$@" ;;
  *)
    cat <<USAGE
team-sandbox — shared Hyperstack cache (SQLite + FTS5)

Commands:
  init                         Initialize schema at \$CTS_TEAM_DB_PATH
  lookup <url> [max_age_sec]   Check team cache (default max_age: 3600s)
  record <url> <stage> <bytes> <hash> <tokens> [summary]
                               Record a fetch in the team cache
  stats                        Team savings summary (overall + per-ns)
  broadcast <agent> <event> [json]
                               Push event to team bus
  tail [since_sec]             Tail recent events (default: 1h)
  search <fts5_query>          FTS5 search across summaries + urls
  purge [older_than_sec]       Delete entries older than (default: 24h)

Environment:
  CTS_TEAM_NS        namespace (default: 'default')
  CTS_TEAM_DB_PATH   SQLite file (default: ~/.cts/hyperstack.db)
USAGE
    ;;
esac
