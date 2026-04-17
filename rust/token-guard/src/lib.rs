//! token_guard — Token safety router for Claude agent teams
//!
//! Rust port of agent_token_guard.py. Rule-based query router that classifies
//! each agent task → optimal tool to minimize token usage.
//!
//! Hot path: called on every agent query. Python: ~2ms. Rust: ~20μs.

use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::LazyLock;

// ── Tool definitions ────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Tool {
    Grep,
    Read,
    WebFetch,
    Bash,
    CtxBatch,
    AgentSpawn,
}

impl Tool {
    pub fn estimated_cost(self) -> u32 {
        match self {
            Tool::Grep => 15,
            Tool::Read => 80,
            Tool::WebFetch => 35,
            Tool::Bash => 150,
            Tool::CtxBatch => 50,
            Tool::AgentSpawn => 30_000,
        }
    }

    pub fn name(self) -> &'static str {
        match self {
            Tool::Grep => "grep",
            Tool::Read => "read",
            Tool::WebFetch => "web_fetch",
            Tool::Bash => "bash",
            Tool::CtxBatch => "ctx_batch",
            Tool::AgentSpawn => "agent_spawn",
        }
    }
}

// ── Routing rules (compiled once) ───────────────────────────────────────

struct Rule {
    pattern: Regex,
    tool: Tool,
    reason: &'static str,
}

static RULES: LazyLock<Vec<Rule>> = LazyLock::new(|| {
    vec![
        Rule {
            pattern: Regex::new(r"(?i)(research|investigate|analyz.+ multiple|summariz.+ pages|compare \d+|5\+|across .+ sources|multi.source)").unwrap(),
            tool: Tool::CtxBatch,
            reason: "multi-source research",
        },
        Rule {
            pattern: Regex::new(r"(?i)(spawn.{0,10}agent|create.{0,10}agent|delegate|subagent|agent.{0,5}team|hand.{0,5}off to)").unwrap(),
            tool: Tool::CtxBatch, // remapped from AgentSpawn
            reason: "agent→ctx_batch (30k→500t)",
        },
        Rule {
            pattern: Regex::new(r"(?i)(https?://|\.com|\.io|\.org|fetch|scrape|download|webpage|website|page from|competitor|pricing page|pdf report)").unwrap(),
            tool: Tool::WebFetch,
            reason: "web content",
        },
        Rule {
            pattern: Regex::new(r"(?i)\b(run |execute|build|compile|install|git |cargo|npm|pnpm|pytest|make |docker)\b").unwrap(),
            tool: Tool::Bash,
            reason: "shell command",
        },
        Rule {
            pattern: Regex::new(r"(?i)(grep|find all|list all|search for|pattern|import|function|class |def |endpoint|todo|fixme|rg |matching \*)").unwrap(),
            tool: Tool::Grep,
            reason: "code search",
        },
        Rule {
            pattern: Regex::new(r"(?i)(read the|open the|show the|display the|cat the|content of|config file|current .+file|\.md file|\.json file)").unwrap(),
            tool: Tool::Read,
            reason: "file content",
        },
    ]
});

// ── Router ──────────────────────────────────────────────────────────────

#[derive(Debug, Serialize)]
pub struct RouteResult {
    pub tool: Tool,
    pub reason: &'static str,
    pub estimated_tokens: u32,
}

pub fn route_query(query: &str) -> RouteResult {
    for rule in RULES.iter() {
        if rule.pattern.is_match(query) {
            return RouteResult {
                tool: rule.tool,
                reason: rule.reason,
                estimated_tokens: rule.tool.estimated_cost(),
            };
        }
    }
    RouteResult {
        tool: Tool::Grep,
        reason: "default: cheapest unknown",
        estimated_tokens: Tool::Grep.estimated_cost(),
    }
}

// ── Budget tracker ──────────────────────────────────────────────────────

#[derive(Debug, Serialize)]
pub struct UsageEntry {
    pub agent: String,
    pub tool: Tool,
    pub tokens_in: u32,
    pub tokens_out: u32,
    pub total: u32,
    pub ms: u32,
}

