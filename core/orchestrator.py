#!/usr/bin/env python3
"""
orchestrator.py — Unified auto-routing engine
═══════════════════════════════════════════════════════════════════════════
Single entrypoint. Given a task + optional URL → picks:
  1. Fetch strategy   (skip | rtk curl | smart-fetch | hyperfetch)
  2. Extraction       (trafilatura | gemma-gate | raw)
  3. Model            (local: smollm2/gemma3/phi4-mini → API: haiku/sonnet/opus-4-7)
  4. Effort level     (low | medium | high | xhigh)  ← Opus 4.7 xhigh = deep reasoning

Decision is fully automatic. Override via env vars or Task.force_* fields.

Usage:
    from core.orchestrator import Orchestrator, Task
    orch = Orchestrator()
    result = orch.run(Task(
        query="Summarize the pricing on this page",
        url="https://stripe.com/pricing",
    ))
    print(result.output)       # clean answer
    print(result.tokens_used)  # budget impact
    print(result.model_used)   # what ran

Environment overrides:
    ANTHROPIC_API_KEY   required for API models
    OLLAMA_URL          default: http://127.0.0.1:11434
    ORC_MAX_TOKENS      hard cap per call (default: 2000)
    ORC_BUDGET          session token budget (default: 50000)
    ORC_FORCE_MODEL     override model selection
    ORC_FORCE_EFFORT    override effort (low|medium|high|xhigh)
    ORC_OFFLINE         1 = never call API, local only
"""

import os, re, sys, json, time, subprocess
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, '/opt/homebrew/lib/python3.12/site-packages')

# ── Constants ─────────────────────────────────────────────────────────────────

OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
API_KEY      = os.environ.get("ANTHROPIC_API_KEY", "")
MAX_TOKENS   = int(os.environ.get("ORC_MAX_TOKENS", "2000"))
SESSION_BUDGET = int(os.environ.get("ORC_BUDGET", "50000"))
OFFLINE      = os.environ.get("ORC_OFFLINE", "0") == "1"

# Model tiers — ordered cheapest → most capable
LOCAL_MODELS = [
    ("smollm2:135m",   20,    "ultra-fast, 270MB, extraction only"),
    ("gemma3:270m",  1038,    "best tiny quality, 291MB, Ollama default"),
    ("phi4-mini",     556,    "best quality/size, MLX preferred"),
]
API_MODELS = [
    ("claude-haiku-4-5-20251001",  0.25,   1.25,  "fast/cheap, simple tasks"),
    ("claude-sonnet-4-6",          3.00,  15.00,  "balanced, daily driver"),
    ("claude-opus-4-7",           15.00,  75.00,  "max quality, 1M ctx, xhigh effort"),
]

# Task complexity signals → model tier
COMPLEXITY_SIGNALS = {
    "local": [
        r'(summarize|extract|classify|clean|strip|compress|tl;?dr)',
        r'(what (is|are)|quick answer|one sentence|briefly)',
        r'(html|article|page content|text from)',
    ],
    "haiku": [
        r'(list|enumerate|bullet|format|convert|translate|rewrite)',
        r'(simple (question|task|lookup)|fact check|definition)',
        r'(short|concise|compact) (answer|response|summary)',
    ],
    "sonnet": [
        r'(analyze|compare|evaluate|review|explain|describe)',
        r'(code|implement|debug|fix|refactor|write.{0,10}function|write.{0,10}script|write.{0,10}class)',
        r'(plan|design|architecture|strategy|approach)',
    ],
    "opus": [
        r'(complex|advanced|deep|thorough|comprehensive|exhaustive)',
        r'(agentic|multi.?step|long.?horizon|orchestrat)',
        r'(research|investigate|synthesize|reason across)',
        r'(vision|screenshot|image|diagram|chart)',  # Opus 4.7 high-res vision
    ],
}

