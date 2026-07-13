"""Evidence tools for Verdict.

Internal functions (return list[dict], used for parallel structured fetching):
  web_search, wikipedia_search, google_factcheck, slack_search

LangChain @tool wrappers (return str, used by debater agents via bind_tools/ToolNode):
  search_web, search_wikipedia, search_factcheckers, search_slack

EVIDENCE_TOOLS — the list passed to bind_tools() and ToolNode.
"""
import os
import re
import httpx
from tavily import TavilyClient
from slack_sdk import WebClient

_tv = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
_slack_user = WebClient(token=os.environ.get("SLACK_USER_TOKEN", ""))

_STOP = {"the", "a", "an", "is", "are", "was", "were", "our", "your", "my", "of",
         "to", "in", "on", "for", "and", "or", "that", "this", "it", "be", "by",
         "with", "at", "as", "do", "does", "from", "has", "have", "we", "you"}


def _key_terms(q: str) -> str:
    """Drop stopwords and numbers so a claim's nouns match Slack content
    (e.g. 'our refund window is 90 days' -> 'refund window days')."""
    words = [w for w in re.findall(r"[a-zA-Z]+", q.lower())
             if w not in _STOP and len(w) > 2]
    return " ".join(words) or q


def web_search(query: str, max_results: int = 4) -> list[dict]:
    """Return [{title, url, content}] from the public web.

    Combines a high-quality general search with a recent-news search (last 30 days)
    so time-sensitive claims get fresh evidence. Published dates are prepended to
    content so the model can prefer the latest reliable sources.
    """
    results, seen = [], set()

    def _add(items: list[dict]) -> None:
        for x in items:
            url = x.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)
            date = x.get("published_date") or ""
            content = x.get("content", "")
            if date:
                content = f"(published {date}) {content}"
            results.append({"title": x.get("title", ""), "url": url, "content": content})

    try:  # high-quality general results
        r = _tv.search(query=query, max_results=max_results, search_depth="advanced")
        _add(r.get("results", []))
    except Exception:
        pass
    try:  # fresh news from the last 30 days (dated)
        r = _tv.search(query=query, max_results=3, topic="news", days=30)
        _add(r.get("results", []))
    except Exception:
        pass

    return results[: max_results + 3]


def wikipedia_search(query: str, max_results: int = 2) -> list[dict]:
    """Return [{title, url, content}] from Wikipedia — reliable factual baseline."""
    try:
        resp = httpx.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "list": "search", "srsearch": query,
                    "srlimit": max_results, "utf8": 1, "format": "json"},
            timeout=10,
        )
        out = []
        for item in resp.json().get("query", {}).get("search", []):
            title = item.get("title", "")
            snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
            url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
            if snippet:
                out.append({"title": f"Wikipedia: {title}", "url": url, "content": snippet})
        return out
    except Exception:
        return []


def google_factcheck(claim: str, max_results: int = 3) -> list[dict]:
    """Query Google's Fact Check API — surfaces human-published verifications from
    Snopes, PolitiFact, AFP, Reuters, and 100+ fact-checking orgs. Free with an API key."""
    key = os.environ.get("GOOGLE_FACTCHECK_API_KEY", "")
    if not key:
        return []
    try:
        resp = httpx.get(
            "https://factchecktools.googleapis.com/v1alpha1/claims:search",
            params={"query": claim, "key": key, "pageSize": max_results},
            timeout=10,
        )
        out = []
        for item in resp.json().get("claims", []):
            for review in item.get("claimReview", []):
                publisher = review.get("publisher", {}).get("name", "?")
                rating = review.get("textualRating", "unrated")
                url = review.get("url", "")
                if not url:
                    continue
                content = (f"Claim: \"{item.get('text', '')}\" | "
                           f"Publisher: {publisher} | Rating: {rating}")
                out.append({
                    "title": f"[{publisher} Fact Check] {rating}",
                    "url": url,
                    "content": content,
                })
                if len(out) >= max_results:
                    return out
        return out
    except Exception:
        return []


def slack_search(query: str, max_results: int = 3) -> list[dict]:
    """Return [{title, url, content}] from THIS workspace's messages, or [].

    Uses Slack's Real-Time Search API (assistant.search.context) with the user token.
    Skips Verdict's own prior posts so it never cites itself.
    """
    if not os.environ.get("SLACK_USER_TOKEN"):
        return []
    try:
        resp = _slack_user.api_call("assistant.search.context",
                                    json={"query": _key_terms(query)})
        if not resp.get("ok"):
            return []
        out = []
        for m in resp.get("results", {}).get("messages", []):
            if m.get("is_author_bot"):
                continue  # don't cite Verdict's own past verdicts
            out.append({
                "title": f"{m.get('author_name', '?')} in #{m.get('channel_name', '?')}",
                "url": m.get("permalink", ""),
                "content": m.get("content", ""),
            })
            if len(out) >= max_results:
                break
        return out
    except Exception:
        return []


# ---------------------------------------------------------------------------
# LangChain @tool wrappers — used by debater agents via bind_tools / ToolNode
# ---------------------------------------------------------------------------
from langchain_core.tools import tool


def _fmt(results: list[dict], tag: str) -> str:
    if not results:
        return f"No {tag} results found."
    return "\n\n".join(
        f"[{tag}] {r['title']} ({r['url']})\n{r['content'][:450]}"
        for r in results
    )


@tool
def search_web(query: str) -> str:
    """Search the live web and recent news. Use for current events, specific facts, recent claims."""
    return _fmt(web_search(query, max_results=4), "WEB")


@tool
def search_wikipedia(query: str) -> str:
    """Search Wikipedia for encyclopedic facts about people, places, science, and history."""
    return _fmt(wikipedia_search(query, max_results=2), "WIKI")


@tool
def search_factcheckers(claim: str) -> str:
    """Search professional fact-checkers (Snopes, PolitiFact, AFP, Reuters). Best for myths and political claims."""
    return _fmt(google_factcheck(claim, max_results=3), "FACTCHECK")


@tool
def search_slack(query: str) -> str:
    """Search this Slack workspace's messages for internal context or contradictions with team policies."""
    return _fmt(slack_search(query, max_results=3), "SLACK")


EVIDENCE_TOOLS = [search_web, search_wikipedia, search_factcheckers, search_slack]
