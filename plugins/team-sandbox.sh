#!/usr/bin/env bash
# team-sandbox: shared context-mode sandbox backed by SurrealDB.
# Enables multi-dev Claude teams to dedupe scraped output across sessions.
# Uses ~/.claude/toolstack.db as single source of truth.

set -euo pipefail

SDB_FILE="${HOME}/.claude/toolstack.db"
SDB_NS="${CTS_TEAM_NS:-default}"
SDB_DB="${CTS_TEAM_DB:-hyperstack}"
CACHE_DIR="${HOME}/.cts/hyperstack"

require_surreal() {
  if ! command -v surreal >/dev/null 2>&1; then
    echo "surreal not installed. install: curl -sSf https://install.surrealdb.com | sh" >&2
    exit 1
  fi
}

init_schema() {
  require_surreal
  surreal sql --conn "file://${SDB_FILE}" --ns "${SDB_NS}" --db "${SDB_DB}" --pretty <<'SQL'
DEFINE TABLE IF NOT EXISTS fetch SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS url ON fetch TYPE string;
DEFINE FIELD IF NOT EXISTS content_hash ON fetch TYPE string;
DEFINE FIELD IF NOT EXISTS stage ON fetch TYPE string;
DEFINE FIELD IF NOT EXISTS bytes ON fetch TYPE int;
DEFINE FIELD IF NOT EXISTS token_estimate ON fetch TYPE int;
DEFINE FIELD IF NOT EXISTS summary ON fetch TYPE option<string>;
DEFINE FIELD IF NOT EXISTS team_ns ON fetch TYPE string;
DEFINE FIELD IF NOT EXISTS fetched_at ON fetch TYPE datetime DEFAULT time::now();
DEFINE FIELD IF NOT EXISTS fetched_by ON fetch TYPE string;
DEFINE INDEX IF NOT EXISTS fetch_url_ns ON fetch FIELDS url, team_ns UNIQUE;
DEFINE INDEX IF NOT EXISTS fetch_hash ON fetch FIELDS content_hash;

DEFINE TABLE IF NOT EXISTS agent_event SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS agent_id ON agent_event TYPE string;
DEFINE FIELD IF NOT EXISTS event_type ON agent_event TYPE string;
DEFINE FIELD IF NOT EXISTS payload ON agent_event TYPE object;
DEFINE FIELD IF NOT EXISTS team_ns ON agent_event TYPE string;
DEFINE FIELD IF NOT EXISTS ts ON agent_event TYPE datetime DEFAULT time::now();
DEFINE INDEX IF NOT EXISTS agent_event_ns ON agent_event FIELDS team_ns, ts;
SQL
  echo "[team-sandbox] schema initialized at ${SDB_FILE} (${SDB_NS}/${SDB_DB})"
}

lookup() {
  local url="$1"
  surreal sql --conn "file://${SDB_FILE}" --ns "${SDB_NS}" --db "${SDB_DB}" --json <<SQL
SELECT * FROM fetch WHERE url = '${url}' AND team_ns = '${SDB_NS}' LIMIT 1;
SQL
}

record() {
  local url="$1" stage="$2" bytes="$3" hash="$4" tokens="$5" who="${USER:-unknown}"
  surreal sql --conn "file://${SDB_FILE}" --ns "${SDB_NS}" --db "${SDB_DB}" --json <<SQL
UPSERT fetch SET
  url = '${url}',
  content_hash = '${hash}',
  stage = '${stage}',
  bytes = ${bytes},
  token_estimate = ${tokens},
  team_ns = '${SDB_NS}',
  fetched_by = '${who}',
  fetched_at = time::now()
WHERE url = '${url}' AND team_ns = '${SDB_NS}';
SQL
}

stats() {
  surreal sql --conn "file://${SDB_FILE}" --ns "${SDB_NS}" --db "${SDB_DB}" --pretty <<SQL
SELECT
  count() AS total_fetches,
  math::sum(token_estimate) AS total_tokens_avoided,
  math::sum(bytes) AS total_bytes_cached,
  count(DISTINCT fetched_by) AS unique_devs,
  count(DISTINCT content_hash) AS unique_content
FROM fetch
WHERE team_ns = '${SDB_NS}'
GROUP ALL;
SQL
}

broadcast() {
  local agent_id="$1" event="$2" payload="${3:-\{\}}"
  surreal sql --conn "file://${SDB_FILE}" --ns "${SDB_NS}" --db "${SDB_DB}" --json <<SQL
CREATE agent_event SET
  agent_id = '${agent_id}',
  event_type = '${event}',
  payload = ${payload},
  team_ns = '${SDB_NS}';
SQL
}

tail_events() {
  local since="${1:-1h}"
  surreal sql --conn "file://${SDB_FILE}" --ns "${SDB_NS}" --db "${SDB_DB}" --pretty <<SQL
SELECT * FROM agent_event
WHERE team_ns = '${SDB_NS}' AND ts > time::now() - ${since}
ORDER BY ts DESC LIMIT 50;
SQL
}

case "${1:-help}" in
  init) init_schema ;;
  lookup) lookup "$2" ;;
  record) record "$2" "$3" "$4" "$5" "$6" ;;
  stats) stats ;;
  broadcast) broadcast "$2" "$3" "${4:-\{\}}" ;;
  tail) tail_events "${2:-1h}" ;;
  *)
    cat <<USAGE
team-sandbox — multi-dev shared context-mode via SurrealDB

  init                         initialize schema
  lookup <url>                 check if url already fetched by team
  record <url> <stage> <bytes> <hash> <tokens>
  stats                        team savings summary
  broadcast <agent> <event> [json]   push event to team bus
  tail [since]                 tail recent events (default 1h)

env:
  CTS_TEAM_NS  namespace (default: 'default')
  CTS_TEAM_DB  database  (default: 'hyperstack')
USAGE
    ;;
esac
