#!/usr/bin/env python3
# dsh — DOMShell stateful REPL wrapper.
# Wraps ~/projects/browser-tools/domshell-lite.py as agent-friendly CLI.
# Persistent session, JSON output, path-based DOM navigation.

import asyncio
import json
import os
import sys
import argparse
from pathlib import Path

DOMSHELL_PATH = Path.home() / "projects" / "browser-tools" / "domshell-lite.py"
SESSION_DIR = Path.home() / ".cts" / "dsh-sessions"

sys.path.insert(0, str(DOMSHELL_PATH.parent))
try:
    from domshell_lite import DOMShell  # type: ignore
except Exception:
    import importlib.util
    spec = importlib.util.spec_from_file_location("domshell_lite", DOMSHELL_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    DOMShell = mod.DOMShell


class DshSession:
    def __init__(self, name: str, host: str = "127.0.0.1", port: int = 9222):
        self.name = name
        self.shell = DOMShell(host=host, port=port)
        self.cwd = "/"
        self.session_file = SESSION_DIR / f"{name}.json"

    async def connect(self):
        await self.shell.connect()
        await self._load_state()

    async def _load_state(self):
        if self.session_file.exists():
            try:
                state = json.loads(self.session_file.read_text())
                self.cwd = state.get("cwd", "/")
            except Exception:
                pass

    async def _save_state(self):
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        self.session_file.write_text(json.dumps({"cwd": self.cwd}))

    async def ls(self, path: str | None = None) -> list[dict]:
        target = path or self.cwd
        script = f"""
        (() => {{
          const el = document.querySelector({json.dumps(target)}) || document.body;
          return Array.from(el.children).map((c, i) => ({{
            idx: i,
            tag: c.tagName.toLowerCase(),
            id: c.id || null,
            cls: c.className || null,
            text: (c.innerText || '').slice(0, 60),
          }}));
        }})()
        """
        result = await self.shell.send("Runtime.evaluate", {
            "expression": script, "returnByValue": True,
        })
        return result.get("result", {}).get("value", [])

    async def read(self, selector: str, attr: str = "innerText") -> str:
        script = f"""
        (() => {{
          const el = document.querySelector({json.dumps(selector)});
          if (!el) return null;
          return el[{json.dumps(attr)}] || el.getAttribute({json.dumps(attr)});
        }})()
        """
        result = await self.shell.send("Runtime.evaluate", {
            "expression": script, "returnByValue": True,
        })
        return result.get("result", {}).get("value", "")

    async def click(self, selector: str) -> bool:
        script = f"""
        (() => {{
          const el = document.querySelector({json.dumps(selector)});
          if (!el) return false;
          el.click();
          return true;
        }})()
        """
        result = await self.shell.send("Runtime.evaluate", {
            "expression": script, "returnByValue": True,
        })
        return bool(result.get("result", {}).get("value"))

    async def goto(self, url: str):
        await self.shell.send("Page.navigate", {"url": url})
        await asyncio.sleep(1.5)

    async def eval_js(self, code: str):
        result = await self.shell.send("Runtime.evaluate", {
            "expression": code, "returnByValue": True, "awaitPromise": True,
        })
        return result.get("result", {}).get("value")


async def run_command(args):
    session = DshSession(args.session, host=args.host, port=args.port)
    await session.connect()

    out = None
    if args.cmd == "ls":
        out = await session.ls(args.target)
    elif args.cmd == "read":
        out = await session.read(args.target, args.attr)
    elif args.cmd == "click":
        out = await session.click(args.target)
    elif args.cmd == "goto":
        await session.goto(args.target)
        out = {"navigated": args.target}
    elif args.cmd == "eval":
        out = await session.eval_js(args.target)
    else:
        out = {"error": f"unknown cmd {args.cmd}"}

    await session._save_state()
    print(json.dumps(out, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(prog="dsh", description="DOMShell CLI — agent-friendly DOM navigation")
    p.add_argument("--session", default="default")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=9222)
    p.add_argument("cmd", choices=["ls", "read", "click", "goto", "eval"])
    p.add_argument("target", nargs="?", default=None)
    p.add_argument("--attr", default="innerText")
    args = p.parse_args()
    asyncio.run(run_command(args))


if __name__ == "__main__":
    main()
