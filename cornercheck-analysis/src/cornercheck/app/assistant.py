"""Assistant handlers: the clearance UX.

Core path is fully deterministic (parse -> pipeline -> card), so the demo's main beats
never depend on the LLM (floor). Free-form questions route to the agentic brain (flex).
Streamed thinking steps show the Retrieve -> Disambiguate -> Clear pipeline live.
"""

import logging
import re

from slack_bolt import Assistant, BoltContext, Say, SetStatus, SetSuggestedPrompts
from slack_sdk import WebClient

from cornercheck.app.blocks.card_board import build_card_board
from cornercheck.app.blocks.card_board import fallback_text as card_fallback
from cornercheck.app.blocks.disambiguation_card import build_disambiguation_card
from cornercheck.app.blocks.verdict_card import build_verdict_card, fallback_text
from cornercheck.app.context import action_token, strip_mentions
from cornercheck.app.parse import parse_card, parse_request
from cornercheck.brain.agent import BrainEvent, BrainTimeoutError, get_brain
from cornercheck.brain.pipeline import clear_card, start_clearance
from cornercheck.search.rts import InjuryScanResult, injury_scan, spotlight

log = logging.getLogger("cornercheck.assistant")

assistant = Assistant()

# A thrown error on the clearance path must surface as an explicit NON-clearance.
FAIL_CLOSED_MESSAGE = (
    ":rotating_light: *CornerCheck could not complete this check.* Treat this as NOT cleared"
    " until it resolves; do not read this as a clearance. Please retry, and if it persists the"
    " clearance service or audit ledger may be down."
)

# WHOLE-WORD meta keywords route to the agentic brain (substring matching would misroute
# real clearance questions, e.g. "how" inside "Howard"). Review finding F1.
_FREEFORM_WORDS = frozenset(
    {
        "audit",
        "chain",
        "ledger",
        "verify",
        "trail",
        "history",
        "why",
        "scan",
        "explain",
        "what",
        "how",
        "list",
        "status",
        "recent",
        "entries",
        "intact",
    }
)
_CUE_WORDS = frozenset(
    {"clear", "cleared", "clearance", "compete", "book", "spar", "fight", "ready", "safe"}
)


def _is_clearance_request(text: str) -> bool:
    """Route to the deterministic clearance card when there is a clearance cue + an
    extractable fighter and no explicit meta/free-form intent. Whole-word matching only."""
    low = text.lower()
    tokens = set(re.findall(r"[a-z']+", low))
    if tokens & _FREEFORM_WORDS or "tell me" in low:
        return False
    has_cue = bool(tokens & _CUE_WORDS) or "good to go" in low
    if not has_cue:
        return False
    return len(parse_request(text).fighter_query) >= 3


_CARD_WORDS = ("card", "lineup", "line-up", "slate", "event", "matchups")


def _is_card_request(text: str) -> bool:
    """A whole-card check: either 2+ matchups, or an explicit card keyword, with >= 2 fighters.
    A single-subject question with one 'vs' ('Is X good to fight vs Y?') is NOT a card; it
    routes to the single-clearance path so the subject is not mangled onto a board."""
    low = text.lower()
    vs_count = len(re.findall(r"\bvs\.?\b|\bversus\b", low))
    has_card_word = any(w in low for w in _CARD_WORDS)
    if not (vs_count >= 2 or has_card_word):
        return False
    return len(parse_card(text).fighters) >= 2


def _action_token(body: dict) -> str | None:
    return action_token(body)


@assistant.thread_started
def on_thread_started(say: Say, set_suggested_prompts: SetSuggestedPrompts) -> None:
    say(
        "I'm CornerCheck. Ask me whether a fighter is cleared to compete and I'll check "
        "cross-jurisdiction suspensions, return windows, and your team's own injury chatter. "
        "I refuse to clear when I can't be sure who the fighter is."
    )
    set_suggested_prompts(
        prompts=[
            {"title": "Check a fighter", "message": "Is Junior dos Santos cleared in Texas?"},
            {
                "title": "Check a whole card",
                "message": (
                    "Check this card in Texas: Junior dos Santos vs Curtis Blaydes, "
                    "Bruno Silva vs Brad Tavares"
                ),
            },
            {"title": "Ambiguous name", "message": "Is Bruno Silva cleared to fight?"},
            {"title": "Famous case", "message": "Is Jon Jones cleared to fight in California?"},
        ]
    )


