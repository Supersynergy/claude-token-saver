"""Adaptive routing — URL/query/command → cheapest viable strategy.

Three routers, one file:

1. fetch_stage(url)   — pick curl | curl_cffi | browser based on host history
2. model_tier(query)  — pick haiku | sonnet | opus based on query complexity
3. detect_backfire(cmd) — warn on commands that waste more tokens than they save

All heuristics are universal (no personal hosts/aliases). Callers adapt by
swapping the stage list, model IDs, or backfire patterns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .host_memory import HostMemory
from .tool_registry import BACKFIRE_PATTERNS


DEFAULT_FETCH_STAGES = ["curl", "curl_cffi", "browser_stealth"]

TIER_HAIKU  = "claude-haiku-4-5"
TIER_SONNET = "claude-sonnet-4-6"
TIER_OPUS   = "claude-opus-4-7"


@dataclass
class FetchPlan:
    stage: str
    confidence: float
    reason: str


@dataclass
class ModelChoice:
    model: str
    effort: str  # "low" | "medium" | "high"
    reason: str


@dataclass
class BackfireWarning:
    matched: str
    suggestion: str


# ---------- Fetch routing ----------

JSON_API_HINT = re.compile(r"/(json|api|health|ping|v\d+/)", re.I)
KNOWN_ANTIBOT_HINT = re.compile(r"(cloudflare|datadome|akamai|perimeterx)", re.I)


def fetch_stage(url: str, memory: HostMemory | None = None,
                stages: Iterable[str] = DEFAULT_FETCH_STAGES) -> FetchPlan:
    stages = list(stages)
    # Cheap heuristic: JSON endpoints almost always work with plain curl.
    if JSON_API_HINT.search(url):
        return FetchPlan(stages[0], 0.9, "json-api-hint")
    if KNOWN_ANTIBOT_HINT.search(url):
        return FetchPlan(stages[-1], 0.8, "antibot-hint")
    if memory is None:
        return FetchPlan(stages[0], 0.5, "no-memory")
    a = memory.advise(url, stages)
    return FetchPlan(a.stage, a.confidence, a.reason)


# ---------- Model tier routing ----------

HEAVY_INTENT = re.compile(
    r"\b(design|architect|refactor|migrate|debug|analyze|audit|plan|synthesize)\b",
    re.I,
)
TRIVIAL_INTENT = re.compile(
    r"\b(list|show|get|fetch|print|count|rename|format|lint)\b",
    re.I,
)


def model_tier(query: str, has_tools: bool = False, long_context: bool = False) -> ModelChoice:
    q = query.strip()
    if long_context or len(q) > 4000:
        return ModelChoice(TIER_OPUS, "high", "long-context")
    if HEAVY_INTENT.search(q) and (has_tools or len(q) > 400):
        return ModelChoice(TIER_OPUS, "high", "heavy-intent")
    if TRIVIAL_INTENT.search(q) and len(q) < 200:
        return ModelChoice(TIER_HAIKU, "low", "trivial-intent")
    return ModelChoice(TIER_SONNET, "medium", "default")


# ---------- Backfire detection ----------

_compiled_backfire = [(re.compile(p), s) for p, s in BACKFIRE_PATTERNS]


def detect_backfire(command: str) -> BackfireWarning | None:
    for pat, suggestion in _compiled_backfire:
        if pat.search(command):
            return BackfireWarning(pat.pattern, suggestion)
    return None
