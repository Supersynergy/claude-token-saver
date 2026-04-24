"""Anthropic prompt caching helpers — standalone adaptation of langchain_anthropic middleware.

Injects cache_control={"type":"ephemeral"} following Anthropic's rules:
- Max 4 cache_control breakpoints per request
- Minimum ~1024 tokens per cached block (enforced by caller; we just annotate)
- Priority order: system > tools > last N user/assistant turns
"""

from __future__ import annotations

from typing import Any

_EPHEMERAL = {"type": "ephemeral"}

# Anthropic hard limit
MAX_CACHE_BLOCKS = 4


def apply_cache_control(
    messages: list[dict[str, Any]],
    system_prompt: str | list[dict[str, Any]] | None = None,
    tools: list[dict[str, Any]] | None = None,
    max_cache_blocks: int = MAX_CACHE_BLOCKS,
) -> tuple[list[dict[str, Any]], str | list[dict[str, Any]] | None, list[dict[str, Any]] | None]:
    """Annotate messages, system_prompt, and tools with ephemeral cache_control.

    Returns (messages, system_prompt, tools) with cache_control injected.
    Blocks are allocated greedily: system first, then tools, then last user turns.

    Args:
        messages: List of {"role": ..., "content": ...} dicts (modified copies returned).
        system_prompt: String or list-of-blocks system prompt.
        tools: Optional tool definitions list.
        max_cache_blocks: Hard cap on cache_control insertions (default 4).

    Returns:
        Tuple of (annotated_messages, annotated_system, annotated_tools).
    """
    budget = min(max_cache_blocks, MAX_CACHE_BLOCKS)
    annotated_system = system_prompt
    annotated_tools = tools

    # 1. Tag last block of system prompt
    if system_prompt and budget > 0:
        annotated_system = _tag_last_block(system_prompt)
        budget -= 1

    # 2. Tag last tool definition
    if tools and budget > 0:
        annotated_tools = list(tools)
        annotated_tools[-1] = {**annotated_tools[-1], "cache_control": _EPHEMERAL}
        budget -= 1

    # 3. Tag last N user turns (walking backwards)
    annotated_messages = list(messages)
    for i in range(len(annotated_messages) - 1, -1, -1):
        if budget <= 0:
            break
        msg = annotated_messages[i]
        if msg.get("role") in ("user", "assistant"):
            content = msg["content"]
            tagged = _tag_last_block(content)
            if tagged is not content:
                annotated_messages[i] = {**msg, "content": tagged}
                budget -= 1

    return annotated_messages, annotated_system, annotated_tools


def _tag_last_block(
    content: str | list[dict[str, Any]],
) -> str | list[dict[str, Any]]:
    """Return content with cache_control on the last block.

    String content is wrapped into a single text block so cache_control can be set.
    Already-tagged content is returned unchanged.
    """
    if isinstance(content, str):
        return [{"type": "text", "text": content, "cache_control": _EPHEMERAL}]

    if not content:
        return content

    last = content[-1]
    if last.get("cache_control") == _EPHEMERAL:
        return content

    tagged = [*content[:-1], {**last, "cache_control": _EPHEMERAL}]
    return tagged
