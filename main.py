"""
Mem0 GTM Outreach Agent
Intercepts developer pain signals across GitHub, Stack Overflow, HN, and job postings.
Scores leads by pain intensity + fit + stage, profiles top GitHub leads,
and generates personalized outreach referencing each developer's specific implementation.
"""

import os
import sys
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from github import Github
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from scrapers import scrape_github, scrape_stackoverflow, scrape_hackernews, scrape_job_postings
from scorer import score_all
from profiler import profile_top_leads
from outreach import generate_all_outreach
from reporter import print_lead_table, print_top_outreach, save_json, save_markdown

console = Console()
OUTPUT_DIR = Path(__file__).parent / "output"


def main() -> None:
    load_dotenv()

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")

    if not anthropic_key:
        console.print("[bold red]Error: ANTHROPIC_API_KEY not set in .env[/bold red]")
        sys.exit(1)
    if not github_token:
        console.print("[bold red]Error: GITHUB_TOKEN not set in .env[/bold red]")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=anthropic_key)
    g = Github(github_token)

    OUTPUT_DIR.mkdir(exist_ok=True)

    console.print(
        Panel.fit(
            "[bold white]Mem0 GTM Outreach Agent[/bold white]\n"
            "[dim]Hunting stateless-agent pain signals across GitHub · Stack Overflow · HN · Jobs[/dim]",
            border_style="cyan",
        )
    )

    # ── Step 1: Collect signals ────────────────────────────────────────────────
    console.print(Rule("[bold]Step 1 — Signal Collection[/bold]"))
    t0 = time.time()

    github_signals = scrape_github(github_token)
    so_signals = scrape_stackoverflow()
    hn_signals = scrape_hackernews()
    job_signals = scrape_job_postings()

    all_signals = github_signals + so_signals + hn_signals + job_signals
    console.print(
        f"\n[bold green]Total signals collected: {len(all_signals)}[/bold green]  "
        f"(GitHub={len(github_signals)}, SO={len(so_signals)}, "
        f"HN={len(hn_signals)}, Jobs={len(job_signals)})\n"
    )

    if not all_signals:
        console.print("[red]No signals collected — check your tokens and network.[/red]")
        sys.exit(1)

    # ── Step 2: Score leads ────────────────────────────────────────────────────
    console.print(Rule("[bold]Step 2 — Lead Scoring[/bold]"))
    scored_leads = score_all(client, all_signals)
    console.print(f"\n[bold green]Scoring complete.[/bold green]  "
                  f"Top score: {scored_leads[0].get('composite', 0):.1f}\n")

    # Deduplicate by owner handle (keep highest-scoring signal per person)
    seen_owners: set[str] = set()
    deduped_leads = []
    for lead in scored_leads:
        owner = lead.get("owner") or lead.get("id", "")
        if owner not in seen_owners:
            seen_owners.add(owner)
            deduped_leads.append(lead)
    before = len(scored_leads)
    scored_leads = deduped_leads
    console.print(f"[dim]Deduped: {before} → {len(scored_leads)} unique leads[/dim]\n")

    # Drop leads already engaged with Mem0
    scored_leads = [l for l in scored_leads if not l.get("already_starred_mem0", False)]

    # ── Step 3: Profile GitHub leads ───────────────────────────────────────────
    console.print(Rule("[bold]Step 3 — Developer Profiling[/bold]"))
    profiled_leads = profile_top_leads(g, scored_leads, threshold=7.0)
    console.print()

    # ── Step 4: Generate outreach ──────────────────────────────────────────────
    console.print(Rule("[bold]Step 4 — Outreach Generation[/bold]"))
    final_leads = generate_all_outreach(client, profiled_leads, top_n=10, threshold=6.5)
    console.print()

    # ── Step 5: Display + output ───────────────────────────────────────────────
    console.print(Rule("[bold]Step 5 — Results[/bold]"))
    print_lead_table(final_leads, top_n=20)
    console.print()
    console.print(Rule("[bold]Top Outreach Samples[/bold]"))
    print_top_outreach(final_leads, top_n=3)

    json_path = save_json(final_leads, OUTPUT_DIR)
    md_path = save_markdown(final_leads, OUTPUT_DIR, top_n=5)

    elapsed = time.time() - t0
    console.print(
        f"\n[bold green]Done in {elapsed:.0f}s.[/bold green]  "
        f"Outputs saved to [cyan]{OUTPUT_DIR.relative_to(Path.cwd()) if OUTPUT_DIR.is_relative_to(Path.cwd()) else OUTPUT_DIR}[/cyan]\n"
        f"  JSON  → [dim]{json_path.name}[/dim]\n"
        f"  Report → [dim]{md_path.name}[/dim]"
    )


if __name__ == "__main__":
    main()
