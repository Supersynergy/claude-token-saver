---
name: cts
description: >-
  Claude Token Saver — 60-90% token savings via vault pattern, RTK compression,
  and context-mode. Now with Universal Token Saver (UTS) support for ALL CLI agents:
  Claude Code, Gemini CLI, Kilo, Codex, Kimi. Adaptive model selection based on
  provider speed/cost. Use / cts init for token optimization, / uts for adaptive model selection.
argument-hint: "[init | search <q> | load <name> | list [cat] | auto <intent> | vault <name> | unvault <name> | stats | tokens | rebuild]"
allowed-tools: [Bash, Read, mcp__context-mode__ctx_search, mcp__context-mode__ctx_index, mcp__context-mode__ctx_batch_execute, mcp__context-mode__ctx_execute, mcp__context-mode__ctx_execute_file, mcp__context-mode__ctx_fetch_and_index, mcp__context-mode__ctx_stats, mcp__context-mode__ctx_doctor, mcp__context-mode__ctx_upgrade, mcp__context-mode__ctx_purge]
model: haiku
---

# Claude Skill Manager & Token Saver (`/sm`)

**Index**: `~/.claude/cts.idx` | 5-col TSV: name/cat/desc/path/vault | grep-able, instant
**Catalog**: `~/.claude/skills-catalog.md` | ctx-indexed, BM25 semantic
**Hot dir**: `~/.claude/skills/` — only `sm.md` here (1 skill, ~40 tokens startup)
**Vault dir**: `~/.claude/cts/` — 313 skills cold-stored, 0 startup tokens
**Rule**: NEVER load all skills. grep idx → ctx_search if fuzzy → Read() only the match.

`[V]` = vault skill (not auto-loaded). Still searchable + loadable on demand via `/ cts load`.

---

## Dispatch on `$ARGUMENTS`

Parse the **first word** to select action. Default (no args) → help + stats.

---

### `init` — One command: extreme token savings for this session

Initializes the full token-saving stack:
1. Index key reference docs into context-mode (load once, search many times)
2. Re-index skills catalog for semantic search
3. Show RTK + context-mode savings dashboard

```bash
echo "=== / cts init — Token Stack Initialization ==="
echo ""

# 1. Index skills catalog for ctx_search
echo "→ Indexing skills catalog..."
```

After the bash block, call these MCP tools in sequence:

**Step 1** — `mcp__context-mode__ctx_index`:
- `path: ~/.claude/skills-catalog.md`
- `source: skills-catalog`

**Step 2** — `mcp__context-mode__ctx_index`:
- `path: ~/.claude/RTK.md`
- `source: RTK`

**Step 3** — `mcp__context-mode__ctx_index`:
- `path: ~/.claude/toolstack-2026.md`
- `source: toolstack`

**Step 4** — show savings dashboard:

```bash
IDX="$HOME/.claude/cts.idx"
HOT=$(awk -F'\t' '$5=="0"' "$IDX" | wc -l | tr -d ' ')
VAULT=$(awk -F'\t' '$5=="1"' "$IDX" | wc -l | tr -d ' ')
TOTAL=$(wc -l < "$IDX" | tr -d ' ')

echo ""
echo "=== Token Stack Active ==="
echo ""
echo "LAYER 0 — Vault (startup savings)"
printf "  %-28s %s\n" "Hot skills:" "$HOT (only sm.md)"
printf "  %-28s %s\n" "Vault skills:" "$VAULT cold-stored = 0 startup tokens"
printf "  %-28s %s\n" "Savings vs loading all:" "~$(echo "$VAULT * 40 / 1000" | bc)K tokens/session"
echo ""
echo "LAYER 1 — RTK (Bash compression, auto-active)"
rtk gain 2>/dev/null | grep -E "Tokens saved|commands" | sed 's/^/  /' || echo "  rtk gain for savings"
echo ""
echo "LAYER 2 — context-mode v1.0.75 (98% context reduction)"
echo "  Indexed: skills-catalog | RTK | toolstack"
echo "  10 tools: ctx_batch_execute | ctx_execute | ctx_execute_file"
echo "  ctx_index | ctx_search | ctx_fetch_and_index | ctx_stats"
echo "  ctx_doctor | ctx_upgrade | ctx_purge"
echo ""
echo "LAYER 3 — Decision Matrix"
echo "  2+ Bash commands       → ctx_batch_execute  (986KB→62KB, ~94% savings)"
echo "  Run code (11 langs)    → ctx_execute        (56KB→299B, ~99% savings)"
echo "  Read large file        → ctx_execute_file   (45KB→155B, ~99% savings)"
echo "  Fetch URL/docs         → ctx_fetch_and_index (60KB→40B, ~99% savings)"
echo "  Search indexed docs    → ctx_search          (~200 tokens)"
echo "  Single quick Bash      → RTK hook (auto)     (60-90% savings)"
echo "  Find a skill           → / cts search          (~0 tokens)"
echo ""
echo "Run / cts tokens for full cheatsheet"
```

