# Universal Token Saver — Multi-CLI Adapter Plan

## Research Results: Die 10+ wichtigsten CLI Coding Agents

| Tool | Repo | Tracking | Status |
|------|------|----------|--------|
| **Claude Code** | `@anthropic-ai/claude-code` | ✅ `.claude/projects/` | Bereits unterstützt |
| **Gemini CLI** | `google-gemini/gemini-cli` | ✅ `.gemini/tmp/*/chats/` | Zu unterstützen |
| **Kilo/Code** | `Kilo-Org/kilocode` | ✅ SQLite DB | Zu unterstützen |
| **OpenCode** | OpenCode (Kilo-basierte) | ✅ SQLite + SQLite | Zu unterstützen |
| **Codex CLI** | `openai/codex` | ✅ `.codex/sessions/` | Zu unterstützen |
| **Kimi Code** | `MoonshotAI/kimi-cli` | ✅ Agent Tracing | Zu unterstützen |
| **OpenClaw** | Clawdbot/Moltbot | ✅ `.openclaw/agents/` | Zu unterstützen |
| **Hermes Agent** | Hermes | ✅ `state.db` | Zu unterstützen |
| **Cursor IDE** | Cursor | ✅ API sync | IDE-spezifisch |
| **Factory Droid** | Droid | ✅ `~/.droid/` | Zu unterstützen |

**Bestehende Lösungen:**
- **Tokscale** (junhoyeo/tokscale) — 1.7k stars, nur Tracking, keine Optimierung
- **token-saver.ai** — Output compression, aber proprietär
- **OpenCode Monitor** — nur OpenCode

---

## Ziel

**Universal Token Saver (UTS)** — eine gemeinsame Basis, die alle Coding Agents mit denselben Optimierungs-Layern versorgt:

```
Layer 0: Vault Pattern (0 Startup)
Layer 1: RTK CLI Compression (60-90%)
Layer 2: Smart Context Batching
Layer 3: Token-Aware Output Filtering
Layer 4: Multi-Agent Dashboard
```

---

## Architektur: Plugin-Adapter System

```
universal-token-saver/
├── core/
│   ├── vault.ts              # Universal vault pattern
│   ├── rtk.ts                # RTK bash compression
│   ├── context-batcher.ts    # Multi-command batching
│   └── output-filter.ts      # Noise reduction
├── adapters/
│   ├── claude-code.ts        # Bestehend
│   ├── gemini-cli.ts         # NEU: Parse .gemini/tmp/
│   ├── kilo-code.ts          # NEU: Parse SQLite DB
│   ├── opencode.ts           # NEU: Parse opencode.db
│   ├── codex.ts              # NEU: Parse .codex/sessions/
│   ├── kimi-cli.ts           # NEU: Parse Agent Tracing
│   └── openclaw.ts          # NEU: Parse .openclaw/
├── cli/
│   └── uts.ts                # Universal CLI Interface
└── plugins/
    ├── rtk-hook/             # PreToolUse hooks
    └── output-proxy/         # CLI output interception
```

---

## Implementierung: Schritt-für-Schritt

### Phase 1: Core Engine (Abstraktion)

**1.1 Universal Adapter Interface**
```typescript
interface CLIAdapter {
  name: string;
  configDir: string;
  sessionPattern: string;
  parseTokens(sessionPath: string): TokenUsage;
  getHistory(days: number): Session[];
  installHook(): void;  // PreToolUse equivalent
  getSavings(): SavingsReport;
}
```

**1.2 Token-Aware Output Filter**
- Intercept CLI output VOR zum LLM
- Pattern: verbose logs, passing tests, progress bars
- Kompression: 70-95% Output-Reduktion
- Adaptiv pro CLI-Tool

### Phase 2: Adapter für jeden CLI-Agent

**2.1 Gemini CLI Adapter**
```bash
# Tracking Location
~/.gemini/tmp/*/chats/*.json

# Telemetry Support
gen_ai.client.token.usage (OpenTelemetry)
```

**2.2 Kilo/Code + OpenCode Adapter**
```bash
# SQLite DB
~/.local/share/opencode/opencode.db

# Tracking
- input_tokens, output_tokens per request
- model, provider, cost
- session, agent, timestamp
```

**2.3 Codex CLI Adapter**
```bash
# Session Storage
~/.codex/sessions/

# Parse session files for token usage
```

**2.4 Kimi Code Adapter**
```bash
# Agent Tracing
~/.kimi/  # oder app-specific

# Telemetry via kimi-vis
```

### Phase 3: Universal Vault System

**3.1 Unified Skills Vault**
```
~/.uts/vault/
├── skills/           # Universelle Skills (CLI-agnostisch)
├── commands/         # CLI-spezifische Commands
└── agents/           # Agent-Definitionen
```

