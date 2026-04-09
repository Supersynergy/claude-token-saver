#!/usr/bin/env bash
# ╔═══════════════════════════════════════════════════════════════════╗
# ║   ⚡ RTK Universal — CLI Compression für ALLE Coding Agents    ║
# ║   Unterstützt: Claude Code, Gemini CLI, Kilo, Codex, Kimi       ║
# ╚═══════════════════════════════════════════════════════════════════╝
# 
# Auto-detectiert den aktiven CLI-Agent und wendet RTK entsprechend an.
# Funktioniert als Proxy oder Direct Wrapper.

set -euo pipefail

# ── Farben ───────────────────────────────────────────────────────
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; C='\033[0;36m'
B='\033[1m'; DIM='\033[2m'; NC='\033[0m'

# ── Version ──────────────────────────────────────────────────────
RTK_VERSION="1.0.0"
RTK_UNIVERSAL_VERSION="1.0.0"

# ── Standard-Pfade ───────────────────────────────────────────────
RTK_HOME="${RTK_HOME:-$HOME/.rtk}"
UTS_HOME="${UTS_HOME:-$HOME/.uts}"
HOOKS_DIR="$UTS_HOME/hooks"

# ── Auto-Detection ───────────────────────────────────────────────
detect_cli() {
  local cli="unknown"
  
  if [[ -d "$HOME/.claude" ]]; then
    cli="claude"
  elif [[ -d "$HOME/.gemini" ]]; then
    cli="gemini"
  elif [[ -f "$HOME/.local/share/opencode/opencode.db" ]]; then
    cli="kilo"
  elif [[ -d "$HOME/.codex" ]]; then
    cli="codex"
  elif [[ -d "$HOME/.kimi" ]]; then
    cli="kimi"
  elif [[ -d "$HOME/.openclaw" ]]; then
    cli="openclaw"
  fi
  
  echo "$cli"
}

# ── RTK Universal Compression Map ─────────────────────────────────
# Pro CLI-Tool angepasste Compressor-Commands
get_compressors() {
  local cli="$1"
  
  case "$cli" in
    claude)
      # Claude Code: nutzt rtk wenn verfügbar
      if command -v rtk &>/dev/null; then
        echo "rtk compress"
      else
        echo "cat"  # Fallback: keine Komprimierung
      fi
      ;;
    gemini)
      # Gemini CLI: nutzt gcloud filter
      echo "uts filter"
      ;;
    kilo|opencode)
      # Kilo/OpenCode: eigenes RTK
      echo "kilo rtk"
      ;;
    codex)
      # Codex: nutzt rtk
      echo "rtk compress"
      ;;
    kimi)
      # Kimi: uts filter
      echo "uts filter"
      ;;
    *)
      echo "cat"
      ;;
  esac
}

# ── Commands Map ──────────────────────────────────────────────────
# Mapping von Original-Commands zu komprimierten Versionen
declare -A RTK_GIT=(
  ["git status"]="git status -sb"
  ["git log"]="git log --oneline --graph --decorate"
  ["git diff"]="git diff --stat"
  ["git diff --cached"]="git diff --cached --stat"
)

declare -A RTK_LS=(
  ["ls -la"]="ls -1"
  ["ls -l"]="ls -1"
  ["ls"]="ls -1"
)

declare -A RTK_GREP=(
  ["grep -r"]="rg -l"
  ["grep -n"]="rg -n"
  ["grep -i"]="rg -i"
)

declare -A RTK_CARGO=(
  ["cargo test"]="cargo test --message-format=short"
  ["cargo build"]="cargo build --quiet"
  ["cargo check"]="cargo check --quiet"
)

declare -A RTK_PYTEST=(
  ["pytest"]="pytest -q --tb=short"
  ["pytest -v"]="pytest -q --tb=line"
)

declare -A RTK_NPM=(
  ["npm install"]="npm install --silent"
  ["npm list"]="npm list --depth=0"
  ["npm test"]="npm test --silent"
)

declare -A RTK_DOCKER=(
  ["docker ps"]="docker ps --format '{{.Names}}\t{{.Status}}'"
  ["docker images"]="docker images --format '{{.Repository}}\t{{.Tag}}\t{{.Size}}'"
  ["docker logs"]="docker logs --tail 50"
)

