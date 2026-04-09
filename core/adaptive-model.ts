#!/usr/bin/env node
/**
 * Universal Agent Token Saver — Adaptive Model Selection
 * 
 * Wählt das optimale Modell basierend auf:
 * 1. Verfügbarem API-Key/Provider
 * 2. Task-Komplexität  
 * 3. Geschwindigkeitsanforderungen
 * 
 * Bei schnellen APIs (MiniMax M2.7) → keine Token-Sparmaßnahmen
 * Bei teuren APIs (Claude/Sonnet) → volle Token-Optimierung
 */

export interface ModelConfig {
  name: string;
  provider: string;
  speed: 'fastest' | 'fast' | 'balanced' | 'slow';
  cost: number; // per 1M tokens (input)
  contextWindow: number;
  bestFor: string[];
}

export interface TaskProfile {
  complexity: 'simple' | 'medium' | 'complex';
  speed: 'fastest' | 'fast' | 'balanced' | 'slow';
  contextNeeded: number;
  codeQuality: 'draft' | 'production';
}

// Bekannte Modelle
export const MODEL_REGISTRY: Record<string, ModelConfig> = {
  // MiniMax Serie (schnellste)
  'minimax-m2.7': {
    name: 'MiniMax M2.7',
    provider: 'MiniMax',
    speed: 'fastest',
    cost: 0.05,
    contextWindow: 1_000_000,
    bestFor: ['code-completion', 'quick-fixes', 'simple-tasks'],
  },
  'minimax-m2': {
    name: 'MiniMax M2',
    provider: 'MiniMax',
    speed: 'fast',
    cost: 0.07,
    contextWindow: 1_000_000,
    bestFor: ['code-generation', 'refactoring'],
  },
  
  // Google Gemini Serie
  'gemini-3-flash': {
    name: 'Gemini 3.0 Flash',
    provider: 'Google',
    speed: 'fastest',
    cost: 0.07,
    contextWindow: 1_000_000,
    bestFor: ['quick-tasks', 'high-volume'],
  },
  'gemini-3-pro': {
    name: 'Gemini 3.0 Pro',
    provider: 'Google',
    speed: 'balanced',
    cost: 1.00,
    contextWindow: 1_000_000,
    bestFor: ['complex-reasoning', 'architecture'],
  },
  'gemini-2.5-flash': {
    name: 'Gemini 2.5 Flash',
    provider: 'Google',
    speed: 'fast',
    cost: 0.15,
    contextWindow: 1_000_000,
    bestFor: ['general-tasks'],
  },
  'gemini-2.5-pro': {
    name: 'Gemini 2.5 Pro',
    provider: 'Google',
    speed: 'balanced',
    cost: 1.25,
    contextWindow: 1_000_000,
    bestFor: ['complex-reasoning'],
  },
  
  // Anthropic Claude Serie
  'claude-3.5-haiku': {
    name: 'Claude 3.5 Haiku',
    provider: 'Anthropic',
    speed: 'fast',
    cost: 0.25,
    contextWindow: 200_000,
    bestFor: ['quick-tasks', 'exploration'],
  },
  'claude-3.5-sonnet': {
    name: 'Claude 3.5 Sonnet',
    provider: 'Anthropic',
    speed: 'balanced',
    cost: 3.00,
    contextWindow: 200_000,
    bestFor: ['code-generation', 'planning'],
  },
  'claude-3.5-opus': {
    name: 'Claude 3.5 Opus',
    provider: 'Anthropic',
    speed: 'slow',
    cost: 15.00,
    contextWindow: 200_000,
    bestFor: ['architecture', 'complex-analysis'],
  },
  'claude-3.7-sonnet': {
    name: 'Claude 3.7 Sonnet',
    provider: 'Anthropic',
    speed: 'balanced',
    cost: 3.00,
    contextWindow: 200_000,
    bestFor: ['extended-thinking', 'complex-tasks'],
  },
  
  // OpenAI Serie
  'gpt-4o': {
    name: 'GPT-4o',
    provider: 'OpenAI',
    speed: 'fast',
    cost: 2.50,
    contextWindow: 128_000,
    bestFor: ['general-tasks'],
  },
  'gpt-4.5': {
    name: 'GPT-4.5',
    provider: 'OpenAI',
    speed: 'balanced',
    cost: 75.00,
    contextWindow: 128_000,
    bestFor: ['complex-reasoning'],
  },
  
  // Kimi Serie
  'kimi-k2.5': {
    name: 'Kimi K2.5',
    provider: 'Moonshot',
    speed: 'fast',
    cost: 0.50,
    contextWindow: 256_000,
    bestFor: ['code-generation', 'refactoring'],
  },
  
  // DeepSeek Serie
  'deepseek-coder': {
    name: 'DeepSeek Coder',
    provider: 'DeepSeek',
    speed: 'fast',
    cost: 0.14,
    contextWindow: 128_000,
    bestFor: ['code-completion', 'quick-fixes'],
  },
  
  // OpenRouter (aggregiert)
  'openrouter-fast': {
    name: 'OpenRouter Fastest',
    provider: 'OpenRouter',
    speed: 'fastest',
    cost: 0.10,
    contextWindow: 200_000,
    bestFor: ['high-volume-tasks'],
  },
};