EFFORT_MAP = {
    "local":  "low",
    "haiku":  "low",
    "sonnet": "medium",
    "opus":   "high",     # default for Opus 4.7
}

# URL patterns → fetch strategy
FETCH_ROUTES = [
    # pattern, strategy, reason
    (r'/(json|health|ping|status|metrics|api/v\d)',       "rtk_curl",    "small JSON API"),
    (r'\.(json|xml|csv|rss|atom)($|\?)',                  "rtk_curl",    "structured data"),
    (r'(github\.com/.+/blob|raw\.githubusercontent)',      "rtk_curl",    "GitHub raw"),
    (r'(docs\.|documentation\.|readme|/docs/)',           "smart_fetch", "documentation"),
    (r'(news\.|blog\.|medium\.|substack\.|article)',      "smart_fetch", "article"),
    (r'(stripe\.com|pricing|plans|checkout|shopify)',     "hyperfetch",  "anti-bot pricing"),
    (r'(cloudflare|datadome|linkedin|instagram|twitter)', "hyperfetch",  "heavy anti-bot"),
]


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class Task:
    query: str                        # what to do / what to answer
    url: Optional[str] = None         # optional: fetch this first
    context: Optional[str] = None     # pre-fetched content (skip fetch step)
    max_tokens: int = MAX_TOKENS
    budget_tokens: int = SESSION_BUDGET
    force_model: Optional[str] = None
    force_effort: Optional[str] = None  # low | medium | high | xhigh
    force_fetch: Optional[str] = None   # rtk_curl | smart_fetch | hyperfetch | none
    offline: bool = OFFLINE
    verbose: bool = False


@dataclass
class Result:
    output: str
    model_used: str
    fetch_strategy: str
    effort: str
    tokens_used: int
    cost_usd: float
    latency_ms: int
    fetch_ms: int
    model_ms: int
    raw_content_tokens: int
    compressed_tokens: int
    compression_ratio: float


# ── Routing logic ─────────────────────────────────────────────────────────────

def classify_complexity(query: str) -> str:
    """Returns: local | haiku | sonnet | opus"""
    q = query.lower()
    # Check from most complex → simplest (first match wins)
    for tier in ["opus", "sonnet", "haiku", "local"]:
        for pattern in COMPLEXITY_SIGNALS[tier]:
            if re.search(pattern, q):
                return tier
    return "haiku"  # default: cheap API


def select_effort(tier: str, force: Optional[str] = None) -> str:
    """Map tier → effort level. Opus 4.7 supports xhigh."""
    if force:
        return force
    effort = EFFORT_MAP.get(tier, "medium")
    # Boost to xhigh for Opus on complex/agentic tasks
    return effort


def route_fetch(url: Optional[str], force: Optional[str] = None) -> tuple:
    """Returns (strategy, reason)"""
    if force:
        return force, "forced"
    if not url:
        return "none", "no URL"
    for pattern, strategy, reason in FETCH_ROUTES:
        if re.search(pattern, url, re.IGNORECASE):
            return strategy, reason
    return "smart_fetch", "default: HTML article"


def select_model(tier: str, offline: bool, force: Optional[str]) -> tuple:
    """Returns (model_id, is_local, tier)"""
    if force:
        is_local = not force.startswith("claude-")
        return force, is_local, tier

    if offline or not API_KEY:
        # Local only: phi4-mini best quality
        if tier == "local":
            return "smollm2:135m", True, "local"
        return "gemma3:270m", True, "local"

    if tier == "local":
        return "gemma3:270m", True, "local"  # free local for simple extract
    if tier == "haiku":
        return "claude-haiku-4-5-20251001", False, "haiku"
    if tier == "sonnet":
        return "claude-sonnet-4-6", False, "sonnet"
    return "claude-opus-4-7", False, "opus"


# ── Fetch implementations ──────────────────────────────────────────────────────

