"""
Lead scoring via Claude. Evaluates pain intensity, fit, and stage for each signal.
Uses prompt caching on the system prompt to reduce token costs across batch scoring.
"""

import json
import anthropic
from rich.console import Console

console = Console()

SCORING_SYSTEM = """\
You are a GTM analyst for Mem0, an AI memory infrastructure company.

Mem0 provides a managed memory layer for AI agents — developers use it to give \
their LLM applications persistent, searchable memory without building the \
infrastructure themselves. Core value: eliminate the stateless agent problem \
in one API call.

Target customer: engineering teams shipping production AI agents who are \
currently managing conversation history, context injection, or vector stores \
themselves — a painful, scaling-hostile DIY approach.

You score inbound signals to identify the highest-priority developer leads.\
"""

SCORING_PROMPT = """\
Signal source: {source}
Signal content:
{raw_signal}

Score this lead on three dimensions. Return ONLY valid JSON — no markdown fences, \
no extra text.

{{
  "pain_intensity": <1-10 int>,
  "pain_evidence": "<one sentence citing specific detail from the signal>",
  "fit": <1-10 int>,
  "fit_evidence": "<one sentence>",
  "stage": <1-10 int>,
  "stage_evidence": "<one sentence>",
  "framework": "<primary AI framework detected, or 'unknown'>",
  "composite": <float, weighted: pain*0.45 + fit*0.35 + stage*0.20>
}}

Scoring rubric:
- pain_intensity: 10 = actively blocked, writing custom memory infra; \
1 = vague mention of AI
- fit: 10 = Python/TS agent with vector store + LLM calls, no managed memory; \
1 = unrelated use case
- stage: 10 = production traffic, team > 1; 1 = hello-world prototype\
"""


def score_signal(client: anthropic.Anthropic, signal: dict) -> dict:
    prompt = SCORING_PROMPT.format(
        source=signal["source"],
        raw_signal=signal["raw_signal"][:2000],
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system=[
                {
                    "type": "text",
                    "text": SCORING_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        scores = json.loads(raw)
        return scores
    except json.JSONDecodeError:
        return {
            "pain_intensity": 0,
            "pain_evidence": "parse error",
            "fit": 0,
            "fit_evidence": "parse error",
            "stage": 0,
            "stage_evidence": "parse error",
            "framework": "unknown",
            "composite": 0.0,
        }
    except Exception as e:
        console.print(f"[yellow]Scoring error: {e}[/yellow]")
        return {
            "pain_intensity": 0,
            "pain_evidence": str(e),
            "fit": 0,
            "fit_evidence": "",
            "stage": 0,
            "stage_evidence": "",
            "framework": "unknown",
            "composite": 0.0,
        }


def score_all(client: anthropic.Anthropic, signals: list[dict]) -> list[dict]:
    scored = []
    total = len(signals)

    for i, signal in enumerate(signals, 1):
        console.print(
            f"  Scoring [{i}/{total}] [dim]{signal['source']}[/dim] "
            f"[bold]{signal.get('title', signal['id'])[:60]}[/bold]"
        )
        scores = score_signal(client, signal)
        merged = {**signal, **scores}
        scored.append(merged)

    scored.sort(key=lambda x: x.get("composite", 0), reverse=True)
    return scored
