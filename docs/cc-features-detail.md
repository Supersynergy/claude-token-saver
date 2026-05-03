# Claude Code Best Practices — May 2026 (v2.1.126)

Caveman style. Source URLs at end of each block. Local KB = sparse on 2.1.x; web docs primary.

---

## 1. New 2.1.x Features (chronological-ish)

### Slash commands new
- `/loop [interval] [prompt]` — recurring task. Omit interval → Claude self-paces 1m–1h via Monitor tool (token-cheap, no polling). Omit prompt → built-in maintenance prompt; customize via `~/.claude/loop.md`. Esc cancels pending wakeup. 7-day expiry. Bedrock/Vertex/Foundry → fixed 10min when no interval. Src: https://docs.anthropic.com/en/docs/claude-code/scheduled-tasks
- `/ultrareview` — parallelized review checks, diffstat in launch dialog. Also CLI: `claude ultrareview [target] --json` (CI-friendly, exit 1 on findings). Src: changelog 2.1.120/2.1.126.
- `/ultraplan` — cloud planning session from terminal, review plan in browser. "Refine with Ultraplan" link in transcript. Src: https://docs.anthropic.com/en/docs/claude-code/remote-control
- `/fast` (Tab toggle) — switches to Opus 4.6 fast mode, 2.5× faster, higher $/tok. `↯` icon when active. Persistent across sessions unless admin forces per-session opt-in. `fastMode: true` in settings.json. Best enabled session-start. Src: https://docs.anthropic.com/en/docs/claude-code/fast-mode
- `/tui fullscreen` — alt-screen render, no flicker, flat memory long sessions. v2.1.89+. Env equivalent `CLAUDE_CODE_NO_FLICKER=1`. Mouse/scroll changes (Ctrl+o for search, click URL direct). Src: https://docs.anthropic.com/en/docs/claude-code/fullscreen
- `/btw` — side-question overlay; answer never enters conversation history (token-saver for quick lookups). Src: best-practices.
- `/rewind` (or `Esc Esc`) — pick checkpoint, choose **Restore** or **Summarize from here**. Per-prompt + per-edit checkpoints. NOT a VCS replacement; bash + external changes untracked. Src: https://docs.anthropic.com/en/docs/claude-code/checkpointing
- `/extra-usage` — now works from Remote Control (mobile/web). 2.1.126.
- `/reload-plugins` — hot-reload plugin skills/agents/hooks/MCP/LSP w/o restart.
- `/mobile` — QR code for Claude iOS/Android.

### Agent teams (`/agents` orchestrator)
- True multi-Claude-session coordination — teammates communicate via shared task list (NOT one-shot subagent return). Each teammate = own context window.
- Spawn pattern: `Create an agent team to <task>. Spawn N teammates: ... Have them debate / claim tasks / report.`
- Modes: parallel review (one-per-domain), competing-hypotheses debate, module ownership, cross-layer coord (FE/BE/tests).
- Knobs: display mode, `model:` per teammate, `requirePlanApproval`, talk-direct, assign/claim/shutdown, hooks for quality gates.
- Cost: significantly more tokens than single session. Use only when independent. Sequential / same-file → subagents instead.
- Src: https://docs.anthropic.com/en/docs/claude-code/agent-teams

### Subagents (refined 2026)
- Inherit all tools incl MCP by default. Restrict via `tools:` (allowlist) or `disallowedTools:` (denylist) in frontmatter; both → deny first, then allow.
- `model:` field per agent; resolution order: `CLAUDE_CODE_SUBAGENT_MODEL` env > per-invocation param > frontmatter > main convo.
- Stalled subagent (no stream 10min) → fail clearly instead of hang silently (2.1.126).
- Preload skills into subagents — full SKILL.md content injected at startup (vs lazy in main session).
- Restrict which subagents may be spawned (`restrict-spawnable`).
- Scope MCP servers per subagent.
- Src: https://docs.anthropic.com/en/docs/claude-code/sub-agents

### Channels (research preview, v2.x)
- Push external events INTO running session — Telegram/Discord/iMessage forward → Claude reacts.
- Allowlist-gated: `claude-plugins-official/external_plugins` default. Org-admin `allowedChannelPlugins`. Dev: `--dangerously-load-development-channels`.
- Distinct from MCP: channels = inbound push; MCP = outbound tool call.
- Src: https://docs.anthropic.com/en/docs/claude-code/channels

