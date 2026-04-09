/**
 * Universal Token Saver — Adapter Registry
 * Alle unterstützten CLI-Tools
 */

export { default as ClaudeAdapter } from './claude-code';
export { default as GeminiAdapter } from './gemini-cli';
export { default as KiloAdapter } from './kilo-code';
export { default as CodexAdapter } from './codex';
export { default as KimiAdapter } from './kimi-cli';

// Registry für dynamisches Laden
export const ADAPTER_REGISTRY = {
  claude: () => import('./claude-code'),
  gemini: () => import('./gemini-cli'),
  kilo: () => import('./kilo-code'),
  opencode: () => import('./kilo-code'),
  codex: () => import('./codex'),
  kimi: () => import('./kimi-cli'),
  openclaw: () => import('./openclaw'), // TODO
};

// Helper: Lade Adapter dynamisch
export async function loadAdapter(name: string) {
  const loader = ADAPTER_REGISTRY[name.toLowerCase()];
  if (!loader) {
    throw new Error(`Unknown adapter: ${name}. Supported: ${Object.keys(ADAPTER_REGISTRY).join(', ')}`);
  }
  const module = await loader();
  return module.default;
}

// Helper: Lade alle verfügbaren Adapter
export async function loadAllAdapters() {
  const adapters = [];
  
  for (const [name, loader] of Object.entries(ADAPTER_REGISTRY)) {
    try {
      const module = await loader();
      adapters.push(module.default);
    } catch {
      // Adapter nicht verfügbar
    }
  }
  
  return adapters;
}
