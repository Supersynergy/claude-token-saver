# SUPER BEST PRACTICES — Programmieren mit Claude Code 2.1.126
**Datum**: 2026-05-03 · **Stack**: Opus 4.7 / Sonnet 4.6 / Haiku 4.5 · **Quellen**: [cc-bestpractices](2026-05-03-cc-bestpractices.md) · [tools-and-rss](2026-05-03-tools-and-rss.md) · [local-arsenal](2026-05-03-local-arsenal.md) · prior: `cc_best_practices_2184.md` (37d) + `feedback_cc_optimization.md` (50d)

---

## §0 SETTINGS-BASELINE (aus prior optimization, weiterhin gültig)

**settings.json HARD-Defaults** (live seit 2026-03-26):
```json
{
  "includeGitInstructions": false,        // -2K tok system prompt (eigene git-rules in CLAUDE.md)
  "companyAnnouncements": false,          // 0 startup noise
  "spinnerTipsEnabled": false,            // 0 spinner tips in context
  "env": {
    "CLAUDE_CODE_SUBPROCESS_ENV_SCRUB": "1"  // strip API keys from subprocess env (security)
  },
  "permissions": {
    "defaultMode": "plan",
    "allow": ["Bash(git *)", "Bash(rtk *)", "Bash(bd *)", "Bash(mise *)",
              "Bash(cargo *)", "Bash(bun *)", "Bash(hermes *)", "Bash(leads *)",
              "Bash(npm *)", "Bash(rg *)", "Bash(fd *)", "Bash(fzf *)", "Bash(bat *)"]
  }
}
```

**Hooks-Hygiene** (per-tool overhead = death):
- ❌ KEINE `npx <thing>` PreToolUse/PostToolUse Hooks (spawnte Node JEDES tool call → 2-5K tok + 500ms)
- ❌ KEIN `gsd-context-monitor.js` PostToolUse (redundant)
- ❌ KEIN `surreal-pretool-inject.sh` PreToolUse (nur SessionStart braucht context-inject)
- ✅ Telegram Stop hook: `async: true`
- ✅ SurrealDB Stop hook: `async: true`
- ✅ SubagentStop: `async: true` (non-blocking)

**Effort default**: `low` (NICHT high, override Anthropic 2.1.117 default). Use `ultrathink` keyword für high-effort turn.

**Memory hard caps**:
- `MEMORY.md` < 200 lines (index ONLY, details in topic files)
- Auto-compact at 25KB AND 200 lines (CC built-in)

**Model routing (strict)**:
- Haiku 4.5 → subagents, exploration, file search, bash ops
- Sonnet 4.6 → code writing, plan review (daily driver)
- Opus 4.7 → architecture decisions ONLY
- ❌ `/fast` NEVER (zu teuer, prior decision steht)

**Context hygiene**:
- `/compact <focus>` wenn Context füllt (focus = topic, NICHT generic)
- `/clear` zwischen unrelated tasks
- Specialized workflows → Skills (load on demand, NICHT in CLAUDE.md)

---

## §1 GOLDEN STACK (top of funnel — alle Sessions)

```
Voice (Whisper Metal)
    ↓
uda ask  → syn hybrid (8ms local KB, 161k chunks)
    ↓ miss?
super-research --count 30 (parallel ingest 20 engines + batch-md-rs)
    ↓
SPEC.md (NEW chat, interview edges)
    ↓
/plan → user approve → acceptEdits OR auto mode
    ↓
worktree fanout (3 approaches parallel) — Haiku tier
    ↓
gsd-executor per worktree (atomic commits + checkpoints)
    ↓
verification-loop  (Build→Types→Lint→Tests→Security→Diff)
    ↓
master-check (parallel dashboard, alle audits)
    ↓
rtk gh pr create  → /ultrareview <PR#>  (cloud multi-agent)
    ↓
syn put (durable learning)  +  omega_store (decision)
```

---

## §2 NEUE 2.1.x KILLER-FEATURES (must-use ab heute)

