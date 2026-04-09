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
