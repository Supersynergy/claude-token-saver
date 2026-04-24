#!/usr/bin/env node
/**
 * Hermes Adapter für Universal Token Saver
 * Target: Nous-Research Hermes agent (https://github.com/NousResearch/hermes-agent)
 * Config at ~/.hermes/config.yaml, sessions at ~/.local/state/hermes/
 *
 * Native tool stack wired via ~/.hermes/hermes-agent/HERMES.md + SOUL.md routing rules.
 * No MCP required — Hermes reads AGENTS.md/HERMES.md on session start.
 */

import { CLIAdapter, TokenUsage, Session, AdapterStats, SavingsReport } from '../core/adapter-interface';

const ADAPTER: CLIAdapter = {
  name: 'Hermes',
  icon: '🪽',
  configDir: `${process.env.HOME}/.hermes`,
  sessionPattern: 'sessions/**/*.jsonl',
  requiresApiKey: false,
  trackingPaths: [
    '~/.hermes/sessions/',
    '~/.local/state/hermes/',
    '~/.hermes/hermes-agent/memory/',
  ],
  vaultDir: `${process.env.HOME}/.hermes/cts-vault`,
  settingsFile: `${process.env.HOME}/.hermes/config.yaml`,

  async parseTokens(sessionPath: string): Promise<TokenUsage | null> {
    const fs = require('fs');
    try {
      if (!fs.existsSync(sessionPath)) return null;
      const lines = fs.readFileSync(sessionPath, 'utf8').split('\n').filter((l: string) => l.trim());
      let inputTokens = 0;
      let outputTokens = 0;
      let model = 'unknown';
      let timestamp = Date.now();
      for (const l of lines) {
        try {
          const j = JSON.parse(l);
          if (j.usage) {
            inputTokens += j.usage.input_tokens || j.usage.prompt_tokens || 0;
            outputTokens += j.usage.output_tokens || j.usage.completion_tokens || 0;
          }
          if (j.model) model = j.model;
          if (j.timestamp) timestamp = new Date(j.timestamp).getTime();
        } catch { /* skip malformed */ }
      }
      if (inputTokens + outputTokens === 0) return null;
      return {
        inputTokens,
        outputTokens,
        totalTokens: inputTokens + outputTokens,
        cost: this.estimateCost({ inputTokens, outputTokens, model }),
        model,
        timestamp: new Date(timestamp),
      };
    } catch {
      return null;
    }
  },

  async getHistory(days: number): Promise<Session[]> {
    const fs = require('fs');
    const path = require('path');
    const glob = require('glob');
    const sessions: Session[] = [];
    const roots = [
      `${process.env.HOME}/.hermes/sessions`,
      `${process.env.HOME}/.local/state/hermes/sessions`,
    ];
    const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
    for (const root of roots) {
      if (!fs.existsSync(root)) continue;
      const files = glob.sync(`${root}/**/*.jsonl`);
      for (const f of files) {
        const stat = fs.statSync(f);
        if (stat.mtimeMs < cutoff) continue;
        const usage = await this.parseTokens(f);
        if (!usage) continue;
        sessions.push({
          id: path.basename(f, '.jsonl'),
          path: f,
          startedAt: new Date(stat.birthtimeMs),
          endedAt: new Date(stat.mtimeMs),
          usage,
        });
      }
    }
    return sessions.sort((a, b) => (b.endedAt?.getTime() || 0) - (a.endedAt?.getTime() || 0));
  },

  async installHook(): Promise<void> {
    // Hermes reads HERMES.md / AGENTS.md / SOUL.md natively — no hook install needed.
    // Token saving via rtk prefix is documented in SOUL.md routing rules.
    // Ensure config.yaml has external skill dirs wired:
    const fs = require('fs');
    const yaml = this.settingsFile;
    if (!fs.existsSync(yaml)) return;
    const src = fs.readFileSync(yaml, 'utf8');
    if (src.includes('~/.claude/skills') && src.includes('~/.gg/skills')) return;
    const patched = src.replace(
      /skills:\s*\n\s*external_dirs:\s*\[\]/,
      `skills:\n  external_dirs:\n    - ~/.claude/skills\n    - ~/.claude/cts/skills\n    - ~/.gg/skills`,
    );
    if (patched !== src) fs.writeFileSync(yaml, patched);
  },

  async uninstallHook(): Promise<void> {
    // No-op: Hermes native config, leave intact.
  },

  isHookActive(): boolean {
    const fs = require('fs');
    const path = require('path');
    const soul = path.join(process.env.HOME || '', '.hermes/SOUL.md');
    if (!fs.existsSync(soul)) return false;
    const src = fs.readFileSync(soul, 'utf8');
    return src.includes('Native tool stack') && src.includes('rtk');
  },

  estimateCost(usage: any): number {
    // Hermes supports multiple providers: Anthropic, OpenAI, Ollama (local=free), Groq, etc.
    const rates: Record<string, { in: number; out: number }> = {
      'claude-opus-4-7':   { in: 15,   out: 75   },
      'claude-sonnet-4-6': { in: 3,    out: 15   },
      'claude-haiku-4-5':  { in: 0.25, out: 1.25 },
      'gpt-5':             { in: 5,    out: 20   },
      'gpt-4o':            { in: 2.5,  out: 10   },
      'llama3.3':          { in: 0,    out: 0    },
      'granite3.2:2b':     { in: 0,    out: 0    },
      'phi4-mini':         { in: 0,    out: 0    },
    };
    const model = (usage.model || '').toLowerCase();
    const rate = Object.entries(rates).find(([k]) => model.includes(k.toLowerCase()))?.[1]
      || { in: 1, out: 5 };
    return (usage.inputTokens / 1_000_000) * rate.in + (usage.outputTokens / 1_000_000) * rate.out;
  },
};

export default ADAPTER;
