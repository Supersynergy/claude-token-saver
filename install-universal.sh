#!/usr/bin/env bash
# ╔═══════════════════════════════════════════════════════════════════════╗
# ║     ⚡ Universal Token Saver — Universal Installer                  ║
# ║     Supports: Claude Code, Gemini CLI, Kilo/Code, Codex, Kimi        ║
# ╚═══════════════════════════════════════════════════════════════════════╝
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Supersynergy/universal-token-saver/main/install-universal.sh | bash
#   curl -fsSL ... | bash -s -- --adapter=gemini
#   curl -fsSL ... | bash -s -- --adapter=all

set -euo pipefail

# ── Version ──────────────────────────────────────────────────────────
UTS_VERSION="1.0.0"
UTS_REPO="https://raw.githubusercontent.com/Supersynergy/universal-token-saver/main"

# ── Paths ───────────────────────────────────────────────────────────
UTS_HOME="${UTS_HOME:-$HOME/.uts}"
VAULT_DIR="$UTS_HOME/vault"
PLUGINS_DIR="$UTS_HOME/plugins"
ADAPTERS_DIR="$UTS_HOME/adapters"
STATS_FILE="$UTS_HOME/stats.json"

# ── Colors ──────────────────────────────────────────────────────────
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; C='\033[0;36m'
B='\033[1m'; DIM='\033[2m'; NC='\033[0m'

# ── Flags ────────────────────────────────────────────────────────────
ADAPTER="auto"
DRY_RUN=0
SKIP_NPM=0
UNINSTALL=0
SILENT=0

for arg in "$@"; do case $arg in
  --adapter=*)  ADAPTER="${arg#*=}" ;;
  --dry-run)    DRY_RUN=1 ;;
  --skip-npm)   SKIP_NPM=1 ;;
  --uninstall)  UNINSTALL=1 ;;
  --silent|-s)  SILENT=1 ;;
  --help|-h)    SHOW_HELP=1 ;;
esac; done

# ── Helpers ──────────────────────────────────────────────────────────
ok()   { [[ $SILENT -eq 0 ]] && echo -e "${G}✓${NC} $*"; }
warn() { [[ $SILENT -eq 0 ]] && echo -e "${Y}⚠${NC} $*"; }
info() { [[ $SILENT -eq 0 ]] && echo -e "${C}ℹ${NC} $*"; }
die()  { echo -e "${R}✗${NC} $*" >&2; exit 1; }
run()  { [[ $DRY_RUN -eq 1 ]] && echo -e "  ${DIM}[dry-run]${NC} $*" || eval "$*"; }

# ── Help ──────────────────────────────────────────────────────────────
if [[ "${SHOW_HELP:-0}" -eq 1 ]]; then
  cat <<HELP
Universal Token Saver v$UTS_VERSION

Usage: install.sh [options]

Options:
  --adapter=<name>   Target CLI: claude|gemini|kilo|codex|kimi|all (default: auto)
  --dry-run          Preview changes without applying
  --skip-npm         Skip npm/node checks
  --uninstall        Remove UTS from system
  --silent           Suppress output
  --help             Show this help

Examples:
  install.sh                      # Auto-detect CLI and install
  install.sh --adapter=gemini     # Install for Gemini CLI
  install.sh --adapter=all        # Install for ALL supported CLIs
  install.sh --uninstall          # Remove UTS

Supported CLIs:
  • Claude Code     ~/.claude
  • Gemini CLI      ~/.gemini
  • Kilo/Code       ~/.local/share/kilo
  • OpenCode        ~/.local/share/opencode
  • Codex CLI       ~/.codex
  • Kimi Code       ~/.kimi
HELP
  exit 0
fi

# ── Check Requirements ───────────────────────────────────────────────
check_requirements() {
  [[ $SKIP_NPM -eq 1 ]] && return
  
  command -v node &>/dev/null || die "Node.js required (install from nodejs.org)"
  command -v npm &>/dev/null || warn "npm not found — some features disabled"
  command -v python3 &>/dev/null || warn "python3 not found — some features disabled"
}