def fetch_content(url: str, strategy: str, verbose: bool = False) -> tuple:
    """Returns (content, fetch_ms, raw_tokens)"""
    t0 = time.perf_counter()

    if strategy == "rtk_curl":
        try:
            r = subprocess.run(["rtk", "curl", "-s", url],
                               capture_output=True, text=True, timeout=15)
            content = r.stdout.strip()
        except Exception as e:
            content = f"[rtk_curl failed: {e}]"

    elif strategy == "smart_fetch":
        try:
            r = subprocess.run(["smart-fetch", url],
                               capture_output=True, text=True, timeout=20)
            content = r.stdout.strip()
        except Exception as e:
            # fallback: trafilatura direct
            try:
                import trafilatura
                downloaded = trafilatura.fetch_url(url)
                content = trafilatura.extract(downloaded) or f"[empty: {url}]"
            except Exception as e2:
                content = f"[fetch failed: {e2}]"

    elif strategy == "hyperfetch":
        try:
            r = subprocess.run(["hyperfetch", url, "--stage", "camoufox"],
                               capture_output=True, text=True, timeout=30)
            content = r.stdout.strip()
        except Exception as e:
            # fallback to smart-fetch
            try:
                r = subprocess.run(["smart-fetch", url],
                                   capture_output=True, text=True, timeout=20)
                content = r.stdout.strip()
            except Exception as e2:
                content = f"[hyperfetch+smart-fetch failed: {e2}]"
    else:
        content = ""

    ms = int((time.perf_counter() - t0) * 1000)
    raw_tokens = len(content.split())
    if verbose:
        print(f"  [fetch:{strategy}] {ms}ms, {raw_tokens}t raw", file=sys.stderr)
    return content, ms, raw_tokens


# ── Local model inference ─────────────────────────────────────────────────────

def run_local_model(model: str, prompt: str, verbose: bool = False) -> tuple:
    """Returns (output, ms). Uses Ollama."""
    t0 = time.perf_counter()
    try:
        import urllib.request
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 512}
        }).encode()
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
            output = data.get("response", "").strip()
    except Exception as e:
        output = f"[local model error: {e}]"
    ms = int((time.perf_counter() - t0) * 1000)
    if verbose:
        print(f"  [model:{model}] {ms}ms, {len(output.split())}t", file=sys.stderr)
    return output, ms


# ── API model inference ────────────────────────────────────────────────────────

def run_api_model(model: str, system: str, user: str,
                  effort: str = "medium", max_tokens: int = 2000,
                  verbose: bool = False) -> tuple:
    """Returns (output, ms, tokens_in, tokens_out). Calls Anthropic API."""
    t0 = time.perf_counter()
    try:
        import urllib.request
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        # Opus 4.7: adaptive thinking via thinking block
        if model == "claude-opus-4-7" and effort in ("high", "xhigh"):
            budget = 8000 if effort == "xhigh" else 3000
            body["thinking"] = {"type": "enabled", "budget_tokens": budget}
            # thinking requires extended_thinking, stream off
        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "interleaved-thinking-2025-05-14",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
            # Extract text blocks (skip thinking blocks)
            output = " ".join(
                b.get("text", "") for b in data.get("content", [])
                if b.get("type") == "text"
            ).strip()
            usage = data.get("usage", {})
            tokens_in  = usage.get("input_tokens", 0)
            tokens_out = usage.get("output_tokens", 0)
    except Exception as e:
        output = f"[API error: {e}]"
        tokens_in = tokens_out = 0
    ms = int((time.perf_counter() - t0) * 1000)
    if verbose:
        print(f"  [api:{model}] effort={effort} {ms}ms in={tokens_in}t out={tokens_out}t", file=sys.stderr)
    return output, ms, tokens_in, tokens_out


# ── Cost calculation ───────────────────────────────────────────────────────────

def calc_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    prices = {m[0]: (m[1], m[2]) for m in API_MODELS}
    if model not in prices:
        return 0.0
    pi, po = prices[model]
    return (tokens_in * pi + tokens_out * po) / 1_000_000