---

### `search <query>` — Instant grep, 0 tokens

```bash
QUERY="${ARGUMENTS#search }"
IDX="$HOME/.claude/cts.idx"
[ ! -f "$IDX" ] && echo "Index missing. Run: / cts rebuild" && exit 0

echo "=== Skills matching: $QUERY ==="
RESULTS=$(rg -i "$QUERY" "$IDX" 2>/dev/null)

if [ -n "$RESULTS" ]; then
  echo "$RESULTS" | awk -F'\t' '{
    vault = ($5=="1") ? " [V]" : ""
    printf "  /%-28s [%s]%s %s\n", $1, $2, vault, $3
  }' | head -30
else
  echo "No exact match. Fuzzy:"
  for word in $QUERY; do
    rg -i "$word" "$IDX" 2>/dev/null
  done | sort -u | awk -F'\t' '{
    vault = ($5=="1") ? " [V]" : ""
    printf "  /%-28s [%s]%s %s\n", $1, $2, vault, $3
  }' | head -20
  echo ""
  echo "For semantic search: / cts auto $QUERY"
fi
```

---

### `load <name>` — Read one skill on demand (works for hot AND vault skills)

```bash
NAME="${ARGUMENTS#load }"
IDX="$HOME/.claude/cts.idx"

LINE=$(rg "^${NAME}\t" "$IDX" 2>/dev/null | head -1)
[ -z "$LINE" ] && LINE=$(rg -i "^${NAME}" "$IDX" 2>/dev/null | head -1)

if [ -n "$LINE" ]; then
  SKILL_PATH=$(echo "$LINE" | cut -f4)
  IS_VAULT=$(echo "$LINE" | cut -f5)
  [ "$IS_VAULT" = "1" ] && echo "[V] Loading from vault: $SKILL_PATH"
  echo "=== /$NAME ==="
  cat "$SKILL_PATH"
else
  echo "Not found: $NAME. Did you mean:"
  rg -i "$NAME" "$IDX" 2>/dev/null | awk -F'\t' '{
    vault = ($5=="1") ? " [V]" : ""
    printf "  /%s%s — %s\n", $1, vault, $3
  }' | head -5
fi
```

---

### `list [category]` — Browse portfolio

```bash
CAT="${ARGUMENTS#list}"
CAT="${CAT## }"
IDX="$HOME/.claude/cts.idx"

if [ -z "$CAT" ]; then
  TOTAL=$(wc -l < "$IDX" | tr -d ' ')
  HOT=$(awk -F'\t' '$5=="0"' "$IDX" | wc -l | tr -d ' ')
  VAULT=$(awk -F'\t' '$5=="1"' "$IDX" | wc -l | tr -d ' ')
  echo "=== Skills Portfolio: $TOTAL total ($HOT hot + $VAULT vault) ==="
  echo ""
  echo "Hot (loaded at startup):"
  awk -F'\t' '$5=="0" {print $2}' "$IDX" | sort | uniq -c | sort -rn | \
    awk '{printf "  %-16s %3d\n", $2, $1}'
  echo ""
  echo "Vault [V] (on-demand, 0 startup cost):"
  awk -F'\t' '$5=="1" {print $2}' "$IDX" | sort | uniq -c | sort -rn | \
    awk '{printf "  %-16s %3d\n", $2, $1}'
else
  COUNT=$(rg -ic "\t${CAT}\t" "$IDX" 2>/dev/null || echo 0)
  echo "=== $CAT ($COUNT skills) ==="
  rg -i "\t${CAT}\t" "$IDX" 2>/dev/null | \
    awk -F'\t' '{
      vault = ($5=="1") ? " [V]" : ""
      printf "  /%-30s%s %s\n", $1, vault, $3
    }' | head -50
fi
```

