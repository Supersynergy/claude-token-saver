"""Power-tools routing table — map intent → best modern CLI.

Universal table distilled from 2026 tool-benchmarks. No personal aliases.
Each entry: intent key → (preferred, fallback, why, typical_savings_vs_stock).

Callers use `suggest(intent)` to get the recommended command for a generic need.
Missing-tool detection: `check_installed()` returns the subset actually available.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolHint:
    preferred: str      # command binary name
    fallback: str       # stock-unix or widely-available alt
    why: str            # one-line reason
    intent: str         # human-readable intent


# Ordered: most-impactful multipliers first.
REGISTRY: dict[str, ToolHint] = {
    "code_text_search":      ToolHint("rg",        "grep",   "2-10x faster, smart ignore",              "search text in code"),
    "code_struct_search":    ToolHint("ast-grep",  "grep",   "AST-aware, no regex pitfalls",            "find/rewrite code by syntax"),
    "code_struct_rewrite":   ToolHint("comby",     "sed",    "syntactic rewrite, cross-lang",           "refactor across files"),
    "security_scan":         ToolHint("semgrep",   "grep",   "OWASP rules, taint, --autofix",           "scan for vulns"),
    "code_diff_review":      ToolHint("difft",     "diff",   "syntax-aware diff",                       "review a diff"),
    "file_find":             ToolHint("fd",        "find",   "5x faster, sane defaults",                "find files by name"),
    "string_replace":        ToolHint("sd",        "sed",    "no escaping hell",                        "replace string in file"),
    "json_query":            ToolHint("jq",        "python", "JSON DSL, streaming",                     "extract from JSON"),
    "yaml_query":            ToolHint("yq",        "python", "jq-like for YAML/TOML",                   "extract from YAML"),
    "bench_cli":             ToolHint("hyperfine", "time",   "statistical benchmarking",                "benchmark commands"),
    "code_stats":            ToolHint("tokei",     "wc",     "fast SLOC, language-aware",               "count lines by lang"),
    "disk_usage":            ToolHint("dust",      "du",     "sorted tree, colour",                     "find disk hogs"),
    "process_inspect":       ToolHint("procs",     "ps",     "human columns, search",                   "inspect processes"),
    "http_test":             ToolHint("xh",        "curl",   "httpie-compatible, faster",               "quick HTTP test"),
    "log_nav":               ToolHint("lnav",      "less",   "auto-format, SQL queries",                "navigate logs"),
    "csv_process":           ToolHint("mlr",       "awk",    "named fields, CSV-native",                "process CSV/TSV"),
    "listing":               ToolHint("eza",       "ls",     "git status, tree, icons",                 "list directory"),
    "pager_cat":             ToolHint("bat",       "cat",    "syntax highlight, line numbers",          "view file contents"),
    "python_lint":           ToolHint("ruff",      "flake8", "lint+format in one, 100x faster",         "lint/format Python"),
    "watch_rerun":           ToolHint("watchexec", "inotify","event-driven rerun",                      "rerun on file change"),
    "version_mgr":           ToolHint("mise",      "asdf",   "single tool for all runtimes",            "manage language versions"),
    "task_runner":           ToolHint("just",      "make",   "simple recipes, no tab traps",            "run project tasks"),
    "html_to_text":          ToolHint("trafilatura","readability","best extraction quality",            "clean HTML to text"),
    "secrets_scan":          ToolHint("gitleaks",  "grep",   "secret patterns + git history",           "scan for leaked secrets"),
    "cve_scan":              ToolHint("osv-scanner","grype", "OSV.dev database",                        "scan deps for CVEs"),
}


# Commands that typically WASTE tokens vs a Claude-native tool.
BACKFIRE_PATTERNS: list[tuple[str, str]] = [
    (r"^cat\s",             "use Read tool"),
    (r"^find\s.*-name",     "use Glob tool or `fd`"),
    (r"^grep\s",            "use Grep tool or `rg`"),
    (r"^ls\s",              "use Glob tool or `eza`"),
    (r"^head\s|^tail\s",    "use Read tool with offset/limit"),
    (r"^(sed|awk)\s.*-i",   "use Edit tool"),
    (r"^echo\s.*>",         "use Write tool"),
    (r"^printf\s.*>",       "use Write tool"),
    (r"^wc\s+-l",           "use Read tool or `tokei`"),
    (r"^du\s+-sh",          "use `dust`"),
    (r"^ps\s+(aux|-ef)",    "use `procs`"),
    (r"^curl\s+[^|]*$",     "use `xh` for tests / WebFetch-alt"),
    (r"\|\s*wc\s+-l\s*$",   "count via tool's native flag"),
    (r"^tree\s",            "use Glob or `eza --tree`"),
    (r"^(pip|poetry)\s+install", "use `uv` / `mise`"),
    (r"^npm\s+install\s*$", "use `pnpm`/`bun`"),
]


def suggest(intent: str) -> ToolHint | None:
    return REGISTRY.get(intent)


def check_installed() -> dict[str, bool]:
    """Return {binary: is_installed} for every preferred tool."""
    return {h.preferred: shutil.which(h.preferred) is not None for h in REGISTRY.values()}


def missing() -> list[str]:
    return [name for name, ok in check_installed().items() if not ok]
