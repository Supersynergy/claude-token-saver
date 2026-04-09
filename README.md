```
 ██████╗████████╗███████╗
██╔════╝╚══██╔══╝██╔════╝
██║        ██║   ███████╗   Claude Token Saver
██║        ██║   ╚════██║   60-90% less tokens. Every session.
╚██████╗   ██║   ███████║   Zero-waste startup. Full vault system.
 ╚═════╝   ╚═╝   ╚══════╝
```

**One command. Saves millions of tokens.**

```bash
curl -fsSL https://raw.githubusercontent.com/Supersynergy/claude-token-saver/main/install.sh | bash
```

---

## The Problem

Every Claude Code session loads tokens you don't need:

| What loads | Tokens wasted |
|-----------|--------------|
| 100+ skill stubs in `commands/` | ~3,000 |
| 50 agent stubs in `agents/` | ~2,500 |
| 10 `rules/common/` files | ~2,800 |
| `CLAUDE.md` with embedded docs | ~5,000 |
| `toolstack-2026.md` via @import | ~4,900 |
| Broken hooks firing on every call | wasted compute |
| LSP plugins loaded globally | ~200 |
| **Total wasted startup** | **~18,000 tokens** |

CTS fixes all of this. Automatically.

---

## What CTS Does

### Layer 0: Vault (0 startup tokens)
All skills, commands, and agents move to `~/.claude/cts/` — cold storage. Zero tokens at startup. Load any of 300+ skills on demand in milliseconds via `/cts search`.

### Layer 1: `/cts` — Smart Skill Manager
Single skill file (~50 tokens). Grep-based index search. Semantic fallback via context-mode.

```
/cts search browser      →  instant grep, 0 tokens
/cts load agent-browser  →  loads one skill (~500-5K tokens)
/cts auto "scrape site"  →  finds + invokes best match
/cts stats               →  savings dashboard
```

### Layer 2: RTK — Bash Token Compression
Auto-rewrites all Bash commands via PreToolUse hook. 60-90% savings on every CLI call.

```bash
rtk gain          # savings dashboard
rtk discover -a   # find missed opportunities
```

### Layer 3: context-mode — Multi-command Batching
`ctx_batch_execute` replaces 30+ separate Bash/Read calls with 1 sandboxed call.

```python
# ❌ 5 calls = ~2,500 tokens overhead
# ✅ 1 ctx_batch_execute = ~300 tokens total
```

### Layer 4: Rules Minimization
10 `rules/common/` files (2.8k tokens) → 1 `rules/core.md` (150 tokens). Full rules moved to `~/.claude/refs/rules/` — accessible on demand.

---

## Install

```bash
# Full install (with backup)
curl -fsSL https://raw.githubusercontent.com/Supersynergy/claude-token-saver/main/install.sh | bash

# Audit what's wasting tokens (read-only)
bash install.sh --audit

# Dry run (preview changes)
bash install.sh --dry-run

# Backup only
bash install.sh --backup-only

# Upgrade to latest CTS
bash install.sh --upgrade
```

**Rollback anytime:** `bash ~/.cts-backup-YYYYMMDD-HHMMSS/restore.sh`

---

## What Gets Migrated

| Before | After | Savings |
|--------|-------|---------|
| `~/.claude/commands/*.md` (100+ stubs) | `~/.claude/cts/commands/` | ~3k tokens |
| `~/.claude/agents/*.md` (50 stubs) | `~/.claude/cts/agents/` | ~2.5k tokens |
| `~/.claude/skills-vault/` | `~/.claude/cts/` (renamed) | seamless |
| `~/.claude/rules/common/*.md` | `~/.claude/refs/rules/` | ~2.8k tokens |
| `toolstack-2026.md` (auto-loaded) | `~/.claude/refs/` | ~4.9k tokens |
| Broken `CLAUDE_PLUGIN_ROOT` hooks | Removed | no more errors |
| Global LSP plugins | Disabled (use per-project) | ~200 tokens |

**Total: 18k → ~4k tokens at startup**

---

## CTS Vault Structure

```
~/.claude/cts/
├── commands/       ← all command skills (was ~/.claude/commands/)
├── agents/         ← all agent definitions (was ~/.claude/agents/)
├── <skill-name>/   ← vault skills (SKILL.md format)
└── ...             ← 300+ skills, 0 startup tokens
```

