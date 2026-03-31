#!/bin/bash
# Claude Skill Manager & Token Saver — Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/Supersynergy/claude-sm/main/install.sh | bash
#
# What this installs:
#   ~/.claude/skills/sm.md                   — /sm slash command
#   ~/.claude/scripts/build-skills-index.py  — index builder
#   ~/.claude/hooks/skills-index-session.sh  — auto-rebuild on session start
#   Adds SessionStart hook to ~/.claude/settings.json

set -e

REPO_RAW="https://raw.githubusercontent.com/Supersynergy/claude-sm/main"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
SKILLS_DIR="$CLAUDE_DIR/skills"
SCRIPTS_DIR="$CLAUDE_DIR/scripts"
HOOKS_DIR="$CLAUDE_DIR/hooks"
SETTINGS="$CLAUDE_DIR/settings.json"

# ── Colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $1"; }
info() { echo -e "${CYAN}→${RESET} $1"; }
warn() { echo -e "${YELLOW}⚠${RESET} $1"; }

echo ""
echo "Claude Skill Manager & Token Saver"
echo "===================================="
echo ""

# ── Detect CLAUDE_DIR ────────────────────────────────────────────────────────
if [ ! -d "$CLAUDE_DIR" ]; then
    warn "~/.claude not found — creating it"
    mkdir -p "$CLAUDE_DIR"
fi

# ── Create dirs ──────────────────────────────────────────────────────────────
mkdir -p "$SKILLS_DIR" "$SCRIPTS_DIR" "$HOOKS_DIR"

# ── Download or copy files ───────────────────────────────────────────────────
install_file() {
    local src="$1" dst="$2" name="$3"
    if [ -f "$src" ]; then
        cp "$src" "$dst"
    else
        curl -fsSL "$REPO_RAW/$src" -o "$dst"
    fi
    ok "$name → $dst"
}

info "Installing files..."
install_file "sm.md" "$SKILLS_DIR/sm.md" "/sm skill"
install_file "build-skills-index.py" "$SCRIPTS_DIR/build-skills-index.py" "build script"
install_file "skills-index-session.sh" "$HOOKS_DIR/skills-index-session.sh" "session hook"
chmod +x "$HOOKS_DIR/skills-index-session.sh"
chmod +x "$SCRIPTS_DIR/build-skills-index.py"

# ── Add SessionStart hook to settings.json ──────────────────────────────────
info "Wiring SessionStart hook..."
if [ -f "$SETTINGS" ]; then
    python3 - <<PYEOF
import json, os, sys

path = os.path.expanduser("~/.claude/settings.json")
with open(path) as f:
    s = json.load(f)

hook = {"async": True, "command": 'bash "$HOME/.claude/hooks/skills-index-session.sh"', "type": "command"}
new_entry = {"hooks": [hook]}

hooks = s.setdefault("hooks", {})
ss = hooks.setdefault("SessionStart", [])

if not any("skills-index-session" in str(h) for h in ss):
    ss.append(new_entry)
    with open(path, "w") as f:
        json.dump(s, f, indent=2)
    print("  Added SessionStart hook to settings.json")
else:
    print("  SessionStart hook already present")
PYEOF
else
    warn "settings.json not found — skipping hook wiring (add manually)"
    info "Manual: add to SessionStart hooks in ~/.claude/settings.json:"
    echo '    {"hooks":[{"async":true,"command":"bash \"$HOME/.claude/hooks/skills-index-session.sh\"","type":"command"}]}'
fi

# ── Build initial index ──────────────────────────────────────────────────────
echo ""
info "Building skills index..."
if python3 "$SCRIPTS_DIR/build-skills-index.py" --skills-dir "$SKILLS_DIR" --output-dir "$CLAUDE_DIR"; then
    TOTAL=$(wc -l < "$CLAUDE_DIR/skills.idx" | tr -d ' ')
    ok "Indexed $TOTAL skills"
else
    warn "Index build failed — run manually: python3 ~/.claude/scripts/build-skills-index.py"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "===================================="
ok "Claude Skill Manager & Token Saver installed"
echo ""
echo "Commands:"
echo "  /sm search <query>   find skills by keyword  (~0 tokens)"
echo "  /sm list             browse by category"
echo "  /sm auto <intent>    find + invoke best skill"
echo "  /sm stats            portfolio + token savings"
echo "  /sm tokens           token saving cheatsheet"
echo "  /sm rebuild          refresh index"
echo ""
echo "Token saving: rg idx (~0) → ctx_search (~200-500) → Read one file (~500-5K)"
echo "              All skills loaded = ~160K tokens (never do that!)"
echo ""
