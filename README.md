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

## Token Saving Stack (2025–2026)

Three tools attack three different token problems. Stack all three for maximum savings.

```
┌─────────────────────────────────────────────────────────────────┐
│  TOKEN PROBLEM          TOOL              SAVINGS               │
├─────────────────────────────────────────────────────────────────┤
│  OUTPUT verbosity       caveman           65% avg (22–87%)      │
│  INPUT flooding         context-mode      98% tool output       │
│  CLI bash noise         RTK               60–90% (optional)     │
└─────────────────────────────────────────────────────────────────┘
```

### How they differ

| Layer | Tool | What it compresses | When |
|-------|------|--------------------|------|
| Output | **caveman** | Agent *responses* — drops articles, filler, hedging | Every response |
| Input | **context-mode** | Tool results (Bash/Read/Grep/WebFetch) — sandboxed via MCP | Every tool call |
| CLI | **RTK** | Raw bash output before it hits LLM | Bash only |

> **RTK + context-mode overlap:** context-mode intercepts ALL tools automatically via hooks including Bash. RTK is additive only for non-Claude-Code terminals or standalone CLI usage outside the MCP sandbox.

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

## RTK Universal — 60–90% CLI Compression

> For expensive APIs (Claude, OpenAI). Optional for fast cheap APIs.

**Status:** Largely superseded by context-mode for Claude Code users. context-mode intercepts all tools (including Bash) automatically. RTK still valuable for:
- Standalone terminal use outside Claude Code
- Non-MCP environments
- Specific CLI output shaping (git, docker, kubectl)

```bash
rtk-universal install     # Install hook
rtk-universal wrap <cmd>  # Compress single command
rtk-universal stats       # Show savings
```

### Command Mapping

| Original | RTK Compressed | Savings |
|----------|---------------|---------|
| `git status` | `git status -sb` | 60% |
| `git log` | `git log --oneline` | 75% |
| `ls -la` | `ls -1` | 80% |
| `pytest -v` | `pytest -q --tb=short` | 85% |
| `npm install` | `npm install --silent` | 90% |
| `cargo test` | `cargo test --message-format=short` | 80% |

### When to use RTK vs context-mode

```
Claude Code + context-mode installed → use ctx_batch_execute, skip RTK for bash
Non-Claude-Code terminal              → use RTK
Both installed                        → RTK handles raw terminal, ctx handles LLM tools
```

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
