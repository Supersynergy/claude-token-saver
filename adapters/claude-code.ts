#!/usr/bin/env node
/**
 * Claude Code Adapter für Universal Token Saver
 */

import { CLIAdapter, TokenUsage, Session, AdapterStats, SavingsReport } from '../core/adapter-interface';

const ADAPTER: CLIAdapter = {
  name: 'Claude Code',
  icon: '🦙',
  configDir: `${process.env.HOME}/.claude`,
  sessionPattern: 'projects/**/*',
  requiresApiKey: false,
  trackingPaths: [
    '~/.claude/projects/',
    '~/.claude/command-sessions/',
  ],
  vaultDir: `${process.env.HOME}/.claude/cts`,
  settingsFile: `${process.env.HOME}/.claude/settings.json`,

  async parseTokens(sessionPath: string): Promise<TokenUsage | null> {
    const fs = require('fs');
    const path = require('path');
    
    try {
      // Claude Code speichert Usage in .usage.json oder in der session
      const sessionDir = path.dirname(sessionPath);
      const usageFile = path.join(sessionDir, '.usage.json');
      
      if (fs.existsSync(usageFile)) {
        const usage = JSON.parse(fs.readFileSync(usageFile, 'utf8'));
        return {
          inputTokens: usage.inputTokens || 0,
          outputTokens: usage.outputTokens || 0,
          totalTokens: (usage.inputTokens || 0) + (usage.outputTokens || 0),
          cost: usage.cost || this.estimateCost(usage),
          model: usage.model || 'claude-sonnet-4-6',
          timestamp: new Date(usage.timestamp || Date.now()),
        };
      }
      
      return null;
    } catch {
      return null;
    }
  },

  async getHistory(days: number): Promise<Session[]> {
    const fs = require('fs');
    const path = require('path');
    const glob = require('glob');
    
    const sessions: Session[] = [];
    const projectsDir = `${this.configDir}/projects`;
    
    if (!fs.existsSync(projectsDir)) return sessions;
    
    const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
    const patterns = glob.sync(`${projectsDir}/**/session.json`);
    
    for (const sessionFile of patterns) {
      try {
        const session = JSON.parse(fs.readFileSync(sessionFile, 'utf8'));
        const mtime = fs.statSync(sessionFile).mtimeMs;
        
        if (mtime < cutoff) continue;
        
        const usage = await this.parseTokens(sessionFile);
        
        sessions.push({
          id: session.id || path.basename(path.dirname(sessionFile)),
          path: sessionFile,
          startTime: new Date(session.startTime || mtime),
          endTime: session.endTime ? new Date(session.endTime) : undefined,
          tokens: usage || { inputTokens: 0, outputTokens: 0, totalTokens: 0, cost: 0, model: 'unknown', timestamp: new Date() },
          commands: session.commandCount || 0,
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
        vault: sessions.length * 18000, // ~18k tokens/session saved
        rtk: sessions.reduce((s, x) => s + x.commands * 500, 0) * 0.7, // 70% via RTK
        output: sessions.reduce((s, x) => s + x.commands * 200, 0) * 0.8, // 80% noise
        total: 0,
      },
    };
  },

  async installHook(): Promise<void> {
    const fs = require('fs');
    const path = require('path');
    
    // Claude Code nutzt PreToolUse Hook in settings.json
    const settingsPath = this.settingsFile;
    let settings: any = {};
    
    if (fs.existsSync(settingsPath)) {
      settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
    }
    
    // RTK Hook hinzufügen
    if (!settings.hooks) settings.hooks = {};
    if (!settings.hooks.PreToolUse) settings.hooks.PreToolUse = [];
    
    const rtkHook = {
      hook: {
        name: 'rtk-compress',
        command: 'rtk proxy',
        enabled: true,
      },
    };
    
    // Nur hinzufügen wenn nicht schon vorhanden
    const exists = settings.hooks.PreToolUse.some((h: any) => 
      h.hook?.command?.includes('rtk')
    );
    
    if (!exists) {
      settings.hooks.PreToolUse.push(rtkHook);
      fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2));
    }
  },

  async uninstallHook(): Promise<void> {
    const fs = require('fs');
    const settingsPath = this.settingsFile;
    
    if (!fs.existsSync(settingsPath)) return;
    
    const settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
    
    if (settings.hooks?.PreToolUse) {
      settings.hooks.PreToolUse = settings.hooks.PreToolUse.filter((h: any) => 
        !h.hook?.command?.includes('rtk')
      );
      fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2));
    }
  },

  isHookActive(): boolean {
    const fs = require('fs');
    if (!fs.existsSync(this.settingsFile)) return false;
    
    try {
      const settings = JSON.parse(fs.readFileSync(this.settingsFile, 'utf8'));
      return settings.hooks?.PreToolUse?.some((h: any) => 
        h.hook?.command?.includes('rtk')
      ) || false;
    } catch {
      return false;
    }
  },

  estimateCost(usage: any): number {
    const rates: Record<string, { in: number; out: number }> = {
      'claude-haiku-4-5': { in: 0.25, out: 1.25 },
      'claude-sonnet-4-6': { in: 3, out: 15 },
      'claude-opus-4-7': { in: 15, out: 75 },
      'claude-3-5-haiku': { in: 0.25, out: 1.25 },
      'claude-3-5-sonnet': { in: 3, out: 15 },
      'claude-3-5-opus': { in: 15, out: 75 },
      'claude-3-7-sonnet': { in: 3, out: 15 },
    };

    const rate = rates[usage.model] || rates['claude-sonnet-4-6'];
    return (usage.inputTokens / 1_000_000) * rate.in + 
           (usage.outputTokens / 1_000_000) * rate.out;
  },
};

export default ADAPTER;
