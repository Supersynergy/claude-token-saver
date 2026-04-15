```
 ██████╗██╗      █████╗ ██╗   ██╗██████╗ ███████╗
██╔════╝██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝
██║     ██║     ███████║██║   ██║██║  ██║█████╗
██║     ██║     ██╔══██║██║   ██║██║  ██║██╔══╝
╚██████╗███████╗██║  ██║╚██████╔╝██████╔╝███████╗
 ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝

████████╗ ██████╗ ██╗  ██╗███████╗███╗   ██╗
╚══██╔══╝██╔═══██╗██║ ██╔╝██╔════╝████╗  ██║
   ██║   ██║   ██║█████╔╝ █████╗  ██╔██╗ ██║
   ██║   ██║   ██║██╔═██╗ ██╔══╝  ██║╚██╗██║
   ██║   ╚██████╔╝██║  ██╗███████╗██║ ╚████║
   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝

███████╗ █████╗ ██╗   ██╗███████╗██████╗
██╔════╝██╔══██╗██║   ██║██╔════╝██╔══██╗
███████╗███████║██║   ██║█████╗  ██████╔╝
╚════██║██╔══██║╚██╗ ██╔╝██╔══╝  ██╔══██╗
███████║██║  ██║ ╚████╔╝ ███████╗██║  ██║
╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝

         ⚡ Speed or 💰 Savings — Adaptive.
         Every CLI. Every Model. Every Budget.
```

**The right model for every task. Every CLI. Every budget.**

```bash
curl -fsSL https://raw.githubusercontent.com/Supersynergy/universal-agent-token-saver/main/install-universal.sh | bash
```

---

## The Core Insight

```
💰 Claude Opus:   $15/M tokens  → Token-Sparmaßnahmen LOHNEN sich
⚡ MiniMax M2.7:  $0.05/M tokens → Token-Sparmaßnahmen KOSTEN Zeit
```

**Bei schnellen, günstigen APIs** → Geschwindigkeit vor Effizienz  
**Bei teuren APIs** → Volle Token-Optimierung aktivieren

---

## Full Stack Timing Benchmarks

Real measured latency + token counts (M4 Max, macOS 24.5, 2026-04-15):

```
Tool/Command              Avg ms    Bytes    Est tok    vs baseline
──────────────────────────────────────────────────────────────────
raw ls -la                  6ms    4,865     1,216t     (baseline)
rtk ls                     10ms    1,861       465t      -62% ✓
raw git status             12ms      100        25t     (baseline)
rtk git status             23ms       47        11t      -53% ✓
raw curl (small API)      814ms      429       107t     (baseline)
rtk curl --schema         957ms      157        39t      -63% ✓
hyperfetch/curl_cffi     1461ms      626       156t      +46% ✗ small page
hyperfetch/camoufox      3460ms      612       153t      +43% ✗ small page
raw cat (head -100 lines)   4ms    4,406     1,101t     (baseline)
rtk read (FULL FILE)        8ms   22,541     5,635t     +412% ✗✗ BUG
ctx_batch_execute (1 call)  3ms       40        10t      -99% ✓✓✓
```

### RTK per-command verdict (real benchmarks)

```
Command          tok saved   speed hit   verdict
──────────────────────────────────────────────────────
rtk git diff     -99%        -30%        ★★★ always use
rtk docker ps    -84%        +22% faster ★★★ always use
rtk find         -57%        -22%        ✓ use
rtk curl         -63%        +18% slower ✓ use for JSON structure
rtk ps aux       -50%        3x slower   ✓ worth it
rtk git status   -53%        2x slower   ✓ worth it
rtk ls           +35% WORSE  2x slower   ✗ never — use Glob tool
rtk env          +105% WORSE 30% slower  ✗ never — use env | grep
rtk grep         +10000% WRS 2x slower   ✗ never — use Grep tool
rtk read         +412% WORSE 2x slower   ✗ never — use Read tool
rtk json         broken      ~1s         ✗ broken (returns empty)
```

### Critical findings from benchmarks

**`rtk read` is broken for token saving** — loads full file + metadata = 5,635t vs 1,101t raw = 5x WORSE. Never use `rtk read`. Use the native `Read` tool instead.

**`hyperfetch` hurts on small responses** — httpbin.org/json raw = 107t, hyperfetch = 156t (+46%). Gemma gate overhead exceeds savings for tiny API responses. `CTS_GEMMA_THRESHOLD=200` is already correctly set. hyperfetch only pays off on large pages (full HTML, docs, dashboards).

**`rtk curl` is the sweet spot for APIs** — -63% tokens, only +18% slower. Best when you need JSON structure/schema. For specific fact extraction from large pages: `hyperfetch --extract "field"`.

