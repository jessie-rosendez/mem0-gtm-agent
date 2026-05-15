"""
Signal scrapers for GitHub, Stack Overflow, Hacker News, and job postings.
Each returns a list of raw signal dicts with source, content, and metadata.
"""

import time
import requests
from github import Github, GithubException
from rich.console import Console

console = Console()

GITHUB_MEMORY_QUERIES = [
    "conversation_history append role language:Python pushed:>2025-04-01",
    "context_window inject_context language:Python pushed:>2025-04-01",
    "session_memory langchain language:Python pushed:>2025-04-01",
    "agent memory langchain language:TypeScript pushed:>2025-04-01",
    "messages append role crewai language:Python pushed:>2025-04-01",
    "vector store memory llamaindex language:Python pushed:>2025-04-01",
    "autogen memory agent language:Python pushed:>2025-04-01",
]

SO_KEYWORDS = [
    "agent memory OR stateless agent OR conversation history LLM",
    "LLM context window persistent memory python",
    "AI agent remember conversation history",
    "langchain memory persist sessions",
    "vector store agent memory management",
]

HN_QUERIES = [
    "agent memory",
    "LLM context stateless",
    "conversation history agent",
    "persistent context llm",
]


def scrape_github(gh_token: str, max_repos: int = 30) -> list[dict]:
    signals = []
    g = Github(gh_token)

    console.print("[bold cyan]  Scanning GitHub...[/bold cyan]")
    seen = set()

    for query in GITHUB_MEMORY_QUERIES:
        try:
            results = g.search_repositories(query=query, sort="updated", order="desc")
            count = 0
            for repo in results:
                if count >= 5:
                    break
                if repo.full_name in seen:
                    continue
                seen.add(repo.full_name)

                # Skip Mem0's own repos
                if "mem0ai" in repo.full_name.lower() or "mem0" in repo.name.lower():
                    continue

                readme_text = ""
                try:
                    readme = repo.get_readme()
                    readme_text = readme.decoded_content.decode("utf-8", errors="ignore")[:3000]
                except Exception:
                    pass

                signals.append({
                    "source": "github",
                    "id": repo.full_name,
                    "url": repo.html_url,
                    "owner": repo.owner.login,
                    "owner_email": repo.owner.email or "",
                    "owner_url": repo.owner.html_url,
                    "title": repo.name,
                    "description": repo.description or "",
                    "readme_snippet": readme_text[:1500],
                    "stars": repo.stargazers_count,
                    "language": repo.language or "",
                    "last_pushed": str(repo.pushed_at),
                    "topics": repo.get_topics(),
                    "raw_signal": f"Repo: {repo.full_name}\nDescription: {repo.description}\nREADME excerpt:\n{readme_text[:800]}",
                })
                count += 1

                if len(signals) >= max_repos:
                    break
            time.sleep(1)
        except GithubException as e:
            console.print(f"[yellow]GitHub query error: {e}[/yellow]")

    console.print(f"[green]  Found {len(signals)} GitHub signals[/green]")
    return signals


def scrape_stackoverflow(max_per_keyword: int = 8) -> list[dict]:
    signals = []
    console.print("[bold cyan]  Scanning Stack Overflow...[/bold cyan]")

    base_url = "https://api.stackexchange.com/2.3/search/advanced"
    seen = set()

    for keyword in SO_KEYWORDS:
        params = {
            "q": keyword,
            "tagged": "python",
            "site": "stackoverflow",
            "sort": "votes",
            "order": "desc",
            "pagesize": max_per_keyword,
            "filter": "withbody",
            "fromdate": 1704067200,  # 2024-01-01
        }
        try:
            resp = requests.get(base_url, params=params, timeout=10)
            resp.raise_for_status()
            items = resp.json().get("items", [])

            for item in items:
                qid = item.get("question_id")
                if qid in seen:
                    continue
                seen.add(qid)

                body = item.get("body", "")[:1000]
                signals.append({
                    "source": "stackoverflow",
                    "id": str(qid),
                    "url": item.get("link", ""),
                    "owner": item.get("owner", {}).get("display_name", "unknown"),
                    "owner_url": item.get("owner", {}).get("link", ""),
                    "owner_email": "",
                    "title": item.get("title", ""),
                    "description": body,
                    "stars": item.get("score", 0),
                    "last_pushed": str(item.get("creation_date", "")),
                    "raw_signal": f"Question: {item.get('title')}\nBody: {body}",
                })
            time.sleep(0.5)
        except Exception as e:
            console.print(f"[yellow]SO error for '{keyword}': {e}[/yellow]")

    console.print(f"[green]  Found {len(signals)} Stack Overflow signals[/green]")
    return signals