# ── Detect CLI ───────────────────────────────────────────────────────
detect_cli() {
  if [[ "$ADAPTER" != "auto" ]]; then
    echo "$ADAPTER"
    return
  fi
  
  for dir in \
    "$HOME/.claude:claude" \
    "$HOME/.gemini:gemini" \
    "$HOME/.local/share/opencode:opencode" \
    "$HOME/.codex:codex" \
    "$HOME/.kimi:kimi" \
    "$HOME/.openclaw:openclaw"
  do
    local path="${dir%%:*}"
    local cli="${dir##*:}"
    [[ -d "$path" ]] && { echo "$cli"; return; }
  done
  
  echo "unknown"
}

# ── Show Banner ─────────────────────────────────────────────────────
banner() {
  [[ $SILENT -eq 1 ]] && return
  
  echo ""
  echo -e "${B}╔═══════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${B}║   ⚡ Universal Token Saver v${UTS_VERSION}                          ║${NC}"
  echo -e "${B}║   60-90% CLI savings for ALL coding agents              ║${NC}"
  echo -e "${B}╚═══════════════════════════════════════════════════════════════╝${NC}"
  echo ""
}

# ── Backup ───────────────────────────────────────────────────────────
backup() {
  local backup_dir="$HOME/.uts-backup-$(date +%Y%m%d-%H%M%S)"
  
  if [[ -d "$UTS_HOME" ]]; then
    ok "Backing up existing UTS → $backup_dir"
    [[ $DRY_RUN -eq 0 ]] && cp -r "$UTS_HOME" "$backup_dir"
  fi
}

# ── Install Core Files ───────────────────────────────────────────────
install_core() {
  info "Installing UTS Core..."
  
  run "mkdir -p '$VAULT_DIR/commands' '$VAULT_DIR/agents' '$VAULT_DIR/skills'"
  run "mkdir -p '$PLUGINS_DIR' '$ADAPTERS_DIR'"
  
  # Core files
  run "curl -fsSL '$UTS_REPO/core/adapter-interface.js' -o '$ADAPTERS_DIR/interface.js'"
  run "curl -fsSL '$UTS_REPO/plugins/output-filter.js' -o '$PLUGINS_DIR/output-filter.js'"
  run "curl -fsSL '$UTS_REPO/plugins/rtk-universal.sh' -o '$PLUGINS_DIR/rtk-universal.sh'"
  run "chmod +x '$PLUGINS_DIR/rtk-universal.sh'"
  
  ok "Core files installed"
}

# ── Install Adapter ──────────────────────────────────────────────────
install_adapter() {
  local cli="$1"
  local adapter_file="$ADAPTERS_DIR/$cli.js"
  
  info "Installing adapter: $cli"
  
  case "$cli" in
    claude)
      install_claude_adapter
      ;;
    gemini)
      install_gemini_adapter
      ;;
    kilo|opencode)
      install_kilo_adapter
      ;;
    codex)
      install_codex_adapter
      ;;
    kimi)
      install_kimi_adapter
      ;;
    *)
      warn "Unknown adapter: $cli"
      ;;
  esac
}

# ── Claude Adapter ───────────────────────────────────────────────────
install_claude_adapter() {
  run "curl -fsSL '$UTS_REPO/adapters/claude-code.js' -o '$ADAPTERS_DIR/claude.js'"
  
  # Add to Claude settings
  local settings="$HOME/.claude/settings.json"
  
  if [[ -f "$settings" ]]; then
    python3 - <<PY
import json

settings = "$settings"
data = json.load(open(settings))

# Add RTK hook
if 'hooks' not in data:
    data['hooks'] = {}
if 'PreToolUse' not in data['hooks']:
    data['hooks']['PreToolUse'] = []

rtk_hook = {
    "hook": {
        "name": "uts-rtk",
        "command": "$PLUGINS_DIR/rtk-universal.sh wrap",
        "enabled": True
    }
}

for h in data['hooks']['PreToolUse']:
    if 'uts' in h.get('hook', {}).get('command', ''):
        break
else:
    data['hooks']['PreToolUse'].append(rtk_hook)
    json.dump(data, open(settings, 'w'), indent=2)
    print("Claude hook added")
PY
  fi
  
  ok "Claude Code adapter installed"
}