**`ctx_batch_execute` is fastest AND smallest** — 3ms, 10t for any N commands. Replaces both Bash calls and research subagents.

---

## Gemma Gate — Why, When to Skip, What to Use Instead

### Why Gemma exists

Gemma (phi4-mini via Ollama) compresses large unstructured HTML before it enters Claude's context window. Without it, a typical web page = 12,500 tokens. With Gemma = 125 tokens.

### When Gemma HURTS (skip it)

```
Scenario              Raw      Gemma     Better alternative
────────────────────────────────────────────────────────────
JSON API call         107t     153t+46%  curl_cffi+keys = 3t  ← -97%
Small API (<500 bytes) 39t     153t+292% rtk curl = 39t
Cached URL (2nd call) 160t     160t      hyperfetch (cache)=137ms
```

### When Gemma HELPS (keep it)

```
Scenario              Raw        trafilatura  Gemma    best
──────────────────────────────────────────────────────────────────
Large HTML article  12,500t     ~1,250t      ~125t    trafilatura first
Doc page (facts)    12,500t       N/A         ~12t    hf --extract "X"
Anti-bot target       N/A         N/A        ~125t    hf --stage camoufox
```

### Gemma alternatives (ranked)

| Option | Size | Overhead | Quality | Use when |
|--------|------|---------|---------|----------|
| **curl_cffi + python extract** | 0 | 0ms | perfect | JSON APIs — programmatic |
| **trafilatura** | installed | 0ms | 90% | HTML articles/docs (no LLM!) |
| **html2text** | installed | 0ms | 80% | simpler HTML conversion |
| **regex strip** | 0 | 5ms | 60% | fastest, good enough |
| **qwen2.5:0.5b** | 397MB | ~100ms | 85% | `ollama pull qwen2.5:0.5b` |
| **phi4-mini (current)** | 2.5GB | ~300ms | 95% | complex extraction |
| **Claude Haiku API** | remote | ~400ms | 99% | $1/M, most accurate |

### Optimization applied: trafilatura-first pipeline

`gemma-gate.py` now runs **trafilatura before Ollama**:
```
HTML input → trafilatura (0ms) → if still >THRESHOLD → phi4-mini
```
Result: 90% of HTML pages never reach the LLM. phi4-mini only activates for complex/JS-rendered content where trafilatura fails.

Override: `CTS_FORCE_LLM=1` to always use LLM | `CTS_GEMMA_MODEL=qwen2.5:0.5b` for lighter model.

### Best combination per scenario

```
JSON API (structure needed)  → rtk curl -s <url>              = 39t, 890ms
JSON API (keys only)         → curl_cffi + python parse        = 3t, 1300ms
HTML page (article/doc)      → curl_cffi + trafilatura         = ~200t, 800ms, 0 LLM
HTML page (specific fact)    → hyperfetch --extract "field"    = 12t, 3200ms
HTML page (anti-bot)         → hyperfetch --stage camoufox     = 153t, 3300ms
HTML page (cached)           → hyperfetch (2nd call)           = 160t, 137ms ★
Docker/process output        → rtk docker ps / rtk ps aux      = 274t, -84%
Git diff review              → rtk diff HEAD~1                 = ~0t, 9ms ★★★
Any multi-command research   → ctx_batch_execute               = 13t, 4ms
```

---

## Hook Architecture Audit

Current: **39 hooks across 9 events**. PreToolUse [Bash] runs **6 hooks serially** = 25–100ms overhead per Bash call.

```
PreToolUse [Bash] — serial execution order:
  1. hyperstack-pretool.sh   (WebFetch intercept, exit 0 for non-web)
  2. rtk-rewrite.sh          (RTK auto-rewrite via Rust binary) ← CANONICAL
  3. ctx-optimizer.sh        (blocks large-output bash)
  4. context-mode hook       (MCP routing enforcement)
  5. tokenguard-auto.sh      (RTK rewrite v2.0) ← REDUNDANT with #2
  6. shellfirm               (destructive command guard)

SessionStart: 11 hooks (costly — 11 process forks at startup)
```

### Optimizations

**A. Remove `tokenguard-auto.sh` from PreToolUse** — `rtk-rewrite.sh` delegates to the Rust `rtk rewrite` binary (single source of truth in `src/discover/registry.rs`). `tokenguard-auto.sh` is a Bash reimplementation of the same logic. Remove the duplicate.

**B. `rtk read` — exclude from usage** — add rule to `ctx-optimizer.sh` blocking `cat`/`head` in Bash and `rtk read` calls; suggest native `Read` tool.

**C. hyperfetch — add URL size hint** — only suggest hyperfetch for non-API-endpoint URLs (skip `/json`, `/get`, `/status/*`, `/health`, `/ping`).

