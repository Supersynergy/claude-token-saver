#!/bin/bash
# Claude Skill Manager & Token Saver — SessionStart hook
# Auto-rebuilds skills.idx if missing or skills dir changed recently
# Runs async, never blocks session start

CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
IDX="$CLAUDE_DIR/skills.idx"
CATALOG="$CLAUDE_DIR/skills-catalog.md"
SCRIPT="$CLAUDE_DIR/scripts/build-skills-index.py"
STAMP="$CLAUDE_DIR/.skills-idx-ts"

# Rebuild if index is missing
if [ ! -f "$IDX" ] || [ ! -f "$CATALOG" ]; then
    if [ -f "$SCRIPT" ]; then
        python3 "$SCRIPT" --quiet 2>/dev/null
    fi
fi

# Throttle: re-stamp once per 6 hours (21600s)
NOW=$(date +%s)
LAST=$(cat "$STAMP" 2>/dev/null || echo 0)
if [ $((NOW - LAST)) -gt 21600 ]; then
    echo "$NOW" > "$STAMP"
fi

exit 0
