# CLAUDE.md Token Stack Snippet

> Copy-paste this block into your `~/.claude/CLAUDE.md` to enforce extreme token savings.
> Requires: [claude-sm](https://github.com/Supersynergy/claude-sm) + [RTK](https://rtk-ai.app) + context-mode (via ECC or npm)

---

```markdown
## Token Stack — ALWAYS USE (Vault + RTK + context-mode)

### Session Start
Run `/sm init` once per session — indexes key docs, shows savings dashboard, activates all layers.

### Layer 0: Vault — Zero Startup Skills
All skills cold-stored in `~/.claude/skills-vault/` = 0 startup tokens.
Only `sm.md` loads (~40 tokens). 313+ skills on-demand via `/sm load <name>`.

### Layer 1: RTK (auto-active, transparent)
PreToolUse hook rewrites ALL Bash automatically → 60-90% compression.
```bash
rtk gain              # savings dashboard
rtk gain --graph      # 30-day trend
rtk discover -a       # find missed opportunities
# Ultra-compact: add -u flag
rtk grep pattern -u   # +10-20% more savings
rtk ls -u
```

### Layer 2: context-mode (83% context reduction)

**RULE: ALWAYS use `ctx_batch_execute` instead of 2+ Bash/Read calls.**

| Situation | Use | Savings |
|-----------|-----|---------|
| 2+ Bash commands | `ctx_batch_execute` | 90% |
| Read large file | `ctx_execute_file` | 85% |
| Fetch URL/docs | `ctx_fetch_and_index` | 80% |
| Search indexed | `ctx_search` | ~200 tokens |
| Single Bash | RTK (automatic) | 60-90% |

**Examples:**
```python
# ❌ NEVER: 4 separate calls
ls src/; grep "fn " src/; cat README.md; git log --oneline -5

# ✅ ALWAYS: 1 batch call
ctx_batch_execute(commands=[
  {"label": "tree", "command": "ls src/"},
  {"label": "functions", "command": "grep 'fn ' src/ -r"},
  {"label": "readme", "command": "cat README.md"},
  {"label": "git", "command": "git log --oneline -5"}
], queries=["project structure", "key functions"])

# Large file read
ctx_execute_file(path="src/main.rs", intent="understand structure")

# Index once, search many times
ctx_index(path="docs/API.md", source="api-docs")
ctx_search(queries=["authentication"], source="api-docs")
```

### Layer 3: Skill Discovery (~0 tokens)
```bash
/sm search <query>    # rg on index, instant, ~0 tokens
/sm auto <intent>     # find + invoke best skill
/sm load <name>       # load from vault on demand
```

### Model Routing
- haiku: search, explore, simple tasks ($1/$5 per M)
- sonnet: code, planning, complex tasks ($3/$15 per M)
- opus: architecture decisions only ($5/$25 per M)

### Combined Potential: 2-3.5M tokens/month saved
```

---

## Quick Install

```bash
# 1. Install claude-sm (skills + vault + RTK integration)
curl -fsSL https://raw.githubusercontent.com/Supersynergy/claude-sm/main/install.sh | bash

# 2. Install RTK
curl -fsSL https://rtk-ai.app/install | bash

# 3. context-mode (via ECC or standalone)
npm install -g context-mode
# or install ECC: https://github.com/Supersynergy/everything-claude-code

# 4. Move all skills to vault (zero startup)
cd ~/.claude/skills && for item in $(ls | grep -v "^sm\.md$"); do mv "$item" ../skills-vault/; done
python3 ~/.claude/scripts/build-skills-index.py --vault-dir ~/.claude/skills-vault

# 5. Initialize stack
# In Claude Code: /sm init
```