| Feature | Wann | Wert |
|---|---|---|
| `/loop [prompt]` ohne Intervall | rekurrierende Wartung, Build-Watch | self-paced via Monitor → token-cheap, 7d Expiry |
| `/ultrareview <PR#>` (+ CLI `claude ultrareview --json`) | jede PR vor Merge | parallele Multi-Agent Review, CI-fähig (exit 1) |
| `/ultraplan` | komplexe Specs > 3 Files | Cloud-Plan, Browser-Review, "Refine"-Link |
| ~~`/fast`~~ | **NEVER** (prior decision) | zu teuer, kein guter Trade |
| `/tui fullscreen` | lange Sessions, viel Tool-Use | flat memory, kein Flicker, alt-screen |
| `/btw` | Side-Frage ohne Context-Bloat | Antwort NICHT in History |
| `Esc Esc → Summarize from here` | Mid-Session Compact | erhält Early Context |
| Auto-Mode (`permissions.defaultMode=auto`) | bekannt-sichere Scopes | classifier blockt Eskalation; **chat-Boundaries gehen bei compact verloren → für Hardgrenze `deny` rules** |
| Agent Teams (`/agents`) | konkurrierende Hypothesen, Cross-Layer (FE/BE/Tests) | shared task list, jeder Teammate eigener Context. NUR wenn unabhängig — sonst Subagents |
| Channels (research preview) | inbound Push (Telegram/Discord/iMessage) | reaktive Sessions, allowlist-gated |
| Remote Control + Mobile Push | Phone-continue laufender Session | outbound HTTPS only, kein Inbound-Port |
| Skills mit `${CLAUDE_EFFORT}` | effort-aware Verhalten | Skill passt sich an low/med/high/xhigh an |
| `/reload-plugins` | Skills/MCP/Hooks Hot-Reload | kein Restart |
| Subagent stall fail @ 10min | seit 2.1.126 | kein silent hang mehr — schnelles Re-Try |

---

## §3 MEINE TOP-COMBOS (Skills × Stack)

**1. SPEC FANOUT VERIFY** (höchster Hebel)
```
gsd-roadmapper → SPEC.md
  → 3× rtk git worktree add ../proj-{a,b,c}
  → 3× Agent (subagent_type=implementer) parallel im einer message
  → verification-loop pro Worktree
  → master-check Diff aller 3
  → merge winner, delete losers
```

**2. RESEARCH→PATTERN→IMPL**
```
super-research "<topic>" --count 50
  → grepgod find-patterns (ast-grep + comby)
  → gsd-codebase-mapper
  → SPEC.md
  → gsd-executor
```

**3. STEALTH FETCH→INDEX→REFACTOR**
```
hyperfetch --stage camoufox <url>     # 0.07s Cloudflare
  → ctx_fetch_and_index
  → ctx_search "<term>"
  → grepgod ast-rewrite
```

**4. SKILL-AS-MCP DISPATCH**
```
qdrant-os-allskills MCP (300+ skills, 0 token bis Invoke)
  → semantic match → load only winner
  → parallel agents via dmux
```

**5. SPEC-DRIVEN PLUS ULTRA**
```
/ultraplan (cloud, browser-refine)
  → claude --worktree fix-auth
  → /agents team (FE + BE + Tests parallel)
  → verification-loop
  → /ultrareview --json | jq '.findings'
  → rtk git push
```

**6. VOICE→SPEC→PR** (3× Tippspeed)
```
Whisper Metal (lokal) → dictate intent
  → SPEC.md
  → /plan → accept
  → gsd-executor + verification-loop
  → /ultrareview → PR
```

---

## §4 NEUE TOOLS — TOP-10 SOFORT INSTALLIEREN (Mai 2026)

Vollständige 50er-Liste in [tools-and-rss.md](2026-05-03-tools-and-rss.md). Quick-wins:

