"""CTS MCP server — exposes CTS savings, cache-replay, and reflection
to other agents (Codex, Cursor, Gemini, Kilo) via Model Context Protocol.

Multiplies adoption: any MCP-aware client gets CTS Layer 6 cache + RTK +
gemma-gate without forking.

Tools exposed:
  cts_cache_check   — query cache by (tool, query, mode); returns hit or null
  cts_cache_write   — store result in shared cache
  cts_compress      — pipe HTML/JSON through gemma-gate
  cts_savings_stats — return cumulative tokens/$ saved
  cts_reflect       — run Haiku critic on a draft answer

Run:
    python -m mcp.cts_mcp_server  (stdio transport; default for Claude Code)

Wire in ~/.claude/settings.json mcpServers:
    "cts": {"command": "python3", "args": ["-m", "mcp.cts_mcp_server"]}
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
except ImportError:
    print(
        "mcp SDK missing. install: pip install mcp",
        file=sys.stderr,
    )
    raise

from core.cache_replay import CacheReplay  # type: ignore

server = Server("cts")
_caches: dict[str, CacheReplay] = {}


def _cache(tool: str) -> CacheReplay:
    if tool not in _caches:
        _caches[tool] = CacheReplay(tool=tool)
    return _caches[tool]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="cts_cache_check",
            description="Look up a cached result. Returns hit text or null.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool": {"type": "string"},
                    "query": {"type": "string"},
                    "mode": {"type": "string", "default": ""},
                },
                "required": ["tool", "query"],
            },
        ),
        Tool(
            name="cts_cache_write",
            description="Store a result for later replay.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool": {"type": "string"},
                    "query": {"type": "string"},
                    "payload": {"type": "string"},
                    "mode": {"type": "string", "default": ""},
                },
                "required": ["tool", "query", "payload"],
            },
        ),
        Tool(
            name="cts_savings_stats",
            description="Cumulative token + $ savings across CTS layers.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="cts_reflect",
            description=(
                "Run a Haiku critic against a draft answer. Returns "
                "{verdict, issues[], patched_answer}."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "draft": {"type": "string"},
                },
                "required": ["task", "draft"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, args: dict) -> list[TextContent]:
    if name == "cts_cache_check":
        cr = _cache(args["tool"])
        hit = cr.check(args["query"], mode=args.get("mode", ""))
        return [TextContent(type="text", text=hit.decode() if hit else "null")]

    if name == "cts_cache_write":
        cr = _cache(args["tool"])
        cr.write(args["query"], args["payload"], mode=args.get("mode", ""))
        return [TextContent(type="text", text="ok")]

    if name == "cts_savings_stats":
        # walk all per-tool perf DBs
        root = Path.home() / ".claude" / "cache"
        rows = []
        if root.exists():
            for tdir in root.iterdir():
                pdb = tdir / "perf.db"
                if pdb.exists():
                    import sqlite3

                    with sqlite3.connect(pdb) as c:
                        n, total_bytes = c.execute(
                            "SELECT COUNT(*), COALESCE(SUM(result_bytes),0) FROM perf"
                        ).fetchone()
                    rows.append({"tool": tdir.name, "calls": n, "bytes": total_bytes})
        return [TextContent(type="text", text=json.dumps(rows, indent=2))]

    if name == "cts_reflect":
        from core.reflection import reflect  # lazy

        result = reflect(task=args["task"], draft=args["draft"])
        return [TextContent(type="text", text=json.dumps(result))]

    return [TextContent(type="text", text=f"unknown tool: {name}")]


async def main() -> None:
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
