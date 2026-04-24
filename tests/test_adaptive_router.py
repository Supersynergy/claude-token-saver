from core.adaptive_router import (
    detect_backfire,
    fetch_stage,
    model_tier,
    TIER_HAIKU,
    TIER_OPUS,
    TIER_SONNET,
)
from core.host_memory import HostMemory
from core.tool_registry import REGISTRY, check_installed


def test_fetch_stage_json_api_hint():
    plan = fetch_stage("https://example.com/api/v1/status")
    assert plan.stage == "curl"
    assert plan.reason == "json-api-hint"


def test_fetch_stage_antibot_hint():
    plan = fetch_stage("https://cloudflare-protected.example.com/")
    assert plan.stage == "browser_stealth"


def test_fetch_stage_with_memory(tmp_path):
    mem = HostMemory(str(tmp_path / "h.db"))
    for _ in range(3):
        mem.record("https://flaky.example.com/page", "curl", success=False)
    plan = fetch_stage("https://flaky.example.com/other", memory=mem)
    assert plan.stage != "curl"


def test_model_tier_trivial():
    assert model_tier("list files").model == TIER_HAIKU


def test_model_tier_heavy():
    q = "analyze this codebase and design a new auth system " * 20
    assert model_tier(q, has_tools=True).model == TIER_OPUS


def test_model_tier_default():
    assert model_tier("write a function to parse CSV").model == TIER_SONNET


def test_backfire_detects_cat():
    w = detect_backfire("cat README.md")
    assert w is not None and "Read tool" in w.suggestion


def test_backfire_detects_find_name():
    w = detect_backfire("find . -name '*.py'")
    assert w is not None


def test_backfire_passes_safe():
    assert detect_backfire("git status") is None


def test_tool_registry_non_empty():
    assert len(REGISTRY) > 10
    assert "code_text_search" in REGISTRY


def test_check_installed_returns_dict():
    result = check_installed()
    assert isinstance(result, dict)
    assert all(isinstance(v, bool) for v in result.values())
