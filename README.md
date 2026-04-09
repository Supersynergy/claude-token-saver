```
 ██████╗████████╗███████╗
██╔════╝╚══██╔══╝██╔════╝
██║        ██║   ███████╗   Universal Agent Token Saver
██║        ██║   ╚════██║   ⚡ Speed or 💰 Savings — Adaptive.
╚██████╗   ██║   ███████║   Every CLI. Every Model.
 ╚═════╝   ╚═╝   ╚══════╝
```

**The right model for every task. Every CLI. Every budget.**

```bash
curl -fsSL https://raw.githubusercontent.com/Supersynergy/universal-token-saver/main/install-universal.sh | bash
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

## Adaptive Model Selection

Wähle das optimale Modell basierend auf:

| Factor | Decision |
|--------|----------|
| API-Key/Provider | MiniMax = ⚡ Speed, Claude = 💰 Savings |
| Task-Komplexität | Simple → Fast, Complex → Smart |
| Geschwindigkeitsanforderung | High → Schnellster Provider |
| Code-Qualität | Draft → Schnell, Production → Qualität |

---

## Provider Comparison

| Provider | Model | Speed | Cost/M | Token Savings | Best For |
|----------|-------|-------|--------|--------------|----------|
| **MiniMax** | M2.7 | ⚡⚡⚡⚡⚡ | $0.05 | **Keine nötig** | High-Volume, Speed |
| **Google** | Gemini 3 Flash | ⚡⚡⚡⚡ | $0.07 | Minimal | Quick Tasks |
| **Google** | Gemini 3 Pro | ⚡⚡⚡ | $1.00 | 60% | Complex Reasoning |
| **Anthropic** | Claude 3.5 Sonnet | ⚡⚡⚡ | $3.00 | **60-90%** | Production Code |
| **Anthropic** | Claude 3.5 Opus | ⚡⚡ | $15.00 | **60-90%** | Architecture |
| **OpenAI** | GPT-4o | ⚡⚡⚡ | $2.50 | **60-90%** | General Tasks |
| **Moonshot** | Kimi K2.5 | ⚡⚡⚡⚡ | $0.50 | Minimal | Code Generation |
| **DeepSeek** | Coder | ⚡⚡⚡⚡ | $0.14 | Minimal | Code Completion |

---

## Supported CLI Agents

> Same savings. Every CLI. Every model.

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
curl -fsSL https://raw.githubusercontent.com/Supersynergy/universal-token-saver/main/install-universal.sh | bash
```

### 2. Check Your Model

```bash
uts check
# Output:
# {
#   "model": "minimax-m2.7",
#   "provider": "MiniMax",
#   "enableTokenSavings": false,
#   "reason": "Fast provider - no token savings needed"
# }
```

### 3. Adaptive Select

```bash
# Quick task → Fastest model
uts select simple fastest

# Production code → Best quality
uts select complex balanced 50000 production

# Exploration → Fast + cheap
uts select simple fast 10000 draft
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
│      │       └─→ YES → Claude 3.5 Sonnet 💰           │
│      │                                                  │
│      ├─→ Complexity = "complex"?                       │
│      │       └─→ YES → Claude 3.5 Opus 💰             │
│      │                                                  │
│      └─→ Default → Gemini 3 Flash ⚡                   │
└─────────────────────────────────────────────────────────┘
```

### 💰 Provider-Based Token Savings

| Provider | Strategy | Why |
|----------|----------|-----|
| MiniMax | **None** | $0.05/M = billig, Geschwindigkeit > Effizienz |
| Google | Minimal | $0.07-1.25/M = moderat |
| Anthropic | **Full** | $3-15/M = teuer, Token-Sparen lohnt sich |
| OpenAI | **Full** | $2.50-75/M = teuer, Token-Sparen lohnt sich |

### 🔧 Multi-CLI Vault System

```
~/.uts/vault/
├── skills/           # Universal skills (CLI-agnostisch)
├── commands/         # CLI-spezifische Commands
└── adapters/        # Einer pro CLI-Tool
    ├── claude.js
    ├── gemini.js
    ├── kilo.js
    └── codex.js
```

