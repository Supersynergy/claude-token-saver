use std::env;
use std::io::{self, BufRead};
use std::time::Instant;
use token_guard::{route_json, TokenGuard};

fn main() {
    let args: Vec<String> = env::args().collect();

    match args.get(1).map(|s| s.as_str()) {
        // Single query: token-guard route "find all imports"
        Some("route") => {
            let query = args[2..].join(" ");
            println!("{}", route_json(&query));
        }

        // Batch mode: reads queries from stdin, one per line
        Some("batch") => {
            let stdin = io::stdin();
            for line in stdin.lock().lines() {
                let q = line.unwrap_or_default();
                if !q.is_empty() {
                    println!("{}", route_json(&q));
                }
            }
        }

        // Demo mode: runs benchmark queries
        Some("demo") | None => {
            let queries = [
                "find all import statements in src/",
                "fetch https://example.com and summarize",
                "read the config file",
                "run npm install and check for errors",
                "research 5 competitor websites and compare pricing",
                "spawn agent to handle database migration",
                "grep for TODO comments across all files",
                "show me the content of README.md",
            ];

            println!("── TokenGuard Rust demo ──\n");
            println!("{:<50} {:<14} {:<25} {:>10}", "Query", "Tool", "Reason", "Est.tokens");
            println!("{}", "-".repeat(100));

            let mut guard = TokenGuard::new(10_000);
            let start = Instant::now();

            for q in &queries {
                let r = guard.route(q);
                let est = r.estimated_tokens;
                guard.record("demo-agent", r.tool, est / 2, est / 2, 0);
                println!("{:<50} {:<14} {:<25} {:>10}", &q[..q.len().min(49)], r.tool.name(), r.reason, est);
            }

            let elapsed = start.elapsed();
            println!("\n{}", guard.report_summary());
            println!("\nRouted {} queries in {:?} ({:.1}μs/query)",
                queries.len(), elapsed, elapsed.as_micros() as f64 / queries.len() as f64);
        }

        Some(cmd) => {
            eprintln!("Unknown command: {cmd}\nUsage: token-guard [route <query> | batch | demo]");
            std::process::exit(1);
        }
    }
}