def scrape_hackernews(max_per_query: int = 8) -> list[dict]:
    signals = []
    console.print("[bold cyan]  Scanning Hacker News...[/bold cyan]")

    seen = set()
    for query in HN_QUERIES:
        url = "https://hn.algolia.com/api/v1/search"
        params = {
            "query": query,
            "tags": "(story,comment)",
            "numericFilters": "created_at_i>1704067200",
            "hitsPerPage": max_per_query,
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            hits = resp.json().get("hits", [])

            for hit in hits:
                obj_id = hit.get("objectID")
                if obj_id in seen:
                    continue
                seen.add(obj_id)

                text = hit.get("story_text") or hit.get("comment_text") or hit.get("title") or ""
                text = text[:1200]

                signals.append({
                    "source": "hackernews",
                    "id": obj_id,
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={obj_id}",
                    "owner": hit.get("author", "unknown"),
                    "owner_url": f"https://news.ycombinator.com/user?id={hit.get('author', '')}",
                    "owner_email": "",
                    "title": hit.get("title") or "(comment)",
                    "description": text,
                    "stars": hit.get("points", 0) or 0,
                    "last_pushed": hit.get("created_at", ""),
                    "raw_signal": f"HN post by {hit.get('author')}: {hit.get('title')}\n{text}",
                })
            time.sleep(0.3)
        except Exception as e:
            console.print(f"[yellow]HN error for '{query}': {e}[/yellow]")

    console.print(f"[green]  Found {len(signals)} HN signals[/green]")
    return signals


def scrape_job_postings() -> list[dict]:
    """
    Scrapes the Hacker News 'Who is Hiring' threads — the highest-signal public
    job data available without authentication. Filters for roles involving agent
    memory, LLM state management, or AI infrastructure at scale.
    """
    signals = []
    console.print("[bold cyan]  Scanning HN Who's Hiring...[/bold cyan]")

    # HN Who's Hiring threads — fetch more threads and paginate comments
    hiring_story_ids = []
    try:
        search_resp = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={
                "query": "Ask HN: Who is hiring",
                "tags": "story",
                "hitsPerPage": 6,
            },
            timeout=10,
        )
        for hit in search_resp.json().get("hits", []):
            if "who is hiring" in hit.get("title", "").lower():
                hiring_story_ids.append(hit.get("objectID"))
    except Exception as e:
        console.print(f"[yellow]Job postings error: {e}[/yellow]")
        return signals

    MEMORY_KEYWORDS = [
        "agent memory", "persistent context", "llm state", "ai agent",
        "memory layer", "stateful agent", "langchain", "crewai", "autogen",
        "llm", "vector", "embeddings", "rag", "openai", "anthropic",
    ]

    seen = set()
    for story_id in hiring_story_ids[:5]:
        try:
            for page in range(3):  # paginate up to 3 pages of 100 comments each
                comments_resp = requests.get(
                    "https://hn.algolia.com/api/v1/search",
                    params={
                        "tags": f"comment,story_{story_id}",
                        "hitsPerPage": 100,
                        "page": page,
                    },
                    timeout=10,
                )
                hits_page = comments_resp.json().get("hits", [])
                if not hits_page:
                    break
                for hit in hits_page:
                    text = hit.get("comment_text") or ""
                    text_lower = text.lower()

                    if not any(kw in text_lower for kw in MEMORY_KEYWORDS):
                        continue

                    obj_id = hit.get("objectID")
                    if obj_id in seen:
                        continue
                    seen.add(obj_id)

                    signals.append({
                        "source": "job_posting",
                        "id": obj_id,
                        "url": f"https://news.ycombinator.com/item?id={obj_id}",
                        "owner": hit.get("author", "unknown"),
                        "owner_url": f"https://news.ycombinator.com/user?id={hit.get('author', '')}",
                        "owner_email": "",
                        "title": "HN Hiring Post",
                        "description": text[:1000],
                        "stars": 0,
                        "last_pushed": hit.get("created_at", ""),
                        "raw_signal": f"Job posting by {hit.get('author')}:\n{text[:800]}",
                    })
                time.sleep(0.3)
        except Exception as e:
            console.print(f"[yellow]Hiring thread error: {e}[/yellow]")

    console.print(f"[green]  Found {len(signals)} job posting signals[/green]")
    return signals
