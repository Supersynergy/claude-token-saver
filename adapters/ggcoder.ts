#!/usr/bin/env node
/**
 * ggcoder / superggcoder Adapter für Universal Token Saver
 * Target: @kenkaiiii/ggcoder (npm global) + super27 patch layer
 * Config at ~/.claude/bin/ggcoder-wrapper.sh, autopatch at ~/.claude/bin/ggcoder-autopatch.mjs
 *
 * Native tool stack (super27): hyperfetch/smart-fetch/batchscraper/supersearch/super-research/
 * grepgod/ghgrep/uda/feeds-pull/fd wired via tools/prompt-hints.js dict overlay + system-prompt
 * routing-table injection. No MCP — direct tool overlays in dist/tools/.
 */

import { CLIAdapter, TokenUsage, Session, AdapterStats, SavingsReport } from '../core/adapter-interface';

const ADAPTER: CLIAdapter = {
  name: 'ggcoder',
  icon: '⚡',
  configDir: `${process.env.HOME}/.claude`,
  sessionPattern: 'command-sessions/**/*',
  requiresApiKey: false,
  trackingPaths: [
    '~/.claude/command-sessions/',
    '~/.claude/logs/ggcoder-autopatch.log',
  ],
  vaultDir: `${process.env.HOME}/.claude/cts/ggcoder`,
  settingsFile: `${process.env.HOME}/.claude/bin/ggcoder-wrapper.sh`,

  async parseTokens(sessionPath: string): Promise<TokenUsage | null> {
    const fs = require('fs');
    try {
      if (!fs.existsSync(sessionPath)) return null;
      const lines = fs.readFileSync(sessionPath, 'utf8').split('\n').filter((l: string) => l.trim());
      let inputTokens = 0;
      let outputTokens = 0;
      let model = 'claude-sonnet-4-6';
      let timestamp = Date.now();
      for (const l of lines) {
        try {
          const j = JSON.parse(l);
          if (j.usage) {
            inputTokens += j.usage.input_tokens || 0;
            outputTokens += j.usage.output_tokens || 0;
            inputTokens += j.usage.cache_read_input_tokens || 0;
          }
          if (j.model) model = j.model;
          if (j.timestamp) timestamp = new Date(j.timestamp).getTime();
        } catch { /* skip */ }
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
    const root = `${this.configDir}/command-sessions`;
    if (!fs.existsSync(root)) return sessions;
    const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
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
    return sessions.sort((a, b) => (b.endedAt?.getTime() || 0) - (a.endedAt?.getTime() || 0));
  },

  async installHook(): Promise<void> {
    // Install means: run autopatch to ensure native tool stack is current.
    const { execFileSync } = require('child_process');
    try {
      execFileSync('node', [`${process.env.HOME}/.claude/bin/ggcoder-autopatch.mjs`], {
        stdio: 'inherit',
        timeout: 60000,
      });
    } catch { /* already patched or patcher missing */ }
  },

  async uninstallHook(): Promise<void> {
    // Revert overlays to .orig backups.
    const fs = require('fs');
    const glob = require('glob');
    const { execSync } = require('child_process');
    const dist = execSync('npm root -g', { encoding: 'utf8' }).trim() + '/@kenkaiiii/ggcoder/dist';
    const origs = glob.sync(`${dist}/**/*.orig`);
    for (const orig of origs) {
      const target = orig.replace(/\.orig$/, '');
      try { fs.copyFileSync(orig, target); } catch {}
    }
  },

  isHookActive(): boolean {
    const fs = require('fs');
    const { execSync } = require('child_process');
    try {
      const dist = execSync('npm root -g', { encoding: 'utf8' }).trim() + '/@kenkaiiii/ggcoder/dist';
      const hints = fs.readFileSync(`${dist}/tools/prompt-hints.js`, 'utf8');
      return hints.includes('super27:prompthints') && hints.includes('batchscraper');
    } catch {
      return false;
    }
  },

  estimateCost(usage: any): number {
    const rates: Record<string, { in: number; out: number }> = {
      'claude-opus-4-7':   { in: 15,   out: 75   },
      'claude-sonnet-4-6': { in: 3,    out: 15   },
      'claude-haiku-4-5':  { in: 0.25, out: 1.25 },
    };
    const model = (usage.model || 'claude-sonnet-4-6').toLowerCase();
    const rate = Object.entries(rates).find(([k]) => model.includes(k.toLowerCase()))?.[1]
      || rates['claude-sonnet-4-6'];
    return (usage.inputTokens / 1_000_000) * rate.in + (usage.outputTokens / 1_000_000) * rate.out;
  },
};

export default ADAPTER;
