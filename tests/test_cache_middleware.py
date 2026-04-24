"""Tests for core/cache_middleware.py — 3 cases: system-only, system+turns, overflow."""

import pytest

from core.cache_middleware import apply_cache_control, _EPHEMERAL, MAX_CACHE_BLOCKS


def test_system_only():
    msgs, sys_out, tools_out = apply_cache_control(
        messages=[],
        system_prompt="You are helpful.",
    )
    assert tools_out is None
    assert msgs == []
    # system string wrapped into block list with cache_control
    assert isinstance(sys_out, list)
    assert sys_out[-1]["cache_control"] == _EPHEMERAL


def test_system_and_turns():
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
        {"role": "user", "content": "Tell me more"},
    ]
    msgs, sys_out, _ = apply_cache_control(
        messages=messages,
        system_prompt="Be concise.",
        max_cache_blocks=4,
    )
    # system tagged
    assert sys_out[-1]["cache_control"] == _EPHEMERAL
    # last user turn tagged
    last_user = [m for m in msgs if m["role"] == "user"][-1]
    content = last_user["content"]
    assert isinstance(content, list)
    assert content[-1]["cache_control"] == _EPHEMERAL


def test_overflow_past_4_blocks():
    """Ensure we never exceed MAX_CACHE_BLOCKS cache_control annotations."""
    messages = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
    tools = [{"name": f"tool_{i}", "description": f"Tool {i}"} for i in range(3)]
    msgs, sys_out, annotated_tools = apply_cache_control(
        messages=messages,
        system_prompt="sys",
        tools=tools,
        max_cache_blocks=4,
    )

    count = 0
    if isinstance(sys_out, list):
        count += sum(1 for b in sys_out if b.get("cache_control") == _EPHEMERAL)
    elif isinstance(sys_out, str):
        pass  # string means not tagged (shouldn't happen here)

    if annotated_tools:
        count += sum(1 for t in annotated_tools if t.get("cache_control") == _EPHEMERAL)

    for m in msgs:
        content = m["content"]
        if isinstance(content, list):
            count += sum(1 for b in content if b.get("cache_control") == _EPHEMERAL)

    assert count <= MAX_CACHE_BLOCKS, f"Expected ≤{MAX_CACHE_BLOCKS} cache blocks, got {count}"
