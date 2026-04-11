#!/usr/bin/env python3
# Real-world benchmark: 20 random shops from profitanalyser DB.
# Tests Python-native hyperfetch on German SMB ecommerce/service sites.

import json
import subprocess
import sys
import time
import statistics
from pathlib import Path

HOME = Path.home()
PY = HOME / ".cts" / "venv" / "bin" / "python"
HF = HOME / ".cts" / "bin" / "hyperfetch.py"
URL_FILE = Path("/tmp/bench20_urls.txt")

if not URL_FILE.exists():
    print(f"URL file missing: {URL_FILE}", file=sys.stderr)
    sys.exit(1)

URLS = [
    line.strip() for line in URL_FILE.read_text().splitlines()
    if line.strip().startswith("http")
]
print(f"Testing {len(URLS)} URLs", file=sys.stderr)


def run(cmd, timeout=45):
    t0 = time.perf_counter()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        ms = (time.perf_counter() - t0) * 1000
        if r.returncode != 0:
            return {"ok": False, "ms": round(ms, 1), "error": r.stderr[:100] or "nonzero"}
        data = json.loads(r.stdout.strip().splitlines()[-1])
        return {"ok": data.get("stage") != "failed", "ms": round(ms, 1), **data}
    except subprocess.TimeoutExpired:
        return {"ok": False, "ms": timeout * 1000, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "ms": 0, "error": str(e)[:100]}


def main():
    results = {"triage_fresh": [], "triage_cache": [], "baseline_bytes": []}

    print("\n# Hyperfetch vs 20 random profitanalyser shops\n", file=sys.stderr)

    for i, url in enumerate(URLS, 1):
        ns = f"pa20-{i}"
        print(f"  [{i}/{len(URLS)}] {url}", file=sys.stderr)

        # Fresh triage
        r_fresh = run([str(PY), str(HF), url, "--team-ns", ns, "--no-cache"])
        results["triage_fresh"].append({"url": url, **r_fresh})

        # Cache hit
        if r_fresh["ok"]:
            r_cache = run([str(PY), str(HF), url, "--team-ns", ns])
            results["triage_cache"].append({"url": url, **r_cache})

    # Compute stats
    ok_fresh = [r for r in results["triage_fresh"] if r.get("ok")]
    ok_cache = [r for r in results["triage_cache"] if r.get("ok")]

    print("\n## Summary\n")
    print(f"- Total URLs tested: {len(URLS)}")
    print(f"- Fresh fetch success: {len(ok_fresh)}/{len(URLS)} ({100*len(ok_fresh)/len(URLS):.0f}%)")
    print(f"- Cache hit success: {len(ok_cache)}/{len(ok_fresh)}")

    if ok_fresh:
        fresh_ms = sorted([r["ms"] for r in ok_fresh])
        fresh_tok = [r.get("tokens", 0) for r in ok_fresh]
        fresh_bytes = [r.get("bytes", 0) for r in ok_fresh]
        baseline_tok = [max(1, b // 4) for b in fresh_bytes]
        reductions = [bt / max(ft, 1) for bt, ft in zip(baseline_tok, fresh_tok)]

        print(f"\n### Fresh fetch latency (ms)")
        print(f"- median: {statistics.median(fresh_ms):.0f}")
        print(f"- p95:    {fresh_ms[int(len(fresh_ms)*0.95)]:.0f}")
        print(f"- max:    {max(fresh_ms):.0f}")
        print(f"- total:  {sum(fresh_ms)/1000:.1f}s")

        print(f"\n### Token efficiency")
        print(f"- baseline total: {sum(baseline_tok):,} tokens")
        print(f"- hyperfetch total: {sum(fresh_tok):,} tokens")
        print(f"- **reduction: {sum(baseline_tok)/max(sum(fresh_tok),1):.1f}x**")
        print(f"- median per-URL: {statistics.median(reductions):.0f}x")
        print(f"- max per-URL:    {max(reductions):.0f}x")

    if ok_cache:
        cache_ms = sorted([r["ms"] for r in ok_cache])
        print(f"\n### Cache hit latency (ms)")
        print(f"- median: {statistics.median(cache_ms):.0f}")
        print(f"- p95:    {cache_ms[int(len(cache_ms)*0.95)]:.0f}")
        print(f"- max:    {max(cache_ms):.0f}")
        print(f"- min:    {min(cache_ms):.0f}")

    # Stage distribution
    stages = {}
    for r in ok_fresh:
        s = r.get("stage", "unknown")
        stages[s] = stages.get(s, 0) + 1
    print(f"\n### Stage distribution")
    for s, c in sorted(stages.items(), key=lambda x: -x[1]):
        print(f"- {s}: {c} ({100*c/max(len(ok_fresh),1):.0f}%)")

    # Errors
    failed = [r for r in results["triage_fresh"] if not r.get("ok")]
    if failed:
        print(f"\n### Failures ({len(failed)})")
        for r in failed:
            print(f"- {r['url'][:50]}: {r.get('error') or r.get('stage','failed')[:50]}")

    # Sample previews
    print(f"\n### Sample previews (first 5)")
    for r in ok_fresh[:5]:
        print(f"\n**{r['url']}** ({r.get('tokens',0)} tokens, {r['ms']:.0f}ms)")
        preview = r.get('preview', '').replace('\n', ' | ')[:200]
        print(f"> {preview}")

    # Save raw
    out = Path(__file__).parent / "profitanalyser_results.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\n(raw data: {out})", file=sys.stderr)


if __name__ == "__main__":
    main()