---

## `/uts` Commands

| Command | Description |
|---------|-------------|
| `/uts check` | Prüfe aktuelles Modell & Strategie |
| `/uts select` | Adaptives Model Selection |
| `/uts strategy` | Zeige Provider-Strategie |
| `/uts list` | Alle verfügbaren Modelle |
| `/uts agents` | Zeige installierte CLI-Agenten |
| `/uts install` | UTS für CLI installieren |
| `/uts dashboard` | Multi-Agent Token Dashboard |
| `/uts upgrade` | Update auf latest |

---

## RTK Universal — 60-90% CLI Compression

> Für teure APIs (Claude, OpenAI) — optional für schnelle APIs

### Automatic Hook

```bash
# RTK Universal erkennt den aktiven CLI automatisch
rtk-universal install     # Installiert Hook
rtk-universal wrap <cmd>  # Einzelne Command komprimieren
rtk-universal stats       # Savings anzeigen
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

### Output Filter

| CLI | Noise Removed | Savings |
|-----|---------------|---------|
| git | Merging, fast-forward, remote: | 70% |
| npm | `added X packages`, warnings | 85% |
| pytest | `passed X tests`, platform info | 85% |
| docker | `Pulling from layer`, Digest | 90% |

---

## Installation

### Auto-Detection + Full Install

```bash
curl -fsSL https://raw.githubusercontent.com/Supersynergy/universal-token-saver/main/install-universal.sh | bash
```

### CLI-Specific

```bash
# Nur Gemini CLI
curl -fsSL ... | bash -s -- --adapter=gemini

# Nur Claude Code
curl -fsSL ... | bash -s -- --adapter=claude

# Alle CLIs
curl -fsSL ... | bash -s -- --adapter=all
```

### CLI-Commands

```bash
uts install          # Aktuellen CLI
uts install gemini   # Spezifischen CLI
uts uninstall        # UTS entfernen
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

**MiniMax (Schnellster Provider)**
```json
{
  "provider": "MiniMax",
  "tokenSavings": "none",
  "cacheStrategy": "disabled",
  "batchStrategy": "never",
  "recommendedModel": "minimax-m2.7"
}
```

**Anthropic (Teuerste Option)**
```json
{
  "provider": "Anthropic",
  "tokenSavings": "full",
  "cacheStrategy": "aggressive",
  "batchStrategy": "always",
  "recommendedModel": "claude-3.5-sonnet"
}
```

---

## Architecture

```
universal-token-saver/
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

## Token Math

### Expensive API (Claude)

```
Before UTS:  ~35,000 tokens/session overhead
After UTS:   ~4,000  tokens/session overhead
Savings:     ~31,000 tokens/session

At 1,000 sessions/month:  31M tokens saved
At Sonnet pricing ($3/M):  ~$93/month saved
At Opus pricing  ($15/M): ~$465/month saved
```

### Fast API (MiniMax)

```
Token-Sparmaßnahmen: NICHT AKTIVIERT
Grund: $0.05/M tokens = Zeitverschwendung zu sparen

Instead: Nutze MiniMax M2.7 für 300x günstigere Speed-Tasks
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

## Requirements

- Node.js ≥ 16
- Python 3.8+ (optional, für Stats)
- macOS / Linux / WSL
- Einen oder mehr CLI Coding Agents installiert

---

## Upgrade

```bash
uts upgrade
# oder
curl -fsSL https://raw.githubusercontent.com/Supersynergy/universal-token-saver/main/install-universal.sh | bash
```

---

## Rollback

```bash
bash ~/.uts-backup-YYYYMMDD-HHMMSS/restore.sh
```

---

## Links

- **GitHub**: [github.com/Supersynergy/universal-token-saver](https://github.com/Supersynergy/universal-token-saver)
- **Docs**: [UTS.md](./UTS.md)
- **Best Practices**: [BEST_PRACTICES.md](./BEST_PRACTICES.md)

---

**Made with obsession for developer efficiency.**
⚡ Speed or 💰 Savings — You Choose.