**3.2 Adapter-spezifische Overrides**
```
~/.uts/adapters/
├── claude/           # Claude-spezifische Skills
├── gemini/           # Gemini-spezifische
├── kilo/             # Kilo/OpenCode-spezifische
└── ...
```

### Phase 4: RTK Universal (CLI Compression)

**4.1 Tool-Agnostische Commands**
```typescript
const RTK_UNIVERSAL = {
  git: { compress: true, ultra: '-u' },
  npm: { compress: true, ultra: '--omit=dev' },
  docker: { compress: true, patterns: verboseLogs },
  pytest: { compress: true, keep: ['FAILED', 'ERROR'] },
  cargo: { compress: true },
  kubectl: { compress: true },
  terraform: { compress: true }
};
```

**4.2 Auto-Detection des aktiven CLI**
```bash
# Detektiere aktiven CLI-Agent
if [ -n "$CLAUDE_DIR" ]; then echo "claude"
elif [ -d "$HOME/.gemini" ]; then echo "gemini"
elif [ -f "$HOME/.local/share/opencode/opencode.db" ]; then echo "opencode"
elif [ -d "$HOME/.codex" ]; then echo "codex"
fi
```

### Phase 5: Output Proxy (Universal)

**5.1 CLI Output Interception**
```typescript
// Universal proxy für alle CLI outputs
class OutputProxy {
  intercept(command: string, output: string): string {
    const patterns = this.getNoisePatterns(this.detectCLI());
    return this.filter(output, patterns);
  }
}
```

**5.2 Noise Patterns pro Tool**
```typescript
const NOISE_PATTERNS = {
  git: [/^Merging|^Auto-merging|^CONFLICT/, ...],
  npm: [/^added \d+ packages/, /^found \d+ vulnerabilities/, ...],
  pytest: [/^=+ \d+ passed/, /^platform \w+/, ...],
  docker: [/^Unable to find image/, /^Pulling from/, ...]
};
```

---

## Dashboard: Multi-Agent Overview

```bash
uts dashboard

╔═══════════════════════════════════════════════════╗
║     Universal Token Saver — Multi-Agent View       ║
╠═══════════════════════════════════════════════════╣
║  Agent          Sessions  Input     Output    Cost ║
╠═══════════════════════════════════════════════════╣
║  Claude Code    127       45.2M     12.1M     $187 ║
║  Gemini CLI      89       31.8M      8.4M     $52 ║
║  Kilo/Code       54       18.9M      5.2M     $38 ║
║  OpenCode        23        7.2M      2.1M     $14 ║
║  Codex CLI       12        3.4M        890K    $7 ║
╠═══════════════════════════════════════════════════╣
║  TOTAL          305      106.5M    28.6M    $298 ║
╠═══════════════════════════════════════════════════╣
║  Savings:                                       ║
║  • Vault Pattern:     2.1M tokens               ║
║  • RTK Compression:   4.8M tokens               ║
║  • Output Filtering:  1.9M tokens               ║
║  ─────────────────────────────────────────────   ║
║  Total Saved:        8.8M tokens = ~$26/mo      ║
╚═══════════════════════════════════════════════════╝
```

---

## Install: Universal Installer

```bash
# Universal install
curl -fsSL https://raw.githubusercontent.com/Supersynergy/universal-token-saver/main/install.sh | bash

# Oder CLI-spezifisch
curl -fsSL https://raw.githubusercontent.com/Supersynergy/universal-token-saver/main/install.sh | bash --adapter=gemini
curl -fsSL https://raw.githubusercontent.com/Supersynergy/universal-token-saver/main/install.sh | bash --adapter=kilo
curl -fsSL https://raw.githubusercontent.com/Supersynergy/universal-token-saver/main/install.sh | bash --adapter=codex
```

---

## Nächste Schritte

1. **Core Engine** → Abstraktes Adapter-Interface
2. **Vault Pattern** → Universalisieren
3. **RTK** → Auf alle CLIs anwendbar machen
4. **Output Proxy** → Universal Noise Filter
5. **Adapter schreiben** → Pro CLI-Tool einen Adapter
6. **Dashboard** → Multi-Agent Overview
7. **Migration** → Von CTS zu UTS

---

## Dateien zu ändern

| Datei | Änderung |
|-------|----------|
| `install.sh` | Multi-Adapter Support + Auto-Detection |
| `cts.md` | UTS.md → universalisieren |
| `RTK.md` | RTK Universal → alle CLIs |
| `BEST_PRACTICES.md` | Multi-Agent Best Practices |
| `README.md` | Universal positioning |
| `build-skills-index.py` | Multi-Adapter Index |
