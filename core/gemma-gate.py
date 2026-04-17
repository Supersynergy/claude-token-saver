#!/usr/bin/env python3
"""
gemma-gate.py — HTML/text summarizer gate for AI coding agent context windows.

Pipeline (fastest → slowest, auto-escalates only when needed):
  1. trafilatura (0ms, no LLM)    → covers 90% of HTML pages
  2. MLX local inference (~556ms) → Phi-4-mini-instruct on Apple Silicon
  3. Ollama fallback (~1038ms)    → gemma3:270m or configured model
  4. Extractive fallback (0ms)    → regex signal extraction, no LLM

CatBoost pre-filter: classifies chunks as signal vs noise BEFORE LLM sees them.
  Only activates for scraping pipelines (CTS_CATBOOST=1).

Config (env vars):
  CTS_GEMMA_MODEL       Ollama model name (default: gemma3:270m)
  CTS_MLX_MODEL         MLX model path (default: mlx-community/Phi-4-mini-instruct-4bit)
  CTS_MLX_FAST_MODEL    Small MLX model (default: mlx-community/Phi-4-mini-instruct-4bit)
  CTS_GEMMA_THRESHOLD   Token threshold to trigger LLM (default: 200)
  CTS_GEMMA_MAX_INPUT   Max chars fed to LLM (default: 4096)
  CTS_FORCE_LLM         1 = always use LLM even if trafilatura succeeds
  CTS_CATBOOST          1 = enable CatBoost noise pre-filter
  CTS_CATBOOST_MODEL    Path to trained .cbm model file
  CTS_GEMMA_EXTRACT     Extraction prompt (for --extract mode)
  OLLAMA_URL            Ollama server URL (default: http://127.0.0.1:11434)

Attribution:
  trafilatura  https://github.com/adbar/trafilatura
  mlx-lm       https://github.com/ml-explore/mlx-lm
  Qwen3        https://huggingface.co/Qwen
  catboost     https://github.com/catboost/catboost
"""

import json
import os
import sys
import re
import time
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import URLError

# ── Config ────────────────────────────────────────────────────────────────────
OLLAMA_URL    = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
# gemma3:270m: 291MB, ~1038ms, 23t output, best tiny quality (2026-04-17 benchmark)
# qwen3 (any size) REMOVED — thinking mode, 160t verbose, 1973ms — not instruct-tuned
OLLAMA_MODEL  = os.environ.get("CTS_GEMMA_MODEL", "gemma3:270m")
# Phi-4-mini-instruct: 2.2GB, ~35ms warm, 94% quality — best instruction-following for summarization
# Benchmarked 2026-04-16 on M4 Max: 118t→55t (-53%), proper structured output
# Qwen3-0.6B NOT suitable — fails instruction following, echoes input instead of summarizing
MLX_MODEL     = os.environ.get("CTS_MLX_MODEL", "mlx-community/Phi-4-mini-instruct-4bit")
MLX_FAST      = os.environ.get("CTS_MLX_FAST_MODEL", "mlx-community/Phi-4-mini-instruct-4bit")
THRESHOLD     = int(os.environ.get("CTS_GEMMA_THRESHOLD", "200"))
MAX_CHARS     = int(os.environ.get("CTS_GEMMA_MAX_INPUT", "4096"))
FORCE_LLM     = os.environ.get("CTS_FORCE_LLM", "0") == "1"
USE_CATBOOST  = os.environ.get("CTS_CATBOOST", "0") == "1"
CB_MODEL_PATH = os.environ.get("CTS_CATBOOST_MODEL", "")
EXTRACT_PROMPT = os.environ.get("CTS_GEMMA_EXTRACT", "").strip()

# ── Prompts ───────────────────────────────────────────────────────────────────
SUMMARY_SYSTEM = """\
Token-budget summarizer for AI coding agent. Extract ONLY facts the agent needs.
Output: max 5 bullets, each ≤15 words. /nothink
Preserve: errors, file paths, line numbers, API values, prices, dates, titles.
Drop: HTML tags, marketing, navs, footers, cookie banners, ASCII art, progress bars.
If nothing useful: output "[empty]"
"""

MARKDOWN_SYSTEM = """\
Convert web page to clean Markdown. /nothink
Keep: headings (#/##/###), informative links, lists, code blocks.
Drop: nav, footer, cookie banners, ads, share widgets, newsletter blocks.
Max 1000 words. Prioritize main article body.
"""


