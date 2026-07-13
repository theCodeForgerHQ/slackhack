"""Channel @-mentions. The manifest subscribes to app_mention; without this handler a
judge's @CornerCheck in a public channel got silence (whole-repo audit, wiring DISC-7).

Mentions get the SAME deterministic pipeline as the assistant pane: a clearance ask
renders the verdict card in the channel thread; a card ask renders the board; anything
else gets a pointer to the assistant pane (the freeform brain stays a DM surface).
Channel events carry no assistant action token, so the injury scan is simply not
attempted here (expected, not a failure).
"""

import contextlib
import logging

from slack_bolt import App, Say

from cornercheck.app.assistant import (
    FAIL_CLOSED_MESSAGE,
    _is_card_request,
    _is_clearance_request,
)
from cornercheck.app.blocks.card_board import build_card_board
from cornercheck.app.blocks.card_board import fallback_text as card_fallback
from cornercheck.app.blocks.disambiguation_card import build_disambiguation_card
from cornercheck.app.blocks.verdict_card import build_verdict_card, fallback_text
from cornercheck.app.context import strip_mentions
from cornercheck.app.parse import parse_card, parse_request
from cornercheck.brain.pipeline import clear_card, start_clearance

log = logging.getLogger("cornercheck.mentions")

_POINTER = (
    "I run clearance checks. Ask me right here, e.g. "
    "_@CornerCheck is Junior dos Santos cleared in Texas?_, or open my Assistant pane "
    "(click my name) for follow-ups, audit trails, and the live safety proof."
)


def _strip_mentions(text: str) -> str:
    return strip_mentions(text)


def register_mentions(app: App) -> None:
    @app.event("app_mention")
    def on_mention(event: dict, say: Say) -> None:
        text = _strip_mentions(event.get("text") or "")
        thread_ts = event.get("thread_ts") or event.get("ts", "")
        thread_key = f"mention:{event.get('channel', '')}:{thread_ts}"
        try:
            if _is_card_request(text):
                parsed = parse_card(text)
                verdicts = clear_card(
                    thread_key, parsed.fighters, parsed.on_date, parsed.target_jurisdiction
                )
                say(
                    blocks=build_card_board(verdicts, parsed.event, parsed.on_date),
                    text=card_fallback(verdicts),
                    thread_ts=thread_ts,
                )
                return
            if _is_clearance_request(text):
                parsed_req = parse_request(text)
                verdict = start_clearance(
                    thread_key,
                    parsed_req.fighter_query,
                    parsed_req.on_date,
                    parsed_req.target_jurisdiction,
                )
                if verdict.status == "NEEDS_DISAMBIGUATION":
                    say(
                        blocks=build_disambiguation_card(verdict),
                        text="Which fighter? CornerCheck won't guess.",
                        thread_ts=thread_ts,
                    )
                    return
                say(
                    blocks=build_verdict_card(verdict),
                    text=fallback_text(verdict),
                    thread_ts=thread_ts,
                )
                return
            say(text=_POINTER, thread_ts=thread_ts)
        except Exception:
            log.exception("app_mention handling failed for thread=%s", thread_key)
            # The fail-closed reply itself can fail (posting-restricted channel);
            # silence there must not crash the listener, only log.
            with contextlib.suppress(Exception):
                say(text=FAIL_CLOSED_MESSAGE, thread_ts=thread_ts)
