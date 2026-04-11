#!/usr/bin/env python3
# hyperfetch.py — Python-native Hyperfetch implementation.
# Drop-in replacement for the bash `hyperfetch` CLI with <100ms cache hits.
# Conforms to methoden/hyperfetch/UNIVERSAL_CLI_SPEC.md v1.0.

import argparse
import hashlib
import json
import os
import random
import re
import socket
import sqlite3
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError
from html.parser import HTMLParser

HOME = Path.home()
DB_PATH = Path(os.environ.get("FETCH_CACHE_DB", HOME / ".cts" / "hyperstack.db"))
DEFAULT_MODEL = os.environ.get("FETCH_LOCAL_MODEL", "phi4-mini:latest")
LOCAL_LLM_URL = os.environ.get("FETCH_LOCAL_URL", "http://127.0.0.1:11434/api/generate")
DEFAULT_NS = os.environ.get("FETCH_TEAM_NS", "default")
MAX_INPUT = int(os.environ.get("FETCH_MAX_INPUT", "4096"))
SUMMARY_THRESHOLD = int(os.environ.get("FETCH_SUMMARY_THRESHOLD", "200"))
ROTATE_BROWSERS = os.environ.get("FETCH_ROTATE_PROFILES", "1") == "1"

CHROME_POOL = ["chrome124", "chrome123", "chrome120", "chrome110", "chrome107"]
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "mc_cid", "mc_eid", "_hsenc", "_hsmi", "msclkid",
}
TTL_DEFAULTS = {
    "api": 600,       # 10min
    "static": 86400,  # 24h
    "news": 1800,     # 30min
    "live": 60,       # 1min
}

# ============================================================================
# Per-host rate limiting — prevents hammering the same domain
# ============================================================================
_host_locks: dict[str, threading.Semaphore] = {}
_host_locks_lock = threading.Lock()
_host_failures: dict[str, int] = defaultdict(int)
_host_last_hit: dict[str, float] = {}
PER_HOST_PARALLEL = int(os.environ.get("FETCH_PER_HOST_PARALLEL", "2"))
PER_HOST_DELAY = float(os.environ.get("FETCH_PER_HOST_DELAY", "0.3"))  # seconds between same-host requests
HOST_FAILURE_BLACKLIST = int(os.environ.get("FETCH_HOST_FAILURE_LIMIT", "5"))


def _get_host_lock(host: str) -> threading.Semaphore:
    with _host_locks_lock:
        if host not in _host_locks:
            _host_locks[host] = threading.Semaphore(PER_HOST_PARALLEL)
        return _host_locks[host]


def _host_is_blacklisted(host: str) -> bool:
    return _host_failures[host] >= HOST_FAILURE_BLACKLIST


def _record_host_result(host: str, success: bool):
    if success:
        _host_failures[host] = max(0, _host_failures[host] - 1)
    else:
        _host_failures[host] += 1
    _host_last_hit[host] = time.time()


def _host_polite_delay(host: str):
    """Wait if we hit the same host too recently."""
    last = _host_last_hit.get(host, 0)
    elapsed = time.time() - last
    if elapsed < PER_HOST_DELAY:
        time.sleep(PER_HOST_DELAY - elapsed)

SUMMARY_SYSTEM = """Extract facts for an AI agent.
- Max 5 bullets
- Each bullet <= 15 words
- Preserve: errors, paths, prices, titles, dates, key values
- Drop: HTML tags, nav, footer, marketing, boilerplate, progress bars
- If nothing useful: output "[empty]"
"""

MARKDOWN_SYSTEM = """Convert input web page to clean Markdown.
- Preserve headings (#, ##, ###), lists, links, code blocks
- Drop nav, footers, cookie banners, ads
- Max 1000 words; prioritize main article body
"""


# ============================================================================
# Cache layer (SQLite)
# ============================================================================