#[derive(Debug)]
pub struct TokenBudget {
    pub budget: u32,
    pub used: u32,
    pub log: Vec<UsageEntry>,
}

impl TokenBudget {
    pub fn new(budget: u32) -> Self {
        Self { budget, used: 0, log: Vec::new() }
    }

    pub fn record(&mut self, agent: &str, tool: Tool, tokens_in: u32, tokens_out: u32, ms: u32) {
        let total = tokens_in + tokens_out;
        self.used += total;
        self.log.push(UsageEntry {
            agent: agent.to_string(),
            tool,
            tokens_in,
            tokens_out,
            total,
            ms,
        });
    }

    pub fn remaining(&self) -> u32 {
        self.budget.saturating_sub(self.used)
    }

    pub fn pct_used(&self) -> f64 {
        self.used as f64 / self.budget as f64 * 100.0
    }

    pub fn should_block(&self, tool: Tool) -> bool {
        if tool == Tool::AgentSpawn {
            return true;
        }
        if self.pct_used() >= 80.0 && tool == Tool::Bash {
            return true;
        }
        if self.pct_used() >= 95.0 && tool != Tool::Grep {
            return true;
        }
        false
    }

    pub fn report(&self) -> BudgetReport {
        let mut by_tool: HashMap<Tool, ToolStats> = HashMap::new();
        for e in &self.log {
            let s = by_tool.entry(e.tool).or_insert(ToolStats { calls: 0, tokens: 0, ms: 0 });
            s.calls += 1;
            s.tokens += e.total;
            s.ms += e.ms;
        }
        BudgetReport {
            budget: self.budget,
            used: self.used,
            remaining: self.remaining(),
            pct_used: (self.pct_used() * 10.0).round() / 10.0,
            by_tool,
        }
    }
}

#[derive(Debug, Serialize)]
pub struct ToolStats {
    pub calls: u32,
    pub tokens: u32,
    pub ms: u32,
}

#[derive(Debug, Serialize)]
pub struct BudgetReport {
    pub budget: u32,
    pub used: u32,
    pub remaining: u32,
    pub pct_used: f64,
    pub by_tool: HashMap<Tool, ToolStats>,
}

// ── TokenGuard (combines router + budget) ───────────────────────────────

pub struct TokenGuard {
    pub budget: TokenBudget,
}

impl TokenGuard {
    pub fn new(budget_limit: u32) -> Self {
        Self { budget: TokenBudget::new(budget_limit) }
    }

    pub fn route(&self, query: &str) -> RouteResult {
        let mut result = route_query(query);
        if self.budget.should_block(result.tool) {
            result = RouteResult {
                tool: Tool::Grep,
                reason: "budget_guard: forced cheap",
                estimated_tokens: Tool::Grep.estimated_cost(),
            };
        }
        result
    }

    pub fn record(&mut self, agent: &str, tool: Tool, tokens_in: u32, tokens_out: u32, ms: u32) {
        self.budget.record(agent, tool, tokens_in, tokens_out, ms);
    }

    pub fn report_summary(&self) -> String {
        let r = self.budget.report();
        let mut lines = vec![
            format!("Budget: {}/{} tokens ({:.1}% used)", r.used, r.budget, r.pct_used),
            format!("Remaining: {}", r.remaining),
            "By tool:".to_string(),
        ];
        let mut tools: Vec<_> = r.by_tool.iter().collect();
        tools.sort_by(|a, b| b.1.tokens.cmp(&a.1.tokens));
        for (tool, stats) in tools {
            lines.push(format!("  {:<14} {} calls  {:>6} tokens  {}ms", tool.name(), stats.calls, stats.tokens, stats.ms));
        }
        lines.join("\n")
    }
}

// ── JSON CLI mode ───────────────────────────────────────────────────────

/// Route a query and return JSON: {"tool":"grep","reason":"...","estimated_tokens":15}
pub fn route_json(query: &str) -> String {
    let result = route_query(query);
    serde_json::json!({
        "tool": result.tool.name(),
        "reason": result.reason,
        "estimated_tokens": result.estimated_tokens,
    }).to_string()
}
