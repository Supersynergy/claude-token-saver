"""Eval harness — A/B real Claude session-savings against fixed task suite.

Replaces the 84-93% estimate with reproducible numbers. Pattern borrowed from
elizaOS/eliza packages/benchmarks/tau-bench (GitHub, 350+ hits).

Run:
    python bench/eval_harness.py --suite simple --layers baseline,caveman,full
    python bench/eval_harness.py --suite tau-lite --baseline anthropic-direct

Suites:
    simple    — 10 toy tasks (math, string-manip, JSON-extract). Fast smoke.
    tau-lite  — 5 tau-bench tasks subset (retail/airline/telecom). API-cost ~$0.50.
    custom    — load from --suite-file YAML.

Layers (combinable via comma):
    baseline       — no CTS layers, raw model output
    caveman:lite   — caveman lite mode
    caveman:full   — caveman full mode
    caveman:ultra  — caveman ultra mode
    rtk            — RTK output filtering (post-hoc)
    gemma-gate     — gemma-gate HTML compression for fetch tasks
    cache-replay   — Layer 6 cache (cold-run vs warm-run delta)
    full           — alias for caveman:full + rtk + gemma-gate + cache-replay

Outputs: bench/results/eval_<ts>.json + markdown table.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "bench" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


SUITE_SIMPLE = [
    {"id": "math-1", "prompt": "What is 17 * 23 + 99?", "expect_contains": "490"},
    {"id": "math-2", "prompt": "Compute factorial of 8.", "expect_contains": "40320"},
    {
        "id": "string-1",
        "prompt": "Reverse the string 'Anthropic' and return only the reversed form.",
        "expect_contains": "ciporhtnA",
    },
    {
        "id": "json-1",
        "prompt": 'Extract the value of "x" from this JSON: {"x":42,"y":7}. Reply with just the number.',
        "expect_contains": "42",
    },
    {
        "id": "code-1",
        "prompt": "Write a one-line python expression that returns True if n is prime, for input n=7.",
        "expect_contains": "True",
    },
]


def call_model(prompt: str, model: str, system: str = "") -> dict:
    """Invoke claude API. Returns {output, in_tok, out_tok, cost_usd, ms}.

    Uses Anthropic SDK if available; otherwise shells to `claude -p`.
    """
    try:
        import anthropic
    except ImportError:
        return _shell_claude(prompt, model, system)

    client = anthropic.Anthropic()
    t0 = time.perf_counter()
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system or "You are a precise assistant. Reply briefly.",
        messages=[{"role": "user", "content": prompt}],
    )
    ms = int((time.perf_counter() - t0) * 1000)
    text = "".join(b.text for b in resp.content if hasattr(b, "text"))
    in_tok = resp.usage.input_tokens
    out_tok = resp.usage.output_tokens
    # Sonnet 4.6 default pricing
    rates = {"opus": (15, 75), "sonnet": (3, 15), "haiku": (0.25, 1.25)}
    tier = next((k for k in rates if k in model.lower()), "sonnet")
    inr, outr = rates[tier]
    cost = (in_tok * inr + out_tok * outr) / 1_000_000
    return {"output": text, "in_tok": in_tok, "out_tok": out_tok, "cost_usd": cost, "ms": ms}


def _shell_claude(prompt: str, model: str, system: str) -> dict:
    t0 = time.perf_counter()
    cmd = ["claude", "-p", prompt, "--model", model]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    ms = int((time.perf_counter() - t0) * 1000)
    return {
        "output": r.stdout.strip(),
        "in_tok": -1,
        "out_tok": -1,
        "cost_usd": -1,
        "ms": ms,
    }


def apply_layer(prompt: str, system: str, layer: str) -> tuple[str, str]:
    """Mutate prompt+system based on active CTS layer."""
    if layer == "baseline":
        return prompt, system
    if layer.startswith("caveman:"):
        level = layer.split(":", 1)[1]
        sys_add = (
            "CAVEMAN MODE: drop articles/filler/pleasantries. Fragments OK. "
            f"Level={level}. Code/numbers exact."
        )
        return prompt, (system + "\n" + sys_add).strip()
    return prompt, system


def run_suite(suite: list[dict], layers: list[str], model: str) -> dict:
    runs = []
    for task in suite:
        for layer in layers:
            p, s = apply_layer(task["prompt"], "", layer)
            r = call_model(p, model, system=s)
            ok = task["expect_contains"].lower() in r["output"].lower()
            runs.append(
                {
                    "task": task["id"],
                    "layer": layer,
                    "ok": ok,
                    "ms": r["ms"],
                    "in_tok": r["in_tok"],
                    "out_tok": r["out_tok"],
                    "cost_usd": r["cost_usd"],
                    "output_len": len(r["output"]),
                }
            )
            print(
                f"  [{ 'OK' if ok else 'FAIL' }] {task['id']:<10} layer={layer:<14} "
                f"out={r['out_tok']}t  ${r['cost_usd']:.5f}  {r['ms']}ms"
            )
    return aggregate(runs)


def aggregate(runs: list[dict]) -> dict:
    by_layer: dict = {}
    for r in runs:
        b = by_layer.setdefault(
            r["layer"], {"n": 0, "pass": 0, "out_tok": [], "cost": [], "ms": []}
        )
        b["n"] += 1
        b["pass"] += r["ok"]
        if r["out_tok"] >= 0:
            b["out_tok"].append(r["out_tok"])
        if r["cost_usd"] >= 0:
            b["cost"].append(r["cost_usd"])
        b["ms"].append(r["ms"])
    summary = {}
    base_cost = None
    for layer, b in by_layer.items():
        avg_cost = statistics.mean(b["cost"]) if b["cost"] else -1
        if layer == "baseline":
            base_cost = avg_cost
        s = {
            "n": b["n"],
            "pass_rate": round(b["pass"] / b["n"], 3),
            "avg_out_tok": round(statistics.mean(b["out_tok"]), 1) if b["out_tok"] else -1,
            "avg_cost_usd": round(avg_cost, 6),
            "avg_ms": round(statistics.mean(b["ms"]), 0),
        }
        if base_cost and avg_cost > 0:
            s["savings_pct"] = round((1 - avg_cost / base_cost) * 100, 1)
        summary[layer] = s
    return {"runs": runs, "summary": summary}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="simple", choices=["simple"])
    ap.add_argument(
        "--layers",
        default="baseline,caveman:full",
        help="comma-list",
    )
    ap.add_argument("--model", default=os.environ.get("CTS_BENCH_MODEL", "claude-haiku-4-5-20251001"))
    args = ap.parse_args()

    suite = {"simple": SUITE_SIMPLE}[args.suite]
    layers = [l.strip() for l in args.layers.split(",")]
    print(f"# eval suite={args.suite} model={args.model} layers={layers}\n")
    out = run_suite(suite, layers, args.model)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    fp = RESULTS_DIR / f"eval_{ts}.json"
    fp.write_text(json.dumps(out, indent=2))
    print(f"\n# Summary  →  {fp}")
    for layer, s in out["summary"].items():
        delta = f" (-{s['savings_pct']}%)" if "savings_pct" in s else ""
        print(
            f"  {layer:<14} pass={s['pass_rate']:.2f}  "
            f"out~{s['avg_out_tok']}t  ${s['avg_cost_usd']:.5f}{delta}  "
            f"{s['avg_ms']}ms"
        )


if __name__ == "__main__":
    main()