# ── Main orchestrator ─────────────────────────────────────────────────────────

class Orchestrator:
    """
    Auto-routing engine. One call does everything.

    Decision flow:
      URL? → route_fetch() → fetch_content() → compress (trafilatura)
      query → classify_complexity() → select_model() → select_effort()
      → run model → return Result

    Override anything with Task.force_* fields.
    """

    def __init__(self):
        self.session_tokens = 0
        self.session_cost   = 0.0
        self.call_log       = []

    def run(self, task: Task) -> Result:
        t_total = time.perf_counter()

        # ── Step 1: Classify task ────────────────────────────────────────────
        tier      = classify_complexity(task.query)
        effort    = select_effort(tier, task.force_effort)
        model_id, is_local, model_tier = select_model(tier, task.offline, task.force_model)

        # Boost effort to xhigh for Opus 4.7 if complex
        if model_id == "claude-opus-4-7" and tier == "opus":
            effort = task.force_effort or "xhigh"

        if task.verbose:
            print(f"[orc] tier={tier} model={model_id} effort={effort}", file=sys.stderr)

        # ── Step 2: Fetch (if URL provided) ──────────────────────────────────
        fetch_strategy, fetch_reason = route_fetch(task.url, task.force_fetch)
        raw_content = task.context or ""
        fetch_ms = 0
        raw_tokens = len(raw_content.split()) if raw_content else 0

        if task.url and fetch_strategy != "none" and not task.context:
            raw_content, fetch_ms, raw_tokens = fetch_content(
                task.url, fetch_strategy, task.verbose)

        # ── Step 3: Compress content if large ────────────────────────────────
        compressed = raw_content
        if raw_content and raw_tokens > 500:
            try:
                import trafilatura
                # Try to strip HTML noise if trafilatura can help
                compressed = trafilatura.extract(raw_content) or raw_content
            except Exception:
                pass
        compressed_tokens = len(compressed.split())

        if task.verbose and raw_tokens > 0:
            ratio = compressed_tokens / max(raw_tokens, 1)
            print(f"[orc] content: {raw_tokens}t raw → {compressed_tokens}t compressed ({ratio:.0%})", file=sys.stderr)

        # ── Step 4: Build prompt ──────────────────────────────────────────────
        system = (
            "You are a precise AI assistant. Answer concisely. "
            "If given content, answer from that content only. "
            "No preamble. No meta-commentary. Just the answer."
        )
        user_parts = []
        if compressed:
            user_parts.append(f"CONTENT:\n{compressed[:6000]}\n")
        user_parts.append(f"TASK: {task.query}")
        user_msg = "\n".join(user_parts)

        # ── Step 5: Run model ────────────────────────────────────────────────
        tokens_in = tokens_out = 0
        model_ms = 0

        if is_local:
            prompt = f"{system}\n\n{user_msg}"
            output, model_ms = run_local_model(model_id, prompt, task.verbose)
            tokens_in  = len(prompt.split())
            tokens_out = len(output.split())
        else:
            output, model_ms, tokens_in, tokens_out = run_api_model(
                model_id, system, user_msg,
                effort=effort, max_tokens=task.max_tokens, verbose=task.verbose
            )

        # ── Step 6: Track + return ────────────────────────────────────────────
        total_tokens = tokens_in + tokens_out
        cost = calc_cost(model_id, tokens_in, tokens_out)
        self.session_tokens += total_tokens
        self.session_cost   += cost
        total_ms = int((time.perf_counter() - t_total) * 1000)

        compression_ratio = (
            compressed_tokens / max(raw_tokens, 1) if raw_tokens > 0 else 1.0
        )

        result = Result(
            output=output,
            model_used=model_id,
            fetch_strategy=fetch_strategy,
            effort=effort,
            tokens_used=total_tokens,
            cost_usd=cost,
            latency_ms=total_ms,
            fetch_ms=fetch_ms,
            model_ms=model_ms,
            raw_content_tokens=raw_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=compression_ratio,
        )
        self.call_log.append(result)
        return result

    def session_summary(self) -> str:
        lines = [
            f"Session: {len(self.call_log)} calls | "
            f"{self.session_tokens:,}t total | "
            f"${self.session_cost:.4f}"
        ]
        by_model = {}
        for r in self.call_log:
            by_model.setdefault(r.model_used, {"calls":0,"tokens":0,"cost":0,"ms":0})
            by_model[r.model_used]["calls"]  += 1
            by_model[r.model_used]["tokens"] += r.tokens_used
            by_model[r.model_used]["cost"]   += r.cost_usd
            by_model[r.model_used]["ms"]     += r.latency_ms
        for m, s in sorted(by_model.items(), key=lambda x: -x[1]["tokens"]):
            lines.append(
                f"  {m:<35} {s['calls']} calls  "
                f"{s['tokens']:>6}t  ${s['cost']:.4f}  avg {s['ms']//s['calls']}ms"
            )
        return "\n".join(lines)


