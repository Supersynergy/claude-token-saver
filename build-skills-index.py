#!/usr/bin/env python3
"""
Claude Skill Manager & Token Saver
Build skills.idx (TSV) and skills-catalog.md from ~/.claude/skills/

Usage:
  python3 build-skills-index.py [--skills-dir PATH] [--output-dir PATH] [--quiet]
"""
import argparse, sys
from pathlib import Path
from collections import defaultdict

# ── Category keyword map (longer/specific keys checked first) ────────────────
CATS = {
    # Browser / Scraping
    'agent-browser':'Browser', 'ghostbrowser':'Browser', 'scrapedeep':'Browser',
    'scrape':'Browser', 'crawl':'Browser', 'browserautomation':'Browser',

    # GSD / OpenSpec
    'gsd':'GSD', 'opsx':'OpenSpec', 'openspec':'OpenSpec', 'spec-build':'OpenSpec',

    # Languages & Frameworks
    'rust-':'Lang', 'python-':'Lang', 'kotlin-':'Lang', 'swift-':'Lang',
    'java-':'Lang', 'golang-':'Lang', 'go-':'Lang', 'cpp-':'Lang',
    'perl-':'Lang', 'django-':'Lang', 'laravel-':'Lang', 'spring':'Lang',
    'typescript':'Lang', 'android-':'Lang', 'compose-multiplatform':'Lang',
    'kotlin-ktor':'Lang', 'swiftui':'Lang', 'jpa-':'Lang',

    # Agents / Orchestration
    'devfleet':'Agents', 'orchestrat':'Agents', 'autonomous':'Agents',
    'claude-devfleet':'Agents', 'jarvis':'Agents', 'dmux':'Agents',
    'nanoclaw':'Agents', 'claw':'Agents', 'agent':'Agents',

    # Business / Revenue / Intel
    'thinkrich':'Biz', 'revshare':'Biz', 'outreach':'Biz', 'intel':'Biz',
    'revenue':'Biz', 'market-':'Biz', 'cold-email':'Biz', 'lead-':'Biz',
    'investor':'Biz', 'trade-':'Biz', 'crisis':'Biz', 'predictive':'Biz',
    'supply-demand':'Biz', 'time-arbitrage':'Biz', 'daily-briefing':'Biz',
    'daily-intel':'Biz', 'hn-intel':'Biz', 'reddit-intel':'Biz',

    # Data / DB / Knowledge
    'knowledge':'Data', 'postgres':'Data', 'clickhouse':'Data', 'database':'Data',
    'surrealdb':'Data', 'sdb-':'Data', 'kb-':'Data', 'chats':'Data',
    'shopdb':'Data', 'videodb':'Data', 'db':'Data',

    # DevOps / Infra
    'docker':'DevOps', 'deploy':'DevOps', 'commit':'DevOps',
    'git-':'DevOps', 'github':'DevOps', 'pm2':'DevOps', 'stacks':'DevOps',

    # Project Management / Quality
    'plane':'PM', 'plan':'PM', 'verify':'PM', 'debug':'PM',
    'tdd-':'PM', 'test':'PM', 'review':'PM', 'audit':'PM',
    'blueprint':'PM', 'checkpoint':'PM', 'eval':'PM', 'refactor':'PM',
    'quality':'PM', 'verification':'PM', 'spec':'PM',

    # Media / Content
    'video':'Media', 'fal-ai':'Media', 'youtube':'Media',
    'article':'Content', 'content-engine':'Content', 'crosspost':'Content',
    'liquid-glass':'Content',

    # Security / Privacy
    'security':'Security', 'dsgvo':'Security', 'privacy':'Security',
    'visa-doc':'Security', 'secret':'Security',

    # AI / LLM Tools
    'claude-api':'AI', 'mcp-server':'AI', 'cost-aware-llm':'AI',
    'token-budget':'AI', 'prompt':'AI', 'foundation-models':'AI',
    'exa-search':'AI', 'fal-ai':'AI', 'ai-first':'AI',

    # Meta / Skill System
    'skill':'Meta', 'continuous-learning':'Meta', 'strategic-compact':'Meta',
    'context-budget':'Meta', 'configure-ecc':'Meta', 'instinct':'Meta',

    # Research
    'deep-research':'Research', 'grep-app':'Research',
    'github-trending':'Research', 'research':'Research',

    # Frontend / UI
    'frontend':'Frontend', 'newwebsite':'Frontend', 'newshop':'Frontend',
    'frontend-slides':'Frontend',
}