// Schnelle Provider (keine Token-Sparmaßnahmen nötig)
const FAST_PROVIDERS = ['MiniMax', 'Google', 'DeepSeek'];

// Teure Provider (volle Token-Optimierung)
const EXPENSIVE_PROVIDERS = ['Anthropic', 'OpenAI'];

/**
 * Prüfe ob Token-Sparmaßnahmen aktiviert werden sollten
 */
export function shouldEnableTokenSavings(modelKey: string): boolean {
  const model = MODEL_REGISTRY[modelKey];
  
  if (!model) return true; // Unbekannte Modelle: konservativ
  
  // Schnelle Provider brauchen keine Sparmaßnahmen
  if (FAST_PROVIDERS.includes(model.provider)) {
    return false;
  }
  
  // Teure Provider: volle Optimierung
  if (EXPENSIVE_PROVIDERS.includes(model.provider)) {
    return true;
  }
  
  // Default: leicht optimiert
  return true;
}

/**
 * Wähle optimales Modell basierend auf Task
 */
export function selectModel(task: TaskProfile, availableModels: string[]): string {
  const candidates: { model: string; score: number; config: ModelConfig }[] = [];
  
  for (const modelKey of availableModels) {
    const config = MODEL_REGISTRY[modelKey];
    if (!config) continue;
    
    let score = 100;
    
    // Speed Match
    if (task.speed === 'fastest' && config.speed !== 'fastest') score -= 30;
    if (task.speed === 'fast' && config.speed === 'slow') score -= 20;
    
    // Context Check
    if (task.contextNeeded > config.contextWindow) score -= 50;
    
    // Complexity Match
    if (task.complexity === 'complex' && config.speed === 'fastest') score -= 40;
    if (task.complexity === 'simple' && config.speed === 'slow') score -= 30;
    
    // Code Quality
    if (task.codeQuality === 'production' && config.speed === 'fastest') score -= 20;
    
    candidates.push({ model: modelKey, score, config });
  }
  
  // Sortiere nach Score absteigend
  candidates.sort((a, b) => b.score - a.score);
  
  return candidates[0]?.model || availableModels[0];
}

/**
 * Hole optimale Modelle für Provider
 */
export function getModelsByProvider(provider: string): ModelConfig[] {
  return Object.entries(MODEL_REGISTRY)
    .filter(([_, config]) => config.provider === provider)
    .map(([key, config]) => config);
}

/**
 * Erstelle Model-Switching Regeln
 */
export interface ModelRule {
  trigger: string;
  condition: (task: TaskProfile) => boolean;
  model: string;
  reason: string;
}

export const MODEL_RULES: ModelRule[] = [
  {
    trigger: 'quick-exploration',
    condition: (t) => t.complexity === 'simple' && t.speed !== 'slow',
    model: 'minimax-m2.7',
    reason: 'Schnellste Option für einfache Tasks',
  },
  {
    trigger: 'code-exploration',
    condition: (t) => t.codeQuality === 'draft',
    model: 'gemini-3-flash',
    reason: 'Schnell + Günstig für Exploration',
  },
  {
    trigger: 'production-code',
    condition: (t) => t.codeQuality === 'production',
    model: 'claude-3.5-sonnet',
    reason: 'Beste Codequalität für Production',
  },
  {
    trigger: 'architecture',
    condition: (t) => t.complexity === 'complex',
    model: 'claude-3.5-opus',
    reason: 'Maximale Reasoning-Power',
  },
  {
    trigger: 'high-volume',
    condition: (t) => t.speed === 'fastest',
    model: 'minimax-m2.7',
    reason: 'Höchster Durchsatz',
  },
];

