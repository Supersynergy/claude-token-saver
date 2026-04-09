#!/usr/bin/env node
/**
 * UTS Universal Output Filter Plugin
 * Reduziert CLI-Output um 70-95% durch Noise-Removal
 */

const { filterOutput } = require('../core/adapter-interface');

/**
 * Noise-Patterns pro Command-Typ
 */
const NOISE_PATTERNS = {
  git: [
    /^Merging|^Auto-merging|^CONFLICT/,
    /^Fast-forward/,
    /^warning: could not unlink/,
    /^remote: Enumerating/,
    /^remote: Counting/,
    /^To https?:\/\//,
    /^From https?:\/\//,
    /^ \* \[new branch\]/,
    /^ \* \[branch\]/,
  ],
  npm: [
    /^added \d+ packages? in \d+\.?\d*s/,
    /^found \d+ vulnerabilities?/,
    /^audited \d+ packages?/,
    /^npm WARN/,
    /^removed \d+ packages?/,
    /^这个世界/g,
  ],
  pytest: [
    /^=+ \d+ passed/,
    /^=+ \d+ failed/,
    /^platform \w+ --/,
    /^cachedir: \./,
    /^test session starts/,
    /^collecting \d+ items/,
    /^---/?.*Picked up/,
  ],
  docker: [
    /^Unable to find image/,
    /^Pulling from layer/,
    /^[a-f0-9]{12}: Pulling/,
    /^Digest: sha256:/,
    /^Status: Downloaded newer/,
    /^Build context/,
    /^Sending build context/,
  ],
  cargo: [
    /^    Updating|^   Compiling|^    Finished/,
    /^warning: unused/,
    /^test result: ok\./,
    /^     Running.*\.+ \d+ tests?/,
  ],
  pip: [
    /^Requirement already satisfied:/,
    /^Installing collected packages/,
    /^Successfully installed/,
    /^Looking in indexes:/,
  ],
  kubectl: [
    /^NAME\s+AGE|^NAMESPACE/,
    /^deployment\.apps\/.* created/,
    /^service\/.* exposed/,
    /^configmap\/.* created/,
    /^persistentvolumeclaim\/.* created/,
  ],
  terraform: [
    /^Apply complete!/,
    /^Resources: \d+ added, \d+ changed, \d+ destroyed/,
    /^Outputs:/,
    /^Refreshing Terraform state/,
  ],
};

/**
 * CLI-spezifische Komprimierung
 */
const COMPRESSORS = {
  git: (output) => {
    const lines = output.split('\n');
    const kept = [];
    
    for (const line of lines) {
      // Nur relevante Zeilen behalten
      if (line.includes('ERROR') || line.includes('error:') || 
          line.includes('FAILED') || line.includes('@@') ||
          (line.startsWith('+') && !line.startsWith('+++')) ||
          (line.startsWith('-') && !line.startsWith('---')) ||
          line.includes('->')) {
        kept.push(line);
      }
    }
    
    return kept.join('\n') || output.substring(0, 500);
  },
  
  pytest: (output) => {
    const lines = output.split('\n');
    const kept = [];
    
    for (const line of lines) {
      // Nur Fehler + Test-Namen behalten
      if (line.includes('FAILED') || line.includes('ERROR') ||
          line.includes('PASSED') || line.includes('::') ||
          line.includes('AssertionError')) {
        kept.push(line);
      }
    }
    
    return kept.join('\n') || 'All tests passed (output filtered)';
  },
  
  npm: (output) => {
    const lines = output.split('\n');
    const kept = [];
    
    for (const line of lines) {
      if (line.includes('ERR!') || line.includes('error') ||
          line.includes('warn') || line.includes('WARN')) {
        kept.push(line);
      }
    }
    
    return kept.join('\n') || 'npm completed successfully (output filtered)';
  },
  
  docker: (output) => {
    const lines = output.split('\n');
    const kept = [];
    
    for (const line of lines) {
      if (line.includes('Error') || line.includes('error') ||
          line.includes('sha256') || line.includes('Successfully') ||
          line.startsWith('CONTAINER ID')) {
        kept.push(line);
      }
    }
    
    return kept.join('\n') || output.substring(0, 500);
  },
};

/**
 * Schätze Token für Output
 */
function estimateTokens(text) {
  return Math.ceil(text.length / 4);
}

/**
 * Hauptsächlicher Filter
 */
function filter(command, output, options = {}) {
  const {
    keepErrors = true,
    keepWarnings = true,
    ultra = false,
  } = options;
  
  if (!output || output.length === 0) return output;
  
  // Command extrahieren
  const cmd = command.split(' ')[0];
  
  // Pattern für dieses Command holen
  const patterns = NOISE_PATTERNS[cmd] || [];
  
  // Filter anwenden
  let filtered = output
    .split('\n')
    .filter(line => {
      // Immer Errors behalten
      if (keepErrors && (line.includes('ERROR') || line.includes('error:'))) {
        return true;
      }
      
      // Warnings optional behalten
      if (keepWarnings && (line.includes('WARN') || line.includes('warning'))) {
        return true;
      }
      
      // Noise-Patterns filtern
      for (const pattern of patterns) {
        if (pattern.test(line)) return false;
      }
      
      return true;
    })
    .join('\n');
  
  // CLI-spezifische Komprimierung
  if (COMPRESSORS[cmd]) {
    filtered = COMPRESSORS[cmd](filtered);
  }
  
  // Ultra-Mode: noch mehr kürzen
  if (ultra) {
    const lines = filtered.split('\n');
    if (lines.length > 50) {
      filtered = lines.slice(0, 20).join('\n') + 
                 `\n... [${lines.length - 40} more lines filtered] ...\n` +
                 lines.slice(-20).join('\n');
    }
  }
  
  return filtered.trim();
}

/**
 * Stats berechnen
 */
function getStats(original, filtered) {
  const origTokens = estimateTokens(original);
  const filteredTokens = estimateTokens(filtered);
  const saved = origTokens - filteredTokens;
  const pct = origTokens > 0 ? ((saved / origTokens) * 100).toFixed(1) : '0.0';
  
  return {
    originalTokens: origTokens,
    filteredTokens: filteredTokens,
    savedTokens: saved,
    savingsPercent: pct,
  };
}

// CLI Interface
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args[0] === '--stats') {
    // Nur Stats berechnen
    const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
    const stats = getStats(input.original, input.filtered);
    console.log(JSON.stringify(stats, null, 2));
  } else if (args[0] === '--help') {
    console.log(`
UTS Output Filter

Usage:
  cat output.txt | node output-filter.js [options]
  node output-filter.js --stats < input.json

Options:
  --ultra     Ultra-compact mode (aggressive filtering)
  --stats     Show filtering statistics
  --help      This help
    `);
  } else {
    // Output filtern
    const ultra = args.includes('--ultra');
    const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
    const filtered = filter(input.command, input.output, { ultra });
    const stats = getStats(input.output, filtered);
    
    console.log(JSON.stringify({
      filtered,
      stats,
    }, null, 2));
  }
}

module.exports = { filter, getStats, filterOutput };
