"""Real-Time Search injury scan.

Runs in the Bolt process: the ephemeral action_token (from
body.event.assistant_thread.action_token, verified spike B) is passed straight to the
Slack API and NEVER enters LLM-visible space. Degrades gracefully, and VISIBLY: a
failed scan returns ok=False so the verdict card can say the check was unavailable
instead of letting "search broke" read as "no injury chatter found".
"""

import logging
from dataclasses import dataclass, field

from slack_sdk import WebClient

from cornercheck.search.lexicon import mentions_injury

log = logging.getLogger("cornercheck.rts")


@dataclass(frozen=True)
class InjuryHit:
    permalink: str
    channel_id: str
    message_ts: str
    snippet: str
    author: str


@dataclass(frozen=True)
class InjuryScanResult:
    """ok=False means an ATTEMPTED scan failed (API error or response-shape drift) and
    the card should say so. No action token (a surface that cannot scan) is ok=True
    with no hits: expected, not a failure."""

    hits: list[InjuryHit] = field(default_factory=list)
    ok: bool = True


def _last_name(full_name: str) -> str:
    parts = full_name.split()
    return parts[-1] if parts else full_name


def injury_scan(
    client: WebClient, action_token: str | None, fighter_full_name: str, limit: int = 10
) -> InjuryScanResult:
    """Keyword-search the workspace for the fighter's name, keep only injury-mentioning
    messages, resolve permalinks. Never raises: an attempted-but-failed scan returns
    ok=False (the parse runs inside the try; a malformed response element must not
    crash an already-computed verdict)."""
    if not action_token:
        return InjuryScanResult()
    last = _last_name(fighter_full_name)
    try:
        result = client.api_call(
            "assistant.search.context",
            json={
                "query": last,
                "action_token": action_token,
                "content_types": ["messages"],
                "limit": limit,
            },
        )
        data = result.data if isinstance(result.data, dict) else {}
        results = data.get("results")
        if not isinstance(results, dict) or "messages" not in results:
            # Shape drift is not an exception: without this check a renamed response
            # field silently kills the feature forever.
            log.warning("RTS response missing results.messages; scan marked unavailable")
            return InjuryScanResult(ok=False)
        hits: list[InjuryHit] = []
        for m in results["messages"] or []:
            if not isinstance(m, dict):
                continue
            content = m.get("content") or ""
            if not mentions_injury(content):
                continue
            channel_id = m.get("channel_id", "")
            ts = m.get("message_ts", "")
            permalink = _permalink(client, channel_id, ts)
            hits.append(
                InjuryHit(
                    permalink=permalink,
                    channel_id=channel_id,
                    message_ts=ts,
                    snippet=content[:180],
                    author=m.get("author_name", "unknown"),
                )
            )
        return InjuryScanResult(hits=hits)
    except Exception as exc:
        # warning, not info: a persistent RTS outage would otherwise be invisible in prod.
        log.warning("RTS injury_scan failed (non-fatal, marked unavailable): %s", exc)
        return InjuryScanResult(ok=False)


def _permalink(client: WebClient, channel_id: str, ts: str) -> str:
    try:
        resp = client.chat_getPermalink(channel=channel_id, message_ts=ts)
        return str(resp.get("permalink", ""))
    except Exception as exc:
        # A systematic permission failure here must not be invisible.
        log.warning("chat.getPermalink failed for %s/%s: %s", channel_id, ts, exc)
        return ""


def _defang(text: str) -> str:
    """Neutralize angle brackets so untrusted content cannot forge the closing delimiter
    and escape the spotlight envelope (review finding F2). Replaces ASCII < > with the
    single-pointing-angle look-alikes U+2039 / U+203A."""
    return text.replace("<", "‹").replace(">", "›")


def spotlight(hits: list[InjuryHit]) -> str:
    """Wrap untrusted workspace text for safe inclusion in an LLM prompt (report 17).
    The model is instructed to treat anything in this block as DATA, never instructions."""
    if not hits:
        return ""
    lines = "\n".join(f"- [{_defang(h.author)}] {_defang(h.snippet)}" for h in hits)
    return f"<untrusted-slack-content>\n{lines}\n</untrusted-slack-content>"
