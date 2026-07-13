"""Arbiter's coordinator — decides WHICH judgment a message needs, and enforces
the one-intervention rule so five modes never pile onto one message.

Cascade (cheapest first — most messages exit at step 1 for free):
  1. Heuristics   — length, question marks, decision phrases, filler density.
                    No LLM call. Kills ~90% of traffic.
  2. Fast model   — single small-model call classifies the survivors.
  3. Mode pipeline — only the winning mode's full pipeline runs.

Arbitration priority (highest wins, one intervention max):
  decision > substance > claim

Modes:
  claim     — a checkable factual statement        → fact-check pipeline (llm.py)
  substance — long/padded content needing a receipt → substance.py
  decision  — a decision forming in the thread      → decisions.py
"""
import os
import re
import json

# Reuse the provider plumbing from llm.py (same fast model as the router)
from llm import _chat, _parse, ROUTER

# ---------------------------------------------------------------------------
# Tunables (env-overridable so demo channels can be made more/less sensitive)
# ---------------------------------------------------------------------------
SUBSTANCE_MIN_WORDS = int(os.environ.get("ARBITER_SUBSTANCE_MIN_WORDS", "75"))
CLAIM_MIN_CHARS     = int(os.environ.get("ARBITER_CLAIM_MIN_CHARS", "15"))

# Decision-forming language — cheap pre-filter before the model confirms
_DECISION_PHRASES = (
    "we'll go with", "we will go with", "let's go with", "lets go with",
    "decided:", "decision:", "we decided", "we've decided", "final call",
    "let's just do", "lets just do", "we're going with", "we are going with",
    "shipping it", "let's ship", "lets ship", "approved,", "approved.",
    "approved:", "approve the", "let's kill", "lets kill", "we should just remove",
    "we're removing", "we are removing", "we're deprecating", "we are deprecating",
    "let's deprecate", "moving forward with", "going ahead with", "signing off on",
    "let's lock", "lets lock", "locking in", "that's final", "thats final",
    "that's the plan", "we're moving", "we are moving", "we're pushing",
    "moving the", "pushing the", "bringing forward", "we'll cancel",
    "we're cancelling", "we're canceling", "let's cancel", "final:", "call it",
    # natural decision phrasings (router-benchmark-driven)
    "i'm calling it", "i am calling it", "calling it:", "decision made",
    "i've decided", "i have decided", "we've made the call", "made the call",
    "we're sunsetting", "we are sunsetting", "going to sunset", "to sunset the",
    "we're consolidating", "we are consolidating", "going forward we",
    "we're freezing", "we are freezing", "we're cutting", "we are cutting",
    "we're pausing", "we are pausing", "we're dropping", "we are dropping",
    "dropping support", "that settles it", "settles it", "we'll outsource",
    "we will outsource", "we're outsourcing", "we are outsourcing",
    "we're reallocating", "that's the call", "thats the call",
)

# Hedge/filler phrases — a *signal* of padded content (full scoring in substance.py)
FILLER_PHRASES = (
    "in today's fast-paced", "it's important to note", "it is important to note",
    "at the end of the day", "leverage synergies", "circle back", "touch base",
    "moving the needle", "low-hanging fruit", "paradigm shift", "best-in-class",
    "cutting-edge", "state-of-the-art", "seamlessly integrate", "robust solution",
    "holistic approach", "deep dive", "unlock the potential", "game-changer",
    "in conclusion", "to summarize", "as we all know", "needless to say",
    "it goes without saying", "in the ever-evolving", "landscape of",
    "plays a crucial role", "plays a vital role", "a testament to",
    "delve into", "navigate the complexities", "foster a culture",
    "actionable insights", "key takeaways", "moving forward",
    "synergy", "alignment across", "stakeholder buy-in",
)

_CLASSIFIER_SYSTEM = (
    "You classify a Slack message for a judgment agent. Respond ONLY with JSON:\n"
    '"decision" (boolean: true if the message is FORMING or ANNOUNCING a team decision '
    "— choosing an option, approving, killing/deprecating something, committing to a plan),\n"
    '"claim" (boolean: true if it contains a checkable factual statement about the world '
    "or the team's work; false for pure opinions, questions, chit-chat),\n"
    '"long_form" (boolean: true if the message is long-form prose — an update, memo, '
    "doc, announcement, status report — REGARDLESS of how good or empty it is; "
    "false for normal conversational chat),\n"
    '"confidence" (0-100 int: your confidence in the strongest label you set).'
)


