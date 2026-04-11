#!/usr/bin/env python3
# Stage helper for hyperfetch — single script that runs one escalation stage.
# Called by ~/.cts/bin/hyperfetch. Uses user's patches/constants for TLS/UA.
# Output: JSON on stdout {status, body, headers, blocked, stage}.

import argparse
import json
import sys
import os
from pathlib import Path

HOME = Path.home()
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "projects" / "browser-tools"))


def try_import_patches_constants():
    try:
        from patches.constants import DEFAULT_USER_AGENT, DEFAULT_HEADERS, DEFAULT_FINGERPRINT
        return DEFAULT_USER_AGENT, DEFAULT_HEADERS, DEFAULT_FINGERPRINT
    except Exception:
        return (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            "chrome124",
        )


def emit(stage, status, body, blocked=False, error=None):
    out = {
        "stage": stage,
        "status": status,
        "body": body if body else "",
        "blocked": bool(blocked),
    }
    if error:
        out["error"] = str(error)[:200]
    sys.stdout.write(json.dumps(out))


CHROME_POOL = ["chrome124", "chrome123", "chrome120", "chrome110", "chrome107"]
SAFARI_POOL = ["safari15_5", "safari17_0", "safari17_2_ios"]
FIREFOX_POOL = ["firefox133", "firefox135"]
ALL_POOL = CHROME_POOL + SAFARI_POOL + FIREFOX_POOL


def pick_impersonate() -> str:
    """Browser pool rotation — based on user's STEALTH_OPTIMIZATION_COMPLETE_REPORT.md."""
    import random
    override = os.environ.get("CTS_IMPERSONATE", "").strip()
    if override:
        return override
    if os.environ.get("CTS_ROTATE_BROWSERS", "1") == "1":
        return random.choice(CHROME_POOL)
    return "chrome124"


def stage_curl_cffi(url: str, timeout: int = 15):
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError as e:
        emit("curl_cffi", 0, "", error=f"import failed: {e}")
        return 1

    ua, headers, fp = try_import_patches_constants()
    headers = {**headers, "User-Agent": ua}
    impersonate = pick_impersonate()

    # Retry chain: if selected impersonation fails to load (newer curl_cffi changes), try fallbacks
    tried = [impersonate]

    last_err = None
    for imp in [impersonate, "chrome124", "chrome123", "chrome120"]:
        if imp in tried and imp != impersonate:
            continue
        tried.append(imp)
        try:
            r = cffi_requests.get(url, headers=headers, timeout=timeout, impersonate=imp, allow_redirects=True)
            status = r.status_code
            body = r.text
            blocked = (
                status in (401, 403, 429, 503)
                or (any(marker in body.lower() for marker in ("cloudflare challenge", "captcha", "attention required", "checking your browser")) and len(body) < 5000)
            )
            emit("curl_cffi", status, body[:500000], blocked=blocked)
            return 0
        except Exception as e:
            last_err = e
            continue
    emit("curl_cffi", 0, "", error=last_err or "all impersonations failed")
    return 1


def stage_crawl4ai(url: str, timeout: int = 120):
    """Stage backed by crawl4ai for clean LLM-ready markdown output."""
    c4a_py = HOME / "projects" / "scraper-benchmark" / ".venv" / "bin" / "python"
    if not c4a_py.exists():
        emit("crawl4ai", 0, "", error=f"crawl4ai venv not found at {c4a_py}")
        return 1

    import subprocess
    script = (
        "import asyncio, json, warnings; warnings.filterwarnings('ignore')\n"
        "async def main():\n"
        "    from crawl4ai import AsyncWebCrawler\n"
        f"    async with AsyncWebCrawler(verbose=False) as c:\n"
        f"        r = await c.arun(url={url!r})\n"
        "        md = (r.markdown or '')[:500000]\n"
        "        print(json.dumps({'body': md, 'status': 200, 'blocked': False}))\n"
        "asyncio.run(main())\n"
    )
    try:
        r = subprocess.run(
            [str(c4a_py), "-c", script],
            capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode != 0:
            emit("crawl4ai", 0, "", error=r.stderr[:200])
            return 1
        # crawl4ai writes status lines to stdout; pick the JSON one
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                import json as _json
                data = _json.loads(line)
                emit("crawl4ai", data.get("status", 200), data.get("body", "")[:500000], blocked=False)
                return 0
        emit("crawl4ai", 0, "", error="no JSON output from crawl4ai subprocess")
        return 1
    except subprocess.TimeoutExpired:
        emit("crawl4ai", 0, "", error="crawl4ai timeout")
        return 1
    except Exception as e:
        emit("crawl4ai", 0, "", error=e)
        return 1


def stage_camoufox(url: str, timeout: int = 45):
    try:
        from camoufox.sync_api import Camoufox
    except ImportError as e:
        emit("camoufox", 0, "", error=f"camoufox not installed: {e}")
        return 1

    try:
        with Camoufox(headless=True) as browser:
            page = browser.new_page()
            page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
            body = page.content()
            emit("camoufox", 200, body[:500000])
            return 0
    except Exception as e:
        emit("camoufox", 0, "", error=e)
        return 1


def stage_domshell(url: str, selector: str = "body", timeout: int = 30):
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "domshell_lite", HOME / "projects" / "browser-tools" / "domshell-lite.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        emit("domshell", 0, "", error=f"domshell import failed: {e}")
        return 1

    import asyncio

    async def run():
        shell = mod.DOMShell()
        try:
            await shell.connect()
        except Exception as e:
            return None, str(e)
        try:
            await shell.send("Page.navigate", {"url": url})
            await asyncio.sleep(1.5)
            result = await shell.send("Runtime.evaluate", {
                "expression": f"document.querySelector('{selector}').innerText",
                "returnByValue": True,
            })
            val = result.get("result", {}).get("value", "")
            return val, None
        except Exception as e:
            return None, str(e)

    try:
        text, err = asyncio.run(run())
        if err:
            emit("domshell", 0, "", error=err)
            return 1
        emit("domshell", 200, text or "")
        return 0
    except Exception as e:
        emit("domshell", 0, "", error=e)
        return 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", required=True, choices=["curl_cffi", "camoufox", "domshell", "browser", "crawl4ai"])
    p.add_argument("--url", required=True)
    p.add_argument("--selector", default="body")
    p.add_argument("--timeout", type=int, default=30)
    args = p.parse_args()

    if args.stage == "curl_cffi":
        sys.exit(stage_curl_cffi(args.url, args.timeout))
    elif args.stage == "camoufox":
        sys.exit(stage_camoufox(args.url, args.timeout))
    elif args.stage == "domshell":
        sys.exit(stage_domshell(args.url, args.selector, args.timeout))
    elif args.stage == "browser":
        sys.exit(stage_camoufox(args.url, args.timeout))
    elif args.stage == "crawl4ai":
        sys.exit(stage_crawl4ai(args.url, args.timeout))


if __name__ == "__main__":
    main()
