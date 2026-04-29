#!/usr/bin/env node
/**
 * Kilo/Code + OpenCode Adapter für Universal Token Saver
 * Tracking: ~/.local/share/opencode/opencode.db (SQLite)
 */

import { CLIAdapter, TokenUsage, Session, AdapterStats } from '../core/adapter-interface';

const ADAPTER: CLIAdapter = {
  name: 'Kilo/Code',
  icon: '⚡',
  configDir: `${process.env.HOME}/.local/share/kilo`,
  sessionPattern: 'opencode.db',
  requiresApiKey: true,
  trackingPaths: [
    '~/.local/share/opencode/',
    '~/.local/share/kilo/',
  ],
  vaultDir: `${process.env.HOME}/.uts/kilo`,
  settingsFile: `${process.env.HOME}/.local/share/kilo/config.json`,

  async parseTokens(sessionPath: string): Promise<TokenUsage | null> {
    // Für SQLite: brauchen wir besseres Parsing
    // Hier ein vereinfachtes Beispiel
    const fs = require('fs');
    
    try {
      // Versuche JSON-Export aus SQLite zu lesen
      if (sessionPath.endsWith('.json')) {
        const data = JSON.parse(fs.readFileSync(sessionPath, 'utf8'));
        return {
          inputTokens: data.input_tokens || 0,
          outputTokens: data.output_tokens || 0,
          totalTokens: (data.input_tokens || 0) + (data.output_tokens || 0),
          cost: data.cost || this.estimateCost(data),
          model: data.model || 'unknown',
          timestamp: new Date(data.timestamp || Date.now()),
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
    const opencodeDir = `${process.env.HOME}/.local/share/opencode`;
    
    if (!fs.existsSync(opencodeDir)) return sessions;
    
    const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
    
    // OpenCode 1.2+ nutzt opencode.db
    const dbFiles = glob.sync(`${opencodeDir}/*.db`);
    
    for (const dbFile of dbFiles) {
      try {
        // SQLite DB parsen (benötigt sqlite3 oder sql.js)
        // Hier: vereinfacht mit JSON-Export wenn verfügbar
        const mtime = fs.statSync(dbFile).mtimeMs;
        if (mtime < cutoff) continue;
        
        const usage = await this.parseFromDB(dbFile);
        
        sessions.push({
          id: path.basename(dbFile, '.db'),
          path: dbFile,
          startTime: new Date(mtime),
          tokens: usage || { inputTokens: 0, outputTokens: 0, totalTokens: 0, cost: 0, model: 'unknown', timestamp: new Date() },
          commands: 0,
        });
      } catch {
        // Skip
      }
    }
    
    // Legacy: message storage
    const messageDir = `${opencodeDir}/storage/message`;
    if (fs.existsSync(messageDir)) {
      const files = glob.sync(`${messageDir}/**/*.json`);
      
      for (const file of files) {
        try {
          const mtime = fs.statSync(file).mtimeMs;
          if (mtime < cutoff) continue;
          
          const usage = await this.parseTokens(file);
          
          sessions.push({
            id: path.basename(file, '.json'),
            path: file,
            startTime: new Date(mtime),
            tokens: usage || { inputTokens: 0, outputTokens: 0, totalTokens: 0, cost: 0, model: 'unknown', timestamp: new Date() },
            commands: this.countMessages(file),
          });
        } catch {
          // Skip
        }
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
        vault: sessions.length * 15000,
        rtk: sessions.reduce((s, x) => s + x.commands * 450, 0) * 0.7,
        output: sessions.reduce((s, x) => s + x.commands * 200, 0) * 0.8,
        total: 0,
      },
    };
  },

  async installHook(): Promise<void> {
    // Kilo/OpenCode nutzt opencode hooks
    const fs = require('fs');
    const home = process.env.HOME;
    
    const hookDir = `${home}/.local/share/opencode/hooks`;
    fs.mkdirSync(hookDir, { recursive: true });
    
    const hookConfig = {
      name: 'uts-output-filter',
      command: 'node',
      args: [`${__dirname}/../plugins/output-filter.js`],
      events: ['pre_tool', 'post_tool'],
      enabled: true,
    };
    
    fs.writeFileSync(`${hookDir}/uts-config.json`, JSON.stringify(hookConfig, null, 2));
  },

  async uninstallHook(): Promise<void> {
    const fs = require('fs');
    const home = process.env.HOME;
    
    const hookFile = `${home}/.local/share/opencode/hooks/uts-config.json`;
    if (fs.existsSync(hookFile)) {
      fs.unlinkSync(hookFile);
    }
  },

  isHookActive(): boolean {
    const fs = require('fs');
    const home = process.env.HOME;
    const hookFile = `${home}/.local/share/opencode/hooks/uts-config.json`;
    
    if (!fs.existsSync(hookFile)) return false;
    
    try {
      const config = JSON.parse(fs.readFileSync(hookFile, 'utf8'));
      return config.enabled === true;
    } catch {
      return false;
    }
  },

  estimateCost(data: any): number {
    const rates: Record<string, { in: number; out: number }> = {
      'gpt-4.5': { in: 2.5, out: 10 },
      'gpt-4o': { in: 2.5, out: 10 },
      'claude-sonnet-4-6': { in: 3, out: 15 },
      'claude-opus-4-7': { in: 15, out: 75 },
      'claude-haiku-4-5': { in: 0.25, out: 1.25 },
      'gemini-2.5-pro': { in: 1.25, out: 5 },
    };
    
    const rate = rates[data.model] || { in: 2.5, out: 10 };
    return ((data.input_tokens || 0) / 1_000_000) * rate.in + 
           ((data.output_tokens || 0) / 1_000_000) * rate.out;
  },

  async parseFromDB(dbFile: string): Promise<TokenUsage | null> {
    // SQLite parsing würde sql.js oder native sqlite3 benötigen
    // Hier: Versuche alternativ JSON-Files zu finden
    const fs = require('fs');
    const path = require('path');
    
    const jsonFile = dbFile.replace('.db', '.json');
    if (fs.existsSync(jsonFile)) {
      return this.parseTokens(jsonFile);
    }
    
    return null;
  },

  countMessages(file: string): number {
    const fs = require('fs');
    try {
      const data = JSON.parse(fs.readFileSync(file, 'utf8'));
      return Array.isArray(data.messages) ? data.messages.length : 0;
    } catch {
      return 0;
    }
  },
};

export default ADAPTER;