**D. SessionStart — parallel launch** — 11 serial hooks can run in parallel with `&` + `wait`. Goal: <500ms total startup overhead.

---

## Token Saving Stack (2025–2026)

Four layers attack four different token problems. Mix and match by use case.

```
┌─────────────────────────────────────────────────────────────────────┐
│  TOKEN PROBLEM          TOOL              SAVINGS                   │
├─────────────────────────────────────────────────────────────────────┤
│  OUTPUT verbosity       caveman           65% avg (22–87%)          │
│  INPUT flooding         context-mode      98% tool output           │
│  CLI bash noise         RTK               62–99% (command-specific) │
│  Scrape/noise pre-sort  catboost          extra 25–50% on input     │
└─────────────────────────────────────────────────────────────────────┘
```

### How they differ

| Layer | Tool | What it compresses | When |
|-------|------|--------------------|------|
| Output | **caveman** | Agent *responses* — drops articles, filler, hedging | Every response |
| Input | **context-mode** | Tool results (Bash/Read/Grep/WebFetch) via MCP sandbox | Every tool call |
| CLI | **RTK** | Raw bash output before it hits LLM | Bash only |
| Pre-filter | **catboost** | Classifies signal vs noise BEFORE ctx-mode indexes | Scraping/log heavy |

> **RTK + context-mode overlap:** context-mode intercepts ALL tools via hooks including Bash. RTK additive only for standalone terminal use outside MCP sandbox.

---

## Combination Benchmarks

Baseline session: **143,000 tokens** (35k output + 100k tool-input + 8k bash).  
Prices: Opus $15/M · Sonnet $3/M · catboost v1.2.10 installed locally.

| Combination | Output | Input | Bash | Total | Saved | Opus$/sess | Sonnet$/sess |
|-------------|-------:|------:|-----:|------:|------:|-----------:|-------------:|
| baseline | 35,000 | 100,000 | 8,000 | 143,000 | 0% | $2.1450 | $0.4290 |
| caveman:full | 12,250 | 100,000 | 8,000 | 120,250 | 15.9% | $1.8037 | $0.3608 |
| caveman:ultra | 8,750 | 100,000 | 8,000 | 116,750 | 18.4% | $1.7512 | $0.3503 |
| context-mode | 35,000 | 2,000 | 8,000 | 45,000 | 68.5% | $0.6750 | $0.1350 |
| RTK only | 35,000 | 100,000 | 2,000 | 137,000 | 4.2% | $2.0550 | $0.4110 |
| **caveman+ctx** | **12,250** | **2,000** | **8,000** | **22,250** | **84.4%** | **$0.3337** | **$0.0668** |
| ultra+ctx | 8,750 | 2,000 | 8,000 | 18,750 | 86.9% | $0.2812 | $0.0563 |
| ctx+RTK | 35,000 | 2,000 | 1,600 | 38,600 | 73.0% | $0.5790 | $0.1158 |
| caveman+ctx+RTK | 12,250 | 2,000 | 1,600 | 15,850 | 88.9% | $0.2378 | $0.0476 |
| ultra+ctx+RTK | 8,750 | 2,000 | 1,600 | 12,350 | 91.4% | $0.1852 | $0.0370 |
| ultra+ctx+RTK+catboost | 8,750 | 1,500 | 1,200 | 11,450 | 92.0% | $0.1718 | $0.0343 |
| hyperstack_full | 8,750 | 2 | 1,200 | 9,952 | 93.0% | $0.1493 | $0.0299 |

### Key findings

- **context-mode alone** outperforms RTK alone by 16x — input flooding dominates
- **caveman alone** only saves 16% total (output is small vs input)
- **caveman + context-mode** = sweet spot: 84.4% savings, minimal config
- **RTK** adds ~4% on top of full stack — worth it for bash-heavy workflows only
- **catboost** pre-filter: additional 0.6% on already-optimized stack. Real value is for raw scraping pipelines before ctx-mode sees them
- **hyperstack chain** hits 93% — but only relevant for web-heavy agent sessions

### hyperfetch: when to use which tool

```
URL type                     Tool                      Why
──────────────────────────────────────────────────────────────────────
Small API (/json, /health)   rtk curl -s <url>         -63% tok, no Gemma
Large page (HTML/docs)       hyperfetch --stage c..    +94% tok savings
Specific fact needed         hyperfetch --extract ".."  5-10t result only
Anti-bot target              hyperfetch --stage cam..  0.07s, stealth
Interactive/SPA              dsh (DOMShell REPL)       stateful, JSON
```

### Optimal Config by Use Case

