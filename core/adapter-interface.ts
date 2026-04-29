#!/usr/bin/env node
/**
 * Universal Token Saver — Core Adapter Interface
 * Unterstützt: Claude Code, Gemini CLI, Kilo/Code, OpenCode, Codex, Kimi, OpenClaw, Hermes
 */

export interface TokenUsage {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  cost: number;
  model: string;
  timestamp: Date;
}

export interface Session {
  id: string;
  path: string;
  startTime: Date;
  endTime?: Date;
  tokens: TokenUsage;
  commands: number;
}

export interface CLIAdapter {
  /** Eindeutiger Name des CLI-Tools */
  name: string;
  
  /** CLI-spezifisches Config-Verzeichnis */
  configDir: string;
  
  /** Pattern für Session-Dateien (glob) */
  sessionPattern: string;
  
  /** Tool-Logo für Dashboard */
  icon: string;
  
  /** API/API-Key Requirements */
  requiresApiKey: boolean;
  
  /** Liste aller Tracking-Pfade */
  trackingPaths: string[];
  
  /** Parse Token-Usage aus Session */
  parseTokens(sessionPath: string): Promise<TokenUsage | null>;
  
  /** Alle Sessions im Zeitraum */
  getHistory(days: number): Promise<Session[]>;
  
  /** Hole aggregierte Stats */
  getStats(days: number): Promise<AdapterStats>;
  
  /** Installiere PreToolUse Hook / Proxy */
  installHook(): Promise<void>;
  
  /** Entferne Hook */
  uninstallHook(): Promise<void>;
  
  /** Ist Hook aktiv? */
  isHookActive(): boolean;
  
  /** Vault-Verzeichnis für Skills */
  vaultDir: string;
  
  /** Settings-Datei */
  settingsFile: string;
}

export interface AdapterStats {
  adapter: string;
  sessions: number;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  cost: number;
  commands: number;
  savings: {
    vault: number;
    rtk: number;
    output: number;
    total: number;
  };
}

export interface SavingsReport {
  totalSaved: number;
  breakdown: {
    vaultTokens: number;
    rtkTokens: number;
    outputTokens: number;
  };
  percentageSaved: number;
  recommendations: string[];
}

/** Noise-Patterns pro CLI-Tool */
export const NOISE_PATTERNS: Record<string, RegExp[]> = {
  git: [
    /^Merging|^Auto-merging|^CONFLICT/,
    /^Fast-forward|^ delete mode/,
    /^\s+\d+\s+file/,
    /^warning: could not unlink/,
  ],
  npm: [
    /^added \d+ packages? in \d+s/,
    /^found \d+ vulnerabilities?/,
    /^audited \d+ packages?/,
    /^npm WARN/,
    /^removed \d+ packages?/,
  ],
  docker: [
    /^Unable to find image/,
    /^Pulling from layer/,
    /^[a-f0-9]{12}: Pulling/,
    /^Digest: sha256:/,
    /^Status: Downloaded newer/,
  ],
  pytest: [
    /^=+ \d+ passed/,
    /^=+ \d+ failed/,
    /^platform \w+ --/,
    /^cachedir: \./,
    /^test session starts/,
    /^collecting \d+ items/,
  ],
  cargo: [
    /^    Updating|^   Compiling|^    Finished/,
    /^warning: unused/,
    /^     Running.*\.+ \d+ tests?/,
    /^test result: ok\./,
  ],
  kubectl: [
    /^NAME\s+AGE|^NAMESPACE/,
    /^deployment\.apps\/.* created/,
    /^service\/.* exposed/,
    /^configmap\/.* created/,
  ],
  terraform: [
    /^Apply complete!/,
    /^Resources: \d+ added, \d+ changed, \d+ destroyed/,
    /^Outputs:/,
  ],
  pip: [
    /^Requirement already satisfied:/,
    /^Installing collected packages/,
    /^Successfully installed/,
  ],
};

