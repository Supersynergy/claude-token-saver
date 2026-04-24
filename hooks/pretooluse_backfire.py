#!/usr/bin/env python3
"""PreToolUse hook — warn on Bash commands that waste tokens.

Wiring (add to ~/.claude/settings.json):

{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Bash",
       "hooks": [{"type": "command",
                  "command": "python3 /path/to/hooks/pretooluse_backfire.py"}]}
    ]
  }
}

Emits a non-blocking warning to stderr. Exit 0 always — never blocks the user.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.adaptive_router import detect_backfire  # noqa: E402


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    command = payload.get("tool_input", {}).get("command", "")
    warn = detect_backfire(command)
    if warn:
        print(f"[cts-backfire] {command!r} → {warn.suggestion}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