### Remote Control
- Local session, continue from phone/web. Outbound HTTPS only, no inbound port. `/remote-control`, `/config → Enable Remote Control for all sessions`. Server mode for multi-concurrent.
- Mobile push notifications.
- Pairs w/ Dispatch (msg phone → spawn Desktop session) and `/extra-usage`.
- Src: https://docs.anthropic.com/en/docs/claude-code/remote-control

### Permission modes (auto mode = killer)
- Modes: `default` | `acceptEdits` | `plan` | `auto` | `dontAsk` | `bypassPermissions`.
- **Auto mode** (v2.1.83+): no prompts; classifier model reviews each action, blocks escalation/unrecognized infra/prompt-injected behavior. Boundaries from chat ("don't push", "wait until I review") become block signals. Boundaries lost on context compact → use `deny` rule for hard guarantee.
- Auto fallback: 3 consecutive blocks OR 20 total → pauses, prompts return. Headless `-p` aborts on repeated blocks.
- Plan mode default per-project: `permissions.defaultMode = "plan"` in `.claude/settings.json`. Auto-name session from accepted plan. `clearContextOnPlanAccept` setting.
- Plans: Max/Team/Enterprise/API. Sonnet 4.6 / Opus 4.6 / Opus 4.7.
- Src: https://docs.anthropic.com/en/docs/claude-code/permission-modes

### Checkpointing
- Auto on every prompt + every edit. Restore code, conversation, or both. 30-day. Bash & external file changes NOT tracked.
- Src: https://docs.anthropic.com/en/docs/claude-code/checkpointing

### Misc 2.1.120–126
- Skills can read `${CLAUDE_EFFORT}` substitution (effort tier aware).
- `AI_AGENT` env exported to subprocesses → tools detect agent context.
- Win: Git Bash no longer required, PowerShell fallback.
- Bash deny rules now match `env`/`sudo`/`watch`/`ionice`/`setsid` wrappers; `find -exec`/`-delete` no longer auto-approved by `Bash(find:*)` allow.
- macOS: `/private/{etc,var,tmp,home}` treated as dangerous removal.
- Multi-line bash w/ comment first line: full cmd shown in transcript (anti-spoof).
- `cd <pwd> && git ...` no perm prompt when cd is no-op.
- Src: https://docs.anthropic.com/en/docs/claude-code/changelog

---

## 2. Skills (Agent Skills, model-invoked)

- Location: `~/.claude/skills/<name>/SKILL.md` (user) | `.claude/skills/` (project) | `<plugin>/skills/` (plugin, namespaced `/<plugin>:<skill>`).
- Frontmatter: `description` (required, used for invocation routing), `allowed-tools`, `disable-model-invocation` (user-only invoke), `user-invocable: false` (Claude-only).
- **Progressive disclosure**: only `description` always-in-context; full SKILL.md loads when invoked, persists rest of session (NOT re-read on later turns).
- Auto-compact preserves invoked skills within budget; on summary, re-attaches most-recent invocation up to first 5000 tokens each.
- Live change detection (edit while running picked up).
- `--add-dir` exception: `.claude/skills/` inside added dir auto-loads.
- Bundled skills: `update-config`, `keybindings-help`, `simplify`, `fewer-permission-prompts`, `loop`, `schedule`, `claude-api`.
- Src: https://docs.anthropic.com/en/docs/claude-code/skills

---

## 3. Plugins

- Structure: `<plugin>/.claude-plugin/plugin.json` + `skills/`, `agents/`, `hooks/`, `commands/`, MCP, LSP, monitors.
- Dev: `claude --plugin-dir ./my-plugin` (multi: repeat flag). `--plugin-dir` overrides installed marketplace plugin of same name (mid-dev test).
- `/reload-plugins` — re-load all (skills/agents/hooks/MCP/LSP) without restart.
- Skills namespaced: `/<plugin-name>:<skill>`. Override prefix via `name` in plugin.json.
- Bundled MCP: `${CLAUDE_PLUGIN_ROOT}` for files, `${CLAUDE_PLUGIN_DATA}` for state surviving updates. Multi transport (stdio/SSE/HTTP).
- Background monitors, default settings shipping, LSP servers.
- Marketplace install: `plugin install` reports `range-conflict` on dep mismatch (2.1.x).
- Src: https://docs.anthropic.com/en/docs/claude-code/plugins

---

## 4. Hooks (automation backbone)

