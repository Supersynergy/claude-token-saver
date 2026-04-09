#!/usr/bin/env node
/**
 * Codex CLI Adapter für Universal Token Saver
 * Tracking: ~/.codex/sessions/
 */

import { CLIAdapter, TokenUsage, Session, AdapterStats } from '../core/adapter-interface';

const ADAPTER: CLIAdapter = {
  name: 'Codex CLI',
  icon: '🔮',
  configDir: `${process.env.HOME}/.codex`,
  sessionPattern: 'sessions/**/*',
  requiresApiKey: true,
  trackingPaths: [
    '~/.codex/sessions/',
    '~/.codex/cache/',
  ],
  vaultDir: `${process.env.HOME}/.uts/codex`,
  settingsFile: `${process.env.HOME}/.codex/config.json`,

  async parseTokens(sessionPath: string): Promise<TokenUsage | null> {
    const fs = require('fs');
    
    try {
      const content = fs.readFileSync(sessionPath, 'utf8');
      const session = JSON.parse(content);
      
      // Codex Session Structure
      return {
        inputTokens: session.usage?.input_tokens || this.estimateTokens(session.messages || []),
        outputTokens: session.usage?.output_tokens || 0,
        totalTokens: (session.usage?.input_tokens || 0) + (session.usage?.output_tokens || 0),
        cost: session.usage?.cost || this.estimateCost(session),
        model: session.model || 'gpt-4o',
        timestamp: new Date(session.created_at || Date.now()),
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
    const sessionsDir = `${this.configDir}/sessions`;
    
    if (!fs.existsSync(sessionsDir)) return sessions;
    
    const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
    const sessionFiles = glob.sync(`${sessionsDir}/**/*.json`);
    
    for (const sessionFile of sessionFiles) {
      try {
        const mtime = fs.statSync(sessionFile).mtimeMs;
        if (mtime < cutoff) continue;
        
        const usage = await this.parseTokens(sessionFile);
        const sessionId = path.basename(path.dirname(sessionFile));
        
        sessions.push({
          id: sessionId,
          path: sessionFile,
          startTime: new Date(mtime),
          tokens: usage || { inputTokens: 0, outputTokens: 0, totalTokens: 0, cost: 0, model: 'unknown', timestamp: new Date() },
          commands: this.countInteractions(sessionFile),
        });
      } catch {
        // Skip invalid sessions
      }
    }
    
    return sessions;
  },

  async getStats(days: number): Promise<AdapterStats> {
    const sessions = await this.getHistory(days);
    
    return {
      adapter: this.name,
      sessions: sessions.length,
      inputTokens: sessions.reduce((s, x) => s + x.tokens.inputTokens, 0),
      outputTokens: sessions.reduce((s, x) => s + x.tokens.outputTokens, 0),
      totalTokens: sessions.reduce((s, x) => s + x.tokens.totalTokens, 0),
      cost: sessions.reduce((s, x) => s + x.tokens.cost, 0),
      commands: sessions.reduce((s, x) => s + x.commands, 0),
      savings: {
        vault: sessions.length * 10000,
        rtk: sessions.reduce((s, x) => s + x.commands * 400, 0) * 0.65,
        output: sessions.reduce((s, x) => s + x.commands * 180, 0) * 0.75,
        total: 0,
      },
    };
  },

  async installHook(): Promise<void> {
    // Codex CLI hooks
    const fs = require('fs');
    const home = process.env.HOME;
    
    const hookScript = `#!/usr/bin/env bash
# UTS Output Filter for Codex CLI
# Wrapper script für rtk integration

CMD="$1"
shift

# Run original command through RTK
result=$(rtk proxy "$CMD" "$@")

# Filter output
echo "$result" | rtk filter
`;
    
    const hooksDir = `${home}/.codex/hooks`;
    fs.mkdirSync(hooksDir, { recursive: true });
    fs.writeFileSync(`${hooksDir}/uts-filter.sh`, hookScript);
    
    // Codex config aktualisieren
    const configPath = `${home}/.codex/config.json`;
    let config: any = {};
    
    if (fs.existsSync(configPath)) {
      config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }
    
    if (!config.hooks) config.hooks = {};
    config.hooks.output_filter = `${hooksDir}/uts-filter.sh`;
    
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
  },

  async uninstallHook(): Promise<void> {
    const fs = require('fs');
    const home = process.env.HOME;
    
    const configPath = `${home}/.codex/config.json`;
    const hookScript = `${home}/.codex/hooks/uts-filter.sh`;
    
    if (fs.existsSync(configPath)) {
      const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      delete config.hooks?.output_filter;
      fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
    }
    
    if (fs.existsSync(hookScript)) {
      fs.unlinkSync(hookScript);
    }
  },

  isHookActive(): boolean {
    const fs = require('fs');
    const home = process.env.HOME;
    const hookScript = `${home}/.codex/hooks/uts-filter.sh`;
    
    if (!fs.existsSync(hookScript)) return false;
    
    const configPath = `${home}/.codex/config.json`;
    if (!fs.existsSync(configPath)) return false;
    
    try {
      const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      return !!config.hooks?.output_filter;
    } catch {
      return false;
    }
  },

  estimateTokens(messages: any[]): number {
    return messages.reduce((sum, msg) => {
      const content = typeof msg.content === 'string' 
        ? msg.content 
        : JSON.stringify(msg.content || '');
      return sum + Math.ceil(content.length / 4);
    }, 0);
  },

  estimateCost(session: any): number {
    const inputTokens = session.usage?.input_tokens || 0;
    const outputTokens = session.usage?.output_tokens || 0;
    
    // GPT-4o pricing
    return (inputTokens / 1_000_000) * 2.5 + (outputTokens / 1_000_000) * 10;
  },

  countInteractions(sessionFile: string): number {
    const fs = require('fs');
    try {
      const session = JSON.parse(fs.readFileSync(sessionFile, 'utf8'));
      return session.messages?.length || 0;
    } catch {
      return 0;
    }
  },
};

export default ADAPTER;
