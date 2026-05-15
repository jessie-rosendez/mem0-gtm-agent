# Mem0 GTM Outreach Agent

An agentic GTM pipeline that hunts developer pain signals across GitHub, Stack Overflow, Hacker News, and job postings — scores each lead with Claude, and generates hyper-personalized outreach referencing the developer's specific codebase or post.

Built for [Mem0](https://mem0.ai), an AI memory infrastructure platform that gives AI agents persistent, isolated memory via a single API.

## What it does

1. **Signal Collection** — Scrapes 4 sources for developers actively fighting stateless-agent problems (custom memory buffers, FAISS DIY stores, session state issues)
2. **Lead Scoring** — Claude evaluates each signal on pain intensity, product fit, and buyer stage (weighted composite score)
3. **Developer Profiling** — Enriches GitHub leads with profile data; filters out anyone already using Mem0
4. **Outreach Generation** — Writes 3 channel-specific messages per lead (LinkedIn note, cold email, GitHub comment) citing the lead's exact pain point
5. **Report** — Saves ranked lead table + full outreach to `output/`

## Sample output

From a single run: **136 signals → 46 qualified leads (score ≥ 6.5) → 10 with full outreach packages**

See [`output/report.md`](output/report.md) for the full ranked lead table and top 5 lead profiles with generated outreach.

## Architecture

```
scrapers.py   — GitHub API, Stack Overflow API, HN Algolia API, HN Who's Hiring
scorer.py     — Claude Sonnet scoring with prompt caching (pain × fit × stage)
profiler.py   — GitHub profile enrichment + Mem0 overlap filter
outreach.py   — Claude-generated 3-channel outreach per lead
reporter.py   — Rich terminal output + JSON/Markdown export
main.py       — Orchestrator
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and GITHUB_TOKEN
python main.py
```

## Technical notes

- **Prompt caching** — `scorer.py` and `outreach.py` use `cache_control: ephemeral` on the system prompt, cutting token costs across the 100+ lead scoring batch
- **Mem0 overlap filter** — checks if a GitHub lead has already starred `mem0ai/mem0` and deprioritizes them so outreach doesn't hit existing users
- **Sources:** GitHub code search, Stack Overflow search API, HN Algolia API, HN "Who is Hiring" threads