# ── HTML Preprocessor ────────────────────────────────────────────────────────
class _TagStripper(HTMLParser):
    _SKIP = {"script", "style", "nav", "footer", "header", "aside",
              "noscript", "svg", "form", "button", "iframe"}
    _BLOCK = {"p", "br", "li", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}

    def __init__(self):
        super().__init__()
        self.parts, self.skip_stack = [], 0

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in self._SKIP:
            self.skip_stack += 1
        elif t in self._BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self._SKIP and self.skip_stack > 0:
            self.skip_stack -= 1

    def handle_data(self, data):
        if self.skip_stack == 0:
            txt = data.strip()
            if txt:
                self.parts.append(txt + " ")

    def get_text(self):
        raw = "".join(self.parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        return re.sub(r"\n{3,}", "\n\n", raw).strip()


def looks_like_html(text: str) -> bool:
    h = text[:500].lower().lstrip()
    return h.startswith("<!doctype") or h.startswith("<html") or (
        "<head" in h and "<body" in text[:2000].lower()
    )


# ── Trafilatura (fastest, no LLM) ────────────────────────────────────────────
def try_trafilatura(html: str) -> str | None:
    """Try trafilatura extraction. Returns None if unavailable or empty result."""
    try:
        # Support both homebrew and system python paths
        import trafilatura
    except ImportError:
        try:
            sys.path.insert(0, "/opt/homebrew/lib/python3.12/site-packages")
            import trafilatura
        except ImportError:
            return None
    try:
        result = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_precision=True,
        )
        if result and len(result.strip()) > 50:
            return result.strip()
        return None
    except Exception:
        return None


# ── MLX inference (fast local, Apple Silicon) ─────────────────────────────────
_mlx_cache: dict = {}

def try_mlx(text: str, system: str, fast: bool = True) -> str | None:
    """
    Run MLX inference with proper chat template.
    Uses Phi-4-mini-instruct-4bit — best instruction-following for summarization.
    Benchmarked: 118t→55t (-53%), 556ms warm, M4 Max 2026-04-16.

    NOTE: Qwen3-0.6B/1.7B NOT suitable for this task — they echo input instead
    of summarizing. Phi-4-mini-instruct follows structured output instructions correctly.
    """
    model_id = MLX_FAST if fast else MLX_MODEL
    try:
        from mlx_lm import load, generate
        if model_id not in _mlx_cache:
            _mlx_cache[model_id] = load(model_id)
        model, tokenizer = _mlx_cache[model_id]

        # Use chat template if available (Phi-4-mini requires it for proper output)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": text[:MAX_CHARS]},
        ]
        if hasattr(tokenizer, "apply_chat_template"):
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            prompt = f"{system}\n\nINPUT:\n{text[:MAX_CHARS]}\n\nOUTPUT:"

        result = generate(model, tokenizer, prompt=prompt, max_tokens=300, verbose=False)
        result = result.strip()
        # Clean any chat template tokens that leaked
        result = re.sub(r"<\|[^|]+\|>", "", result).strip()
        result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL).strip()
        if result and len(result) > 10:
            return result
        return None
    except Exception:
        return None


# ── Ollama fallback ───────────────────────────────────────────────────────────
def try_ollama(text: str, system: str, timeout: int = 30) -> str | None:
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": f"{system}\n\nINPUT:\n{text[:MAX_CHARS]}\n\nOUTPUT:",
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 300, "num_ctx": 4096},
    }).encode()
    req = Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            result = data.get("response", "").strip()
            return result if result else None
    except (URLError, TimeoutError, json.JSONDecodeError):
        return None


# ── Extractive fallback (0ms, no deps) ───────────────────────────────────────
def extractive_fallback(text: str, max_lines: int = 5) -> str:
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 20]
    signals, rest = [], []
    sig_re = re.compile(r"error|fail|exception|traceback|warn|critical|title:|price|\$\d", re.I)
    for line in lines:
        (signals if sig_re.search(line) else rest).append(line)
    picks = (signals + rest)[:max_lines]
    return "\n".join(f"- {l[:120]}" for l in picks) or "[empty]"


# ── CatBoost noise filter ─────────────────────────────────────────────────────
def catboost_filter_chunks(text: str, min_score: float = 0.5) -> str:
    """
    Split text into paragraphs, score each with CatBoost, keep signal chunks.
    Falls back to full text if model not available.

    Best practice for HTML noise classification:
    Features: char_count, word_count, link_density, digit_ratio, upper_ratio,
              sentence_count, avg_word_len, starts_with_verb
    Train: catboost_train.py with labelled HTML paragraphs (signal=1, noise=0)
    """
    if not CB_MODEL_PATH or not os.path.exists(CB_MODEL_PATH):
        return text
    try:
        from catboost import CatBoostClassifier
        import numpy as np
        model = CatBoostClassifier()
        model.load_model(CB_MODEL_PATH)

        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if len(p.strip()) > 30]
        if not paragraphs:
            return text

        def featurize(p: str) -> list:
            words = p.split()
            chars = len(p)
            links = len(re.findall(r"https?://", p))
            digits = sum(c.isdigit() for c in p)
            uppers = sum(c.isupper() for c in p)
            sentences = len(re.findall(r"[.!?]+", p))
            avg_word = sum(len(w) for w in words) / max(len(words), 1)
            return [
                chars,
                len(words),
                links / max(chars / 100, 1),   # link density
                digits / max(chars, 1),          # digit ratio
                uppers / max(chars, 1),          # uppercase ratio
                sentences,
                avg_word,
                int(bool(words and words[0][0].isupper())),
            ]

        X = np.array([featurize(p) for p in paragraphs])
        scores = model.predict_proba(X)[:, 1]
        kept = [p for p, s in zip(paragraphs, scores) if s >= min_score]
        return "\n\n".join(kept) if kept else text
    except Exception:
        return text


