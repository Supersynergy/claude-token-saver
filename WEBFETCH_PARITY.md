# WebFetch / RTK / context-mode — Feature Parity Matrix

How the Hyperstack replaces (and extends) Claude Code's `WebFetch`, RTK's command compression, and context-mode's sandbox indexing.

## Coverage matrix

| Feature | Claude Code `WebFetch` | RTK | context-mode | Hyperstack |
|---------|:----------------------:|:---:|:------------:|:----------:|
| **Fetching** |
| HTTP GET | ✅ | ❌ | ❌ | ✅ |
| Custom headers | ⚠️ limited | ❌ | ❌ | ✅ (curl_cffi + patches) |
| TLS fingerprint spoofing | ❌ | ❌ | ❌ | ✅ (chrome124 JA3) |
| Cloudflare bypass | ❌ | ❌ | ❌ | ✅ (camoufox escalation) |
| Auth / cookie flows | ❌ | ❌ | ❌ | ✅ (dsh stateful) |
| JS rendering | ❌ | ❌ | ❌ | ✅ (camoufox + domshell) |
| DOM navigation | ❌ | ❌ | ❌ | ✅ (dsh REPL) |
| **Processing** |
| Raw HTML → plaintext | ⚠️ basic | ❌ | ❌ | ✅ (HTML preprocessor) |
| HTML → Markdown | ✅ | ❌ | ❌ | ✅ (`--markdown` flag) |
| Prompt-based extraction | ✅ | ❌ | ❌ | ✅ (`--extract "prompt"`) |
| Local LLM summarization | ❌ | ❌ | ❌ | ✅ (phi4-mini, 0 API cost) |
| ML-based noise filtering | ❌ | ❌ | ❌ | ✅ (catboost) |
| Token counting | ❌ | ❌ | ✅ | ✅ |
| **Caching** |
| Per-session cache | ✅ 15min | ❌ | ✅ FTS5 | ✅ SQLite + FTS5 |
| Cross-session cache | ❌ | ❌ | ✅ | ✅ |
| Cross-dev team cache | ❌ | ❌ | ❌ | ✅ (SQLite shared) |
| TTL control | ❌ fixed | ❌ | ⚠️ | ✅ (per-call + purge) |
| Content-addressable dedupe | ❌ | ❌ | ✅ | ✅ (SHA hash) |
| **Output** |
| Markdown | ✅ | ❌ | ❌ | ✅ |
| JSON | ❌ | ❌ | ✅ | ✅ (single-line) |
| FTS5-searchable archive | ❌ | ❌ | ✅ | ✅ |
| **Orchestration** |
| Parallel fetches | ❌ | ❌ | ⚠️ batch_execute | ✅ (xargs -P10 + subagents) |
| Per-fetch role assignment | ❌ | ❌ | ❌ | ✅ (frontliner/researcher/heavy) |
| Budget tracking | ❌ | ❌ | ⚠️ tokens saved | ✅ (per-ns + per-dev) |
| Multi-agent team bus | ❌ | ❌ | ❌ | ✅ (`cts-team broadcast`) |
| **Command compression (Bash)** |
| `git status -sb` auto | ❌ | ✅ | ❌ | ❌ (RTK still best) |
| `ls -1` auto | ❌ | ✅ | ❌ | ❌ (RTK still best) |
| `pytest -q --tb=short` | ❌ | ✅ | ❌ | ❌ (RTK still best) |
| **General tool output sandbox** |
| `ctx_batch_execute` | ❌ | ❌ | ✅ | ❌ (context-mode still best) |
| `ctx_search` cross-index | ❌ | ❌ | ✅ | ⚠️ (only for cached fetches) |
| `ctx_fetch_and_index` | ❌ | ❌ | ✅ | ✅ (hyperfetch auto-indexes) |

## The three tools solve different layers

