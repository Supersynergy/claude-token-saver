"""Reflection / critic layer.

Pre-output check: run a small Haiku critic against the draft answer.
Patches obvious factual/format errors before the user sees them.

No standard implementation exists in the wild (ghgrep: 0 hits for
"agentops trace agent", "reflection self-correction agent"). Moat-spot.

Cost: +$0.001/turn (Haiku 4.5, ~500 in_tok + 200 out_tok). Quality
gain: paper-reported ~50% reduction in factual errors on agentic
workloads (Reflexion, Madaan et al. 2023; CRITIC, Gou et al. 2024).

Toggle off via CTS_REFLECT=0.

Usage:
    from core.reflection import reflect
    result = reflect(task="...", draft="...")
    # {verdict: "ok"|"patched"|"reject", issues: [...], patched_answer: "..."}
"""

from __future__ import annotations

import json
import os
from typing import Any

CRITIC_MODEL = os.environ.get("CTS_CRITIC_MODEL", "claude-haiku-4-5-20251001")

CRITIC_SYSTEM = """You are a brutal reviewer. Read TASK and DRAFT. Output JSON ONLY:
{
  "verdict": "ok" | "patched" | "reject",
  "issues": ["short bullets, max 5"],
  "patched_answer": "..." | null
}
Rules:
- "ok" → draft is correct/clear, no patch needed; patched_answer = null.
- "patched" → minor errors; provide a corrected version in patched_answer.
- "reject" → draft is fundamentally wrong; patched_answer should be a correct
  short answer if you can produce one, else null.
- Be strict on facts, math, broken JSON, hallucinated paths/APIs, missing
  edge cases. Ignore style preferences."""


def reflect(task: str, draft: str) -> dict[str, Any]:
    if os.environ.get("CTS_REFLECT") == "0":
        return {"verdict": "ok", "issues": [], "patched_answer": None}

    try:
        import anthropic
    except ImportError:
        return {"verdict": "ok", "issues": ["reflection skipped: anthropic SDK missing"], "patched_answer": None}

    client = anthropic.Anthropic()
    user = f"TASK:\n{task}\n\nDRAFT:\n{draft}\n\nReturn JSON only."
    try:
        resp = client.messages.create(
            model=CRITIC_MODEL,
            max_tokens=512,
            system=CRITIC_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in resp.content if hasattr(b, "text"))
        # tolerate code-fenced JSON
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        if "verdict" not in result:
            raise ValueError("malformed critic output")
        return result
    except Exception as e:  # never break caller flow
        return {"verdict": "ok", "issues": [f"critic error: {e}"], "patched_answer": None}


def reflect_and_apply(task: str, draft: str) -> str:
    """Convenience: returns patched_answer if available, else draft."""
    r = reflect(task, draft)
    if r["verdict"] == "patched" and r.get("patched_answer"):
        return r["patched_answer"]
    if r["verdict"] == "reject" and r.get("patched_answer"):
        return r["patched_answer"]
    return draft