- Cadences: per-session (`SessionStart`, `SessionEnd`, `Setup`), per-turn (`UserPromptSubmit`, `UserPromptExpanded`, `Stop`, `StopFailure`), per-tool (`PreToolUse`, `PostToolUse`).
- Handler types: shell command (stdin JSON), HTTP (POST body), MCP tool, LLM prompt, agent.
- Output: exit codes (2 = block w/ stderr context per event), JSON `{decision: "block"|"approve", message: "...", contextForClaude: "..."}` to inject context, deny, or auto-approve.
- Matchers: glob on tool name, MCP tool match `mcp__<server>__<tool>`.
- Reference scripts by path (no inline). Hooks live IN skills + agents (scoped automation).
- `/hooks` menu UI to inspect/disable.
- Async hooks supported.
- Locations: project `.claude/settings.json`, user `~/.claude/settings.json`, plugins.
- Src: https://docs.anthropic.com/en/docs/claude-code/hooks

---

## 5. Output Styles

- Modify system prompt → role/tone/format. Keep core capabilities (bash, files, TODOs).
- Built-in: default, explanatory, learning, etc.
- Custom: markdown w/ frontmatter `name`, `description`. `/output-style` to switch.
- Vs CLAUDE.md: output-style replaces default sys prompt parts; CLAUDE.md = added user context; `--append-system-prompt` = ad-hoc.
- Vs agents: agents = isolated context + tools; output-style = style only, same context.
- Vs skills: skills = on-demand task; output-style = always-on voice.
- Src: https://docs.anthropic.com/en/docs/claude-code/output-styles

---

## 6. Effective Programming Workflows (high-leverage)

### Explore → Plan → Code → Verify (canonical)
- `claude` cold → ask to read files first (no code yet).
- Switch to **plan mode** (Shift+Tab cycle), iterate plan.
- Approve plan → exec mode (acceptEdits or auto).
- Verify gate: run lints/types/tests; ask Claude to run + fix.
- Src: https://docs.anthropic.com/en/docs/claude-code/best-practices

### Spec-driven (highest leverage)
- Issue → SPEC.md (interview edges in NEW chat) → review → impl in clean worktree → verify-loop → PR.
- Skip impl-without-spec for >3 file changes. 80% bugs = unstated assumptions.

### Worktree fanout (parallel competing approaches)
```
for a in a b c; do git worktree add ../proj-$a -b try/$a; done
```
Spawn N subagents one-per-worktree. Eval harness scores. Merge winner. Cheap w/ Haiku tier.

### Plan-mode + auto-approve
- `EnterPlanMode` → user approves once → `acceptEdits` mode for known-safe scope. 10× throughput on multi-step.

### Subagent parallelism
- Independent queries → ONE message, N Agent tool calls in parallel.
- For deep cross-talk → agent teams (debate hypotheses).

### Verification loop (pre-PR)
```
[ ] tsc --noEmit         0 errors
[ ] biome lint           0 warn
[ ] bun test --bail      green
[ ] cargo clippy --fix   0 warn
[ ] cargo nextest        green
[ ] semgrep --autofix    clean
```

### `/btw` for context hygiene
- Ask side question without bloating context.

### Checkpoint + summarize
- `Esc Esc → Summarize from here` to compact mid-conversation while preserving early context.

### Eval-driven prompt iteration
- promptfoo/inspect-ai golden set BEFORE shipping skill/hook prompt changes.

### Continuous compaction
- Trigger `/compact <focus>` at ~60% (not 90%); preserves cache hits.

---

## 7. Token-Saving / Model Routing

- **Tier ladder**: Haiku 4.5 = explore/batch ($0.25/$1.25) → Sonnet 4.6 = code daily ($3/$15) → Opus 4.7 = arch only ($15/$75). Bandit (Thompson) auto-route via `core/orchestrator.py`.
- `/fast` only for live debugging where latency > $.
- `/loop` w/o interval uses Monitor tool → no polling (token-cheap).
- Skill progressive disclosure → full content only on invoke.
- Subagents = isolated context (free up main).
- `acceptEdits` + `auto` mode = fewer round-trips (no perm-prompt re-read).
- RTK prefix all bash → 60-90% on git/build/test.
- context-mode `ctx_batch_execute` for 2+ commands (one round-trip vs many).
- Synapse `syn hybrid` 8ms recall before web fetch.
- Subagent stall fails fast at 10min (no token bleed).

---

## 8. Agent SDK patterns

