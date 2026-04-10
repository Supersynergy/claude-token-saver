#!/usr/bin/env python3
# Bootstrap catboost trainer — synthesizes labels from scraper_swarm results
# using heuristics when explicit labels are missing. Good enough to kickstart
# the classifier, then retrain from live agent feedback.

import json
import sys
import re
from pathlib import Path

HOME = Path.home()
RESULTS_DIR = HOME / "projects" / "scraper_swarm" / "results"
MODEL_PATH = HOME / ".cts" / "models" / "ml-filter.cbm"

FEATURES = [
    "len", "line_count", "json_density", "html_density",
    "error_kw", "warn_kw", "path_density", "uniq_tokens",
]

SIGNAL_KEYWORDS = {"error", "fail", "exception", "traceback", "CRITICAL", "undefined", "null", "panic"}
NOISE_MARKERS = [
    r"Building wheel", r"Downloaded \d+", r"node_modules",
    r"^\s*$", r"^(DEBUG|INFO):", r"✓ \d+ tests? passed",
    r"^\s*-{3,}\s*$", r"^\s*={3,}\s*$",
]


def features(text: str) -> list[float]:
    lines = text.splitlines()
    tokens = re.findall(r"\w+", text)
    return [
        len(text),
        len(lines),
        text.count("{") / max(len(text), 1),
        text.count("<") / max(len(text), 1),
        sum(1 for kw in SIGNAL_KEYWORDS if kw in text.lower()),
        text.lower().count("warn"),
        text.count("/") / max(len(text), 1),
        len(set(tokens)),
    ]


def synth_label(text: str, data: dict) -> str:
    """Synthesize a label when the result file doesn't carry one."""
    if "label" in data:
        return data["label"]
    if data.get("success") is False or "error" in data:
        return "error"
    if any(re.search(p, text) for p in NOISE_MARKERS) and not any(kw in text.lower() for kw in SIGNAL_KEYWORDS):
        return "noise"
    tokens = re.findall(r"\w+", text)
    if len(set(tokens)) < 20 and len(text) > 500:
        return "boilerplate"
    if any(kw in text.lower() for kw in SIGNAL_KEYWORDS):
        return "error"
    if data.get("success") is True or text.strip():
        return "signal"
    return "noise"


def train():
    try:
        from catboost import CatBoostClassifier, Pool
    except ImportError:
        print(json.dumps({"error": "catboost not installed — run: ~/.cts/venv/bin/pip install catboost"}), file=sys.stderr)
        sys.exit(1)

    if not RESULTS_DIR.exists():
        # Bootstrap mode: generate synthetic training data
        print(f"[ml-train] {RESULTS_DIR} not found — bootstrapping synthetic corpus", file=sys.stderr)
        return bootstrap_synthetic()

    X, y = [], []
    scanned = 0
    for p in RESULTS_DIR.rglob("*.json"):
        scanned += 1
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    _extract_one(item, X, y)
            continue
        if not isinstance(data, dict):
            continue
        _extract_one(data, X, y)
    return _finalize_training(X, y, scanned)


def _extract_one(data: dict, X: list, y: list):
    body = data.get("body") or data.get("content") or data.get("stdout") or data.get("raw") or data.get("text") or ""
    if not isinstance(body, str) or not body.strip():
        return
    label = synth_label(body, data)
    X.append(features(body))
    y.append(label)


def _finalize_training(X, y, scanned):
    from catboost import CatBoostClassifier, Pool
    print(f"[ml-train] scanned={scanned} usable={len(X)}", file=sys.stderr)

    if len(X) < 30:
        print("[ml-train] not enough real samples, adding synthetic corpus", file=sys.stderr)
        Xs, ys = synthetic_samples()
        X.extend(Xs)
        y.extend(ys)

    unique_labels = sorted(set(y))
    print(f"[ml-train] labels={unique_labels} total={len(X)}", file=sys.stderr)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model = CatBoostClassifier(
        iterations=300,
        depth=6,
        learning_rate=0.08,
        loss_function="MultiClass",
        verbose=0,
    )
    model.fit(Pool(X, y))
    model.save_model(str(MODEL_PATH))

    # Quick eval on training set (no holdout, this is a bootstrap)
    preds = model.predict(X)
    correct = sum(1 for p, yi in zip(preds, y) if (p[0] if hasattr(p, "__len__") else p) == yi)
    acc = correct / max(1, len(X))

    report = {
        "trained": True,
        "samples": len(X),
        "labels": {lbl: y.count(lbl) for lbl in unique_labels},
        "train_accuracy": round(acc, 3),
        "model_path": str(MODEL_PATH),
    }
    print(json.dumps(report, indent=2))


def synthetic_samples():
    corpus = [
        # signal
        ("ERROR: Connection refused at db.js:15\nConnection pool exhausted", "error"),
        ("TypeError: Cannot read property 'name' of undefined\n  at main.js:42", "error"),
        ('{"status":200,"data":{"user":"alice","email":"a@b.c"}}', "signal"),
        ("# Installation\n\nRun `npm install`\n\n## Usage\n\nSee examples/", "signal"),
        ("Price: $42.99\nStock: 12\nSKU: ABC-123", "signal"),
        ("Title: Machine Learning for Beginners\nAuthor: Jane Doe\nPages: 312", "signal"),
        # noise
        ("Building wheel for package-xyz (pyproject.toml)", "noise"),
        ("Downloaded 150 packages in 2.3s\n[INFO] done", "noise"),
        ("==========\nnode_modules/.bin/jest\n==========", "noise"),
        ("✓ 245 tests passed\n✓ all good", "noise"),
        ("\n\n\n  \n\t\n", "noise"),
        ("DEBUG: heartbeat tick\nDEBUG: heartbeat tick\nDEBUG: heartbeat tick", "noise"),
        # boilerplate
        ("Home | About | Contact | Privacy | Terms | Home | About | Contact", "boilerplate"),
        ("Cookie notice: we use cookies. Accept? Yes No Cookie notice: ...", "boilerplate"),
        ("Subscribe to our newsletter for updates. Subscribe. Subscribe. Subscribe.", "boilerplate"),
        ("<!DOCTYPE html><html><head><title>Loading...</title></head><body></body></html>", "boilerplate"),
    ]
    X = [features(text) for text, _ in corpus]
    y = [label for _, label in corpus]
    return X, y


def bootstrap_synthetic():
    try:
        from catboost import CatBoostClassifier, Pool
    except ImportError:
        print(json.dumps({"error": "catboost not installed"}), file=sys.stderr)
        sys.exit(1)

    X, y = synthetic_samples()
    # Duplicate with perturbation to avoid tiny-dataset degenerate training
    import random
    random.seed(42)
    for text, lbl in list(zip([f"sample {i}" for i in range(20)], ["signal"] * 10 + ["noise"] * 10)):
        X.append(features(text))
        y.append(lbl)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model = CatBoostClassifier(iterations=150, depth=4, learning_rate=0.1, loss_function="MultiClass", verbose=0)
    model.fit(Pool(X, y))
    model.save_model(str(MODEL_PATH))
    print(json.dumps({
        "trained": True,
        "mode": "bootstrap-synthetic",
        "samples": len(X),
        "model_path": str(MODEL_PATH),
    }, indent=2))


if __name__ == "__main__":
    train()