---

### `auto <intent>` — Find best skill and invoke it

1. `rg -i` on intent (searches name + desc in idx)
2. Score: exact name > prefix > desc keyword > semantic
3. 1 clear winner → invoke via Skill tool
4. Multiple candidates → show top 5, ask
5. Vault skills can be invoked — load their content first via Read()

```bash
INTENT="${ARGUMENTS#auto }"
IDX="$HOME/.claude/cts.idx"
echo "Searching for: $INTENT"
MATCHES=$(rg -i "$INTENT" "$IDX" 2>/dev/null | head -5)
echo "$MATCHES" | awk -F'\t' '{
  vault = ($5=="1") ? " [V]" : ""
  printf "  /%s%s — %s\n", $1, vault, $3
}'
```

If MATCHES is empty → use `mcp__context-mode__ctx_search` with `queries=["$INTENT"]` and `source="skills-catalog"`

Then reason about best match and invoke via Skill tool. For vault skills: Read() the path first, then follow the skill's instructions.

---

### `vault <name>` — Move hot skill to vault (saves startup tokens)

```bash
NAME="${ARGUMENTS#vault }"
IDX="$HOME/.claude/cts.idx"
LINE=$(rg "^${NAME}\t" "$IDX" 2>/dev/null | head -1)
if [ -z "$LINE" ]; then echo "Skill not found: $NAME"; exit 0; fi

IS_VAULT=$(echo "$LINE" | cut -f5)
if [ "$IS_VAULT" = "1" ]; then echo "Already in vault: $NAME"; exit 0; fi

SKILL_PATH=$(echo "$LINE" | cut -f4)
SKILL_ITEM=$(echo "$SKILL_PATH" | sed "s|$HOME/.claude/skills/||" | cut -d'/' -f1)
SRC="$HOME/.claude/skills/$SKILL_ITEM"
VAULT="$HOME/.claude/cts"

if [ -e "$SRC" ]; then
  mv "$SRC" "$VAULT/"
  echo "Vaulted: $NAME ($SKILL_ITEM)"
  echo "Rebuilding index..."
  python3 "$HOME/.claude/scripts/build-skills-index.py" \
    --vault-dir "$HOME/.claude/cts" -q
  echo "Done. $NAME is now cold-stored — use / cts load $NAME to access."
else
  echo "Cannot vault: $SRC not found (may be from ECC plugin)"
fi
```

---

### `unvault <name>` — Restore vault skill to hot (auto-loads at startup)

```bash
NAME="${ARGUMENTS#unvault }"
IDX="$HOME/.claude/cts.idx"
LINE=$(rg "^${NAME}\t" "$IDX" 2>/dev/null | head -1)
if [ -z "$LINE" ]; then echo "Skill not found: $NAME"; exit 0; fi

IS_VAULT=$(echo "$LINE" | cut -f5)
if [ "$IS_VAULT" = "0" ]; then echo "Already hot: $NAME"; exit 0; fi

SKILL_PATH=$(echo "$LINE" | cut -f4)
SKILL_ITEM=$(echo "$SKILL_PATH" | sed "s|$HOME/.claude/cts/||" | cut -d'/' -f1)
SRC="$HOME/.claude/cts/$SKILL_ITEM"
HOT="$HOME/.claude/skills"

if [ -e "$SRC" ]; then
  mv "$SRC" "$HOT/"
  echo "Unvaulted: $NAME ($SKILL_ITEM) — will auto-load next session"
  python3 "$HOME/.claude/scripts/build-skills-index.py" \
    --vault-dir "$HOME/.claude/cts" -q
else
  echo "Cannot unvault: $SRC not found"
fi
```

---

### `stats` — Portfolio + full token savings dashboard