```
┌─────────────────────────────────────────────────────────┐
│ Agent's context window                                  │
└──────────────┬──────────────────────────────────────────┘
               │
      ┌────────┴────────┬──────────────────┐
      │                 │                  │
      ▼                 ▼                  ▼
  Hyperstack       context-mode           RTK
  (WEB content)    (TOOL output)          (COMMAND output)

  - Stage chain    - ctx_batch_execute    - git -sb rewrite
  - Team cache     - ctx_search FTS5      - ls -1 rewrite
  - ML filter      - ctx_execute sandbox  - pytest -q rewrite
  - gemma gate     - Indexed tool results - Bash hook transparent
  - dsh DOM nav    - MCP-first design     - 60-90% per command
```

**They compose.** A complete CC session uses all three:

1. **RTK** compresses every git/npm/ls command transparently (60-90% per command).
2. **Hyperstack** handles every web fetch (75-359x per page).
3. **context-mode** sandboxes every `ctx_batch_execute`/`ctx_execute_file` call (keeps raw stdout out of the window).

## Drop-in replacement commands

### Replace `WebFetch` everywhere

The PreToolUse hook blocks `WebFetch` and tells the agent to use `hyperfetch` instead. For manual use:

```bash
# WebFetch equivalent (markdown output with extraction prompt)
hyperfetch https://example.com --markdown
hyperfetch https://example.com --extract "main article body as markdown"

# Feature that WebFetch doesn't have
hyperfetch https://example.com --extract "price, stock, sku as JSON"
```

### Replace `curl` / `wget` for scraping

The hook intercepts raw `curl|wget https://...` and suggests `hyperfetch`. Override with `HYPERSTACK_BYPASS=1` for genuine raw POST bodies or API calls to your own backend.

### Replace `playwright snapshot` / `puppeteer`

Use `dsh` — it's stateful, JSON-only, and runs on camoufox/patchright underneath:

```bash
# Old: playwright codegen
dsh --session login goto https://app.example.com
dsh --session login eval "document.querySelector('#email').value='x@y.z'"
dsh --session login click "button[type=submit]"
```

### Replace `ctx_fetch_and_index` for web content specifically

context-mode's `ctx_fetch_and_index` works but uses a simple fetcher. For stealth-required or JS-heavy pages, route through Hyperstack first, then the result lands in both the Hyperstack team cache AND context-mode's sandbox (via the agent's subsequent `ctx_index` call on the preview).

## What Hyperstack does NOT replace

- **RTK**: Keep using it. Hyperstack doesn't touch `git`/`ls`/`pytest`/`npm` — that's RTK's job.
- **context-mode**: Keep using it. Hyperstack doesn't sandbox general tool output — that's what `ctx_batch_execute` is for.
- **Claude Code's native features**: /memory, /teams, /loop, PostCompact hook, Worktree isolation — all still work. Hyperstack integrates with them (see `HYPERSTACK.md` integration section).

## When to use which

| Situation | Best tool |
|-----------|----------|
| Fetching a web page | **Hyperstack** (`hyperfetch`) |
| Running a git/npm command | **RTK** (transparent) |
| Running a multi-step shell script with big output | **context-mode** (`ctx_execute`) |
| Researching across multiple already-fetched pages | **Hyperstack team cache** + **context-mode** `ctx_search` |
| Navigating a logged-in dashboard | **Hyperstack** (`dsh`) |
| Indexing a local directory for later search | **context-mode** (`ctx_index`) |
| Batch-processing 50 scraped pages | **Hyperstack** subagent (`hyperstack-scraper`) |

## The compound effect

Using all three together on a typical research session (30 git commands + 10 web fetches + 5 big tool calls):

| Layer | Without | With | Savings |
|-------|---------|------|---------|
| RTK (30 commands) | 15k tok | 3k tok | 12k |
| Hyperstack (10 fetches) | 150k tok | 2k tok | 148k |
| context-mode (5 tool calls) | 50k tok | 5k tok | 45k |
| **Session total** | **215k tok** | **10k tok** | **205k (21.5x)** |

At Opus 4.6 rates ($15/M): **$3.23 → $0.15** per session. Multiply by 1000 sessions/month and a team of 10 devs with shared caches, and you're in the 1,000x territory — no single-tool hack gets you there.
