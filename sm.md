---
name: sm
description: Claude Skill Manager & Token Saver — find, load, and manage skills on demand with ~0 token overhead. Auto-invokes when user asks "what skill", "which command", "can you", "do you have a skill for", mentions needing a capability, or says "skills". Saves tokens via lazy loading, ctx_search, and RTK integration.
argument-hint: "[search <q> | load <name> | list [cat] | auto <intent> | stats | tokens | rebuild]"
allowed-tools: [Bash, Read, mcp__context-mode__ctx_search, mcp__context-mode__ctx_index, mcp__context-mode__ctx_batch_execute, mcp__context-mode__ctx_stats]
model: haiku
---

# Claude Skill Manager & Token Saver (`/sm`)

**Index**: `~/.claude/skills.idx` | grep-able TSV, instant
**Catalog**: `~/.claude/skills-catalog.md` | ctx-indexed, BM25 semantic
**Rule**: NEVER load all skills. grep index first → ctx_search if fuzzy → Read() only the match.

---

## Dispatch on `$ARGUMENTS`

Parse the **first word** to select action. Default (no args) → help + stats.

---

### `search <query>` — Instant grep, 0 tokens

```bash
QUERY="${ARGUMENTS#search }"
IDX="$HOME/.claude/skills.idx"
[ ! -f "$IDX" ] && echo "Index missing. Run: /sm rebuild" && exit 0

echo "=== Skills matching: $QUERY ==="
RESULTS=$(rg -i "$QUERY" "$IDX" 2>/dev/null)

if [ -n "$RESULTS" ]; then
  echo "$RESULTS" | awk -F'\t' '{printf "  /%-28s [%s] %s\n", $1, $2, $3}' | head -30
else
  echo "No exact match. Fuzzy:"
  for word in $QUERY; do
    rg -i "$word" "$IDX" 2>/dev/null
  done | sort -u | awk -F'\t' '{printf "  /%-28s [%s] %s\n", $1, $2, $3}' | head -20
  echo ""
  echo "For semantic search: /sm auto $QUERY"
fi
```

---

### `load <name>` — Read one skill on demand

```bash
NAME="${ARGUMENTS#load }"
IDX="$HOME/.claude/skills.idx"

LINE=$(rg "^${NAME}\t" "$IDX" 2>/dev/null | head -1)
[ -z "$LINE" ] && LINE=$(rg -i "^${NAME}" "$IDX" 2>/dev/null | head -1)

if [ -n "$LINE" ]; then
  SKILL_PATH=$(echo "$LINE" | cut -f4)
  echo "=== /$NAME ==="
  cat "$SKILL_PATH"
else
  echo "Not found: $NAME. Did you mean:"
  rg -i "$NAME" "$IDX" 2>/dev/null | awk -F'\t' '{printf "  /%s — %s\n", $1, $3}' | head -5
fi
```

---

### `list [category]` — Browse portfolio

```bash
CAT="${ARGUMENTS#list}"
CAT="${CAT## }"
IDX="$HOME/.claude/skills.idx"

if [ -z "$CAT" ]; then
  TOTAL=$(wc -l < "$IDX" | tr -d ' ')
  echo "=== Skills Portfolio ($TOTAL skills) ==="
  awk -F'\t' '{print $2}' "$IDX" | sort | uniq -c | sort -rn | \
    awk '{printf "  %-16s %3d skills\n", $2, $1}'
else
  COUNT=$(rg -ic "\t${CAT}\t" "$IDX" 2>/dev/null || echo 0)
  echo "=== $CAT ($COUNT skills) ==="
  rg -i "\t${CAT}\t" "$IDX" 2>/dev/null | \
    awk -F'\t' '{printf "  /%-30s %s\n", $1, $3}' | head -50
fi
```

---

### `auto <intent>` — Find best skill and invoke it

1. `rg -i` on intent (searches name + desc in idx)
2. Score: exact name > prefix > desc keyword > semantic
3. 1 clear winner → invoke via Skill tool
4. Multiple candidates → show top 5, ask

```bash
INTENT="${ARGUMENTS#auto }"
IDX="$HOME/.claude/skills.idx"
echo "Searching for: $INTENT"
MATCHES=$(rg -i "$INTENT" "$IDX" 2>/dev/null | head -5)
echo "$MATCHES" | awk -F'\t' '{printf "  /%s — %s\n", $1, $3}'
```

If MATCHES is empty → use ctx_search:
`mcp__context-mode__ctx_search` with `queries=["$INTENT"]` and `source="skills-catalog"`

Then reason about best match and invoke via Skill tool.

---