# ── Ultra-Compact Mode ─────────────────────────────────────────────
ultra_compact() {
  local cmd="$1"
  shift
  local args="$@"
  
  # Ultra-Flag Erkennung
  if [[ " $args " =~ " -u " ]] || [[ " $args " =~ " --ultra " ]]; then
    return 0
  fi
  return 1
}

# ── Command Rewrite ───────────────────────────────────────────────
rewrite_cmd() {
  local cli="$1"
  local original="$2"
  
  # Extrahiere Command + Args
  local cmd_part=$(echo "$original" | awk '{print $1}')
  local args_part=$(echo "$original" | awk '{$1=""; print $0}' | sed 's/^ //')
  
  # Ultra-Compact?
  local ultra=""
  if ultra_compact "$original" "$args_part"; then
    ultra="-u "
    args_part=$(echo "$args_part" | sed 's/ -u / /g; s/ --ultra / /g')
  fi
  
  # CLI-spezifisches Mapping
  case "$cli" in
    claude|kilo|codex)
      # Nutze RTK wenn verfügbar
      if command -v rtk &>/dev/null; then
        # Spezielle Mappings
        case "$cmd_part" in
          git)   echo "rtk git ${args_part:-$ultra}" ;;
          ls)    echo "rtk ls ${args_part:-$ultra}" ;;
          grep)  echo "rtk grep ${args_part:-$ultra}" ;;
          find)  echo "rtk find ${args_part:-$ultra}" ;;
          *)     echo "$original" ;;
        esac
      else
        echo "$original"
      fi
      ;;
    gemini|kimi)
      # Nutze UTS filter
      echo "uts filter \"$original\""
      ;;
    *)
      echo "$original"
      ;;
  esac
}

# ── RTK Stats ─────────────────────────────────────────────────────
show_stats() {
  local stats_file="$UTS_HOME/stats.json"
  
  if [[ ! -f "$stats_file" ]]; then
    echo "No stats yet. RTK Universal hasn't tracked any commands."
    return
  fi
  
  echo ""
  echo -e "${B}⚡ RTK Universal — Token Savings${NC}"
  echo -e "${B}═══════════════════════════════════${NC}"
  echo ""
  
  # Lese und formatiere Stats
  python3 - <<PY
import json
import os

stats_file = os.path.expanduser("$stats_file")

if os.path.exists(stats_file):
    with open(stats_file) as f:
        stats = json.load(f)
    
    total_saved = stats.get('total_saved_tokens', 0)
    commands = stats.get('total_commands', 0)
    sessions = stats.get('sessions', 0)
    
    print(f"  Total Commands:  {commands}")
    print(f"  Sessions:        {sessions}")
    print(f"  Tokens Saved:    {total_saved:,}")
    print(f"  Est. Cost Saved: \${total_saved * 0.000003:.2f}/month")
    print("")
    
    # Per-CLI breakdown
    if 'by_cli' in stats:
        print(f"  ${B}By CLI Agent:${NC}")
        for cli, data in stats['by_cli'].items():
            saved = data.get('saved_tokens', 0)
            cmds = data.get('commands', 0)
            print(f"    {cli}: {saved:,} tokens ({cmds} cmds)")
else:
    print("  No stats file found.")
PY
  
  echo ""
}

# ── Install Hook ──────────────────────────────────────────────────
install_hook() {
  local cli="${1:-$(detect_cli)}"
  
  echo -e "\n${B}Installing RTK Universal Hook for: $cli${NC}\n"
  
  # Erstelle UTS Home
  mkdir -p "$UTS_HOME/hooks"
  
  # Generiere Hook-Script
  cat > "$UTS_HOME/hooks/rtk-wrapper.sh" <<'WRAPPER'
#!/usr/bin/env bash
# RTK Universal Wrapper
# Wird von PreToolUse Hook aufgerufen

COMMAND="$1"
CLI="${RTK_CLI:-$(detect_cli)}"

# Rewrite Command wenn RTK verfügbar
if command -v rtk &>/dev/null; then
    case "$CLI" in
        claude|kilo|codex)
            # RTK passt automatisch via PreToolUse
            ;;
        gemini|kimi)
            # Filter verbose output
            COMMAND=$(rtk-universal compress "$COMMAND")
            ;;
    esac
fi

