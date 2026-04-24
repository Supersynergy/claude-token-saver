# Layer 5 — Adaptive Routing

CTS Layers 0–4 cut *startup* tokens. Layer 5 cuts *per-action* tokens by picking
the cheapest tool/model/fetch-stage that will actually succeed.

All heuristics are universal and learn from your own history. No hardcoded host
lists, no personal aliases, no vendor lock-in.

## Three Routers

### 1. Fetch stage router — `fetch_stage(url)`

Picks the cheapest HTTP strategy per URL, escalating only when history proves
it necessary.

```python
from core.adaptive_router import fetch_stage
from core.host_memory import HostMemory

mem = HostMemory()                # ~/.cts/host_memory.db
plan = fetch_stage("https://news.example.com/", memory=mem)
# → FetchPlan(stage='curl', confidence=0.5, reason='no-memory')

# After 3 failures with curl:
mem.record("https://news.example.com/", "curl", success=False)  # x3
plan = fetch_stage("https://news.example.com/", memory=mem)
# → stage='curl_cffi'
```

Default stage hierarchy (override via `stages=...`):

| Stage | Use | Cost |
|-------|-----|------|
| `curl` | plain GET, JSON endpoints | free, 50ms |
| `curl_cffi` | TLS fingerprinting needed | free, 2-3s |
| `browser_stealth` | JS-render + anti-bot | slow, heavy |

Stages are arbitrary strings — plug in your own stack (`rquest`, `camoufox`,
`playwright`, …).

### 2. Model tier router — `model_tier(query)`

Matches query complexity to Claude model tier — don't pay Opus prices for
`list files`.

```python
from core.adaptive_router import model_tier
model_tier("list TODOs").model          # → claude-haiku-4-5
model_tier("fix this bug").model        # → claude-sonnet-4-6
model_tier("refactor auth system ...", has_tools=True).model  # → claude-opus-4-7
```

Signals: verb class (trivial/heavy), query length, long-context flag, tool-use
flag. Override the regexes or tier constants for your own taxonomy.

### 3. Backfire detector — `detect_backfire(command)`

Flags Bash commands that burn more tokens than a native Claude tool would.

```python
detect_backfire("cat README.md")
# → BackfireWarning(suggestion='use Read tool')

detect_backfire("find . -name '*.py'")
# → BackfireWarning(suggestion='use Glob tool or `fd`')

detect_backfire("git status")   # → None (safe)
```

Wire into a PreToolUse hook to nudge before the waste happens.

## Host Memory Learning

`HostMemory` (SQLite at `~/.cts/host_memory.db`) records `(host, stage, wins, fails)`
and decays entries after 7 days. Escalates when a stage logs ≥3 failures with
zero wins.

```python
mem = HostMemory()
mem.record(url, stage, success=True)
advice = mem.advise(url, ["curl", "curl_cffi", "browser"])
# → StageAdvice(stage=..., confidence=..., reason="3w/0f")
```

Zero external deps. Portable. Safe to delete the DB — it rebuilds itself.

## Power Tools Registry

`core/tool_registry.py` maps generic intents to modern CLIs (rg, fd, sd, jq,
ast-grep, semgrep, difft, …). Use it to:

- suggest the right tool for a given task
- detect missing installs (`missing()` → list of absent binaries)
- drive install scripts that only grab what's missing

```python
from core.tool_registry import suggest, missing
suggest("code_text_search").preferred   # → "rg"
missing()                               # → ["comby", "gitleaks", ...]
```

## Install Hint

Layer 5 is library-only. Import from your own hooks or wrappers:

```python
from core.adaptive_router import fetch_stage, model_tier, detect_backfire
from core.host_memory import HostMemory
from core.tool_registry import suggest, missing
```

No daemons, no services, no phone-home.