def _init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=5, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fetch(
            url TEXT NOT NULL,
            team_ns TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'triage',
            content_hash TEXT,
            stage TEXT,
            bytes INTEGER DEFAULT 0,
            token_estimate INTEGER DEFAULT 0,
            summary TEXT,
            fetched_at INTEGER DEFAULT (strftime('%s','now')),
            fetched_by TEXT,
            UNIQUE(url, team_ns, mode)
        )""")
    # Migration: old schema lacked `mode` column
    cols = [row[1] for row in conn.execute("PRAGMA table_info(fetch)").fetchall()]
    if "mode" not in cols:
        try:
            conn.execute("ALTER TABLE fetch ADD COLUMN mode TEXT NOT NULL DEFAULT 'triage'")
            # Recreate unique constraint — SQLite doesn't support adding to index
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fetch_mode ON fetch(url, team_ns, mode)")
        except Exception:
            pass
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def normalize_url(url: str) -> str:
    try:
        s = urlsplit(url.strip())
    except Exception:
        return url
    scheme = (s.scheme or "https").lower()
    netloc = s.netloc.lower()
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]
    path = s.path.rstrip("/") or "/"
    params = [(k, v) for k, v in parse_qsl(s.query) if k not in TRACKING_PARAMS]
    params.sort()
    query = urlencode(params)
    return urlunsplit((scheme, netloc, path, query, ""))


def cache_lookup(conn, url: str, team_ns: str, mode: str, max_age: int) -> dict | None:
    cutoff = int(time.time()) - max_age
    r = conn.execute(
        "SELECT stage, bytes, token_estimate, summary, fetched_at, fetched_by "
        "FROM fetch WHERE url=? AND team_ns=? AND mode=? AND fetched_at > ? LIMIT 1",
        (url, team_ns, mode, cutoff),
    ).fetchone()
    if not r:
        return None
    return {
        "stage": r[0], "bytes": r[1], "tokens": r[2],
        "summary": r[3] or "", "fetched_at": r[4], "fetched_by": r[5],
    }


def cache_write(conn, url: str, team_ns: str, mode: str, stage: str,
                bytes_: int, tokens: int, summary: str, content_hash: str):
    who = os.environ.get("USER", "unknown")
    # Delete existing row for (url, team_ns, mode) then insert (avoids ON CONFLICT need on multi-column unique)
    conn.execute("DELETE FROM fetch WHERE url=? AND team_ns=? AND mode=?", (url, team_ns, mode))
    conn.execute("""
        INSERT INTO fetch(url, team_ns, mode, content_hash, stage, bytes, token_estimate, summary, fetched_by)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, (url, team_ns, mode, content_hash, stage, bytes_, tokens, summary[:4000], who))
    conn.commit()


def ttl_for(url: str, default: int = 3600) -> int:
    low = url.lower()
    if "/api/" in low or low.endswith(".json"):
        return TTL_DEFAULTS["api"]
    if "robots.txt" in low or "sitemap" in low:
        return 86400 * 7
    if "news" in low or "ticker" in low:
        return TTL_DEFAULTS["news"]
    return TTL_DEFAULTS["static"]


# ============================================================================
# Stage 1: HTTP fetch with TLS fingerprint rotation
# ============================================================================