```bash
IDX="$HOME/.claude/cts.idx"
TOTAL=$(wc -l < "$IDX" | tr -d ' ')
HOT=$(awk -F'\t' '$5=="0"' "$IDX" | wc -l | tr -d ' ')
VAULT=$(awk -F'\t' '$5=="1"' "$IDX" | wc -l | tr -d ' ')
CATS=$(awk -F'\t' '{print $2}' "$IDX" | sort -u | wc -l | tr -d ' ')
IDX_BYTES=$(wc -c < "$IDX" | tr -d ' ')

echo "=== Skill Manager — Full Token Dashboard ==="
echo ""
printf "  %-22s %s total (%s hot + %s vault)\n" "Skills indexed:" "$TOTAL" "$HOT" "$VAULT"
printf "  %-22s %s\n" "Categories:" "$CATS"
printf "  %-22s %s bytes\n" "Index size:" "$IDX_BYTES"
echo ""
echo "Startup Cost (this session):"
printf "  %-32s %s\n" "Hot skills:" "~$(echo "$HOT * 40 / 1000" | bc)K tokens (only sm.md)"
printf "  %-32s %s\n" "Vault skills:" "0 tokens ($VAULT cold-stored)"
printf "  %-32s %s\n" "Savings vs full load:" "~$(echo "$VAULT * 40 / 1000" | bc)K tokens saved"
echo ""
echo "RTK Savings (Bash compression):"
rtk gain 2>/dev/null | grep -E "Tokens saved|commands|Efficiency" | sed 's/^/  /' || echo "  rtk gain — check savings"
echo ""
echo "context-mode Savings (run / cts init to activate):"
echo "  ctx_stats — run after session for full report"
```

Then call `mcp__context-mode__ctx_stats` and display the result.

---

### `tokens` — Complete token-saving stack cheatsheet

```bash
echo "=== Complete Token-Saving Stack ==="
echo ""
echo "━━━ LAYER 0: VAULT — Zero Startup Cost ━━━"
echo "  All skills in cold storage by default"
echo "  ~/.claude/skills/       = HOT  (auto-loaded, ~40 tokens/skill)"
echo "  ~/.claude/cts/ = COLD (on-demand, 0 tokens)"
echo "  / cts vault <name>        move to cold storage"
echo "  / cts load <name>         load from vault on demand"
echo ""
echo "━━━ LAYER 1: RTK v0.33.1 — CLI Compression ━━━"
echo "  Auto-active via PreToolUse hook (transparent)"
echo "  git/grep/ls/find/cargo/pytest → 60-90% compression"
echo "  Add -u flag for ultra-compact mode (+10-20%)"
echo "  rtk gain                show total savings"
echo "  rtk gain --graph        30-day trend"
echo "  rtk discover -a         find missed opportunities"
echo ""
echo "━━━ LAYER 2: context-mode v1.0.75 — 98% Context Reduction ━━━"
echo "  RULE: 2+ Bash calls → ctx_batch_execute (94% savings)"
echo ""
echo "  ctx_batch_execute       N commands in 1 call  (986KB→62KB, ~94%)"
echo "  ctx_execute             run code in 11 langs   (56KB→299B, ~99%)"
echo "  ctx_execute_file        large file → summary  (45KB→155B, ~99%)"
echo "  ctx_index               chunk+index doc       (load once)"
echo "  ctx_search              query indexed docs    (~200 tokens)"
echo "  ctx_fetch_and_index     URL → indexed         (60KB→40B, ~99%)"
echo "  ctx_stats               session savings report"
echo "  ctx_doctor              diagnose installation"
echo "  ctx_upgrade             upgrade to latest"
echo "  ctx_purge               delete all indexed content"
echo ""
echo "  Decision Matrix:"
echo "  2+ Bash/grep/ls/find   → ctx_batch_execute"
echo "  Code execution (11 lang)→ ctx_execute (intent-driven if >5KB)"
echo "  Read file > 100 lines   → ctx_execute_file"
echo "  Fetch URL / docs        → ctx_fetch_and_index"
echo "  Search loaded docs      → ctx_search"
echo "  Single quick command    → RTK hook (automatic)"
echo ""
echo "━━━ LAYER 3: SKILL DISCOVERY ━━━"
echo "  / cts search <q>          ~0 tokens    rg on idx"
echo "  / cts auto <intent>       ~0-500       grep + optional ctx_search"
echo "  / cts load <name>         ~500-5K      one skill on demand"
echo ""
echo "━━━ LAYER 4: STRATEGIC ━━━"
echo "  / cts init                initialize all layers at session start"
echo "  /compact                after milestones — reset context pressure"
echo "  haiku   search/explore  \$1/\$5 per M tokens"
echo "  sonnet  code/planning   \$3/\$15 per M tokens"
echo "  opus    architecture    \$5/\$25 per M tokens"
echo ""
echo "Combined potential: 2-3.5M tokens/month saved"
```

