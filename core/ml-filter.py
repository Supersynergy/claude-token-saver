#!/usr/bin/env python3
# catboost pre-filter: classifies tool output before it hits context-mode.
# Categories: signal, boilerplate, noise, error. Only "signal" is indexed.
# Trained on scraper_swarm/results/*.json labels.

import json
import sys
import os
import re
from pathlib import Path

MODEL_PATH = Path.home() / ".cts" / "models" / "ml-filter.cbm"
FEATURES = [
    "len", "line_count", "json_density", "html_density",
    "error_kw", "warn_kw", "path_density", "uniq_tokens",
]

NOISE_PATTERNS = [
    r"^\s*$", r"DEBUG", r"INFO:.+heartbeat", r"✓ \d+ tests passed",
    r"Downloaded \d+ packages", r"node_modules", r"Building wheel",
]

SIGNAL_KEYWORDS = {"error", "fail", "exception", "traceback", "CRITICAL", "undefined", "null", "panic"}


def extract_features(text: str) -> dict:
    lines = text.splitlines()
    tokens = re.findall(r"\w+", text)
    return {
        "len": len(text),
        "line_count": len(lines),
        "json_density": text.count("{") / max(len(text), 1),
        "html_density": text.count("<") / max(len(text), 1),
        "error_kw": sum(1 for kw in SIGNAL_KEYWORDS if kw in text.lower()),
        "warn_kw": text.lower().count("warn"),
        "path_density": text.count("/") / max(len(text), 1),
        "uniq_tokens": len(set(tokens)),
    }


def rule_based_fallback(text: str) -> dict:
    f = extract_features(text)
    if any(re.search(p, text) for p in NOISE_PATTERNS) and f["error_kw"] == 0:
        return {"keep": False, "category": "noise", "confidence": 0.85}
    if f["error_kw"] > 0:
        return {"keep": True, "category": "error", "confidence": 0.95}
    if f["json_density"] > 0.02 or f["html_density"] > 0.05:
        return {"keep": True, "category": "signal", "confidence": 0.8}
    if f["uniq_tokens"] < 20 and f["line_count"] > 5:
        return {"keep": False, "category": "boilerplate", "confidence": 0.7}
    return {"keep": True, "category": "signal", "confidence": 0.5}


def classify_with_catboost(text: str) -> dict:
    try:
        from catboost import CatBoostClassifier
    except ImportError:
        return rule_based_fallback(text)
    if not MODEL_PATH.exists():
        return rule_based_fallback(text)
    model = CatBoostClassifier()
    model.load_model(str(MODEL_PATH))
    f = extract_features(text)
    vec = [f[k] for k in FEATURES]
    pred = model.predict([vec])[0]
    proba = model.predict_proba([vec])[0]
    categories = ["noise", "boilerplate", "signal", "error"]
    idx = int(pred) if isinstance(pred, (int, float)) else categories.index(str(pred))
    cat = categories[idx]
    return {
        "keep": cat in {"signal", "error"},
        "category": cat,
        "confidence": float(max(proba)),
    }


def train_from_scraper_swarm():
    try:
        from catboost import CatBoostClassifier, Pool
    except ImportError:
        print(json.dumps({"error": "catboost not installed — run: uv pip install catboost"}), file=sys.stderr)
        sys.exit(1)

    results_dir = Path.home() / "projects" / "scraper_swarm" / "results"
    if not results_dir.exists():
        print(json.dumps({"error": f"no training data at {results_dir}"}), file=sys.stderr)
        sys.exit(1)

    X, y = [], []
    for p in results_dir.glob("*.json"):
        try:
            data = json.loads(p.read_text())
            body = data.get("body") or data.get("content") or ""
            if not body:
                continue
            f = extract_features(body)
            label = data.get("label") or ("signal" if data.get("success") else "error")
            X.append([f[k] for k in FEATURES])
            y.append(label)
        except Exception:
            continue

    if len(X) < 50:
        print(json.dumps({"warning": f"only {len(X)} samples, using rule-based"}), file=sys.stderr)
        return

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model = CatBoostClassifier(iterations=200, depth=6, learning_rate=0.1, verbose=0)
    model.fit(Pool(X, y))
    model.save_model(str(MODEL_PATH))
    print(json.dumps({"trained": True, "samples": len(X), "path": str(MODEL_PATH)}))


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: ml-filter.py --classify|--train", file=sys.stderr)
        sys.exit(2)
    if args[0] == "--train":
        train_from_scraper_swarm()
        return
    if args[0] == "--classify":
        text = sys.stdin.read()
        result = classify_with_catboost(text)
        print(json.dumps(result))
        return
    sys.exit(2)


if __name__ == "__main__":
    main()
