"""Slack payload helpers shared across handler modules."""

import re

_MENTION_RE = re.compile(r"<[@!][^>]+>")


def strip_mentions(text: str) -> str:
    """Remove <@U...>, <@U...|name>, and <!here>-style tokens. Needed in the assistant
    pane too: a user typing '@CornerCheck is Jon Jones cleared?' there otherwise sends
    the raw user-id token into the fighter query ('U0B8F1V1KSB Jon Jones' -> NO MATCH,
    caught live by Stephen)."""
    return _MENTION_RE.sub(" ", text).strip()


def action_token(body: dict) -> str | None:
    """The ephemeral Real-Time Search action token, wherever this payload shape
    carries it: assistant message events, assistant-thread interactivity payloads, or
    message metadata. One helper instead of the two divergent copies the audit found."""
    return (
        body.get("event", {}).get("assistant_thread", {}).get("action_token")
        or body.get("assistant", {}).get("thread", {}).get("action_token")
        or body.get("message", {}).get("metadata", {}).get("event_payload", {}).get("action_token")
    )
