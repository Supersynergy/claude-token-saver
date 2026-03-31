# Claude Skill Manager & Token Saver

> **Discover and load 300+ Claude Code skills with ~0 token overhead.**
> Three-layer lazy loading: grep index → semantic search → on-demand file read.
> Never loads all skills at once. Saves 100K–160K tokens per session.

[![Claude Code](https://img.shields.io/badge/Claude_Code-2.1+-blueviolet)](https://claude.ai/code)
[![Token savings](https://img.shields.io/badge/token_savings-up_to_160K_per_session-brightgreen)](#token-savings)
[![ripgrep](https://img.shields.io/badge/powered_by-ripgrep_15+-orange)](https://github.com/BurntSushi/ripgrep)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## The Problem

Claude Code loads skill **metadata for every skill at startup**. With 300+ skills that's ~160K tokens burned before you even start working. And finding the right skill means either remembering exact names or loading all files.

## The Solution

`/sm` — a three-layer lazy loading system that makes discovery essentially free:

| Layer | Method | Tokens | Speed |
|-------|--------|--------|-------|
| **1. Grep** | `rg` on 54KB `skills.idx` TSV | **~0** | <20ms |
| **2. Semantic** | `ctx_search` BM25 on catalog | ~200–500 | fast |
| **3. Load** | `Read()` one matched skill file | ~500–5K | on-demand |
| ~~All skills~~ | ~~Load everything~~ | ~~160K+~~ | ~~never~~ |

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Supersynergy/claude-sm/main/install.sh | bash
```

Or manually:
```bash
cp sm.md ~/.claude/skills/sm.md
cp build-skills-index.py ~/.claude/scripts/
cp skills-index-session.sh ~/.claude/hooks/
chmod +x ~/.claude/hooks/skills-index-session.sh ~/.claude/scripts/build-skills-index.py
python3 ~/.claude/scripts/build-skills-index.py
```

**Requirements:** Claude Code 2.1+, Python 3.8+, [ripgrep](https://github.com/BurntSushi/ripgrep) (`brew install ripgrep`)

---

## Usage

```
/sm search <query>     — instant keyword search (~0 tokens)
/sm list [category]    — browse by category
/sm load <name>        — read full skill content
/sm auto <intent>      — find best skill and invoke it
/sm stats              — portfolio overview + RTK savings
/sm tokens             — token saving cheatsheet
/sm rebuild            — regenerate index after adding skills
```

### Examples

```bash
/sm search plane           # → finds /plane (Plane.so PM skill)
/sm search browser         # → finds agent-browser, ghostbrowser, ...
/sm list Agents            # → all 16 agent skills
/sm list Lang              # → all 36 language skills
/sm auto "scrape a website with stealth"  # → finds + invokes /ghostbrowser
/sm auto "create a new issue in PM"       # → finds + invokes /plane
/sm load agent-browser     # → loads full 200-line skill content
/sm stats                  # → shows index size, RTK savings, categories
```

---

## Auto-Invocation

`/sm` auto-triggers when you say:

- *"what skill can..."* / *"which command..."*
- *"can you scrape / deploy / test..."*
- *"do you have a skill for..."*
- *"I need to..."* + any capability keyword
- *"show me skills"* / *"list skills"*

---

## Token Savings Architecture

This works alongside other token-saving layers already in Claude Code:

```
Request arrives
    │
    ├─ 1. /sm grep idx (rg)     ~0 tokens    ← this tool
    │
    ├─ 2. /sm ctx_search        ~200-500      ← this tool (semantic fallback)
    │
    ├─ 3. RTK hook              60-90% CLI    ← if rtk installed
    │     (rewrites git/grep/ls/curl → compact)
    │
    ├─ 4. context-mode          virtualize    ← large output management
    │     (ctx_index + ctx_search)
    │
    └─ 5. strategic compact     100-200K/mo   ← /compact at milestones
```

**Combined potential: 4–5M tokens/month saved** (active Claude Code user)

---

## How the Index Works

`~/.claude/skills.idx` — TSV, one skill per line, grep-able:
```
agent-browser   Agents   Ultra-fast browser automation for AI agents. 93% fewer tokens...   /path/to/SKILL.md
plane           PM       Plane.so project management — create issues, query projects...      /path/to/plane.md
rust-patterns   Lang     Idiomatic Rust patterns, ownership, lifetimes, error handling...    /path/to/SKILL.md
```

`~/.claude/skills-catalog.md` — Markdown by category, indexed with context-mode BM25:
```markdown
## Agents (16 skills)
- `/agent-browser` — Ultra-fast browser automation...
- `/ghostbrowser` — Stealth browser automation...
```

The catalog is chunked by `## Category` headings so `ctx_index` creates one chunk per category — enabling semantic search that returns only the relevant category section.

---

## Files

| File | Purpose | Install Location |
|------|---------|-----------------|
| `sm.md` | `/sm` skill (slash command) | `~/.claude/skills/sm.md` |
| `build-skills-index.py` | Builds `skills.idx` + catalog | `~/.claude/scripts/` |
| `skills-index-session.sh` | Auto-rebuild SessionStart hook | `~/.claude/hooks/` |
| `install.sh` | One-command installer | run via curl |

---

## Build Script Options

```bash
python3 build-skills-index.py [options]

Options:
  --skills-dir PATH   Skills directory (default: ~/.claude/skills)
  --output-dir PATH   Output dir for idx + catalog (default: ~/.claude)
  --quiet, -q         Suppress output
```

Supports any skills directory layout — not just `~/.claude/skills`. Works with custom skill repositories.

---

## Categories

Auto-assigned from skill name. Expand `CATS` dict in `build-skills-index.py` for custom mappings:

`Agents` `AI` `Biz` `Browser` `Content` `Data` `DevOps` `Frontend` `GSD` `Lang` `Media` `Meta` `OpenSpec` `PM` `Research` `Security` `Other`

---

## Contributing

- Add new skills: place `.md` files with `name:` + `description:` frontmatter in `~/.claude/skills/`
- Run `/sm rebuild` to re-index
- Improve categories: extend `CATS` dict in `build-skills-index.py`

---

## By

[Supersynergy](https://github.com/Supersynergy) — AI agent infrastructure, open source.

Related: [claude-session-restore](https://github.com/Supersynergy/claude-session-restore) · [awesome-agentic-coding](https://github.com/Supersynergy/awesome-agentic-coding)
