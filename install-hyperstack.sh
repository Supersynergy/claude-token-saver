#!/usr/bin/env bash
# Hyperstack installer — sets up curl_cffi + camoufox + domshell + catboost + gemma + team sandbox
# April 2026 stack. Uses uv for Python, Ollama for local LLM, SurrealDB for team cache.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CTS_HOME="${HOME}/.cts"
MODEL_DIR="${CTS_HOME}/models"
BIN_DIR="${CTS_HOME}/bin"

echo "==> Hyperstack installer"

check_cmd() {
  if command -v "$1" >/dev/null 2>&1; then
    echo "  [x] $1"
  else
    echo "  [ ] $1 — $2"
    return 1
  fi
}

echo "==> Checking prerequisites"
check_cmd uv "install: curl -LsSf https://astral.sh/uv/install.sh | sh" || MISSING_UV=1
check_cmd node "install: brew install node" || MISSING_NODE=1
check_cmd ollama "install: brew install ollama" || MISSING_OLLAMA=1
check_cmd surreal "install: curl -sSf https://install.surrealdb.com | sh" || MISSING_SURREAL=1

if [[ "${MISSING_UV:-0}" == "1" ]]; then
  echo "uv is required. Install and re-run." >&2
  exit 1
fi

echo "==> Creating directories"
mkdir -p "${CTS_HOME}/hyperstack" "${MODEL_DIR}" "${BIN_DIR}" "${CTS_HOME}/dsh-sessions"

echo "==> Installing Python dependencies (uv)"
uv pip install --system --quiet \
  curl_cffi \
  websockets \
  catboost \
  2>&1 | tail -5 || echo "  [!] some deps failed — check manually"

echo "==> Checking scraper patches"
for p in "${HOME}/patches/curl_cffi_patch.py" "${HOME}/patches/camoufox_patch.py"; do
  if [[ -f "$p" ]]; then
    echo "  [x] $p"
  else
    echo "  [ ] $p — missing, copy from your scraper toolkit"
  fi
done

DOMSHELL="${HOME}/projects/browser-tools/domshell-lite.py"
if [[ -f "$DOMSHELL" ]]; then
  echo "  [x] domshell-lite: $DOMSHELL"
else
  echo "  [ ] domshell-lite missing at $DOMSHELL"
fi

echo "==> Symlinking CLIs to ${BIN_DIR}"
ln -sf "${ROOT}/plugins/dsh-cli.py" "${BIN_DIR}/dsh"
ln -sf "${ROOT}/plugins/team-sandbox.sh" "${BIN_DIR}/cts-team"
ln -sf "${ROOT}/core/ml-filter.py" "${BIN_DIR}/cts-ml"
ln -sf "${ROOT}/core/gemma-gate.py" "${BIN_DIR}/cts-gemma"
chmod +x "${ROOT}/plugins/dsh-cli.py" "${ROOT}/plugins/team-sandbox.sh" \
         "${ROOT}/core/ml-filter.py" "${ROOT}/core/gemma-gate.py" 2>/dev/null || true

if ! echo ":$PATH:" | grep -q ":${BIN_DIR}:"; then
  echo ""
  echo "  Add to shell rc:"
  echo "    export PATH=\"${BIN_DIR}:\$PATH\""
fi

echo "==> Initializing team sandbox schema"
if command -v surreal >/dev/null 2>&1; then
  bash "${ROOT}/plugins/team-sandbox.sh" init || echo "  [!] schema init failed — run manually later"
else
  echo "  [ ] surrealdb not installed, skipping schema init"
fi

echo "==> Pulling local summarizer model (Ollama)"
if command -v ollama >/dev/null 2>&1; then
  if pgrep -x ollama >/dev/null 2>&1; then
    ollama pull gemma3:4b 2>&1 | tail -3 || echo "  [!] gemma3:4b pull failed — try gemma2:2b"
  else
    echo "  [ ] ollama not running — start with: ollama serve &"
  fi
else
  echo "  [ ] ollama missing — skip local summarizer"
fi

echo "==> Training ml-filter from scraper_swarm data (if available)"
if [[ -d "${HOME}/projects/scraper_swarm/results" ]]; then
  uv run python "${ROOT}/core/ml-filter.py" --train 2>&1 | tail -3 || echo "  [!] training skipped"
else
  echo "  [ ] no training data — rule-based fallback will be used"
fi

echo ""
echo "==> Hyperstack installed"
echo ""
echo "Quick test:"
echo "  dsh --session test goto https://example.com"
echo "  dsh --session test read h1"
echo "  cts-team stats"
echo "  echo 'some output' | cts-ml --classify"
echo ""
echo "Docs: ${ROOT}/HYPERSTACK.md"