Everything searchable via `~/.claude/cts.idx` (TSV index, grep-able in <5ms).

---

## Plugin Recommendations

| Plugin | Keep? | Reason |
|--------|-------|--------|
| `claude-hud` | ✅ Yes | Lightweight HUD, ~50 tokens |
| `claude-mem` | ✅ Yes | Memory system, useful |
| `minimal-claude` | ✅ Yes | 7 tiny stubs, ~200 tokens |
| `pyright-lsp` | ⚠️ Per-project | Disable globally, enable in Python projects |
| `rust-analyzer-lsp` | ⚠️ Per-project | Disable globally, enable in Rust projects |
| GSD plugin | ⚠️ Your choice | ~2500 tokens for /gsd:* skills |

Enable LSP per-project: add `"enabledPlugins": {"pyright-lsp@claude-plugins-official": true}` to project's `.claude/settings.json`.

---

## Auto-Update

CTS checks for updates on every install run. To update:

```bash
bash install.sh --upgrade
```

Or add to your workflow: the install script is always safe to re-run (idempotent + auto-backup).

---

## Requirements

- Claude Code ≥ 2.0
- Python 3.8+
- macOS / Linux / WSL
- Optional: RTK (`brew install rtk-ai/tap/rtk`), shellfirm (`brew install shellfirm`)

---

## Token Math

```
Before CTS:  ~35,000 tokens/session startup overhead
After CTS:   ~4,000  tokens/session startup overhead
Savings:     ~31,000 tokens/session

At 1,000 sessions/month:  31M tokens saved
At Sonnet pricing ($3/1M): ~$93/month saved
At Opus pricing  ($5/1M):  ~$155/month saved
```

---

**Made with obsession for token efficiency.**
`github.com/Supersynergy/claude-token-saver`

---

## ⚡ Universal Token Saver — All Coding Agents

> Same savings. Every CLI. Every model.

```bash
curl -fsSL https://raw.githubusercontent.com/Supersynergy/universal-token-saver/main/install-universal.sh | bash
```

### Supported CLI Agents

| Agent | Icon | Tracking | Savings |
|-------|------|----------|---------|
| **Claude Code** | 🦙 | `.claude/projects/` | ✅ 60-90% |
| **Gemini CLI** | ✨ | `.gemini/tmp/` | ✅ 60-90% |
| **Kilo/Code** | ⚡ | `opencode.db` | ✅ 60-90% |
| **OpenCode** | ⚡ | `opencode.db` | ✅ 60-90% |
| **Codex CLI** | 🔮 | `.codex/sessions/` | ✅ 60-90% |
| **Kimi Code** | 🌙 | Agent Tracing | ✅ 60-90% |
| **OpenClaw** | 🦞 | `.openclaw/` | ✅ 60-90% |
| **Hermes** | 🤖 | `state.db` | ✅ 60-90% |

### Architecture

```
universal-token-saver/
├── core/                  # Adapter Interface + Filter Engine
├── adapters/              # Ein Adapter pro CLI-Tool
│   ├── claude-code.ts
│   ├── gemini-cli.ts
│   ├── kilo-code.ts
│   ├── codex.ts
│   └── kimi-cli.ts
├── plugins/               # RTK + Output Filter
└── cli/uts.ts            # Multi-Dashboard
```

### Features

1. **Universal Vault** — 0 startup tokens for any CLI
2. **RTK Universal** — 60-90% CLI compression (all CLIs)
3. **Output Filter** — 70-95% noise reduction
4. **Multi-Dashboard** — All agents in one view
5. **Auto-Detection** — Detects active CLI automatically

### Quick Commands

```bash
uts dashboard     # Multi-agent token dashboard
uts agents        # List detected CLIs
uts stats         # Detailed stats
uts install gemini # Install for specific CLI
uts uninstall     # Remove UTS
```

### Comparison: Before vs After

```
BEFORE: ~35K tokens/session startup (Claude)
AFTER:  ~4K tokens/session startup

BEFORE: 100% CLI output sent to LLM
AFTER:  10-30% filtered output (useful parts only)
```
