# Mem0 GTM Outreach Agent

An agentic GTM pipeline that hunts developer pain signals across GitHub, Stack Overflow, Hacker News, and job postings — scores each lead with Claude, and generates hyper-personalized outreach referencing the developer's specific codebase or post.

Built for [Mem0](https://mem0.ai), an AI memory infrastructure platform that gives AI agents persistent, isolated memory via a single API.

**Live web demo:** [mem0-gtm-web.vercel.app](https://mem0-gtm-web.vercel.app) — run the agent in a browser, see results in real time.

---

## Sample Output

> From a single run: **136 signals collected → 46 qualified leads (score ≥ 6.5) → 10 with full outreach packages**

Full results: [`output/report.md`](output/report.md) · [`output/leads.json`](output/leads.json)

### Ranked lead table (top 5)

| # | Source | Handle | Framework | Pain | Fit | Stage | Score |
|---|--------|--------|-----------|------|-----|-------|-------|
| 1 | stackoverflow | Sergio G | LangChain | 9 | 10 | 9 | **9.2** |
| 2 | hackernews | yashsolanky | unknown | 9 | 10 | 8 | **9.2** |
| 3 | github | GitHpriyanshu23 | FastAPI | 9 | 10 | 8 | **9.1** |
| 4 | github | doobidoo | LangGraph | 10 | 9 | 8 | **9.1** |
| 5 | hackernews | BERTmackliin | unknown | 10 | 9 | 8 | **9.1** |

### Generated outreach — Lead #1 (Sergio G, score 9.2)

**LinkedIn note**
> Saw your FastAPI + LangChain scaling question - the per-user memory mixing issue is exactly what we built Mem0 to solve. We handle persistent, isolated memory for each user session without the agent instantiation headaches. Has a free tier if you want to test it.

**Cold email** · *Subject: Re: Your LangChain agent scaling question*
> Saw your question about per-user memory mixing in your FastAPI LangChain setup. This exact problem - session data bleeding across users - is why we built Mem0. Instead of managing memory state in your agent initialization, Mem0 gives each user isolated, persistent memory via a simple API call. You can test it free with your existing FastAPI setup. Would save you from having to architect the per-user memory isolation yourself.

**GitHub comment**
> The per-user memory mixing you're hitting is a common LangChain scaling issue. Mem0 handles isolated user sessions without requiring separate agent instances - each user gets their own memory space via API calls. Free tier available for testing with your FastAPI setup. Might be cleaner than managing session state in your agent architecture.

---

## How it works

1. **Signal Collection** — Parallel scrape across GitHub, Stack Overflow, HN, and HN Who's Hiring for developers actively fighting stateless-agent problems
2. **Lead Scoring** — Claude evaluates each signal on pain intensity (1-10), product fit (1-10), and buyer stage (1-10); computes a weighted composite score
3. **Developer Profiling** — For GitHub leads above threshold: pulls repo details, bio, stack context; filters anyone already using Mem0
4. **Outreach Generation** — Claude writes 3 channel-specific messages per lead (LinkedIn, email, GitHub comment) referencing the lead's exact code or post
5. **Report** — Saves ranked table + full profiles to `output/report.md` and `output/leads.json`

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