# ── Demo: simulate 8 real use cases ───────────────────────────────────────────

if __name__ == "__main__":
    orch = Orchestrator()

    tasks = [
        # (description, Task config)
        ("UC1: extract article",
         Task(query="extract main article text",
              url="https://example.com", verbose=True)),

        ("UC2: summarize docs page",
         Task(query="summarize this documentation in 3 bullet points",
              context="Claude Opus 4.7 is our most capable model. It supports 1M token context, "
                      "128k max output, adaptive thinking with xhigh effort, and high-resolution "
                      "image input up to 2576px. Best for agentic coding and complex reasoning.",
              verbose=True)),

        ("UC3: simple fact → haiku",
         Task(query="what is the capital of France?", verbose=True)),

        ("UC4: code task → sonnet",
         Task(query="write a Python function to parse CSV and return dict list",
              verbose=True)),

        ("UC5: complex agentic → opus xhigh",
         Task(query="research and synthesize the best token optimization strategies "
                    "for multi-agent systems with complex long-horizon reasoning",
              verbose=True)),

        ("UC6: local extract only (offline)",
         Task(query="summarize this text",
              context="Token optimization reduces Claude Code costs by 93%. "
                      "Use trafilatura for HTML, gemma3:270m for fallback.",
              offline=True, verbose=True)),

        ("UC7: forced haiku override",
         Task(query="what is 2+2?",
              force_model="claude-haiku-4-5-20251001",
              force_effort="low", verbose=True)),

        ("UC8: opus xhigh forced",
         Task(query="analyze the architectural tradeoffs of event-driven vs request-response systems",
              force_model="claude-opus-4-7",
              force_effort="xhigh",
              max_tokens=1000, verbose=True)),
    ]

    print("=" * 70)
    print("ORCHESTRATOR SIMULATION — 8 USE CASES")
    print("=" * 70)

    for label, task in tasks:
        print(f"\n{'─'*70}")
        print(f"{label}")
        print(f"  query: {task.query[:60]}...")

        result = orch.run(task)

        print(f"  model:    {result.model_used}")
        print(f"  effort:   {result.effort}")
        print(f"  fetch:    {result.fetch_strategy} ({result.fetch_ms}ms)")
        print(f"  tokens:   {result.raw_content_tokens}t raw → {result.compressed_tokens}t compressed")
        print(f"  api cost: ${result.cost_usd:.5f}")
        print(f"  total:    {result.latency_ms}ms | {result.tokens_used}t")
        out = result.output[:120].replace('\n', ' ')
        print(f"  output:   {out}{'...' if len(result.output) > 120 else ''}")

    print(f"\n{'='*70}")
    print(orch.session_summary())
    print("=" * 70)