SKIP_DIRS  = {'.github','documentation','docs','.git','__pycache__',
              'node_modules','.venv','venv','dist','build','target',
              'ISSUE_TEMPLATE','workflows'}
SKIP_FILES = {'README.md','CHANGELOG.md','CODE_OF_CONDUCT.md','CONTRIBUTING.md',
              'LICENSE.md','INSTALL.md','ARCHITECTURE.md','QUICK_REFERENCE.md',
              'SECURITY.md','AGENTS.md'}


def get_cat(name: str) -> str:
    n = name.lower()
    for k, v in sorted(CATS.items(), key=lambda x: -len(x[0])):
        if n.startswith(k) or (len(k) > 3 and k in n):
            return v
    return 'Other'


def parse_frontmatter(content: str) -> dict:
    fm: dict = {}
    lines = content.split('\n')
    if not lines or lines[0].strip() != '---':
        return fm
    in_fm = False
    for line in lines[:50]:
        s = line.strip()
        if s == '---':
            if not in_fm:
                in_fm = True; continue
            break
        if in_fm and ':' in s:
            key, _, val = s.partition(':')
            fm[key.strip()] = val.strip()
    return fm


def is_valid(fm: dict) -> bool:
    return bool(fm.get('name') and fm.get('description'))


def should_skip(f: Path) -> bool:
    for part in f.parts:
        if part in SKIP_DIRS:
            return True
    if '.github' in str(f):
        return True
    if f.name in SKIP_FILES:
        return True
    return False


def build(skills_dir: Path, out_dir: Path):
    entries = defaultdict(list)
    seen: set = set()
    skipped = 0

    for f in sorted(skills_dir.rglob('*.md')):
        if should_skip(f):
            skipped += 1
            continue
        try:
            content = f.read_text(errors='ignore')
            fm = parse_frontmatter(content)
            if not is_valid(fm):
                skipped += 1
                continue
            name = fm['name']
            if name in seen:
                continue
            desc = fm['description'].replace('\n', ' ').strip()[:90]
            seen.add(name)
            entries[get_cat(name)].append((name, desc, str(f)))
        except Exception:
            skipped += 1

    # TSV index: name TAB cat TAB desc TAB path
    idx_lines = []
    for cat, skills in entries.items():
        for name, desc, path in skills:
            idx_lines.append(f"{name}\t{cat}\t{desc.replace(chr(9),' ')}\t{path}")
    idx_lines.sort()
    (out_dir / 'skills.idx').write_text('\n'.join(idx_lines) + '\n')

    # Markdown catalog with ## Category headers (ctx_index chunks on headings)
    md = ['# Claude Skills Catalog\n']
    for cat in sorted(entries.keys()):
        skills = sorted(entries[cat])
        md.append(f'\n## {cat} ({len(skills)} skills)\n')
        for name, desc, _ in skills:
            md.append(f'- `/{name}` — {desc}')
    (out_dir / 'skills-catalog.md').write_text('\n'.join(md))

    return sum(len(v) for v in entries.values()), skipped, entries


def main():
    p = argparse.ArgumentParser(description='Build Claude skills index')
    p.add_argument('--skills-dir', default=str(Path.home()/'.claude/skills'))
    p.add_argument('--output-dir', default=str(Path.home()/'.claude'))
    p.add_argument('--quiet', '-q', action='store_true')
    args = p.parse_args()

    skills_dir = Path(args.skills_dir)
    out_dir    = Path(args.output_dir)

    if not skills_dir.exists():
        print(f'ERROR: Skills dir not found: {skills_dir}', file=sys.stderr)
        sys.exit(1)
    out_dir.mkdir(parents=True, exist_ok=True)

    total, skipped, entries = build(skills_dir, out_dir)

    if not args.quiet:
        print(f'Built: {total} skills indexed | {skipped} skipped')
        print(f'  {out_dir}/skills.idx')
        print(f'  {out_dir}/skills-catalog.md')
        print()
        for cat, skills in sorted(entries.items(), key=lambda x: -len(x[1])):
            if cat != 'Other':
                print(f'  {cat:<16} {len(skills):3}')
        print(f'  {"Other":<16} {len(entries.get("Other",[]))}')

if __name__ == '__main__':
    sys.exit(main())
