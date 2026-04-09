#!/usr/bin/env node
/**
 * Kimi Code CLI Adapter für Universal Token Saver
 * Tracking: Agent Tracing Visualizer (kimi-vis)
 */

import { CLIAdapter, TokenUsage, Session, AdapterStats } from '../core/adapter-interface';

const ADAPTER: CLIAdapter = {
  name: 'Kimi Code',
  icon: '🌙',
  configDir: `${process.env.HOME}/.kimi`,
  sessionPattern: '**/*.json',
  requiresApiKey: true,
  trackingPaths: [
    '~/.kimi/',
    '~/.config/kimi/',
  ],
  vaultDir: `${process.env.HOME}/.uts/kimi`,
  settingsFile: `${process.env.HOME}/.kimi/config.json`,

  async parseTokens(sessionPath: string): Promise<TokenUsage | null> {
    const fs = require('fs');
    
    try {
      const content = fs.readFileSync(sessionPath, 'utf8');
      const trace = JSON.parse(content);
      
      // Kimi Trace Structure
      let inputTokens = 0;
      let outputTokens = 0;
      let model = 'kimi-k2.5';
      
      // Wire events contain usage info
      if (trace.events) {
        for (const event of trace.events) {
          if (event.usage) {
            inputTokens += event.usage.prompt_tokens || 0;
            outputTokens += event.usage.completion_tokens || 0;
          }
          if (event.model) {
            model = event.model;
          }
        }
      }
      
      // Alternative: estimate from messages
      if (inputTokens === 0 && trace.messages) {
        inputTokens = this.estimateTokens(trace.messages);
      }
      
      return {
        inputTokens,
        outputTokens,
        totalTokens: inputTokens + outputTokens,
        cost: this.estimateCost(inputTokens, outputTokens, model),
        model,
        timestamp: new Date(trace.createTime || Date.now()),
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
    
    // Kimi CLI configs in verschiedenen Locations
    const possibleDirs = [
      `${process.env.HOME}/.kimi`,
      `${process.env.HOME}/.config/kimi`,
      `${process.env.HOME}/.local/share/kimi`,
    ];
    
    const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
    
    for (const dir of possibleDirs) {
      if (!fs.existsSync(dir)) continue;
      
      // Suche nach Session/Trace Files
      const traceFiles = glob.sync(`${dir}/**/traces/*.json`, { nocase: true })
        .concat(glob.sync(`${dir}/**/sessions/*.json`, { nocase: true }));
      
      for (const traceFile of traceFiles) {
        try {
          const mtime = fs.statSync(traceFile).mtimeMs;
          if (mtime < cutoff) continue;
          
          const usage = await this.parseTokens(traceFile);
          
          sessions.push({
            id: path.basename(traceFile, '.json'),
            path: traceFile,
            startTime: new Date(mtime),
            tokens: usage || { inputTokens: 0, outputTokens: 0, totalTokens: 0, cost: 0, model: 'kimi-k2.5', timestamp: new Date() },
            commands: this.countTurns(traceFile),
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
        vault: sessions.length * 14000,
        rtk: sessions.reduce((s, x) => s + x.commands * 420, 0) * 0.68,
        output: sessions.reduce((s, x) => s + x.commands * 190, 0) * 0.78,
        total: 0,
      },
    };
  },

  async installHook(): Promise<void> {
    const fs = require('fs');
    const home = process.env.HOME;
    
    // Kimi CLI Plugin-Integration
    const pluginDir = `${home}/.kimi/plugins`;
    fs.mkdirSync(pluginDir, { recursive: true });
    
    const pluginManifest = {
      name: 'uts-token-saver',
      version: '1.0.0',
      description: 'Universal Token Saver for Kimi Code',
      hooks: {
        pre_tool: `${pluginDir}/pre-tool.js`,
        post_tool: `${pluginDir}/post-tool.js`,
      },
      enabled: true,
    };
    
    fs.writeFileSync(`${pluginDir}/manifest.json`, JSON.stringify(pluginManifest, null, 2));
    
    // Pre-tool hook für Output-Filtering
    const preHook = `
// UTS Pre-Tool Hook for Kimi Code
const { filterOutput } = require('${__dirname}/../../core/adapter-interface');

module.exports = async function preToolHook(context) {
  const { command, output } = context;
  
  if (output) {
    context.filteredOutput = filterOutput('kimi', command, output);
  }
  
  return context;
};
`;
    
    fs.writeFileSync(`${pluginDir}/pre-tool.js`, preHook);
  },

  async uninstallHook(): Promise<void> {
    const fs = require('fs');
    const home = process.env.HOME;
    
    const pluginDir = `${home}/.kimi/plugins/uts-token-saver`;
    if (fs.existsSync(pluginDir)) {
      fs.rmSync(pluginDir, { recursive: true });
    }
  },

  isHookActive(): boolean {
    const fs = require('fs');
    const home = process.env.HOME;
    const manifest = `${home}/.kimi/plugins/uts-token-saver/manifest.json`;
    
    if (!fs.existsSync(manifest)) return false;
    
    try {
      const plugin = JSON.parse(fs.readFileSync(manifest, 'utf8'));
      return plugin.enabled === true;
    } catch {
      return false;
    }
  },

  estimateTokens(messages: any[]): number {
    return messages.reduce((sum, msg) => {
      const content = typeof msg.content === 'string'
        ? msg.content
        : JSON.stringify(msg.content || '');
      // Kimi verwendet BPE Tokenizer, ca. 3.5 chars per token
      return sum + Math.ceil(content.length / 3.5);
    }, 0);
  },

  estimateCost(inputTokens: number, outputTokens: number, model: string): number {
    // Kimi API Pricing (kimi-k2.5)
    const rateIn = 0.5; // $0.5 per M input
    const rateOut = 1.5; // $1.5 per M output
    
    return (inputTokens / 1_000_000) * rateIn + (outputTokens / 1_000_000) * rateOut;
  },

  countTurns(traceFile: string): number {
    const fs = require('fs');
    try {
      const trace = JSON.parse(fs.readFileSync(traceFile, 'utf8'));
      return trace.events?.length || trace.turns?.length || 0;
    } catch {
      return 0;
    }
  },
};

export default ADAPTER;