def _word_count(text: str) -> int:
    return len(re.findall(r"[\w'-]+", text))


def filler_hits(text: str) -> list[str]:
    """Filler phrases present in the text (case-insensitive)."""
    low = text.lower()
    return [p for p in FILLER_PHRASES if p in low]


def _heuristics(text: str) -> dict:
    """Free pre-filter. Returns which modes are even *possible* for this message."""
    words = _word_count(text)
    low = text.lower()
    return {
        "maybe_decision":  any(p in low for p in _DECISION_PHRASES),
        "maybe_substance": words >= SUBSTANCE_MIN_WORDS,
        "maybe_claim":     len(text) >= CLAIM_MIN_CHARS and not text.rstrip().endswith("?"),
        "words":           words,
    }


def classify(text: str) -> dict:
    """Classify a message into judgment modes.

    Returns {"mode": "decision"|"substance"|"claim"|None,
             "confidence": int, "heuristics": dict}.
    Only calls the model when a heuristic gate opens.
    """
    h = _heuristics(text)
    if not (h["maybe_decision"] or h["maybe_substance"] or h["maybe_claim"]):
        return {"mode": None, "confidence": 100, "heuristics": h}

    # temperature=0: the same message must classify the same way every time.
    try:
        d = _parse(_chat(ROUTER[0], ROUTER[1], _CLASSIFIER_SYSTEM,
                         f"MESSAGE:\n{text[:4000]}", temperature=0))
    except Exception:
        d = {}

    # The fast classifier decides "is this a decision" — a keyword list can't
    # generalize to messy real phrasings ("ship it", "done deal", "we've settled
    # on X"), so we trust the model. The phrase heuristic still opens the gate
    # cheaply; it just no longer GATES the verdict.
    is_decision  = bool(d.get("decision"))
    # "Long-form" is a fact about length, not a judgment — the word-count
    # heuristic is authoritative. The model only arbitrates decision vs claim.
    is_substance = h["maybe_substance"] and not is_decision
    is_claim     = bool(d.get("claim")) and h["maybe_claim"]
    conf         = int(d.get("confidence", 0) or 0)

    # Arbitration: one mode wins. A decision forming outranks everything;
    # a long doc gets a receipt (its claims are checked *inside* the receipt);
    # a short checkable claim gets the classic fact-check.
    if is_decision:
        mode = "decision"
    elif is_substance:
        mode = "substance"
    elif is_claim:
        mode = "claim"
    else:
        mode = None

    return {"mode": mode, "confidence": conf, "heuristics": h}


# ---------------------------------------------------------------------------
# Mention-command parsing (explicit user asks bypass the classifier entirely)
# ---------------------------------------------------------------------------
# No-arg commands match EXACTLY (else claims like "watch out, rates rose" misroute);
# arg-taking commands (substance/quorum) also match as a prefix.
_EXACT_COMMANDS = {
    "stats":    ("stats", "feedback", "verdict stats", "arbiter stats"),
    "watch":    ("watch", "monitor", "watch this channel"),
    "unwatch":  ("unwatch", "stop monitoring", "stop watching"),
    "audit":    ("audit", "transparency", "audit report", "audit canvas"),
    "ledger":   ("ledger", "predictions", "who said it first", "track record"),
}
_PREFIX_COMMANDS = {
    # primary command is "voices"; "quorum" kept as a silent legacy alias
    "voices":    ("voices", "quorum", "missing voices", "who's missing", "whos missing"),
    "substance": ("substance", "score this", "slop check", "slopcheck", "workslop"),
    "ask":       ("ask",),
    "roundtable": ("act as", "actas", "roundtable", "debate as", "act like",
                   "panel of", "convene"),
    # catchup is prefix-matched so natural phrasings work ("catch me up on X")
    "catchup":   ("catchup", "catch up", "what did i miss", "what i missed",
                  "what'd i miss", "whatd i miss", "catch me up", "fill me in"),
}


def parse_command(text: str) -> str | None:
    """Match an explicit @Arbiter subcommand; None means 'judge the text'."""
    t = (text or "").strip().lower().rstrip(".!?…")
    for cmd, aliases in _EXACT_COMMANDS.items():
        if t in aliases:
            return cmd
    for cmd, aliases in _PREFIX_COMMANDS.items():
        if t in aliases or any(t.startswith(a + " ") for a in aliases):
            return cmd
    return None
