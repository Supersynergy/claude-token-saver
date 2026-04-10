#!/usr/bin/env python3
# Local LLM summarizer gate. Runs gemma3/gemma2 via Ollama before output hits Claude.
# Token threshold triggered — small outputs pass through unchanged.

import json
import os
import sys
import re
from urllib.request import Request, urlopen
from urllib.error import URLError

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("CTS_GEMMA_MODEL", "phi4-mini:latest")
THRESHOLD = int(os.environ.get("CTS_GEMMA_THRESHOLD", "500"))

SYSTEM = """You are a token-budget summarizer for an AI coding agent.
Extract ONLY the facts the agent needs to act. Drop formatting, preamble, boilerplate.
Output format:
- Maximum 5 bullet points
- Each bullet ≤ 15 words
- Preserve: error messages, file paths, line numbers, API responses, key values
- Drop: marketing, repeated output, ASCII art, progress bars, stack trace middle frames
- If nothing useful: output "[empty]"
"""


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def call_ollama(prompt: str, timeout: int = 20) -> str | None:
    payload = json.dumps({
        "model": MODEL,
        "prompt": f"{SYSTEM}\n\nINPUT:\n{prompt}\n\nSUMMARY:",
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 200},
    }).encode()
    req = Request(f"{OLLAMA_URL}/api/generate", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data.get("response", "").strip()
    except (URLError, TimeoutError, json.JSONDecodeError):
        return None


def extractive_fallback(text: str, max_lines: int = 5) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return "[empty]"
    signals = []
    for line in lines:
        if re.search(r"error|fail|exception|traceback|warn|critical", line, re.I):
            signals.append(line)
        elif re.match(r"^[/\w.-]+:\d+", line):
            signals.append(line)
    picks = (signals + lines)[:max_lines]
    return "\n".join(f"- {l[:100]}" for l in picks)


def summarize(text: str) -> str:
    if estimate_tokens(text) < THRESHOLD:
        return text
    result = call_ollama(text)
    if result and result != "[empty]":
        return result
    return extractive_fallback(text)


def main():
    args = sys.argv[1:]
    if not args or args[0] != "--summarize":
        print("usage: gemma-gate.py --summarize < input", file=sys.stderr)
        sys.exit(2)
    text = sys.stdin.read()
    summary = summarize(text)
    sys.stdout.write(summary)


if __name__ == "__main__":
    main()
