#!/usr/bin/env python3
# Local LLM summarizer gate. Runs phi4-mini/gemma via Ollama before output hits Claude.
# Token threshold triggered — small outputs pass through unchanged.
# Includes HTML preprocessor (strips tags) and input truncation.

import json
import os
import sys
import re
from urllib.request import Request, urlopen
from urllib.error import URLError
from html.parser import HTMLParser

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("CTS_GEMMA_MODEL", "phi4-mini:latest")
THRESHOLD = int(os.environ.get("CTS_GEMMA_THRESHOLD", "200"))
MAX_INPUT_CHARS = int(os.environ.get("CTS_GEMMA_MAX_INPUT", "4096"))
EXTRACT_PROMPT = os.environ.get("CTS_GEMMA_EXTRACT", "").strip()

DEFAULT_SYSTEM = """You are a token-budget summarizer for an AI coding agent.
Extract ONLY the facts the agent needs to act. Drop formatting, preamble, boilerplate.
Output format:
- Maximum 5 bullet points
- Each bullet <= 15 words
- Preserve: error messages, file paths, line numbers, API responses, key values, titles, prices, dates
- Drop: HTML/XML tags, marketing, repeated output, ASCII art, progress bars, stack trace middle frames, cookie banners, navigation menus
- If nothing useful: output "[empty]"
- Never output tags like <!DOCTYPE> or <html> — the input was HTML but you write plain text
"""

MARKDOWN_SYSTEM = """Convert the input web page content to clean Markdown.
Rules:
- Preserve headings as #, ##, ###
- Preserve links as [text](url) only if informative
- Preserve lists, code blocks, quotes
- Drop: nav menus, footers, cookie banners, ads, "subscribe to newsletter" blocks, social share widgets
- Keep it under 1000 words. If the input is longer, prioritize the main article body.
"""


class _TagStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_stack = 0
        self._skip_tags = {"script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "form", "button"}

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self._skip_tags:
            self.skip_stack += 1
        elif tag.lower() in ("p", "br", "li", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self._skip_tags and self.skip_stack > 0:
            self.skip_stack -= 1

    def handle_data(self, data):
        if self.skip_stack == 0:
            txt = data.strip()
            if txt:
                self.parts.append(txt + " ")

    def get_text(self):
        raw = "".join(self.parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def looks_like_html(text: str) -> bool:
    head = text[:500].lower().lstrip()
    return head.startswith("<!doctype") or head.startswith("<html") or ("<head" in head and "<body" in text[:2000].lower())


def preprocess(text: str) -> str:
    """Strip HTML tags if input looks like HTML, collapse whitespace, truncate."""
    if looks_like_html(text):
        try:
            parser = _TagStripper()
            parser.feed(text)
            text = parser.get_text()
        except Exception:
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_INPUT_CHARS:
        head = text[: MAX_INPUT_CHARS // 2]
        tail = text[-MAX_INPUT_CHARS // 2:]
        text = f"{head}\n...[truncated]...\n{tail}"
    return text


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def call_ollama(prompt: str, system: str, timeout: int = 60) -> str | None:
    payload = json.dumps({
        "model": MODEL,
        "prompt": f"{system}\n\nINPUT:\n{prompt}\n\nOUTPUT:",
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 300, "num_ctx": 4096},
    }).encode()
    req = Request(f"{OLLAMA_URL}/api/generate", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data.get("response", "").strip()
    except (URLError, TimeoutError, json.JSONDecodeError):
        return None


def extractive_fallback(text: str, max_lines: int = 5) -> str:
    cleaned = preprocess(text) if looks_like_html(text) else text
    lines = [l.strip() for l in cleaned.splitlines() if l.strip()]
    if not lines:
        return "[empty]"
    signals = []
    for line in lines:
        if re.search(r"error|fail|exception|traceback|warn|critical|title:|price|\\$\\d", line, re.I):
            signals.append(line)
        elif re.match(r"^[A-Z][^.!?]{20,120}[.!?]", line):
            signals.append(line)
    picks = (signals + lines)[:max_lines]
    return "\n".join(f"- {l[:120]}" for l in picks)


def summarize(text: str, mode: str = "summary") -> str:
    # Always process when user explicitly asked for markdown/extract, even for small inputs
    if mode == "summary" and estimate_tokens(text) < THRESHOLD:
        return text
    cleaned = preprocess(text)
    if mode == "markdown":
        system = MARKDOWN_SYSTEM
    elif EXTRACT_PROMPT:
        system = f"You extract facts from web content.\n\nTask: {EXTRACT_PROMPT}\n\nOutput only the extracted facts, nothing else. Be concise."
    else:
        system = DEFAULT_SYSTEM
    result = call_ollama(cleaned, system)
    if result and result != "[empty]" and len(result) > 0:
        return result
    return extractive_fallback(text)


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
    else:
        print(f"unknown args: {args}", file=sys.stderr)
        sys.exit(2)

    text = sys.stdin.read()
    result = summarize(text, mode=mode)
    sys.stdout.write(result)


if __name__ == "__main__":
    main()