---

### `rebuild` — Regenerate index from hot + vault dirs

```bash
SCRIPT="$HOME/.claude/scripts/build-skills-index.py"
if [ -f "$SCRIPT" ]; then
  echo "Rebuilding skills index (hot + vault)..."
  python3 "$SCRIPT" --vault-dir "$HOME/.claude/cts"
  echo ""
  echo "Re-indexing catalog for ctx_search..."
else
  echo "Build script missing. Reinstall:"
  echo "  curl -fsSL https://raw.githubusercontent.com/Supersynergy/claude-sm/main/install.sh | bash"
fi
```

After rebuild, call `mcp__context-mode__ctx_index` with:
- `path: ~/.claude/skills-catalog.md`
- `source: skills-catalog`

---

### No args → Help

```bash
IDX="$HOME/.claude/cts.idx"
[ ! -f "$IDX" ] && echo "Index not found. Run: python3 ~/.claude/scripts/build-skills-index.py" && exit 0
TOTAL=$(wc -l < "$IDX" | tr -d ' ')
HOT=$(awk -F'\t' '$5=="0"' "$IDX" | wc -l | tr -d ' ')
VAULT=$(awk -F'\t' '$5=="1"' "$IDX" | wc -l | tr -d ' ')
BYTES=$(wc -c < "$IDX" | tr -d ' ')

echo "=== Claude Skill Manager & Token Saver — $TOTAL skills ($HOT hot + $VAULT vault) ==="
echo ""
echo "  / cts init              ★ initialize full token-saving stack for this session"
echo "  / cts search <query>    find by keyword  (~0 tokens)"
echo "  / cts list [category]   browse portfolio (hot + vault)"
echo "  / cts load <name>       read full skill  (works for vault too)"
echo "  / cts auto <intent>     find + invoke best match"
echo "  / cts vault <name>      move skill to cold storage (saves tokens)"
echo "  / cts unvault <name>    restore vault skill to hot"
echo "  / cts stats             full token dashboard (skills + RTK + context-mode)"
echo "  / cts tokens            complete token-saving cheatsheet"
echo "  / cts rebuild           refresh index"
echo ""
echo "  [V] = vault skill — searchable but not auto-loaded (0 startup cost)"
echo ""
echo "  Stack: Vault (~0 startup) + RTK (60-90% CLI) + context-mode v1.0.75 (98% context)"
echo "  Run / cts init to activate all layers"
echo ""
echo "Index: ~/.claude/cts.idx ($BYTES bytes)"
```

---

## Token Budget Table

| Method | Raw → Context | Savings |
|--------|---------------|---------|
| Vault skills at startup | **0** | cold-stored, never auto-loaded |
| Hot skill metadata | ~40/skill | loaded at startup (only cts.md) |
| `rg` on idx | **~0** | exact/keyword search, <20ms |
| `ctx_search` | ~200 | semantic/fuzzy on indexed catalog |
| `ctx_batch_execute` N cmds | 986KB → 62KB | ~94% (~300 tokens) |
| `ctx_execute` (11 langs) | 56KB → 299B | ~99% (intent-driven if >5KB) |
| `ctx_execute_file` | 45KB → 155B | ~99% |
| `ctx_fetch_and_index` | 60KB → 40B | ~99% |
| `Read` one skill | ~500-5K | loading content on demand |
| All skills loaded | ~150K | **never do this** |

**New in v1.0.75:** Porter stemming for fuzzy matching, 11 language runtimes (JS/TS/Python/Shell/Ruby/Go/Rust/PHP/Perl/R/Elixir), Bun auto-detection for 3-5x faster execution.