# Führe aus und tracke
/usr/bin/time -f "%E" $COMMAND 2>&1 | head -100
WRAPPER

  chmod +x "$UTS_HOME/hooks/rtk-wrapper.sh"
  
  # CLI-spezifische Installation
  case "$cli" in
    claude)
      install_claude_hook
      ;;
    gemini)
      install_gemini_hook
      ;;
    kilo)
      install_kilo_hook
      ;;
    codex)
      install_codex_hook
      ;;
  esac
  
  echo -e "${G}✓${NC} RTK Universal installed for $cli"
  echo -e "${G}✓${NC} Hook: $UTS_HOME/hooks/rtk-wrapper.sh"
}

# ── Claude Code Hook ──────────────────────────────────────────────
install_claude_hook() {
  local settings="$HOME/.claude/settings.json"
  
  if [[ ! -f "$settings" ]]; then
    echo -e "${Y}⚠${NC} Claude Code settings not found"
    return
  fi
  
  python3 - <<PY
import json

settings = "$settings"
backup = settings + ".bak"

# Backup
with open(settings) as f:
    content = f.read()
    with open(backup, 'w') as b:
        b.write(content)

data = json.loads(content)

# Add RTK hook
if 'hooks' not in data:
    data['hooks'] = {}
if 'PreToolUse' not in data['hooks']:
    data['hooks']['PreToolUse'] = []

rtk_hook = {
    "hook": {
        "name": "rtk-universal",
        "command": "rtk-universal wrap",
        "enabled": True
    }
}

# Check if already installed
for h in data['hooks']['PreToolUse']:
    if h.get('hook', {}).get('command', '').includes('rtk-universal'):
        print("RTK Universal already installed")
        break
else:
    data['hooks']['PreToolUse'].append(rtk_hook)
    with open(settings, 'w') as f:
        json.dump(data, f, indent=2)
    print("Claude Code hook installed")
PY
}

# ── Gemini CLI Hook ───────────────────────────────────────────────
install_gemini_hook() {
  echo "Gemini CLI: Copy hook to ~/.gemini/hooks/"
  mkdir -p "$HOME/.gemini/hooks"
  cp "$UTS_HOME/hooks/rtk-wrapper.sh" "$HOME/.gemini/hooks/"
}

# ── Kilo Hook ─────────────────────────────────────────────────────
install_kilo_hook() {
  echo "Kilo/OpenCode: Adding hook to config"
  mkdir -p "$HOME/.local/share/opencode/hooks"
  cat > "$HOME/.local/share/opencode/hooks/uts.json" <<EOF
{
  "name": "rtk-universal",
  "script": "$UTS_HOME/hooks/rtk-wrapper.sh",
  "events": ["pre_tool", "post_tool"],
  "enabled": true
}
EOF
}

# ── Codex Hook ─────────────────────────────────────────────────────
install_codex_hook() {
  echo "Codex CLI: Adding to config"
  mkdir -p "$HOME/.codex/hooks"
  cat > "$HOME/.codex/config.json" <<EOF
{
  "hooks": {
    "output_filter": "$UTS_HOME/hooks/rtk-wrapper.sh"
  }
}
EOF
}

# ── Main Dispatcher ───────────────────────────────────────────────
main() {
  local cmd="${1:-}"
  
  case "$cmd" in
    ""|-h|--help)
      echo "RTK Universal v$RTK_UNIVERSAL_VERSION"
      echo ""
      echo "Usage: rtk-universal <command>"
      echo ""
      echo "Commands:"
      echo "  wrap <cmd>       Execute command with RTK compression"
      echo "  compress <cmd>   Show compressed version"
      echo "  stats            Show savings statistics"
      echo "  install          Install hook for detected CLI"
      echo "  install <cli>    Install hook for specific CLI"
      echo "  detect           Detect active CLI"
      echo "  help             This help"
      echo ""
      ;;
    wrap)
      shift
      local cli=$(detect_cli)
      local compressed=$(rewrite_cmd "$cli" "$*")
      eval "$compressed"
      ;;
    compress)
      shift
      local cli=$(detect_cli)
      rewrite_cmd "$cli" "$*"
      ;;
    stats)
      show_stats
      ;;
    install)
      shift
      install_hook "$@"
      ;;
    detect)
      detect_cli
      ;;
    version|-v|--version)
      echo "RTK Universal v$RTK_UNIVERSAL_VERSION"
      ;;
    *)
      echo "Unknown command: $cmd"
      echo "Run 'rtk-universal help' for usage"
      exit 1
      ;;
  esac
}

main "$@"
