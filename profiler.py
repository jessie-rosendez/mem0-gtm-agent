"""
Developer profiling for GitHub leads scoring above threshold.
Enriches lead data with GitHub profile and checks if they already use Mem0.
"""

import time
from github import Github, GithubException
from rich.console import Console

console = Console()


def profile_github_lead(g: Github, lead: dict) -> dict:
    owner = lead.get("owner", "")
    if not owner:
        return lead

    try:
        user = g.get_user(owner)
        enriched = {
            **lead,
            "profile_name": user.name or owner,
            "profile_bio": user.bio or "",
            "profile_company": user.company or "",
            "profile_location": user.location or "",
            "profile_email": user.email or lead.get("owner_email", ""),
            "profile_followers": user.followers,
            "profile_public_repos": user.public_repos,
            "profile_url": user.html_url,
        }

        # Check if they already starred Mem0 (deprioritize if yes)
        already_starred = False
        try:
            mem0_repo = g.get_repo("mem0ai/mem0")
            starred_repos = [r.full_name for r in user.get_starred()[:50]]
            already_starred = mem0_repo.full_name in starred_repos
        except Exception:
            pass

        enriched["already_starred_mem0"] = already_starred
        if already_starred:
            console.print(f"  [dim]  {owner} already starred Mem0 — composite score halved[/dim]")
            enriched["composite"] = enriched.get("composite", 0) * 0.5

        # Check for other AI/agent repos
        ai_repos = []
        ai_keywords = {"agent", "llm", "langchain", "crewai", "autogen", "gpt", "ai", "memory"}
        try:
            for repo in user.get_repos(type="owner", sort="updated")[:20]:
                if any(kw in (repo.name + " " + (repo.description or "")).lower() for kw in ai_keywords):
                    ai_repos.append(repo.full_name)
        except Exception:
            pass

        enriched["other_ai_repos"] = ai_repos[:5]
        time.sleep(0.5)
        return enriched

    except GithubException as e:
        console.print(f"[yellow]  Profile error for {owner}: {e}[/yellow]")
        return lead


def profile_top_leads(g: Github, scored_leads: list[dict], threshold: float = 7.0) -> list[dict]:
    profiled = []
    github_leads = [l for l in scored_leads if l["source"] == "github" and l.get("composite", 0) >= threshold]

    console.print(f"[bold cyan]  Profiling {len(github_leads)} GitHub leads above {threshold}...[/bold cyan]")

    for lead in scored_leads:
        if lead["source"] == "github" and lead.get("composite", 0) >= threshold:
            profiled.append(profile_github_lead(g, lead))
        else:
            profiled.append(lead)

    profiled.sort(key=lambda x: x.get("composite", 0), reverse=True)
    return profiled