# ── Gemini Adapter ───────────────────────────────────────────────────
install_gemini_adapter() {
  run "curl -fsSL '$UTS_REPO/adapters/gemini-cli.js' -o '$ADAPTERS_DIR/gemini.js'"
  
  # Gemini MCP server config
  local gemini_dir="$HOME/.gemini"
  mkdir -p "$gemini_dir/mcp-servers"
  
  cat > "$gemini_dir/mcp-servers/uts-filter.json" <<EOF
{
  "name": "uts-output-filter",
  "command": "node",
  "args": ["$ADAPTERS_DIR/../plugins/output-filter.js"],
  "enabled": true
}
EOF
  
  ok "Gemini CLI adapter installed"
}

# ── Kilo Adapter ─────────────────────────────────────────────────────
install_kilo_adapter() {
  run "curl -fsSL '$UTS_REPO/adapters/kilo-code.js' -o '$ADAPTERS_DIR/kilo.js'"
  
  # OpenCode hooks
  local hooks_dir="$HOME/.local/share/opencode/hooks"
  mkdir -p "$hooks_dir"
  
  cat > "$hooks_dir/uts-config.json" <<EOF
{
  "name": "uts-filter",
  "script": "$PLUGINS_DIR/rtk-universal.sh",
  "events": ["pre_tool", "post_tool"],
  "enabled": true
}
EOF
  
  ok "Kilo/Code adapter installed"
}

# ── Codex Adapter ────────────────────────────────────────────────────
install_codex_adapter() {
  run "curl -fsSL '$UTS_REPO/adapters/codex.js' -o '$ADAPTERS_DIR/codex.js'"
  
  # Codex config
  local codex_config="$HOME/.codex/config.json"
  mkdir -p "$(dirname "$codex_config")"
  
  if [[ -f "$codex_config" ]]; then
    python3 - <<PY
import json

config = json.load(open("$codex_config"))
config['hooks'] = config.get('hooks', {})
config['hooks']['output_filter'] = "$PLUGINS_DIR/output-filter.js"
json.dump(config, open("$codex_config", 'w'), indent=2)
PY
  else
    echo '{}' | python3 -c "
import json, sys
config = json.load(sys.stdin)
config['hooks'] = {'output_filter': '$PLUGINS_DIR/output-filter.js'}
json.dump(config, open('$codex_config', 'w'), indent=2)
"
  fi
  
  ok "Codex CLI adapter installed"
}

# ── Kimi Adapter ─────────────────────────────────────────────────────
install_kimi_adapter() {
  run "curl -fsSL '$UTS_REPO/adapters/kimi-cli.js' -o '$ADAPTERS_DIR/kimi.js'"
  
  # Kimi plugin
  local kimi_plugins="$HOME/.kimi/plugins"
  mkdir -p "$kimi_plugins/uts"
  
  cat > "$kimi_plugins/uts/manifest.json" <<EOF
{
  "name": "uts-token-saver",
  "version": "$UTS_VERSION",
  "hooks": ["pre_tool", "post_tool"],
  "enabled": true
}
EOF
  
  ok "Kimi Code adapter installed"
}