def dns_resolvable(host: str, timeout: float = 2.0) -> bool:
    """Quick DNS check — lets us skip dead domains before the full HTTP dance."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.gethostbyname(host)
        return True
    except (socket.gaierror, socket.timeout, OSError):
        return False


def stage_1(url: str, timeout: int = 15) -> dict:
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        return {"body": "", "status": 0, "blocked": True, "error": "curl_cffi not installed", "stage": "stage_1"}

    impersonate = random.choice(CHROME_POOL) if ROTATE_BROWSERS else "chrome124"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Upgrade-Insecure-Requests": "1",
    }

    last_err = None
    for profile in (impersonate, "chrome124", "chrome123", "chrome120"):
        try:
            r = cffi_requests.get(
                url, headers=headers, timeout=timeout,
                impersonate=profile, allow_redirects=True,
            )
            body = r.text
            status = r.status_code
            blocked = (
                status in (401, 403, 429, 503) or
                (any(m in body.lower() for m in ("cloudflare challenge", "captcha", "attention required", "checking your browser")) and len(body) < 5000)
            )
            return {
                "body": body, "status": status, "blocked": blocked,
                "stage": "stage_1", "impersonate": profile,
            }
        except Exception as e:
            last_err = e
            continue
    return {"body": "", "status": 0, "blocked": True, "stage": "stage_1", "error": str(last_err)[:200]}


# ============================================================================
# Stage 2+: placeholder hooks (fall through to existing Hyperstack CLI)
# ============================================================================

def stage_escalate(url: str, max_stage: str = "auto") -> dict:
    """Shell out to the existing hyperfetch-stage.py for stages 2+ (camoufox, domshell, browser)."""
    import subprocess
    stage_helper = HOME / ".cts" / "bin" / "hyperfetch-stage.py"
    venv_py = HOME / ".cts" / "venv" / "bin" / "python"
    if not stage_helper.exists() or not venv_py.exists():
        return {"body": "", "status": 0, "blocked": True, "error": "stage helper missing"}

    for stage_name in ("camoufox", "domshell", "browser"):
        try:
            r = subprocess.run(
                [str(venv_py), str(stage_helper), "--stage", stage_name, "--url", url],
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode == 0 and r.stdout.strip():
                data = json.loads(r.stdout.strip().splitlines()[-1])
                if data.get("body") and not data.get("blocked"):
                    return {
                        "body": data["body"], "status": data.get("status", 200),
                        "blocked": False, "stage": stage_name,
                    }
        except Exception:
            continue
    return {"body": "", "status": 0, "blocked": True, "stage": "failed"}


# ============================================================================
# HTML preprocessor
# ============================================================================

class _TagStripper(HTMLParser):
    _skip_tags = {"script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "form", "button"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_stack = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self._skip_tags:
            self.skip_stack += 1
        elif tag in ("p", "br", "li", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self._skip_tags and self.skip_stack > 0:
            self.skip_stack -= 1

    def handle_data(self, data):
        if self.skip_stack == 0:
            txt = data.strip()
            if txt:
                self.parts.append(txt + " ")

    def get_text(self) -> str:
        raw = "".join(self.parts)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def looks_like_html(text: str) -> bool:
    head = text[:500].lower().lstrip()
    return head.startswith("<!doctype") or head.startswith("<html") or ("<head" in head and "<body" in text[:2000].lower())


def preprocess(text: str, max_chars: int = MAX_INPUT) -> str:
    if looks_like_html(text):
        try:
            p = _TagStripper()
            p.feed(text)
            text = p.get_text()
        except Exception:
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        head = text[: max_chars // 2]
        tail = text[-max_chars // 2:]
        text = f"{head}\n...[truncated]...\n{tail}"
    return text


# ============================================================================
# Mode processors
# ============================================================================

def mode_triage(body: str) -> str:
    def pick(pattern, default=""):
        m = re.search(pattern, body, re.I | re.S)
        return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else default

    title = pick(r"<title[^>]*>(.*?)</title>")
    h1 = pick(r"<h1[^>]*>(.*?)</h1>")
    meta = re.search(r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\'](.*?)["\']', body, re.I)
    desc = meta.group(1).strip()[:300] if meta else ""
    first_p = pick(r"<p[^>]*>(.*?)</p>")[:300]

    lines = []
    if title:
        lines.append(f"title: {title[:200]}")
    if h1 and h1 != title:
        lines.append(f"h1: {h1[:200]}")
    if desc:
        lines.append(f"desc: {desc}")
    if first_p and first_p not in (title, desc):
        lines.append(f"p1: {first_p}")
    return "\n".join(lines) or body[:500].replace("\n", " ")


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def call_local_llm(system: str, user_text: str, timeout: int = 60) -> str | None:
    cleaned = preprocess(user_text)
    payload = json.dumps({
        "model": DEFAULT_MODEL,
        "prompt": f"{system}\n\nINPUT:\n{cleaned}\n\nOUTPUT:",
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 300, "num_ctx": 4096},
    }).encode()
    req = Request(LOCAL_LLM_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
            return data.get("response", "").strip()
    except (URLError, TimeoutError, json.JSONDecodeError):
        return None


def extractive_fallback(text: str, max_lines: int = 5) -> str:
    cleaned = preprocess(text) if looks_like_html(text) else text
    lines = [l.strip() for l in cleaned.splitlines() if l.strip()]
    if not lines:
        return "[empty]"
    signals = [l for l in lines if re.search(r"error|fail|exception|traceback|warn|critical|title|price|\\$\\d", l, re.I)]
    picks = (signals + lines)[:max_lines]
    return "\n".join(f"- {l[:120]}" for l in picks)


def mode_summary(body: str) -> str:
    if estimate_tokens(body) < SUMMARY_THRESHOLD:
        return preprocess(body)
    result = call_local_llm(SUMMARY_SYSTEM, body)
    if result and result != "[empty]":
        return result
    return extractive_fallback(body)


def mode_extract(body: str, task: str) -> str:
    system = f"You extract facts from web content.\n\nTask: {task}\n\nOutput only the extracted facts, nothing else. Be concise."
    result = call_local_llm(system, body)
    return result or mode_triage(body)


def mode_markdown(body: str) -> str:
    if estimate_tokens(body) < SUMMARY_THRESHOLD:
        return preprocess(body)
    result = call_local_llm(MARKDOWN_SYSTEM, body)
    return result or preprocess(body)[:5000]


# ============================================================================
# Main entry point
# ============================================================================

def fetch_one(conn, url: str, mode: str, team_ns: str, no_cache: bool,
              task: str = "", max_stage: str = "auto",
              skip_dns_check: bool = False, max_retries: int = 1,
              escalate_on_block: bool = True) -> dict:
    nurl = normalize_url(url)
    t0 = time.perf_counter()
    host = urlsplit(nurl).netloc.lower()

    # Gate 1: cache lookup
    if not no_cache:
        hit = cache_lookup(conn, nurl, team_ns, mode, max_age=ttl_for(nurl))
        if hit:
            return {
                "url": url, "stage": "cached", "status": 200, "mode": mode,
                "bytes": hit["bytes"], "tokens": hit["tokens"], "cached": True,
                "team_ns": team_ns, "fetched_at": hit["fetched_at"],
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "preview": hit["summary"],
            }

    # Early dead-domain skip
    if _host_is_blacklisted(host):
        return {
            "url": url, "stage": "blacklisted", "status": 0, "mode": mode,
            "error": f"host blacklisted after {_host_failures[host]} failures",
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }

    if not skip_dns_check and not dns_resolvable(host):
        _record_host_result(host, False)
        return {
            "url": url, "stage": "dns_fail", "status": 0, "mode": mode,
            "error": f"DNS resolution failed for {host}",
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }

    # Per-host polite delay + semaphore
    host_lock = _get_host_lock(host)
    with host_lock:
        _host_polite_delay(host)

        # Stage 1 with retries + exponential backoff
        r = None
        for attempt in range(max_retries + 1):
            r = stage_1(nurl)
            if r.get("body") and not r.get("blocked"):
                break
            if attempt < max_retries:
                backoff = 0.5 * (2 ** attempt) + random.uniform(0, 0.2)
                time.sleep(backoff)

        _record_host_result(host, bool(r and r.get("body") and not r.get("blocked")))

    # Auto-escalation to stage 2 if stage 1 blocked
    if (r.get("blocked") or not r.get("body")) and escalate_on_block and max_stage != "1":
        r2 = stage_escalate(nurl, max_stage=max_stage)
        if r2.get("body"):
            r = r2
        else:
            return {
                "url": url, "stage": "failed", "status": r.get("status", 0),
                "mode": mode, "error": r.get("error", "blocked"),
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            }
    elif not r.get("body"):
        return {
            "url": url, "stage": "failed", "status": r.get("status", 0),
            "mode": mode, "error": r.get("error", "blocked"),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        }

    body = r["body"]

    # Mode processing
    if mode == "triage":
        payload = mode_triage(body)
    elif mode == "summary":
        payload = mode_summary(body)
    elif mode == "extract":
        payload = mode_extract(body, task)
    elif mode == "markdown":
        payload = mode_markdown(body)
    elif mode == "raw":
        payload = body[:50000]
    else:
        payload = mode_triage(body)

    bytes_ = len(body.encode("utf-8"))
    tokens = estimate_tokens(payload)
    content_hash = hashlib.sha1(body.encode("utf-8")).hexdigest()[:16]

    # Write-through cache
    cache_write(conn, nurl, team_ns, mode, r.get("stage", "stage_1"),
                bytes_, tokens, payload, content_hash)

    return {
        "url": url, "stage": r.get("stage", "stage_1"), "status": r.get("status", 200),
        "mode": mode, "bytes": bytes_, "tokens": tokens, "cached": False,
        "team_ns": team_ns, "fetched_at": int(time.time()),
        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        "content_hash": content_hash, "preview": payload[:2000],
    }


def doctor() -> int:
    checks = []
    # DB
    try:
        conn = _init_db()
        conn.execute("SELECT 1").fetchone()
        checks.append(("cache db", True, str(DB_PATH)))
    except Exception as e:
        checks.append(("cache db", False, str(e)[:100]))
    # curl_cffi
    try:
        import curl_cffi  # noqa
        checks.append(("curl_cffi", True, "import ok"))
    except ImportError:
        checks.append(("curl_cffi", False, "not installed"))
    # Local LLM
    try:
        req = Request(LOCAL_LLM_URL.replace("/api/generate", "/api/tags"))
        with urlopen(req, timeout=3) as r:
            checks.append(("local LLM", True, f"{LOCAL_LLM_URL}"))
    except Exception as e:
        checks.append(("local LLM", False, str(e)[:100]))
    # Stage 1 smoke
    try:
        r = stage_1("https://example.com", timeout=5)
        checks.append(("stage 1 smoke", bool(r.get("body")), f"status={r.get('status')}"))
    except Exception as e:
        checks.append(("stage 1 smoke", False, str(e)[:100]))

    print("## hyperfetch doctor")
    all_ok = True
    for name, ok, msg in checks:
        mark = "[x]" if ok else "[ ]"
        print(f"  {mark} {name}: {msg}")
        if not ok:
            all_ok = False
    return 0 if all_ok else 1


def main():
    p = argparse.ArgumentParser(prog="hyperfetch", description="Python-native Hyperfetch")
    p.add_argument("url", nargs="?", default=None)
    # Modes
    p.add_argument("--triage", action="store_const", dest="mode", const="triage")
    p.add_argument("--summary", action="store_const", dest="mode", const="summary")
    p.add_argument("--markdown", action="store_const", dest="mode", const="markdown")
    p.add_argument("--extract", dest="extract_task", default=None, help="extract a specific fact per your prompt")
    p.add_argument("--raw", action="store_const", dest="mode", const="raw")
    p.add_argument("--prefetch", action="store_const", dest="mode", const="triage")  # alias
    p.set_defaults(mode="triage")
    # Cache
    p.add_argument("--team-ns", default=DEFAULT_NS)
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--cache-only", action="store_true")
    # Stage
    p.add_argument("--stage", default="auto", choices=["1", "2", "3", "4", "auto"])
    # Batch
    p.add_argument("--batch", action="store_true", help="read URLs from stdin")
    p.add_argument("--parallel", type=int, default=10)
    p.add_argument("--retries", type=int, default=1, help="per-URL retry attempts on transient failures")
    p.add_argument("--resume", action="store_true", help="skip URLs already in cache (batch mode)")
    p.add_argument("--no-escalate", action="store_true", help="don't auto-escalate to stage 2 on block")
    # Meta
    p.add_argument("--doctor", action="store_true")
    p.add_argument("--version", action="store_true")
    args = p.parse_args()

    if args.version:
        print("fetch hyperfetch/0.4.0 spec/1.0")
        return 0
    if args.doctor:
        return doctor()

    if args.extract_task:
        args.mode = "extract"

    conn = _init_db()

    if args.batch:
        import concurrent.futures
        raw_urls = [line.strip() for line in sys.stdin if line.strip()]
        if not raw_urls:
            print(json.dumps({"error": "no URLs in stdin"}))
            return 2

        # Dedup while preserving order
        seen = set()
        urls = []
        for u in raw_urls:
            nu = normalize_url(u)
            if nu not in seen:
                seen.add(nu)
                urls.append(u)

        total = len(urls)
        duped = len(raw_urls) - total
        if duped > 0:
            print(f"[hyperfetch] deduped {duped} URLs, processing {total}", file=sys.stderr)
        else:
            print(f"[hyperfetch] processing {total} URLs", file=sys.stderr)

        # Checkpoint: skip URLs already in cache unless --no-cache
        if not args.no_cache and args.resume:
            skipped = 0
            pending = []
            for u in urls:
                nu = normalize_url(u)
                if cache_lookup(conn, nu, args.team_ns, args.mode, max_age=ttl_for(nu)):
                    skipped += 1
                else:
                    pending.append(u)
            if skipped:
                print(f"[hyperfetch] resume: {skipped} already cached, {len(pending)} pending", file=sys.stderr)
            urls = pending

        # Progress tracking
        counter = {"done": 0, "ok": 0, "failed": 0, "cached": 0, "start": time.time()}
        counter_lock = threading.Lock()
        failures = defaultdict(list)

        def progress_tick(result):
            with counter_lock:
                counter["done"] += 1
                if result.get("stage") == "cached":
                    counter["cached"] += 1
                elif result.get("error") or result.get("stage") == "failed":
                    counter["failed"] += 1
                    reason = result.get("error", "unknown")[:40] or result.get("stage", "")
                    failures[reason].append(result.get("url", ""))
                else:
                    counter["ok"] += 1

                d = counter["done"]
                if d % max(1, total // 20) == 0 or d == total:
                    elapsed = time.time() - counter["start"]
                    rate = d / max(elapsed, 0.1)
                    eta = (total - d) / max(rate, 0.1)
                    print(
                        f"[hyperfetch] {d}/{total} "
                        f"ok={counter['ok']} cache={counter['cached']} fail={counter['failed']} "
                        f"rate={rate:.1f}/s eta={eta:.0f}s",
                        file=sys.stderr,
                    )

        # Execute in parallel
        max_workers = min(args.parallel, 50)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [
                ex.submit(
                    fetch_one, conn, u, args.mode, args.team_ns,
                    args.no_cache, args.extract_task or "", args.stage,
                    False, args.retries, not args.no_escalate,
                )
                for u in urls
            ]
            for fut in concurrent.futures.as_completed(futures):
                try:
                    result = fut.result()
                    print(json.dumps(result))
                    progress_tick(result)
                except Exception as e:
                    err = {"error": str(e)[:200], "stage": "failed"}
                    print(json.dumps(err))
                    progress_tick(err)

        # Final report
        elapsed = time.time() - counter["start"]
        print(
            f"\n[hyperfetch] DONE — {counter['done']}/{total} in {elapsed:.1f}s "
            f"(ok={counter['ok']} cached={counter['cached']} failed={counter['failed']})",
            file=sys.stderr,
        )
        if failures:
            print("[hyperfetch] failure breakdown:", file=sys.stderr)
            for reason, urls_failed in sorted(failures.items(), key=lambda x: -len(x[1]))[:10]:
                print(f"  {len(urls_failed)}x  {reason}", file=sys.stderr)
        return 0

    if not args.url:
        p.print_help()
        return 2

    result = fetch_one(
        conn, args.url, args.mode, args.team_ns,
        args.no_cache, args.extract_task or "", args.stage,
    )
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