- Packages: `@anthropic-ai/claude-agent-sdk` (TS, bundles native binary), `claude-agent-sdk` (Py).
- Auth: `ANTHROPIC_API_KEY` | Bedrock (`CLAUDE_CODE_USE_BEDROCK=1`) | Vertex (`CLAUDE_CODE_USE_VERTEX=1`) | Foundry.
- Modes: streaming-input (real-time multi-turn) vs single-mode (one-shot).
- Sessions: persistent state, resumable.
- Custom tools: function decorators → JSONSchema auto.
- **Tool search**: scale to many tools — semantic match selects subset before each turn (avoids prompt bloat).
- MCP integration as first-class.
- Subagents in SDK with model + tool restriction.
- System prompt modification (replace, prepend, append).
- Slash commands programmable.
- Skills + plugins loadable in SDK.
- Permissions API: callback per tool call.
- Hooks SDK: intercept/control programmatically.
- File checkpointing (rewind file state).
- Cost tracking per turn/session.
- Observability hooks.
- Structured outputs (JSON schema).
- Src: https://docs.anthropic.com/en/docs/claude-code/agent-sdk/overview

---

## 9. MCP Server Design

- Scopes: local (this dir) | project (.mcp.json checked-in) | user (global) | plugin. Precedence: local > project > user > plugin.
- Transports: stdio (subprocess), SSE (deprecated-ish), HTTP (preferred remote), channels (push).
- Plugin MCP: auto-lifecycle (start/stop on enable/disable + `/reload-plugins`). Use `${CLAUDE_PLUGIN_ROOT}` & `${CLAUDE_PLUGIN_DATA}`.
- Dynamic tool updates (`notifications/tools/list_changed`).
- Auto-reconnect.
- OAuth: fixed callback port option, pre-configured creds option.
- Hook matcher `mcp__<server>__<tool>` for per-tool gating.
- Concurrent-call timeout fix landed 2.1.126 (one tool's late msg no longer disarms another's timer).
- Best practice: keep tool surface small (use tool-search if many), namespace clearly, document in `description`, return structured content (text + resource links), respect cancellation.
- Src: https://docs.anthropic.com/en/docs/claude-code/mcp

---

## 10. Settings Quick Hits

- `.claude/settings.json` (project) | `~/.claude/settings.json` (user) | `.claude/settings.local.json` (gitignored).
- Key: `permissions.defaultMode`, `permissions.allow`/`deny`, `fastMode`, `tui`, `clearContextOnPlanAccept`, `hooks.*`, `mcpServers`, `allowedChannelPlugins`, `outputStyle`, `model`.
- AGENTS.md ↔ CLAUDE.md symlink for cross-tool portability (Cursor/Aider/Codex/Continue).

---

## Sources (canonical)
- Overview: https://docs.anthropic.com/en/docs/claude-code/overview
- Changelog (live): https://docs.anthropic.com/en/docs/claude-code/changelog | https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md
- Best practices: https://docs.anthropic.com/en/docs/claude-code/best-practices
- Common workflows: https://docs.anthropic.com/en/docs/claude-code/common-workflows
- Skills: https://docs.anthropic.com/en/docs/claude-code/skills
- Plugins: https://docs.anthropic.com/en/docs/claude-code/plugins
- Hooks ref: https://docs.anthropic.com/en/docs/claude-code/hooks
- Subagents: https://docs.anthropic.com/en/docs/claude-code/sub-agents
- Agent teams: https://docs.anthropic.com/en/docs/claude-code/agent-teams
- Channels: https://docs.anthropic.com/en/docs/claude-code/channels
- Remote Control: https://docs.anthropic.com/en/docs/claude-code/remote-control
- Permission modes: https://docs.anthropic.com/en/docs/claude-code/permission-modes
- Fullscreen: https://docs.anthropic.com/en/docs/claude-code/fullscreen
- Fast mode: https://docs.anthropic.com/en/docs/claude-code/fast-mode
- Checkpointing: https://docs.anthropic.com/en/docs/claude-code/checkpointing
- Scheduled tasks: https://docs.anthropic.com/en/docs/claude-code/scheduled-tasks
- Output styles: https://docs.anthropic.com/en/docs/claude-code/output-styles
- Agent SDK: https://docs.anthropic.com/en/docs/claude-code/agent-sdk/overview
- MCP: https://docs.anthropic.com/en/docs/claude-code/mcp
- llms.txt index: https://code.claude.com/docs/llms.txt