@assistant.user_message
def on_user_message(
    payload: dict,
    body: dict,
    say: Say,
    set_status: SetStatus,
    client: WebClient,
    context: BoltContext,
) -> None:
    # Mention tokens are stripped HERE too, not just in the channel handler: typing
    # "@CornerCheck is X cleared?" inside the assistant pane otherwise pollutes the
    # fighter query with the raw user-id token (caught live).
    text = strip_mentions(payload.get("text") or "")
    thread_key = f"{payload.get('channel', '')}:{payload.get('thread_ts', payload.get('ts', ''))}"
    if _is_card_request(text):
        _handle_card(thread_key, text, say, set_status)
        return
    if not _is_clearance_request(text):
        _handle_freeform(thread_key, text, body, say, set_status, client)
        return
    _handle_clearance(thread_key, text, body, say, set_status, client)


def _handle_card(thread_key: str, text: str, say: Say, set_status: SetStatus) -> None:
    """Whole-card review: every bout banded on one board, fail-closed per fighter."""
    set_status("checking the whole card...")
    parsed = parse_card(text)
    if len(parsed.fighters) < 2:
        say("I couldn't read a fight card. Try: _Check this card: A vs B, C vs D_")
        return
    say(f":checkered_flag: Checking *{len(parsed.fighters)} fighters*...")
    try:
        verdicts = clear_card(
            thread_key, parsed.fighters, parsed.on_date, parsed.target_jurisdiction
        )
        say(
            blocks=build_card_board(verdicts, parsed.event, parsed.on_date),
            text=card_fallback(verdicts),
        )
    except Exception:
        log.exception("card pipeline failed for thread=%s", thread_key)
        say(FAIL_CLOSED_MESSAGE)


def _handle_clearance(
    thread_key: str, text: str, body: dict, say: Say, set_status: SetStatus, client: WebClient
) -> None:
    set_status("resolving fighter identity...")
    parsed = parse_request(text)
    if not parsed.fighter_query:
        say("I couldn't pick out a fighter name. Try: _Is Junior dos Santos cleared in Texas?_")
        return

    say(f":mag: Resolving *{parsed.fighter_query}*...")
    # Bolt's default error handler only LOGS; on any pipeline/DB/ledger failure we must post
    # an explicit fail-closed reply, never leave the user hanging on "Resolving..." (finding).
    try:
        verdict = start_clearance(
            thread_key, parsed.fighter_query, parsed.on_date, parsed.target_jurisdiction
        )
        if verdict.status == "NEEDS_DISAMBIGUATION":
            say(
                blocks=build_disambiguation_card(verdict),
                text="Which fighter? CornerCheck won't guess.",
            )
            return
        if verdict.status == "NOT_FOUND":
            say(blocks=build_verdict_card(verdict), text=fallback_text(verdict))
            return

        set_status("checking suspensions and scanning your Slack...")
        scan = InjuryScanResult()
        if verdict.fighter_name:
            scan = injury_scan(client, _action_token(body), verdict.fighter_name)
        say(
            blocks=build_verdict_card(verdict, injury_hits=scan.hits, injury_scan_ok=scan.ok),
            text=fallback_text(verdict),
        )
    except Exception:
        log.exception(
            "clearance pipeline failed for query=%r thread=%s", parsed.fighter_query, thread_key
        )
        say(FAIL_CLOSED_MESSAGE)


def _handle_freeform(
    thread_key: str, text: str, body: dict, say: Say, set_status: SetStatus, client: WebClient
) -> None:
    set_status("thinking...")

    def on_event(e: BrainEvent) -> None:
        # A status-update hiccup (expired surface, rate limit) must never abort the
        # model's response mid-stream: that would poison the shared brain stream.
        try:
            if e.kind == "tool_use":
                set_status(f"using {e.tool_name.split('__')[-1]}...")
        except Exception:
            log.debug("set_status failed mid-response; continuing without status updates")

    try:
        prompt = text
        # Best-effort injury context, spotlighted as untrusted data (inside the try so a
        # surprise here still yields the friendly fallback, not a silent drop).
        tok = _action_token(body)
        if tok:
            parsed = parse_request(text)
            if parsed.fighter_query:
                scan = injury_scan(client, tok, parsed.fighter_query)
                ctx = spotlight(scan.hits)
                if ctx:
                    prompt = f"{text}\n\nWorkspace context (untrusted):\n{ctx}"
                elif not scan.ok:
                    # Without this the model confidently narrates "no injury chatter
                    # found" when the scan actually failed.
                    prompt = f"{text}\n\n(Note: the workspace injury scan is unavailable.)"
        answer = get_brain().ask(thread_key, prompt, on_event)
        say(answer or "I don't have an answer for that.")
    except BrainTimeoutError:
        say(
            "That took too long to reason through. Try a direct clearance check, e.g. "
            "_Is Junior dos Santos cleared in Texas?_"
        )
    except Exception:
        log.exception("freeform brain call failed")
        say(
            "Something went wrong reasoning through that. The clearance check still works: "
            "ask _Is <fighter> cleared in <state>?_"
        )