| Use Case | Stack | Savings | Note |
|----------|-------|---------|------|
| Daily coding (Sonnet) | caveman:full + context-mode | **84%** | Best ROI, zero friction |
| Heavy research (Opus) | ultra + ctx + RTK | **91%** | Worth the setup |
| Scraping agents | ultra + ctx + RTK + catboost | **92%** | catboost pre-filters noise |
| Web agent sessions | hyperstack full chain | **93%** | 73,333x on scrapes |
| Fast cheap APIs (MiniMax) | caveman only | readability | No ctx overhead needed |
| 10-dev team, same targets | hyperstack + SurrealDB cache | shared 2t | 750x vs solo |

> **RTK verdict:** Skip unless bash-heavy workflow. context-mode already intercepts Bash. RTK standalone value = non-Claude-Code terminals only.

---

## caveman — 65% Output Token Savings

> why use many token when few do trick

One-line install. Auto-activates every session via SessionStart hook.

```bash
claude plugin marketplace add JuliusBrussee/caveman && claude plugin install caveman@caveman
```

### Official Benchmarks (10 real API calls)

| Task | Normal | Caveman | Saved |
|------|-------:|--------:|------:|
| Explain React re-render bug | 1,180 | 159 | **87%** |
| Fix auth middleware token expiry | 704 | 121 | **83%** |
| Set up PostgreSQL connection pool | 2,347 | 380 | **84%** |
| Explain git rebase vs merge | 702 | 292 | 58% |
| Refactor callback to async/await | 387 | 301 | 22% |
| Architecture: microservices vs monolith | 446 | 310 | 30% |
| Review PR for security issues | 678 | 398 | 41% |
| Docker multi-stage build | 1,042 | 290 | **72%** |
| Debug PostgreSQL race condition | 1,200 | 232 | **81%** |
| Implement React error boundary | 3,454 | 456 | **87%** |
| **Average** | **1,214** | **294** | **65%** |

*Source: [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) — reproducible via `uv run python evals/llm_run.py`*

### Intensity Levels

| Level | Drop | Savings |
|-------|------|---------|
| `lite` | Articles, filler words | ~40% |
| `full` | Articles + fragments OK + short synonyms | ~65% |
| `ultra` | Maximum compression, telegram-style | ~75% |
| `wenyan` | Classical Chinese mode | ~75% |

Switch: `/caveman lite` · `/caveman ultra` · `stop caveman`

### caveman-compress (Input Savings)

`caveman-compress` rewrites CLAUDE.md / memory files in caveman format — cuts **~46% of input tokens** every session without losing any technical substance.

```bash
# Compress a memory/instruction file
/caveman:compress ~/.claude/CLAUDE.md
```

### Key Insight

> Caveman only affects **output tokens** — thinking/reasoning tokens untouched. Caveman make *mouth* smaller, not brain smaller. A March 2026 paper found brevity constraints improved accuracy by **26 percentage points** on certain benchmarks.

---

## context-mode — 98% Context Reduction (v1.0.89)

> 315 KB of tool output → 5.4 KB. Everything else stays in a SQLite/FTS5 sandbox.

```bash
/plugin marketplace add mksglu/context-mode
/plugin install context-mode@context-mode
```

**The Problem:** Every MCP tool call dumps raw data into context. Playwright snapshot = 56 KB. 20 GitHub issues = 59 KB. One access log = 45 KB. After 30 min, 40% of context is gone — and when the agent compacts, it forgets what it was doing.

**The Solution:** 3-sided attack:
1. **Context Saving** — sandbox keeps raw data out of window
2. **Session Continuity** — file edits, git ops, tasks tracked in SQLite; retrieved via BM25 search on compaction
3. **Think in Code** — agent writes scripts to count/analyze, not reads 50 files into context

### Tools

| Tool | Purpose |
|------|---------|
| `ctx_batch_execute` | N commands + queries in ONE call (primary gather) |
| `ctx_search` | BM25 search across indexed output |
| `ctx_execute` | Run analysis code in sandbox |
| `ctx_execute_file` | Same, on a file path |
| `ctx_fetch_and_index` | WebFetch replacement — stores + indexes |
| `ctx_index` | Manually index file/dir |
| `ctx_stats` | Session token savings breakdown |
| `ctx_doctor` | Install health diagnostics |
| `ctx_upgrade` | Pull latest + rebuild |
| `ctx_purge` | Clear sandbox index |
| `ctx_insight` | 15+ metric analytics dashboard |

**Rule:** 2+ commands → `ctx_batch_execute`. Never multiple Bash calls.

### Upgrade

```bash
/ctx-upgrade
# or
/context-mode:ctx-upgrade
```

---

## RTK Universal — Keep It. But Use It Right.

> Verdict: **NOT redundant** vs context-mode. Complementary. Different attack surface.

### Why RTK survives

context-mode sandboxes MCP tool results. RTK compresses raw Bash output **before** it leaves the shell. They catch different things:

| Command | context-mode covers? | RTK covers? | RTK savings |
|---------|---------------------|-------------|-------------|
| `cargo build` | No | **Yes** | **97.2%** |
| `curl -s` (inline Bash) | Only if you use ctx_fetch_and_index | **Yes** (passive) | **99.8%** |
| `ps aux` | No | **Yes** | **98.4%** |
| `docker exec` | No | **Yes** | ~80% |
| `grep -n` (raw Bash) | Only if you use Grep tool | **Yes** | ~70% |
| `ls -la` (raw Bash) | Only if you use Glob tool | **Yes** | 62.5% |

### Real measured data (333 RTK calls, global)

```
Total saved:  3.4M tokens (39.4% avg)
Cargo build:  1.3M tokens saved (97.2%) — biggest single win
curl calls:   1.0M tokens saved (99.7%) — schema only, no bloat
ps aux:       304K tokens saved (98.4%)
rtk ls:       143K tokens saved (62.5%)
```

### MISSED savings (last 30 days — 0.1% adoption problem)

RTK only works when explicitly invoked. 40,762 raw Bash commands in 30 days, only 41 used RTK.

| Missed command | Count | Est. tokens missed |
|---------------|------:|-------------------:|
| `tail -5` | 2,631 | 680,300 |
| `ls -la` | 3,458 | 422,700 |
| `curl -s` | 2,034 | 299,400 |
| `grep -n` | 1,294 | 204,200 |
| `find` | 1,023 | 166,000 |
| `cargo build` | 503 | 77,300 |
| **TOTAL MISSED** | | **~2.06M tokens = $30.97/month Opus** |

**Fix:** Run `rtk discover` to see your own missed commands. Add `rtk X` prefix rules to CLAUDE.md.

### RTK commands worth always using

```bash
rtk cargo build    # 97% savings — never run naked
rtk cargo check    # 99.6%
rtk curl -s <url>  # 99.8% — when you want schema/shape not summary
rtk ps aux         # 98.4%
rtk docker <cmd>   # ~80%
rtk git status     # 70%
rtk ls             # 62%
rtk read <file>    # 33% — catches raw Bash cat/head
```

### RTK vs hyperfetch for curl

| Tool | Output | Savings | Use when |
|------|--------|---------|----------|
| raw curl | ~900t | 0% | Never |
| `rtk curl --schema` | ~15t | **99.8%** | Need API shape/structure |
| `hyperfetch --extract "field"` | ~5–10t | **99%+** | Need specific facts |
| `hyperfetch --markdown` | ~50t | 94% | Need readable summary |

---

## Adaptive Model Selection

| Factor | Decision |
|--------|----------|
| API-Key/Provider | MiniMax = ⚡ Speed, Claude = 💰 Savings |
| Task complexity | Simple → Fast, Complex → Smart |
| Speed requirement | High → Fastest provider |
| Code quality | Draft → Fast, Production → Quality |

---

## Provider Comparison

| Provider | Model | Speed | Cost/M | Token Savings | Best For |
|----------|-------|-------|--------|--------------|----------|
| **MiniMax** | M2.7 | ⚡⚡⚡⚡⚡ | $0.05 | **None needed** | High-Volume, Speed |
| **Google** | Gemini 3 Flash | ⚡⚡⚡⚡ | $0.07 | Minimal | Quick Tasks |
| **Google** | Gemini 3 Pro | ⚡⚡⚡ | $1.00 | 60% | Complex Reasoning |
| **Anthropic** | Claude Sonnet 4.6 | ⚡⚡⚡ | $3.00 | **60–90%** | Production Code |
| **Anthropic** | Claude Opus 4.6 | ⚡⚡ | $15.00 | **60–90%** | Architecture |
| **Anthropic** | Claude Haiku 4.5 | ⚡⚡⚡⚡ | $1.00 | **60–90%** | Fast Agents |
| **OpenAI** | GPT-4o | ⚡⚡⚡ | $2.50 | **60–90%** | General Tasks |
| **Moonshot** | Kimi K2.5 | ⚡⚡⚡⚡ | $0.50 | Minimal | Code Generation |
| **DeepSeek** | Coder | ⚡⚡⚡⚡ | $0.14 | Minimal | Code Completion |

---

## Supported CLI Agents

| Agent | Icon | Config Path | Optimization |
|-------|------|------------|--------------|
| **Claude Code** | 🦙 | `~/.claude/` | Full (expensive) |
| **Gemini CLI** | ✨ | `~/.gemini/` | Minimal (fast) |
| **Kilo/Code** | ⚡ | `~/.local/share/kilo/` | Minimal |
| **OpenCode** | ⚡ | `~/.local/share/opencode/` | Minimal |
| **Codex CLI** | 🔮 | `~/.codex/` | Full (expensive) |
| **Kimi Code** | 🌙 | `~/.kimi/` | Minimal |
| **OpenClaw** | 🦞 | `~/.openclaw/` | Full |
| **Hermes** | 🤖 | `$HERMES_HOME/` | Full |