| # | Tool | Use | Install |
|---|---|---|---|
| 1 | **prek** | 10× pre-commit (Rust) | `cargo install prek` |
| 2 | **ty** (Astral) | mypy/pyright Killer, 50-200× | `uv add ty --dev` |
| 3 | **OpenCode** | Terminal-Agent, 70+ LLMs | `npm i -g @opencode/cli` |
| 4 | **zizmor** | GH Actions Static-Analyzer | `cargo install zizmor` |
| 5 | **OpenObserve** | ELK+Loki+Tempo Replacement, 140× günstiger | docker |
| 6 | **kingfisher** | MongoDB Secret-Scanner, schneller als gitleaks | `cargo install kingfisher` |
| 7 | **gitu** | Magit-style TUI Git (Rust) | `cargo install gitu` |
| 8 | **Limbo** | Async SQLite-Rewrite + vec built-in | `cargo install limbo` |
| 9 | **Pkl** | typed config (Apple), YAML/Jsonnet Killer | `brew install pkl` |
| 10 | **Atuin 18** | Shell-History Sync E2E-encrypted | `brew install atuin` |

---

## §5 RSS — TOP 1000 GITHUB RELEASES

**Empfehlung**: **newreleases.io Pro** ($10/mo, unlimited) → Webhook → eigenes **miniflux** self-host

```
newreleases.io (1000 repos: GH+GitLab+npm+PyPI+crates+Docker+Helm)
    ├─→ Telegram channel "releases"  (instant)
    ├─→ Email Daily-Digest 08:00
    └─→ Webhook → miniflux self-host
                     ↓
            miniflux-digest skill
                     ↓
            Obsidian + Synapse Index
```

Setup: bulk OPML Import via REST API (`/v1/projects`). Fallback ohne SaaS: miniflux + `gh-releases-bridge` (rss-bridge fork) + cron.

---

## §6 TOKEN-RULES (kosten-optimiert)

1. **Tier-Ladder**: Haiku=explore → Sonnet=code → Opus=arch only. Bandit auto via `core/orchestrator.py`
2. **RTK prefix immer** — 60-90% savings auf git/build/test
3. **ctx_batch_execute** statt 2+ Bash → 1 round-trip statt N
4. **syn hybrid 8ms** vor jedem Web-Fetch
5. **Skills progressive disclosure** — nur `description` always-loaded
6. **Subagents = isolated context** → main bleibt frei
7. **/btw** für Side-Fragen — geht NICHT in History
8. **/compact <focus> @ 60%** — nicht erst bei 90%, cache-hits bleiben warm
9. **/loop ohne Intervall** — Monitor tool, kein Polling
10. **`/fast` NIE** — prior decision, zu teuer
11. **effort=low default**, `ultrathink` keyword nur für komplexe turns
12. **NPX-Hooks killen** — pro tool call 2-5K tok + 500ms overhead
13. **Stop-Hooks `async: true`** — blockiert sonst exit

---

## §7 PROJEKT-ERFOLGS-REGELN (was = "erfolgreiches Projekt")

### A. ENTRY (jede Task)
- [ ] CLAUDE.md + sub-CLAUDE.md gelesen
- [ ] `uda ask "<keywords>"` ausgeführt
- [ ] `know.py broken` check
- [ ] Wenn > 3 Files → SPEC.md + NEW chat
- [ ] Context > 70% → `/clear` + 3-Zeilen Handoff
- [ ] OMEGA welcome + protocol

### B. PLAN
- [ ] Edges interviewed (kein "ich nehm an")
- [ ] SPEC.md geschrieben + reviewed
- [ ] `/plan` mode, approve EINMAL, dann `acceptEdits`
- [ ] Worktree fanout wenn Approach unklar
- [ ] Cost-Schätzung pro Tier (Haiku/Sonnet/Opus)

### C. EXECUTE
- [ ] `rtk` prefix auf JEDEM Bash
- [ ] `bun` statt npm/yarn/pnpm; `uv` statt pip; `cargo nextest` statt cargo test
- [ ] Mining-first: ghgrep + steal + minimal-adapt VOR scratch
- [ ] Subagents parallel wenn unabhängig (1 message, N Agent calls)
- [ ] Atomic commits per logical unit
- [ ] Checkpoints (`Esc Esc`) vor riskanten Changes

