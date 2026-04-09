#!/usr/bin/env node
/**
 * Gemini CLI Adapter für Universal Token Saver
 * Tracking: ~/.gemini/tmp/*/chats/*.json
 * Telemetry: OpenTelemetry gen_ai.client.token.usage
 */

import { CLIAdapter, TokenUsage, Session, AdapterStats } from '../core/adapter-interface';

const ADAPTER: CLIAdapter = {
  name: 'Gemini CLI',
  icon: '✨',
  configDir: `${process.env.HOME}/.gemini`,
  sessionPattern: 'tmp/*/chats/*.json',
  requiresApiKey: true,
  trackingPaths: [
    '~/.gemini/tmp/',
    '~/.gemini/cache/',
  ],
  vaultDir: `${process.env.HOME}/.uts/gemini`,
  settingsFile: `${process.env.HOME}/.gemini/settings.json`,

  async parseTokens(sessionPath: string): Promise<TokenUsage | null> {
    const fs = require('fs');
    
    try {
      const content = fs.readFileSync(sessionPath, 'utf8');
      const chat = JSON.parse(content);
      
      // Gemini CLI Chat Structure
      let inputTokens = 0;
      let outputTokens = 0;
      let model = 'gemini-2.0-flash';
      
      // Parse turns/messages
      if (chat.turns) {
        for (const turn of chat.turns) {
          if (turn.parts) {
            for (const part of turn.parts) {
              if (part.text) {
                // Rough estimation: ~4 chars per token
                const textTokens = Math.ceil(part.text.length / 4);
                if (turn.role === 'user') {
                  inputTokens += textTokens;
                } else {
                  outputTokens += textTokens;
                }
              }
            }
          }
          // Gemini-specific usage
          if (turn.usageMetadata) {
            inputTokens = turn.usageMetadata.promptTokenCount || inputTokens;
            outputTokens = turn.usageMetadata.candidatesTokenCount || outputTokens;
            model = turn.usageMetadata.modelVersion || model;
          }
        }
      }
      
      return {
        inputTokens,
        outputTokens,
        totalTokens: inputTokens + outputTokens,
        cost: this.estimateCost(inputTokens, outputTokens, model),
        model,
        timestamp: new Date(chat.createTime || Date.now()),
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
    const chatsDir = `${this.configDir}/tmp`;
    
    if (!fs.existsSync(chatsDir)) return sessions;
    
    const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
    
    // Find all chat JSON files
    const chatFiles = glob.sync(`${chatsDir}/**/chats/*.json`, { 
      nocase: true 
    });
    
    for (const chatFile of chatFiles) {
      try {
        const mtime = fs.statSync(chatFile).mtimeMs;
        if (mtime < cutoff) continue;
        
        const usage = await this.parseTokens(chatFile);
        
        sessions.push({
          id: path.basename(chatFile, '.json'),
          path: chatFile,
          startTime: new Date(mtime),
          tokens: usage || { inputTokens: 0, outputTokens: 0, totalTokens: 0, cost: 0, model: 'unknown', timestamp: new Date() },
          commands: this.countMessages(chatFile),
        });
      } catch {
        // Skip invalid chats
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
        vault: sessions.length * 12000, // Gemini hat weniger Startup
        rtk: sessions.reduce((s, x) => s + x.commands * 400, 0) * 0.65,
        output: sessions.reduce((s, x) => s + x.commands * 180, 0) * 0.75,
        total: 0,
      },
    };
  },

  async installHook(): Promise<void> {
    // Gemini CLI unterstützt MCP-Hooks
    const fs = require('fs');
    const home = process.env.HOME;
    
    // MCP Server für Token-Tracking erstellen
    const mcpDir = `${home}/.gemini/mcp-servers`;
    fs.mkdirSync(mcpDir, { recursive: true });
    
    const hookScript = `#!/usr/bin/env node
// Gemini CLI UTS Hook — Output Compression
const { filterOutput } = require('${__dirname}/../core/adapter-interface');

const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const { command, output } = input;

// Filter verbose output
const filtered = filterOutput('gemini', command, output);

console.log(JSON.stringify({ ...input, output: filtered }));
`;
    
    fs.writeFileSync(`${mcpDir}/uts-compress.js`, hookScript);
    
    // Settings aktualisieren
    const settingsPath = `${home}/.gemini/settings.json`;
    let settings: any = {};
    
    if (fs.existsSync(settingsPath)) {
      settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
    }
    
    if (!settings.mcpServers) settings.mcpServers = {};
    settings.mcpServers['uts-compress'] = {
      command: 'node',
      args: [`${mcpDir}/uts-compress.js`],
      enabled: true,
    };
    
    fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2));
  },

  async uninstallHook(): Promise<void> {
    const fs = require('fs');
    const home = process.env.HOME;
    const settingsPath = `${home}/.gemini/settings.json`;
    
    if (fs.existsSync(settingsPath)) {
      const settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
      delete settings.mcpServers?.['uts-compress'];
      fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2));
    }
  },

  isHookActive(): boolean {
    const fs = require('fs');
    const home = process.env.HOME;
    const settingsPath = `${home}/.gemini/settings.json`;
    
    if (!fs.existsSync(settingsPath)) return false;
    
    try {
      const settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
      return settings.mcpServers?.['uts-compress']?.enabled === true;
    } catch {
      return false;
    }
  },

  estimateCost(inputTokens: number, outputTokens: number, model: string): number {
    // Gemini Pricing (Stand 2026)
    const rates: Record<string, { in: number; out: number }> = {
      'gemini-2.0-flash': { in: 0.10, out: 0.40 },
      'gemini-2.5-flash': { in: 0.15, out: 0.60 },
      'gemini-2.5-pro': { in: 1.25, out: 5.00 },
      'gemini-3-flash': { in: 0.07, out: 0.28 },
      'gemini-3-pro': { in: 1.00, out: 4.00 },
    };
    
    const rate = rates[model] || rates['gemini-2.5-flash'];
    return (inputTokens / 1_000_000) * rate.in + 
           (outputTokens / 1_000_000) * rate.out;
  },

  countMessages(chatFile: string): number {
    const fs = require('fs');
    try {
      const chat = JSON.parse(fs.readFileSync(chatFile, 'utf8'));
      return chat.turns?.length || 0;
    } catch {
      return 0;
    }
  },
};

export default ADAPTER;