# ── Truncate ──────────────────────────────────────────────────────────────────
def truncate(text: str) -> str:
    if len(text) <= MAX_CHARS:
        return text
    h = MAX_CHARS // 2
    return f"{text[:h]}\n...[truncated]...\n{text[-h:]}"


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


# ── Main pipeline ─────────────────────────────────────────────────────────────
def summarize(text: str, mode: str = "summary") -> str:
    t0 = time.perf_counter()
    is_html = looks_like_html(text)
    tokens_in = estimate_tokens(text)

    # Pass-through: short enough and not forced
    if mode == "summary" and tokens_in < THRESHOLD and not FORCE_LLM:
        return text

    # ── Step 1: trafilatura (HTML only, 0ms, no LLM) ─────────────────────────
    if is_html and not FORCE_LLM and mode != "markdown":
        traf = try_trafilatura(text)
        if traf:
            # CatBoost filter on extracted text if enabled
            if USE_CATBOOST:
                traf = catboost_filter_chunks(traf)
            ms = int((time.perf_counter() - t0) * 1000)
            print(f"[gemma-gate] trafilatura: {tokens_in}t→{estimate_tokens(traf)}t ({ms}ms)", file=sys.stderr)
            return traf

    # ── Preprocess for LLM ────────────────────────────────────────────────────
    if is_html:
        try:
            parser = _TagStripper()
            parser.feed(text)
            cleaned = parser.get_text()
        except Exception:
            cleaned = re.sub(r"<[^>]+>", " ", text)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
    else:
        cleaned = text

    # CatBoost filter before LLM (reduces input tokens)
    if USE_CATBOOST:
        cleaned = catboost_filter_chunks(cleaned)

    cleaned = truncate(cleaned)

    # Select system prompt
    if mode == "markdown":
        system = MARKDOWN_SYSTEM
    elif EXTRACT_PROMPT:
        system = f"Extract facts from web content.\nTask: {EXTRACT_PROMPT}\nOutput only the extracted facts. Be concise. /nothink"
    else:
        system = SUMMARY_SYSTEM

    # ── Step 2: MLX (fast, ~12ms Qwen3-0.6B, ~22ms Qwen3-1.7B) ─────────────
    result = try_mlx(cleaned, system, fast=True)
    if result:
        ms = int((time.perf_counter() - t0) * 1000)
        print(f"[gemma-gate] MLX {MLX_FAST}: {tokens_in}t→{estimate_tokens(result)}t ({ms}ms)", file=sys.stderr)
        return result

    # ── Step 3: Ollama (gemma3:270m, ~1038ms, 23t output) ────────────────────
    result = try_ollama(cleaned, system)
    if result:
        ms = int((time.perf_counter() - t0) * 1000)
        print(f"[gemma-gate] Ollama {OLLAMA_MODEL}: {tokens_in}t→{estimate_tokens(result)}t ({ms}ms)", file=sys.stderr)
        return result

    # ── Step 4: Extractive fallback (0ms) ────────────────────────────────────
    ms = int((time.perf_counter() - t0) * 1000)
    print(f"[gemma-gate] extractive fallback ({ms}ms)", file=sys.stderr)
    return extractive_fallback(cleaned)


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    if not args:
        print("usage: gemma-gate.py --summarize|--markdown|--extract '<prompt>' < input", file=sys.stderr)
        sys.exit(2)

    mode = "summary"
    global EXTRACT_PROMPT
    if args[0] == "--summarize":
        mode = "summary"
    elif args[0] == "--markdown":
        mode = "markdown"
    elif args[0] == "--extract" and len(args) >= 2:
        EXTRACT_PROMPT = args[1]
        mode = "extract"
    elif args[0] == "--benchmark":
        _run_benchmark()
        return
    else:
        print(f"unknown args: {args}", file=sys.stderr)
        sys.exit(2)

    text = sys.stdin.read()
    result = summarize(text, mode=mode)
    sys.stdout.write(result)


def _run_benchmark():
    """Quick self-benchmark to verify pipeline speeds."""
    import urllib.request
    test_html = urllib.request.urlopen("http://example.com", timeout=5).read().decode()
    test_api = '{"status":"ok","version":"1.2.3","data":{"items":[1,2,3],"total":100}}'

    print("=== gemma-gate benchmark ===")
    for label, text in [("HTML page", test_html), ("JSON API", test_api)]:
        t0 = time.perf_counter()
        out = summarize(text)
        ms = int((time.perf_counter() - t0) * 1000)
        print(f"{label}: {estimate_tokens(text)}t → {estimate_tokens(out)}t ({ms}ms)")


if __name__ == "__main__":
    main()