---

## Quick Start

### 1. Install (Auto-Detection)

```bash
curl -fsSL https://raw.githubusercontent.com/Supersynergy/universal-agent-token-saver/main/install-universal.sh | bash
```

### 2. Install caveman (Claude Code)

```bash
claude plugin marketplace add JuliusBrussee/caveman && claude plugin install caveman@caveman
```

### 3. Install context-mode (Claude Code)

```bash
/plugin marketplace add mksglu/context-mode && /plugin install context-mode@context-mode
```

### 4. Check your stack

```bash
uts check
/ctx-doctor
```

---

## Core Features

### ⚡ Adaptive Model Selection

```
┌─────────────────────────────────────────────────────────┐
│  Task gestartet                                         │
│      │                                                  │
│      ├─→ Speed = "fastest"?                            │
│      │       └─→ YES → MiniMax M2.7 ⚡                │
│      │                                                  │
│      ├─→ Code Quality = "production"?                  │
│      │       └─→ YES → Claude Sonnet 4.6 💰           │
│      │                                                  │
│      ├─→ Complexity = "complex"?                       │
│      │       └─→ YES → Claude Opus 4.6 💰             │
│      │                                                  │
│      └─→ Default → Gemini 3 Flash ⚡                   │
└─────────────────────────────────────────────────────────┘
```

### 💰 Provider-Based Token Savings

| Provider | Strategy | Why |
|----------|----------|-----|
| MiniMax | **None** | $0.05/M = cheap, speed > efficiency |
| Google | Minimal | $0.07–1.25/M = moderate |
| Anthropic | **Full** | $3–15/M = expensive, savings pay off |
| OpenAI | **Full** | $2.50–75/M = expensive, savings pay off |

### 🔧 Multi-CLI Vault System

```
~/.uts/vault/
├── skills/           # Universal skills (CLI-agnostic)
├── commands/         # CLI-specific commands
└── adapters/        # One per CLI tool
    ├── claude.js
    ├── gemini.js
    ├── kilo.js
    └── codex.js
```

---

## `/uts` Commands

| Command | Description |
|---------|-------------|
| `/uts check` | Check current model & strategy |
| `/uts select` | Adaptive model selection |
| `/uts strategy` | Show provider strategy |
| `/uts list` | All available models |
| `/uts agents` | Show installed CLI agents |
| `/uts install` | Install UTS for CLI |
| `/uts dashboard` | Multi-agent token dashboard |
| `/uts upgrade` | Update to latest |

---

## 🚀 Hyperstack — 10,000x Claude Code Experience

> 4-stage escalation chain + local ML triage + shared team sandbox.
> Target: **same price, 10,000x more effective Claude Code sessions**.

```
curl_cffi → camoufox → domshell → browser (fail-forward)
      ↓ catboost pre-filter (local, 5ms)
      ↓ gemma local summarizer (Ollama, 200ms)
      ↓ context-mode sandbox
      ↓ SurrealDB team cache (multi-dev dedupe)
```

**Install**: `./install-hyperstack.sh` · **Docs**: [HYPERSTACK.md](./HYPERSTACK.md)

| Scenario | Baseline | Hyperstack | Factor |
|----------|----------|------------|--------|
| Single web scrape | 15k tok | 200 tok | **75x** |
| 10-dev team, same target | 150k tok | 200 tok | **750x** |
| + catboost noise filter | — | 40 tok | **3,666x** |
| + gemma summary gate | — | 2 tok | **~73,333x** |

---

## New Fused Tools (2026-04-15)

### `smart-fetch` — auto-routing web fetch

Replaces: `hyperfetch` + `rtk curl` + raw `curl` + `curl_cffi`

```bash
smart-fetch <url>                    # auto-detect JSON vs HTML
smart-fetch <url> --mode json        # force JSON schema extract
smart-fetch <url> --mode html        # force trafilatura clean text
smart-fetch <url> --extract "field"  # targeted extraction
```