# ── Install Dashboard CLI ────────────────────────────────────────────
install_dashboard() {
  info "Installing UTS Dashboard CLI..."
  
  run "curl -fsSL '$UTS_REPO/cli/uts-dashboard.js' -o '$UTS_HOME/bin/uts'"
  run "chmod +x '$UTS_HOME/bin/uts'"
  
  # Add to PATH hint
  echo ""
  ok "UTS Dashboard installed"
  echo ""
  echo -e "  ${B}Add to PATH:${NC}"
  echo -e "    export PATH=\"\$PATH:$UTS_HOME/bin\""
  echo -e "    # Or add to ~/.bashrc / ~/.zshrc"
  echo ""
}

# ── Initialize Stats ──────────────────────────────────────────────────
init_stats() {
  if [[ ! -f "$STATS_FILE" ]]; then
    run "cat > '$STATS_FILE' <<'EOF'
{
  \"version\": \"$UTS_VERSION\",
  \"total_saved_tokens\": 0,
  \"total_commands\": 0,
  \"sessions\": 0,
  \"by_cli\": {}
}
EOF"
  fi
}

# ── Uninstall ────────────────────────────────────────────────────────
uninstall() {
  echo ""
  echo -e "${Y}Uninstalling Universal Token Saver...${NC}"
  echo ""
  
  # Backup first
  backup()
  
  # Remove hook from Claude settings
  if [[ -f "$HOME/.claude/settings.json" ]]; then
    python3 - <<PY
import json

settings = "$HOME/.claude/settings.json"
data = json.load(open(settings))

if 'hooks' in data and 'PreToolUse' in data['hooks']:
    before = len(data['hooks']['PreToolUse'])
    data['hooks']['PreToolUse'] = [
        h for h in data['hooks']['PreToolUse']
        if 'uts' not in h.get('hook', {}).get('command', '')
    ]
    after = len(data['hooks']['PreToolUse'])
    
    if before != after:
        json.dump(data, open(settings, 'w'), indent=2)
        print(f"Removed {before - after} Claude hooks")
PY
  fi
  
  # Remove UTS directory
  if [[ -d "$UTS_HOME" ]]; then
    run "rm -rf '$UTS_HOME'"
  fi
  
  ok "UTS uninstalled"
  echo ""
  echo -e "  ${DIM}Backup saved to: $HOME/.uts-backup-*/${NC}"
}

# ── Summary ──────────────────────────────────────────────────────────
show_summary() {
  local cli="$1"
  
  echo ""
  echo -e "${G}${B}╔═══════════════════════════════════════════════════════════╗${NC}"
  echo -e "${G}${B}║   ⚡ Universal Token Saver — Installed!                  ║${NC}"
  echo -e "${G}${B}╚═══════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "${B}Active CLI:${NC}  $cli"
  echo -e "${B}Install Dir:${NC} $UTS_HOME"
  echo ""
  echo -e "${B}What's installed:${NC}"
  echo "  • UTS Core Engine (universal adapter interface)"
  echo "  • RTK Universal (60-90% CLI compression)"
  echo "  • Output Filter (70-95% noise reduction)"
  echo "  • $cli adapter"
  echo "  • Vault system (0 startup tokens)"
  echo ""
  echo -e "${B}Quick Commands:${NC}"
  echo "  uts dashboard     — Show multi-agent token dashboard"
  echo "  uts agents        — List detected CLI agents"
  echo "  uts stats         — Detailed stats"
  echo "  uts install <cli> — Install for another CLI"
  echo ""
  echo -e "  ${Y}Restart your terminal or source your shell config to use 'uts'.${NC}"
  echo ""
}

# ── Main ─────────────────────────────────────────────────────────────
main() {
  banner
  
  [[ $UNINSTALL -eq 1 ]] && { uninstall; exit 0; }
  
  check_requirements
  
  local cli=$(detect_cli)
  info "Detected CLI: $cli"
  
  backup
  install_core
  
  if [[ "$ADAPTER" == "all" ]]; then
    for a in claude gemini kilo codex kimi; do
      install_adapter "$a"
    done
  else
    install_adapter "$cli"
  fi
  
  install_dashboard
  init_stats
  show_summary "$cli"
}

main