/**
 * Erstelle Adapter-Konfiguration für Provider
 */
export interface AdapterStrategy {
  provider: string;
  tokenSavings: 'full' | 'minimal' | 'none';
  cacheStrategy: 'aggressive' | 'normal' | 'disabled';
  batchStrategy: 'always' | 'smart' | 'never';
  recommendedModel: string;
}

export function getAdapterStrategy(provider: string): AdapterStrategy {
  switch (provider) {
    case 'MiniMax':
      return {
        provider: 'MiniMax',
        tokenSavings: 'none', // Schneller Provider
        cacheStrategy: 'disabled', // Nicht nötig
        batchStrategy: 'never', // Geschwindigkeit vor Effizienz
        recommendedModel: 'minimax-m2.7',
      };
    
    case 'Google':
      return {
        provider: 'Google',
        tokenSavings: 'minimal',
        cacheStrategy: 'normal',
        batchStrategy: 'smart',
        recommendedModel: 'gemini-3-flash',
      };
    
    case 'Anthropic':
      return {
        provider: 'Anthropic',
        tokenSavings: 'full', // Teuerste Option
        cacheStrategy: 'aggressive',
        batchStrategy: 'always',
        recommendedModel: 'claude-3.5-sonnet',
      };
    
    case 'OpenAI':
      return {
        provider: 'OpenAI',
        tokenSavings: 'full',
        cacheStrategy: 'aggressive',
        batchStrategy: 'always',
        recommendedModel: 'gpt-4o',
      };
    
    default:
      return {
        provider,
        tokenSavings: 'minimal',
        cacheStrategy: 'normal',
        batchStrategy: 'smart',
        recommendedModel: 'minimax-m2.7',
      };
  }
}

// CLI Interface
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args[0] === '--check') {
    const model = args[1] || 'minimax-m2.7';
    const savings = shouldEnableTokenSavings(model);
    const config = MODEL_REGISTRY[model];
    
    console.log(JSON.stringify({
      model,
      provider: config?.provider,
      speed: config?.speed,
      enableTokenSavings: savings,
      reason: savings 
        ? 'Provider is expensive - token savings recommended'
        : 'Provider is fast - no token savings needed',
    }, null, 2));
  }
  
  if (args[0] === '--select') {
    const task: TaskProfile = {
      complexity: (args[1] as any) || 'medium',
      speed: (args[2] as any) || 'balanced',
      contextNeeded: parseInt(args[3]) || 50000,
      codeQuality: (args[4] as any) || 'production',
    };
    
    const available = Object.keys(MODEL_REGISTRY);
    const selected = selectModel(task, available);
    const config = MODEL_REGISTRY[selected];
    const strategy = getAdapterStrategy(config?.provider || 'unknown');
    
    console.log(JSON.stringify({
      task,
      selectedModel: selected,
      provider: config?.provider,
      strategy,
    }, null, 2));
  }
  
  if (args[0] === '--strategy') {
    const provider = args[1] || 'Anthropic';
    const strategy = getAdapterStrategy(provider);
    console.log(JSON.stringify(strategy, null, 2));
  }
  
  if (args[0] === '--list') {
    console.log('Available Models:');
    console.log('');
    
    const byProvider: Record<string, ModelConfig[]> = {};
    for (const [key, config] of Object.entries(MODEL_REGISTRY)) {
      if (!byProvider[config.provider]) byProvider[config.provider] = [];
      byProvider[config.provider].push(config);
    }
    
    for (const [provider, models] of Object.entries(byProvider)) {
      console.log(`\n${provider}:`);
      for (const model of models) {
        const savings = shouldEnableTokenSavings(Object.entries(MODEL_REGISTRY).find(([_, c]) => c === model)?.[0] || '') 
          ? '💰' : '⚡';
        console.log(`  ${savings} ${model.name} (${model.speed})`);
      }
    }
  }
}
