"""
Generates three personalized outreach variants per qualified lead using Claude.
Variants: LinkedIn connection note, cold email, GitHub issue comment.
Uses prompt caching on the system context.
"""

import json
import anthropic
from rich.console import Console

console = Console()

OUTREACH_SYSTEM = """\
You write outreach for Mem0, an AI memory infrastructure platform. \
Mem0 gives AI agents persistent, searchable memory via a single API — \
replacing hand-rolled conversation buffers, context injection loops, and DIY vector stores.

Your outreach rules:
1. Lead with their specific pain — cite the exact thing you saw
2. Never mention that you found them through monitoring or signal tracking
3. No buzzwords: "game-changer", "revolutionary", "seamlessly", "leverage"
4. Be direct and human — write like a peer developer, not a sales rep
5. Reference their actual implementation detail or question — make it impossible to ignore
6. Mem0 has a free tier — mention it naturally, not as a pitch
7. Keep everything tight: LinkedIn ≤ 300 chars, email ≤ 5 sentences, \
GitHub comment ≤ 4 sentences\
"""

OUTREACH_PROMPT = """\
Developer profile:
- Name/handle: {name}
- Background: {background}
- Company: {company}
- Framework: {framework}

Their specific pain signal:
{raw_signal}

Pain evidence (why this is acute): {pain_evidence}
Fit evidence: {fit_evidence}
Stage: {stage_evidence}

Write all three outreach variants. Return ONLY valid JSON, no markdown fences:

{{
  "linkedin_note": "<≤300 chars, connection request note>",
  "email_subject": "<≤60 chars subject line>",
  "email_body": "<5 sentences max, plain text, no HTML>",
  "github_comment": "<4 sentences max — only if they have an open issue about memory/context, \
otherwise write a comment they could post on their own repo's issue tracker>"
}}\
"""


def generate_outreach(client: anthropic.Anthropic, lead: dict) -> dict:
    name = lead.get("profile_name") or lead.get("owner") or lead.get("owner", "there")
    background_parts = []
    if lead.get("profile_bio"):
        background_parts.append(lead["profile_bio"])
    if lead.get("profile_followers"):
        background_parts.append(f"{lead['profile_followers']} GitHub followers")
    if lead.get("other_ai_repos"):
        background_parts.append(f"also building: {', '.join(lead['other_ai_repos'][:3])}")
    background = "; ".join(background_parts) or "developer"

    prompt = OUTREACH_PROMPT.format(
        name=name,
        background=background,
        company=lead.get("profile_company") or "unknown",
        framework=lead.get("framework", "unknown"),
        raw_signal=lead.get("raw_signal", "")[:1500],
        pain_evidence=lead.get("pain_evidence", ""),
        fit_evidence=lead.get("fit_evidence", ""),
        stage_evidence=lead.get("stage_evidence", ""),
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": OUTREACH_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        return json.loads(raw)
    except json.JSONDecodeError as e:
        console.print(f"[yellow]Outreach JSON parse error for {name}: {e}[/yellow]")
        return {
            "linkedin_note": "",
            "email_subject": "",
            "email_body": "",
            "github_comment": "",
        }
    except Exception as e:
        console.print(f"[yellow]Outreach error for {name}: {e}[/yellow]")
        return {
            "linkedin_note": "",
            "email_subject": "",
            "email_body": "",
            "github_comment": "",
        }


def generate_all_outreach(
    client: anthropic.Anthropic,
    leads: list[dict],
    top_n: int = 10,
    threshold: float = 6.5,
) -> list[dict]:
    qualified = [l for l in leads if l.get("composite", 0) >= threshold][:top_n]
    console.print(
        f"[bold cyan]  Generating outreach for {len(qualified)} qualified leads...[/bold cyan]"
    )

    for i, lead in enumerate(qualified, 1):
        name = lead.get("profile_name") or lead.get("owner") or lead.get("id")
        console.print(f"  Drafting [{i}/{len(qualified)}] [bold]{name}[/bold]")
        messages = generate_outreach(client, lead)
        lead["outreach"] = messages

    return leads
