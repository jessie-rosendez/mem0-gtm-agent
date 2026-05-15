"""
Terminal display and file output (JSON + Markdown) for the GTM agent results.
"""

import json
import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text

console = Console()


def print_lead_table(leads: list[dict], top_n: int = 20) -> None:
    table = Table(
        title=f"Mem0 GTM — Ranked Leads (Top {min(top_n, len(leads))})",
        box=box.ROUNDED,
        show_lines=True,
        highlight=True,
    )

    table.add_column("#", style="dim", width=3)
    table.add_column("Source", width=10)
    table.add_column("Handle / Repo", width=28, no_wrap=True)
    table.add_column("Framework", width=12)
    table.add_column("Pain", justify="center", width=5)
    table.add_column("Fit", justify="center", width=5)
    table.add_column("Stage", justify="center", width=5)
    table.add_column("Score", justify="center", width=6, style="bold green")
    table.add_column("Pain Evidence", width=42)

    for i, lead in enumerate(leads[:top_n], 1):
        score = lead.get("composite", 0)
        color = "green" if score >= 7 else "yellow" if score >= 5 else "red"
        table.add_row(
            str(i),
            lead.get("source", ""),
            (lead.get("owner") or lead.get("id", ""))[:28],
            lead.get("framework", "unknown")[:12],
            str(lead.get("pain_intensity", "-")),
            str(lead.get("fit", "-")),
            str(lead.get("stage", "-")),
            Text(f"{score:.1f}", style=color),
            (lead.get("pain_evidence") or "")[:42],
        )

    console.print(table)


def print_top_outreach(leads: list[dict], top_n: int = 3) -> None:
    qualified = [l for l in leads if l.get("outreach") and l.get("composite", 0) >= 6.5][:top_n]

    for lead in qualified:
        name = lead.get("profile_name") or lead.get("owner") or lead.get("id")
        score = lead.get("composite", 0)
        outreach = lead.get("outreach", {})
        url = lead.get("url", "")

        header = f"[bold]{name}[/bold]  score={score:.1f}  {url}"
        body = []

        if outreach.get("linkedin_note"):
            body.append(f"[bold cyan]LinkedIn:[/bold cyan]\n{outreach['linkedin_note']}")

        if outreach.get("email_subject") and outreach.get("email_body"):
            body.append(
                f"[bold cyan]Email — {outreach['email_subject']}[/bold cyan]\n{outreach['email_body']}"
            )

        if outreach.get("github_comment"):
            body.append(f"[bold cyan]GitHub comment:[/bold cyan]\n{outreach['github_comment']}")

        console.print(Panel("\n\n".join(body), title=header, box=box.SIMPLE, padding=(1, 2)))


def save_json(leads: list[dict], output_dir: Path) -> Path:
    out_path = output_dir / "leads.json"
    # Strip non-serializable fields
    clean = []
    for lead in leads:
        row = {k: v for k, v in lead.items() if isinstance(v, (str, int, float, list, dict, bool, type(None)))}
        clean.append(row)

    with open(out_path, "w") as f:
        json.dump(clean, f, indent=2, default=str)
    return out_path


def save_markdown(leads: list[dict], output_dir: Path, top_n: int = 5) -> Path:
    out_path = output_dir / "report.md"
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# Mem0 GTM Outreach Report",
        f"_Generated: {date_str}_",
        "",
        "## Signal Summary",
        "",
    ]

    sources = {}
    for lead in leads:
        src = lead.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    for src, count in sorted(sources.items()):
        lines.append(f"- **{src}**: {count} signals")
    lines.append(f"- **Total leads scored**: {len(leads)}")
    lines.append("")

    qualified = [l for l in leads if l.get("composite", 0) >= 6.5]
    lines.append(f"- **Qualified leads (score ≥ 6.5)**: {len(qualified)}")
    lines.append("")

    lines.append("## Ranked Lead Table")
    lines.append("")
    lines.append("| # | Source | Handle | Framework | Pain | Fit | Stage | Score |")
    lines.append("|---|--------|--------|-----------|------|-----|-------|-------|")

    for i, lead in enumerate(leads[:20], 1):
        lines.append(
            f"| {i} | {lead.get('source','')} | "
            f"{lead.get('owner') or lead.get('id','')} | "
            f"{lead.get('framework','?')} | "
            f"{lead.get('pain_intensity','-')} | "
            f"{lead.get('fit','-')} | "
            f"{lead.get('stage','-')} | "
            f"**{lead.get('composite',0):.1f}** |"
        )
    lines.append("")

    # Top N full profiles with outreach
    top_with_outreach = [l for l in leads if l.get("outreach")][:top_n]
    lines.append(f"## Top {len(top_with_outreach)} Leads — Full Profiles & Outreach")
    lines.append("")

    for i, lead in enumerate(top_with_outreach, 1):
        name = lead.get("profile_name") or lead.get("owner") or lead.get("id", "")
        score = lead.get("composite", 0)
        url = lead.get("url", "")
        outreach = lead.get("outreach", {})

        lines.append(f"### {i}. {name} — Score: {score:.1f}")
        lines.append("")
        lines.append(f"**Source:** {lead.get('source', '')}  ")
        lines.append(f"**URL:** {url}  ")
        if lead.get("profile_company"):
            lines.append(f"**Company:** {lead['profile_company']}  ")
        if lead.get("profile_bio"):
            lines.append(f"**Bio:** {lead['profile_bio']}  ")
        lines.append(f"**Framework:** {lead.get('framework', 'unknown')}  ")
        lines.append("")

        lines.append("**Scores:**")
        lines.append(f"- Pain intensity: {lead.get('pain_intensity','-')}/10 — {lead.get('pain_evidence','')}")
        lines.append(f"- Fit: {lead.get('fit','-')}/10 — {lead.get('fit_evidence','')}")
        lines.append(f"- Stage: {lead.get('stage','-')}/10 — {lead.get('stage_evidence','')}")
        lines.append("")

        if outreach.get("linkedin_note"):
            lines.append("**LinkedIn Note:**")
            lines.append(f"> {outreach['linkedin_note']}")
            lines.append("")

        if outreach.get("email_subject") and outreach.get("email_body"):
            lines.append(f"**Email — Subject: {outreach['email_subject']}**")
            lines.append("")
            lines.append(outreach["email_body"])
            lines.append("")

        if outreach.get("github_comment"):
            lines.append("**GitHub Comment:**")
            lines.append(f"> {outreach['github_comment']}")
            lines.append("")

        lines.append("---")
        lines.append("")

    with open(out_path, "w") as f:
        f.write("\n".join(lines))

    return out_path
