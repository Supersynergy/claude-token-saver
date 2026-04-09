#!/usr/bin/env node
/**
 * UTS Universal CLI Dashboard
 * Multi-Agent Token Tracking & Savings
 */

import { detectActiveCLI, AdapterStats } from '../core/adapter-interface';

// Adapter Imports
import ClaudeAdapter from '../adapters/claude-code';
import GeminiAdapter from '../adapters/gemini-cli';
import KiloAdapter from '../adapters/kilo-code';
import CodexAdapter from '../adapters/codex';
import KimiAdapter from '../adapters/kimi-cli';

const ADAPTERS = [
  ClaudeAdapter,
  GeminiAdapter,
  KiloAdapter,
  CodexAdapter,
  KimiAdapter,
];

interface CLIOptions {
  adapter?: string;
  days?: number;
  json?: boolean;
  compact?: boolean;
}

/**
 * Formatiere große Zahlen lesbar
 */
function formatNumber(n: number): string {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

/**
 * Formatiere Dollar-Betrag
 */
function formatCost(cost: number): string {
  if (cost < 0.01) return '$0.00';
  return `$${cost.toFixed(2)}`;
}

/**
 * Formatiere Prozentbalken
 */
function formatBar(value: number, max: number, width: number = 20): string {
  const pct = Math.min(value / max, 1);
  const filled = Math.round(pct * width);
  return '█'.repeat(filled) + '░'.repeat(width - filled);
}

/**
 * Hole Stats für alle oder spezifische Adapter
 */
async function getAllStats(days: number): Promise<AdapterStats[]> {
  const results: AdapterStats[] = [];
  
  for (const adapter of ADAPTERS) {
    try {
      const stats = await adapter.getStats(days);
      if (stats.sessions > 0) {
        // Berechne total savings
        stats.savings.total = stats.savings.vault + stats.savings.rtk + stats.savings.output;
        results.push(stats);
      }
    } catch {
      // Adapter nicht installiert, skip
    }
  }
  
  return results;
}

/**
 * Zeige ASCII Dashboard
 */
function renderDashboard(stats: AdapterStats[], days: number, compact: boolean = false) {
  // Totals berechnen
  const totals = stats.reduce((acc, s) => ({
    sessions: acc.sessions + s.sessions,
    inputTokens: acc.inputTokens + s.inputTokens,
    outputTokens: acc.outputTokens + s.outputTokens,
    totalTokens: acc.totalTokens + s.totalTokens,
    cost: acc.cost + s.cost,
    commands: acc.commands + s.commands,
    savings: {
      vault: acc.savings.vault + s.savings.vault,
      rtk: acc.savings.rtk + s.savings.rtk,
      output: acc.savings.output + s.savings.output,
      total: acc.savings.total + s.savings.total,
    },
  }), {
    sessions: 0,
    inputTokens: 0,
    outputTokens: 0,
    totalTokens: 0,
    cost: 0,
    commands: 0,
    savings: { vault: 0, rtk: 0, output: 0, total: 0 },
  });

  const maxTokens = Math.max(...stats.map(s => s.totalTokens), 1);
  const maxSavings = Math.max(...stats.map(s => s.savings.total), 1);

  console.log('\n');
  console.log('╔══════════════════════════════════════════════════════════════════════╗');
  console.log('║     ⚡ Universal Token Saver — Multi-Agent Dashboard                ║');
  console.log('╠══════════════════════════════════════════════════════════════════════╣');
  console.log(`║  Zeitraum: ${days} Tage${' '.repeat(47 - days.toString().length)}║`);
  console.log('╠══════════════════════════════════════════════════════════════════════╣');
  console.log('║  Agent           Sessions  Input     Output    Cost   Savings        ║');
  console.log('╠══════════════════════════════════════════════════════════════════════╣');

  for (const s of stats) {
    const adapter = ADAPTERS.find(a => a.name === s.adapter);
    const icon = adapter?.icon || '•';
    const bar = formatBar(s.totalTokens, maxTokens, 8);
    
    console.log(
      `║  ${icon} ${s.adapter.padEnd(13)} ${String(s.sessions).padStart(3)}     ` +
      `${formatNumber(s.inputTokens).padStart(7)}  ${formatNumber(s.outputTokens).padStart(7)}  ` +
      `${formatCost(s.cost).padStart(6)}  ${formatBar(s.savings.total, maxSavings, 10)} ║`
    );
  }

  console.log('╠══════════════════════════════════════════════════════════════════════╣');
  console.log(
    `║  ${'TOTAL'.padEnd(14)} ${String(totals.sessions).padStart(3)}     ` +
    `${formatNumber(totals.inputTokens).padStart(7)}  ${formatNumber(totals.outputTokens).padStart(7)}  ` +
    `${formatCost(totals.cost).padStart(6)}                     ║`
  );
  console.log('╠══════════════════════════════════════════════════════════════════════╣');
  console.log('║  💰 SAVINGS BREAKDOWN                                                ║');
  console.log('╠══════════════════════════════════════════════════════════════════════╣');
  
  const savingsBar = formatBar(totals.savings.total, totals.totalTokens, 40);
  const savingsPct = totals.totalTokens > 0 
    ? ((totals.savings.total / (totals.totalTokens + totals.savings.total)) * 100).toFixed(1)
    : '0.0';
  
  console.log(`║  Vault Pattern:     ${formatNumber(totals.savings.vault).padStart(8)} tokens                            ║`);
  console.log(`║  RTK Compression:   ${formatNumber(totals.savings.rtk).padStart(8)} tokens                            ║`);
  console.log(`║  Output Filtering:  ${formatNumber(totals.savings.output).padStart(8)} tokens                            ║`);
  console.log('║                                                                    ║');
  console.log(`║  ${savingsBar} ${savingsPct.padStart(5)}% ║`);
  console.log('║                                                                    ║');
  console.log(`║  Total Saved: ${formatCost(totals.cost * (totals.savings.total / (totals.totalTokens || 1) * 0.5)).padStart(8)}/mo ║`);
  console.log('╚══════════════════════════════════════════════════════════════════════╝');

  if (!compact) {
    console.log('\n  Quick Actions:');
    console.log('    uts agents      — List all detected CLI agents');
    console.log('    uts install    — Install UTS for active CLI');
    console.log('    uts stats      — Detailed per-agent stats');
    console.log('    uts savings    — Show savings recommendations');
  }
}

/**
 * Zeige Agent-Status
 */
async function showAgents() {
  const active = detectActiveCLI();
  
  console.log('\n╔══════════════════════════════════════════════════════╗');
  console.log('║     ⚡ Detected CLI Agents                          ║');
  console.log('╠══════════════════════════════════════════════════════╣');
  
  for (const adapter of ADAPTERS) {
    const isActive = adapter.name.toLowerCase().includes(active || '');
    const isInstalled = adapter.isHookActive();
    
    const status = isInstalled ? '✓' : isActive ? '●' : '○';
    const hookStatus = isInstalled ? ' [hook active]' : '';
    
    console.log(`║  ${status} ${adapter.icon} ${adapter.name.padEnd(16)}${hookStatus.padEnd(14)}║`);
  }
  
  console.log('╠══════════════════════════════════════════════════════╣');
  console.log(`║  Active CLI: ${(active || 'unknown').toUpperCase().padEnd(38)}║`);
  console.log('╚══════════════════════════════════════════════════════╝');
}

/**
 * Zeige detaillierte Stats
 */
async function showDetailedStats(adapterName?: string) {
  const days = 30;
  const allStats = await getAllStats(days);
  
  if (adapterName) {
    const stats = allStats.filter(s => 
      s.adapter.toLowerCase().includes(adapterName.toLowerCase())
    );
    
    if (stats.length === 0) {
      console.log(`No stats found for: ${adapterName}`);
      return;
    }
    
    for (const s of stats) {
      console.log(`\n=== ${s.adapter} Stats (${days} days) ===`);
      console.log(`  Sessions:     ${s.sessions}`);
      console.log(`  Input Tokens: ${formatNumber(s.inputTokens)}`);
      console.log(`  Output Tokens:${formatNumber(s.outputTokens)}`);
      console.log(`  Total Tokens: ${formatNumber(s.totalTokens)}`);
      console.log(`  Cost:         ${formatCost(s.cost)}`);
      console.log(`  Commands:     ${s.commands}`);
      console.log(`\n  Savings:`);
      console.log(`    Vault:       ${formatNumber(s.savings.vault)} tokens`);
      console.log(`    RTK:        ${formatNumber(s.savings.rtk)} tokens`);
      console.log(`    Output:     ${formatNumber(s.savings.output)} tokens`);
      console.log(`    Total:      ${formatNumber(s.savings.total)} tokens`);
    }
  } else {
    // Zeige alle
    for (const s of allStats) {
      console.log(`\n${s.adapter}:`);
      console.log(`  Sessions: ${s.sessions} | Tokens: ${formatNumber(s.totalTokens)} | Cost: ${formatCost(s.cost)}`);
    }
  }
}

/**
 * Zeige Savings-Empfehlungen
 */
async function showSavings() {
  console.log('\n╔══════════════════════════════════════════════════════╗');
  console.log('║     💡 Token Saving Recommendations                  ║');
  console.log('╠══════════════════════════════════════════════════════╣');
  
  const recommendations = [
    { icon: '📦', title: 'Enable Vault Pattern', desc: 'Cold-storage for unused skills' },
    { icon: '⚡', title: 'Install RTK Hook', desc: '60-90% CLI output compression' },
    { icon: '🔇', title: 'Enable Output Filter', desc: 'Remove verbose logs/noise' },
    { icon: '📊', title: 'Use Multi-Agent Dashboard', desc: 'Track savings across all CLIs' },
    { icon: '🧠', title: 'Batch Commands', desc: 'Use ctx_batch_execute for 2+ commands' },
  ];
  
  for (const rec of recommendations) {
    console.log(`║  ${rec.icon} ${rec.title.padEnd(20)} ${rec.desc.padEnd(24)}║`);
  }
  
  console.log('╚══════════════════════════════════════════════════════╝');
}

// CLI Parser
const args = process.argv.slice(2);
const options: CLIOptions = {
  days: 30,
  compact: args.includes('--compact'),
  json: args.includes('--json'),
};

const command = args[0] || 'dashboard';

async function main() {
  switch (command) {
    case 'agents':
      await showAgents();
      break;
      
    case 'stats':
      await showDetailedStats(args[1]);
      break;
      
    case 'savings':
    case 'recommendations':
      await showSavings();
      break;
      
    case 'install':
      const target = args[1] || detectActiveCLI();
      if (!target) {
        console.error('No CLI detected. Specify: uts install <claude|gemini|kilo|codex|kimi>');
        process.exit(1);
      }
      
      const adapter = ADAPTERS.find(a => a.name.toLowerCase().includes(target.toLowerCase()));
      if (!adapter) {
        console.error(`Unknown CLI: ${target}`);
        process.exit(1);
      }
      
      await adapter.installHook();
      console.log(`✓ UTS installed for ${adapter.name}`);
      break;
      
    case 'uninstall':
      const targetUninstall = args[1] || detectActiveCLI();
      const adapterUninstall = ADAPTERS.find(a => 
        a.name.toLowerCase().includes((targetUninstall || '').toLowerCase())
      );
      if (adapterUninstall) {
        await adapterUninstall.uninstallHook();
        console.log(`✓ UTS uninstalled for ${adapterUninstall.name}`);
      }
      break;
      
    case 'dashboard':
    default:
      const stats = await getAllStats(options.days || 30);
      
      if (options.json) {
        console.log(JSON.stringify(stats, null, 2));
      } else {
        renderDashboard(stats, options.days || 30, options.compact);
      }
  }
}

main().catch(console.error);