/** Output-Komprimierung pro CLI */
export const OUTPUT_COMPRESSORS: Record<string, (output: string) => string> = {
  git: (o) => o
    .replace(/^diff --git.*$/gm, '')
    .replace(/^index [a-f0-9]+\.\.[a-f0-9]+/gm, '')
    .replace(/^--- a\//gm, '---')
    .replace(/^\+\+\+ b\//gm, '+++')
    .split('\n').filter(l => !/^\s*$/.test(l) || l.includes('+') || l.includes('-')).join('\n'),
  
  pytest: (o) => o
    .split('\n')
    .filter(l => l.includes('FAILED') || l.includes('ERROR') || l.includes('PASSED') || l.includes('::'))
    .join('\n'),
  
  npm: (o) => o
    .split('\n')
    .filter(l => l.includes('ERR!') || l.includes('error') || l.includes('warn'))
    .join('\n'),
};

/** Auto-Detection: Welcher CLI ist aktiv? */
export function detectActiveCLI(): string | null {
  const fs = require('fs');
  const home = process.env.HOME || process.env.USERPROFILE || '';
  
  const detectors = [
    { dir: `${home}/.claude`, name: 'claude' },
    { dir: `${home}/.gemini`, name: 'gemini' },
    { dir: `${home}/.local/share/opencode`, name: 'opencode' },
    { dir: `${home}/.local/share/kilo`, name: 'kilo' },
    { dir: `${home}/.codex`, name: 'codex' },
    { dir: `${home}/.kimi`, name: 'kimi' },
    { dir: `${home}/.openclaw`, name: 'openclaw' },
    { dir: `${home}/.hermes`, name: 'hermes' },
  ];
  
  for (const d of detectors) {
    if (fs.existsSync(d.dir)) return d.name;
  }
  
  return null;
}

/** Universeller Output-Filter */
export function filterOutput(cli: string, command: string, output: string): string {
  const cmd = command.split(' ')[0];
  
  // Finde CLI-spezifische Patterns
  const patterns = NOISE_PATTERNS[cmd] || [];
  let filtered = output
    .split('\n')
    .filter(line => !patterns.some(p => p.test(line)))
    .join('\n');
  
  // CLI-spezifische Komprimierung
  if (OUTPUT_COMPRESSORS[cmd]) {
    filtered = OUTPUT_COMPRESSORS[cmd](filtered);
  }
  
  return filtered.trim();
}

/**
 * Per-model profile: caveman compat + recommended cache strategy.
 * Source: bench/results/eval_*.json (8-model OpenRouter eval, 2026-04).
 * Caveman-incompatible models (e.g. Kimi reasoning) backfire — DO NOT enable.
 */
export interface ModelProfile {
  caveman_compatible: boolean;
  caveman_default: 'lite' | 'full' | 'ultra' | 'wenyan-full';
  cache_ttl: '5m' | '1h';
  context_window: number;
  notes?: string;
}

export const MODEL_PROFILES: Record<string, ModelProfile> = {
  'claude-opus-4-7':      { caveman_compatible: true,  caveman_default: 'ultra', cache_ttl: '1h', context_window: 1_000_000, notes: '1M ctx, ultra default for cost' },
  'claude-sonnet-4-6':    { caveman_compatible: true,  caveman_default: 'full',  cache_ttl: '1h', context_window: 200_000, notes: 'follows system msg rigorously, -34% out' },
  'claude-haiku-4-5':     { caveman_compatible: false, caveman_default: 'lite',  cache_ttl: '5m', context_window: 200_000, notes: 'tier C: only -5% save, skip caveman' },
  'gemini-2.5-flash':     { caveman_compatible: true,  caveman_default: 'full',  cache_ttl: '5m', context_window: 1_000_000, notes: 'tier S: -80% out' },
  'gemini-2.5-pro':       { caveman_compatible: true,  caveman_default: 'full',  cache_ttl: '5m', context_window: 2_000_000 },
  'minimax-2.7':          { caveman_compatible: true,  caveman_default: 'full',  cache_ttl: '5m', context_window: 1_000_000, notes: 'tier S: -63% out' },
  'deepseek-v4-flash':    { caveman_compatible: true,  caveman_default: 'wenyan-full', cache_ttl: '5m', context_window: 128_000, notes: 'Chinese tokenizer favors wenyan; cheapest at $0.000051/call' },
  'deepseek-v4-pro':      { caveman_compatible: true,  caveman_default: 'wenyan-full', cache_ttl: '1h', context_window: 128_000 },
  'grok-4-fast':          { caveman_compatible: true,  caveman_default: 'lite',  cache_ttl: '5m', context_window: 256_000, notes: 'tier B: only -17%' },
  'glm-4.7':              { caveman_compatible: false, caveman_default: 'lite',  cache_ttl: '5m', context_window: 200_000, notes: 'tier B: -7% only' },
  'kimi-2.6':             { caveman_compatible: false, caveman_default: 'lite',  cache_ttl: '5m', context_window: 200_000, notes: 'BACKFIRE: caveman INCREASES output +22% — disable' },
};

export function profileFor(model: string): ModelProfile {
  return MODEL_PROFILES[model] || { caveman_compatible: false, caveman_default: 'lite', cache_ttl: '5m', context_window: 200_000 };
}

/**
 * Build Anthropic prompt-cache header set.
 * Use 1h TTL for stable system blocks (CLAUDE.md, tool defs).
 * Per Anthropic 2026-04 docs: 1h blocks MUST precede 5m blocks in request.
 * Beta header: extended-cache-ttl-2025-04-11 — write 2×, read 0.1×.
 */
export function cacheHeaders(ttl: '5m' | '1h' = '5m'): { anthropic_beta?: string; cache_control: { type: 'ephemeral'; ttl?: string } } {
  if (ttl === '1h') {
    return {
      anthropic_beta: 'extended-cache-ttl-2025-04-11',
      cache_control: { type: 'ephemeral', ttl: '1h' },
    };
  }
  return { cache_control: { type: 'ephemeral' } };
}

