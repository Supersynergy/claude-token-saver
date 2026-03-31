# RTK — Rust Token Killer v0.33.1

**Auto-active via PreToolUse hook.** All Bash commands transparently rewritten.
**Savings**: 60-90% per CLI call | **Ultra-compact**: add `-u` for +10-20% more

## Meta Commands (call rtk directly — NOT via hook)

```bash
rtk gain                      # Token savings dashboard
rtk gain --graph              # 30-day ASCII trend
rtk gain --history            # Per-command history
rtk discover -a               # Find ALL missed opportunities
rtk discover --since 7        # Last 7 days only
rtk verify                    # Validate hook integrity
rtk proxy <cmd>               # Execute raw, no compression (debug)
rtk init -g                   # Refresh hook to latest version
```

## Ultra-Compact Mode (`-u` flag) — +10-20% additional savings

```bash
rtk ls -u                     # ASCII icons, inline format
rtk grep pattern -u           # Deduplicated, minimal output
rtk find . -name "*.ts" -u    # Compact results
```

## Hook-Based (Automatic — transparent)

```
git status/log/diff  →  rtk git *     (80% savings)
ls / find            →  rtk ls/find   (80-96% savings)
grep / rg            →  rtk grep      (55-75% savings)
cargo test/check     →  rtk cargo *   (91-98% savings)
pytest / npm test    →  rtk pytest    (80-90% savings)
docker ps/images     →  rtk docker *  (70% savings)
npm list / uv list   →  rtk npm/uv    (60-80% savings)
```

## ⚠️ Name Collision

If `rtk gain` fails → you have `reachingforthejack/rtk` (Rust Type Kit) instead.
Fix: `brew install rtk-ai/tap/rtk` or check https://rtk-ai.app