### `stats` — Portfolio + token savings overview

```bash
IDX="$HOME/.claude/skills.idx"
TOTAL=$(wc -l < "$IDX" | tr -d ' ')
CATS=$(awk -F'\t' '{print $2}' "$IDX" | sort -u | wc -l | tr -d ' ')
IDX_BYTES=$(wc -c < "$IDX" | tr -d ' ')

echo "=== Skill Manager & Token Saver — Stats ==="
echo ""
printf "  %-20s %s\n" "Skills indexed:" "$TOTAL"
printf "  %-20s %s\n" "Categories:" "$CATS"
printf "  %-20s %s bytes\n" "Index size:" "$IDX_BYTES"
echo ""
echo "Token Saving Layers:"
printf "  %-28s %s\n" "rg on idx (Layer 1):" "~0 tokens, <20ms"
printf "  %-28s %s\n" "ctx_search (Layer 2):" "~200-500 tokens, BM25"
printf "  %-28s %s\n" "Read one skill (Layer 3):" "~500-5K tokens"
printf "  %-28s %s\n" "All skills loaded:" "~160K+ (NEVER)"
echo ""
echo "RTK Savings (this session):"
rtk gain 2>/dev/null | grep -E "Tokens saved|Efficiency meter" | sed 's/^/  /' || echo "  rtk gain — check savings"
```

---

### `tokens` — Token saving cheatsheet

```bash
echo "=== Token Saving Cheatsheet ==="
echo ""
echo "SKILL DISCOVERY (this manager)"
echo "  /sm search <q>       ~0 tokens    rg on 54KB index"
echo "  /sm auto <intent>    ~0-500       grep + optional ctx_search"
echo "  /sm load <name>      ~500-5K      one skill on demand"
echo ""
echo "RTK — CLI COMPRESSION  (60-90% per command)"
echo "  Hooks auto-rewrite: git, grep, ls, curl, find, docker, gh..."
echo "  rtk gain             show total savings"
echo "  rtk discover -a      find missed opportunities"
echo ""
echo "CONTEXT-MODE — LARGE OUTPUT VIRTUALIZATION"
echo "  ctx_batch_execute    run N queries in 1 call"
echo "  ctx_index + search   index large files, avoid loading them"
echo "  ctx_search           ~200 tokens vs reading the file"
echo ""
echo "STRATEGIC COMPACT"
echo "  /compact             after milestones — reset context pressure"
echo "  What survives:       CLAUDE.md, Memory files, git state"
echo ""
echo "MODEL ROUTING"
echo "  haiku:  search, explore, simple tasks  (\$1/\$5 per M)"
echo "  sonnet: code, planning, complex tasks  (\$3/\$15 per M)"
echo "  opus:   architecture decisions only    (\$5/\$25 per M)"
```

---

### `rebuild` — Regenerate index from skills dir

```bash
SCRIPT="$HOME/.claude/scripts/build-skills-index.py"
if [ -f "$SCRIPT" ]; then
  echo "Rebuilding skills index..."
  python3 "$SCRIPT"
  echo ""
  echo "Re-indexing catalog for ctx_search..."
  # ctx_index will be called after this block
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
IDX="$HOME/.claude/skills.idx"
[ ! -f "$IDX" ] && echo "Index not found. Run: python3 ~/.claude/scripts/build-skills-index.py" && exit 0
TOTAL=$(wc -l < "$IDX" | tr -d ' ')
BYTES=$(wc -c < "$IDX" | tr -d ' ')

echo "=== Claude Skill Manager & Token Saver — $TOTAL skills ==="
echo ""
echo "  /sm search <query>    find by keyword  (~0 tokens)"
echo "  /sm list [category]   browse portfolio"
echo "  /sm load <name>       read full skill"
echo "  /sm auto <intent>     find + invoke best match"
echo "  /sm stats             portfolio + RTK savings overview"
echo "  /sm tokens            token saving tips"
echo "  /sm rebuild           refresh index"
echo ""
echo "Top categories:"
awk -F'\t' '{print $2}' "$IDX" | sort | uniq -c | sort -rn | head -8 | \
  awk '{printf "  %-16s %3d skills\n", $2, $1}'
echo ""
echo "Index: ~/.claude/skills.idx ($BYTES bytes) | Tip: /sm auto <describe what you need>"
```

---

## Token Budget Table

| Method | Tokens | When |
|--------|--------|------|
| `rg` on idx | **~0** | exact/keyword search |
| `ctx_search` | ~200-500 | semantic/fuzzy |
| `Read` one skill | ~500-5K | loading content |
| All skills loaded | ~160K | **never do this** |