### D. VERIFY (HARD-GATE — alle ✅)
- [ ] `tsc --noEmit` 0 errors
- [ ] `biome lint` 0 warnings (oder ruff/clippy)
- [ ] `bun test --bail` green
- [ ] `bun run build` success
- [ ] `cargo nextest run` green (Rust)
- [ ] `semgrep --config=auto` clean
- [ ] `gitleaks` no findings
- [ ] `verification-loop` 6/6 ✅
- [ ] `master-check` dashboard alles grün

### E. SECURITY
- [ ] `smac-secscan .`
- [ ] husky pre-commit Biome aktiv
- [ ] Auto-Mode `deny` rules für irreversible Ops (rm -rf, force-push, DROP)
- [ ] Bash deny matched env/sudo/watch/ionice/setsid wrappers
- [ ] OAuth/Secrets nicht in commit (gitleaks)

### F. SHIP
- [ ] `claude ultrareview --json` exit 0
- [ ] Conventional Commit Message (`fix:` `feat:` `refactor:` …) mit Issue-Ref `#NNN`
- [ ] PR Description aus SPEC.md generiert
- [ ] CI grün
- [ ] OMEGA `omega_store(content, "decision")` min 1 pro Session
- [ ] Synapse `syn put` für durable learning

### G. POST
- [ ] `rtk gain` Token-Savings Check
- [ ] Telepathy update (cross-session sync)
- [ ] Skill/Tool-Lessons → `feedback_*.md` memory
- [ ] Project memory updated wenn Scope/Deadline changed

---

## §8 ANTI-PATTERNS (NIEMALS)

- ❌ npm/yarn/pnpm new project · pip/poetry/pipx · ESLint+Prettier · Webpack/Babel · Jest · Selenium · Heroku · Datadog · ChromaDB · Pinecone · LangChain · SurrealDB-prod · Mongo · Firebase · Clerk · Auth0 · Vercel-prod · Qwen models
- ❌ Agent für simple Lookup (use Read/Grep direkt)
- ❌ WebFetch unknown site (use hyperfetch)
- ❌ rtk ls/grep/env/read (overhead +35-10000%)
- ❌ `cat` via Bash (use Read)
- ❌ raw `find -name` (use fd)
- ❌ Implementation ohne SPEC bei > 3 Files
- ❌ Force-push ohne user confirm
- ❌ Auto-Mode mit chat-Boundaries als Sicherheit (compact = lost)
- ❌ Agent Teams für sequential/same-file work (use Subagents)
- ❌ `/fast` überhaupt (prior decision NEVER)
- ❌ `npx <thing>` in PreToolUse/PostToolUse Hooks (pro-call Overhead)
- ❌ Synchronous Stop hooks (blockt exit)
- ❌ effort=high als Default (override → low, ultrathink für complex)
- ❌ Settings ohne `includeGitInstructions:false` (verschwendet 2K tok wenn eigene git-rules)
- ❌ Mocks in Integration-Tests (lessons learned)

---

## §9 QUICK-START NEXT SESSION

```bash
omega_welcome && omega_protocol           # memory briefing
uda ask "<keywords>"                       # local KB
rtk gain --history                         # token savings check
rtk skill-health                           # 3 new skills present?
/context-budget                            # window usage
/plan                                      # plan mode default
```

---

## §10 DAILY HABIT (5 min/Tag)

1. `tail ~/.claude/logs/ggcoder-autopatch.log`
2. miniflux digest top-3 releases (via newreleases.io webhook)
3. `syn timeline 24h` — was ist passiert
4. `omega_call(tool='omega_reflect', args={topic:'today'})`
5. ein neues Skill/Tool aus §4 testen + bewerten

---

**Erfolg = SPEC frontloaded + Verify-Gate strict + Token-Tier diszipliniert + Mining-first + Memory persistent.**

Files:
- Best practices detail: `~/.claude/research/2026-05-03-cc-bestpractices.md`
- Tools + RSS detail: `~/.claude/research/2026-05-03-tools-and-rss.md`
- Local arsenal detail: `~/.claude/research/2026-05-03-local-arsenal.md`
- Diese Datei: `~/.claude/research/SUPER-BESTPRACTICES-2026-05.md`