Attribution: [curl_cffi](https://github.com/yifeikong/curl_cffi) + [trafilatura](https://github.com/adbar/trafilatura) + [rtk](https://github.com/rtk-ai/rtk)

Benchmark results (real, 2026-04-15):
```
raw curl /json:       107t, 814ms  (baseline)
rtk curl /json:        39t, 889ms  -63%
smart-fetch /json:      5t, 995ms  -95%  ← auto JSON schema
smart-fetch /html:     35t, 213ms  -73%  ← trafilatura, no LLM
hyperfetch+phi4mini:  153t,2670ms  +43%  ← WORSE on small APIs
```

Routing logic:
```
URL path matches /api/|/v1/|.json|/get|/status  →  curl_cffi + json.keys()  =  3-5t
HTML page (article/doc)                          →  curl_cffi + trafilatura  =  35-200t
Anti-bot target                                  →  curl_cffi chrome110      =  auto
```

### `sg` — smart grep (ayg + ripgrep auto-router)

Replaces: `grep`, `rg`, `rtk grep` (proven +10,000% worse)

```bash
sg <pattern>              # auto-route: ayg (indexed) or rg (fallback)
sg build .                # build ayg index once (~30s for large repos)
sg stats                  # show routing decision
sg <pattern> --force-ayg  # always use indexed search
```

Attribution: [ayg/aygrep](https://github.com/hemeda3/aygrep) — sparse n-gram indexed search, built for AI coding agents

Benchmarks (ayg vs ripgrep):
```
Repo size           rg time    ayg time   speedup
< 10k files         ~20ms      needs build  —
10k-100k files      ~500ms     ~60ms        8x
> 100k files        ~29s       ~60ms       460x  (Chromium, M3 Max warm)
Linux kernel 40M    ~1.5s      ~6ms        250x  (hot)
```

Routing: `ayg_index/` present → ayg. Otherwise → rg. Build once: `sg build .`

### RTK bad-rewrite patch

`rtk-rewrite.sh` hook now intercepts RTK's Rust auto-rewriter before bad commands execute:

```
ls -la → rtk ls    BLOCKED  (+35% more tokens)  → use Glob tool
grep   → rtk grep  BLOCKED  (+10,000% overhead)  → use Grep tool / sg
env    → rtk env   BLOCKED  (+105% more bytes)   → use env | grep
cat    → rtk read  BLOCKED  (+412% more tokens)  → use Read tool

docker ps → rtk docker ps  ALLOWED  (-84% tokens)  ✓
git diff  → rtk diff       ALLOWED  (-99% tokens)  ✓
curl      → rtk curl       ALLOWED  (-63% tokens)  ✓
cargo     → rtk cargo      ALLOWED  (-97% tokens)  ✓
ps aux    → rtk ps         ALLOWED  (-50% tokens)  ✓
```

---

## Subagent Token Patterns

Per subagent spawn: **30,000 tokens** ($0.45 Opus). Scale fast.

| N agents | Raw cost | Caveman-optimized | ctx_batch replaces all |
|----------|---------:|------------------:|----------------------:|
| 1 | 30,000t | 25,450t | **500t** |
| 3 | 90,000t | 76,350t | **500t** |
| 5 | 150,000t | 127,250t | **500t** |
| 10 | 300,000t | 254,500t | **500t** |
| 20 | 600,000t | 509,000t | **500t** |

`ctx_batch_execute` replaces research subagents entirely — **280x cheaper** than spawning an Explore agent.

### When to spawn vs when to batch

| Task | Spawn subagent? | Optimization |
|------|----------------|-------------|
| Research / grep / fetch | **NEVER** | `ctx_batch_execute` — 280x cheaper |
| Parallel code execution | YES, minimal ctx | Pass task spec only (caveman prompt) |
| Web scraping N URLs | YES + hyperfetch | Each agent: `hyperfetch --extract "..."` |
| Long builds | YES, `background=True` | `rtk cargo build` inside agent |
| Code review | YES, structured output | Demand JSON result back, not prose |
| Security scan | YES, isolated worktree | Pass file list, not full parent context |

### Subagent prompt optimization rules

```
1. ctx_batch_execute first — eliminates 80% of research subagent needs
2. Pass caveman-mode prompts → 35% smaller task spec to each agent
3. Demand structured output (JSON/bullets) — not prose
4. Never pass full parent context — slice only what agent needs
5. use background=True for independent parallel work
6. hyperfetch --extract for web tasks → skip spawning researcher agent
7. RTK wraps bash inside subagents too (they run Bash independently)
```

---

## beads (bd) — Task Tracking + Memory

> Replaces TodoWrite/TaskCreate and markdown notes with a grep-able issue DB.

```bash
bd ready                    # Available work, no blockers
bd create --title=... --type=task --priority=2
bd update <id> --claim
bd close <id1> <id2> ...
bd remember "..."           # Persistent cross-session memory
bd memories <keyword>
```

Pairs with CTS: `bd` tracks the work, `context-mode` keeps output out of window, `RTK` compresses standalone CLI.

---

## Token Math

### Expensive API (Claude) — Full Stack

```
Before stack:  ~35,000 tokens/session overhead
After caveman: ~12,250 tokens (65% output reduction)
After ctx-mode: ~5,400 tokens (98% tool output reduction)
After RTK:     ~4,000 tokens (bash noise removed)

At 1,000 sessions/month:  31M tokens saved
At Sonnet pricing ($3/M):  ~$93/month saved
At Opus pricing  ($15/M): ~$465/month saved
```

### Fast API (MiniMax)

```
Token savings: NOT ACTIVATED
Reason: $0.05/M = waste of time to optimize
Use caveman for speed/readability, not cost
```

---

## Decision Matrix

| Task Type | Fast API | Expensive API |
|-----------|----------|---------------|
| Quick Fix | MiniMax M2.7 ⚡ | Claude Haiku 💰 |
| Exploration | Gemini 3 Flash ⚡ | Claude Sonnet 💰 |
| Code Generation | Kimi K2.5 ⚡ | Claude Sonnet 💰 |
| Production | Gemini 3 Pro ⚡ | Claude Sonnet 💰 |
| Architecture | Gemini 3 Pro ⚡ | Claude Opus 💰 |

---

## Installation

### Auto-Detection + Full Install

```bash
curl -fsSL https://raw.githubusercontent.com/Supersynergy/universal-agent-token-saver/main/install-universal.sh | bash
```

### CLI-Specific

```bash
# Gemini CLI only
curl -fsSL ... | bash -s -- --adapter=gemini

# Claude Code only
curl -fsSL ... | bash -s -- --adapter=claude

# All CLIs
curl -fsSL ... | bash -s -- --adapter=all
```

---

## Configuration

### `~/.uts/config.json`

```json
{
  "provider": "minimax",
  "model": "minimax-m2.7",
  "strategy": {
    "tokenSavings": "none",
    "cacheStrategy": "disabled",
    "batchStrategy": "never"
  },
  "preferences": {
    "preferSpeed": true,
    "maxCostPerMonth": 100
  }
}
```

### Provider Strategies

**MiniMax (Fastest)**
```json
{
  "provider": "MiniMax",
  "tokenSavings": "none",
  "cacheStrategy": "disabled",
  "batchStrategy": "never",
  "recommendedModel": "minimax-m2.7"
}
```

**Anthropic (Full Stack)**
```json
{
  "provider": "Anthropic",
  "tokenSavings": "full",
  "cacheStrategy": "aggressive",
  "batchStrategy": "always",
  "recommendedModel": "claude-sonnet-4-6"
}
```

---

## Architecture

```
universal-agent-token-saver/
├── core/
│   ├── adapter-interface.ts    # Universal Adapter Interface
│   └── adaptive-model.ts       # Model Selection Logic
├── adapters/
│   ├── claude-code.ts          # Claude Code Adapter
│   ├── gemini-cli.ts           # Gemini CLI Adapter
│   ├── kilo-code.ts            # Kilo/Code + OpenCode
│   ├── codex.ts               # Codex CLI Adapter
│   ├── kimi-cli.ts            # Kimi Code Adapter
│   └── index.ts               # Adapter Registry
├── plugins/
│   ├── output-filter.js       # 70-95% Noise Reduction
│   └── rtk-universal.sh       # CLI Compression
├── cli/
│   └── uts-dashboard.ts      # Multi-Agent Dashboard
├── UTS.md                     # /uts Skill Documentation
└── install-universal.sh       # Universal Installer
```

---

## Requirements

- Node.js ≥ 16
- Python 3.8+ (optional, for stats)
- macOS / Linux / WSL
- One or more CLI coding agents installed

---

## Upgrade

```bash
uts upgrade
# or
curl -fsSL https://raw.githubusercontent.com/Supersynergy/universal-agent-token-saver/main/install-universal.sh | bash
```

---

## Rollback

```bash
bash ~/.uts-backup-YYYYMMDD-HHMMSS/restore.sh
```

---

## Links

- **GitHub**: [github.com/Supersynergy/claude-token-saver](https://github.com/Supersynergy/claude-token-saver)
- **Docs**: [UTS.md](./UTS.md)
- **caveman plugin**: [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman)
- **context-mode**: [mksglu/context-mode](https://github.com/mksglu/context-mode)

---

## Acknowledgments

| Project | What it does |
|---------|-------------|
| **caveman** | 65% output token savings, auto-activates via SessionStart hook |
| **context-mode** | 98% context reduction, 10 MCP sandbox tools, session continuity |
| **RTK (Rust Token Killer)** | 60-90% CLI bash output compression |
| **shellfirm** | Destructive command protection |
| **beads (bd)** | Issue tracking + persistent memory |

---

**Made with obsession for developer efficiency.**  
⚡ Speed or 💰 Savings — You Choose.  
**Universal Agent Token Saver** — *Every CLI. Every Model.*
