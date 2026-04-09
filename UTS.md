---
name: uts
description: >-
  Universal Agent Token Saver + Adaptive Model Selector. Wählt das optimale Modell
  basierend auf API-Key/Provider, Task-Komplexität und Geschwindigkeitsanforderungen.
  Bei MiniMax M2.7 Highspeed → keine Token-Sparmaßnahmen (Geschwindigkeit vor Effizienz).
  Bei Claude/Sonnet → volle Token-Optimierung aktiviert. Multi-CLI Support: Claude Code,
  Gemini CLI, Kilo, Codex, Kimi, OpenCode. Auto-detectiert aktiven CLI-Agent.
argument-hint: "[check | select | strategy | list | install | agents]"
allowed-tools: [Bash, Read]
model: haiku
---

# Universal Agent Token Saver (`/uts`)

**Adaptive Model Selection** — Das richtige Modell für die Aufgabe, nicht das teuerste.

## Core Philosophy

```
Schnelle API (MiniMax M2.7) → Geschwindigkeit vor Effizienz
Teure API (Claude/Sonnet)    → Volle Token-Optimierung
```

---

## Provider-Übersicht

| Provider | Model | Speed | Token Savings | Use Case |
|----------|-------|-------|---------------|----------|
| **MiniMax** | M2.7 | ⚡⚡⚡⚡⚡ | Keine nötig | High-Volume, Speed |
| **Google** | Gemini 3 Flash | ⚡⚡⚡⚡ | Minimal | Quick Tasks |
| **Anthropic** | Claude 3.5 Sonnet | ⚡⚡⚡ | Voll | Production Code |
| **OpenAI** | GPT-4o | ⚡⚡⚡ | Voll | General Tasks |
| **Moonshot** | Kimi K2.5 | ⚡⚡⚡⚡ | Minimal | Code Generation |
| **DeepSeek** | Coder | ⚡⚡⚡⚡ | Minimal | Code Completion |

---

## `/uts check` — Prüfe Modell-Strategie

```bash
uts check minimax-m2.7
uts check claude-3.5-sonnet
```

**Output:**
```json
{
  "model": "minimax-m2.7",
  "provider": "MiniMax",
  "speed": "fastest",
  "enableTokenSavings": false,
  "reason": "Provider is fast - no token savings needed"
}
```

---

## `/uts select` — Adaptives Model Selection

```bash
uts select simple fastest 10000 draft
uts select complex balanced 50000 production
uts select medium fast 30000 draft
```

**Parameter:**
- `complexity`: `simple` | `medium` | `complex`
- `speed`: `fastest` | `fast` | `balanced` | `slow`
- `contextNeeded`: number (tokens)
- `codeQuality`: `draft` | `production`

---

## `/uts strategy` — Provider-Strategie

```bash
uts strategy Anthropic
uts strategy MiniMax
uts strategy Google
```

**Output:**
```json
{
  "provider": "MiniMax",
  "tokenSavings": "none",
  "cacheStrategy": "disabled",
  "batchStrategy": "never",
  "recommendedModel": "minimax-m2.7"
}
```

---

## `/uts list` — Alle verfügbaren Modelle

```bash
uts list
```

**Output:**
```
Available Models:

MiniMax:
  ⚡ MiniMax M2.7 (fastest)
  ⚡ MiniMax M2 (fast)

Google:
  ⚡ Gemini 3.0 Flash (fastest)
  💰 Gemini 3.0 Pro (balanced)
  ⚡ Gemini 2.5 Flash (fast)
  💰 Gemini 2.5 Pro (balanced)

Anthropic:
  💰 Claude 3.5 Haiku (fast)
  💰 Claude 3.5 Sonnet (balanced)
  💰 Claude 3.5 Opus (slow)
  💰 Claude 3.7 Sonnet (balanced)

OpenAI:
  💰 GPT-4o (fast)
  💰 GPT-4.5 (balanced)
```

---

## Adaptive Rules

```bash
uts rules
```

| Trigger | Condition | Model | Reason |
|---------|-----------|-------|--------|
| `quick-exploration` | simple + fast | MiniMax M2.7 | Schnellste Option |
| `code-exploration` | draft quality | Gemini 3 Flash | Schnell + Günstig |
| `production-code` | production quality | Claude 3.5 Sonnet | Beste Qualität |
| `architecture` | complex | Claude 3.5 Opus | Maximale Reasoning |
| `high-volume` | fastest required | MiniMax M2.7 | Höchster Durchsatz |

---

## Multi-CLI Support

```bash
uts agents           # Zeigt alle installierten CLI-Agenten
uts install gemini   # Installiert UTS für Gemini CLI
uts install claude   # Installiert UTS für Claude Code
uts install kilo     # Installiert UTS für Kilo/Code
uts dashboard        # Multi-Agent Token Dashboard
```

**Unterstützte CLI-Agenten:**

| Agent | Icon | Detection Path |
|-------|------|----------------|
| Claude Code | 🦙 | `~/.claude/` |
| Gemini CLI | ✨ | `~/.gemini/` |
| Kilo/Code | ⚡ | `~/.local/share/kilo/` |
| OpenCode | ⚡ | `~/.local/share/opencode/` |
| Codex CLI | 🔮 | `~/.codex/` |
| Kimi Code | 🌙 | `~/.kimi/` |
| OpenClaw | 🦞 | `~/.openclaw/` |

---

## Installation

```bash
# Auto-Detection + Full Install
curl -fsSL https://raw.githubusercontent.com/Supersynergy/universal-token-saver/main/install-universal.sh | bash

# CLI-spezifisch
curl -fsSL ... | bash -s -- --adapter=gemini
curl -fsSL ... | bash -s -- --adapter=claude

# Update
uts upgrade
```

---

## Config (`~/.uts/config.json`)

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
  },
  "autoSelect": {
    "enabled": true,
    "rules": ["complexity", "speed", "context"]
  }
}
```

---

## Token Savings by Provider

| Provider | Strategy | Savings |
|----------|----------|---------|
| MiniMax | Keine nötig | 0% overhead |
| Google | Minimal | 10% overhead |
| Anthropic | Voll | 60-90% savings |
| OpenAI | Voll | 60-90% savings |

**Begründung:** Bei $0.05/M tokens (MiniMax) vs $15/M tokens (Claude Opus) sind Token-Sparmaßnahmen bei MiniMax Zeitverschwendung. Die Zeit die man spart ist mehr Wert als die Tokens.

---

## Quick Commands

```
/uts check          — Prüfe aktuelles Modell
/uts select simple  — Wähle Modell für einfache Task
/uts strategy       — Zeige Provider-Strategie
/uts list           — Alle Modelle
/uts agents         — Installierte CLIs
/uts install        — UTS installieren
/uts dashboard      — Token Dashboard
/uts upgrade        — Update auf latest
```

---

## Model Selection Decision Tree

```
Task gestartet
    │
    ├─→ Speed = "fastest"?
    │       │
    │       └─→ YES → MiniMax M2.7 ⚡
    │
    ├─→ Code Quality = "production"?
    │       │
    │       └─→ YES → Claude 3.5 Sonnet 💰
    │
    ├─→ Complexity = "complex"?
    │       │
    │       └─→ YES → Claude 3.5 Opus 💰
    │
    └─→ Default → Gemini 3 Flash ⚡
```

**Schnelle Entscheidung für 80% der Tasks:**
- Quick Fix → MiniMax M2.7
- Exploration → Gemini 3 Flash
- Production → Claude 3.5 Sonnet
