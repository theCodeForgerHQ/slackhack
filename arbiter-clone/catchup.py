"""Catch-up — when you return from being away, Arbiter briefs you on what you
missed, assembled from things it already knows:

  - your direct @mentions while you were gone (RTS, author != you)
  - decisions that formed in your watched channels (from the audit trail)
  - anything the away-delegate answered ON YOUR BEHALF while you were out
  - false claims Arbiter flagged, so you don't re-read them as true

Each line is actionable and the digest ends with 👍/👎 — that feedback is
logged and feeds the same preference signal that tunes intervention
thresholds in learning.py (see `record_digest_feedback`).

Triggered by `@Arbiter catchup`, or automatically DM'd on presence
away -> active when a channel is watched.
"""
import time
import datetime as _dt

from tools import slack_search
import audit
import feedback
from arblog import get_logger

log = get_logger(__name__)


def build_digest(user_name: str, user_id: str, since_ts: float,
                 max_items: int = 8) -> list[dict]:
    """Assemble a 'what you missed' digest. Returns Block Kit blocks (or [] if
    genuinely nothing to report)."""
    since_h = max(1, int((time.time() - since_ts) / 3600))
    lines_mentions, lines_agent = [], []

    # 1. Your @mentions while away (RTS, exclude your own messages)
    try:
        for m in slack_search(f"<@{user_id}>", 8):
            author = (m.get("title") or "").split(" in #")[0].strip()
            if author.lower() == (user_name or "").lower():
                continue
            lines_mentions.append(
                f"• *{author}* in {('#' + m.get('title','').split(' in #')[-1]) if ' in #' in m.get('title','') else 'a channel'}: "
                f"“{(m.get('content') or '')[:120]}”"
                + (f" (<{m['url']}|open>)" if m.get("url") else ""))
    except Exception as e:
        log.warning(f"catchup mentions search failed: {e}")

    # 2. Agent interventions since you left (from the audit trail)
    delegated, decisions, flags = [], [], []
    for r in audit._recent(60):
        if r.get("ts", 0) < since_ts:
            continue
        mode, trig, summ = r.get("mode"), r.get("trigger", ""), str(r.get("summary", ""))[:90]
        if mode == "delegate" and "away" in trig and user_name.lower() in summ.lower():
            delegated.append(f"• I answered on your behalf: “{summ}”")
        elif mode == "decision":
            decisions.append(f"• A decision formed: *{summ}*")
        elif mode == "claim" and "false" in str(r.get("action", "")).lower():
            flags.append(f"• I flagged a false claim: “{summ}”")

    if not (lines_mentions or delegated or decisions or flags):
        return []

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "emoji": True,
         "text": f"👋 Welcome back — here's the last {since_h}h"}},
    ]

    def _section(title, items):
        if items:
            blocks.append({"type": "section", "text": {"type": "mrkdwn",
                "text": f"*{title}*\n" + "\n".join(items[:max_items])}})

    _section("You were mentioned", lines_mentions)
    _section("Handled for you while away", delegated)
    _section("Decisions that formed", decisions)
    _section("Claims I flagged (don't re-read as true)", flags)

    # 3. Feedback footer — the signal that tunes what's worth surfacing
    _fb_up = f'{{"kind":"catchup","vote":"up","user":"{user_id}"}}'
    _fb_down = f'{{"kind":"catchup","vote":"down","user":"{user_id}"}}'
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
        "text": "Was this digest useful? Your 👍/👎 tunes what I surface next time."}]})
    blocks.append({"type": "actions", "elements": [
        {"type": "button", "text": {"type": "plain_text", "text": "👍 Useful"},
         "action_id": "catchup_up", "value": _fb_up},
        {"type": "button", "text": {"type": "plain_text", "text": "👎 Too much"},
         "action_id": "catchup_down", "value": _fb_down}]})
    return blocks


def record_digest_feedback(user_id: str, vote: str) -> None:
    """Feedback on digest usefulness — feeds the same store that tunes behavior."""
    try:
        feedback.log_feedback(f"catchup:{user_id}", "digest", vote)
    except Exception:
        pass
