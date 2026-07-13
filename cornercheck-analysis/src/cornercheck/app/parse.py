"""Deterministic parse of a clearance request: fighter name, date, target jurisdiction.

Imperfect extraction is SAFE: the ER banding fails closed, so a rough name lands in the
disambiguation card rather than a wrong clearance. This keeps the core demo path free of
any LLM dependency (floor under flex)."""

import re
from dataclasses import dataclass
from datetime import date

# keyword -> clean jurisdiction token (rule engine does substring matching)
_JURISDICTIONS = {
    "texas": "Texas",
    "tdlr": "Texas",
    "nevada": "Nevada",
    "nsac": "Nevada",
    "vegas": "Nevada",
    "california": "California",
    "csac": "California",
    "new york": "New York",
    "nysac": "New York",
    "maryland": "Maryland",
    "new jersey": "New Jersey",
    "germany": "Germany",
}

_STOPWORDS = {
    "is",
    "are",
    "can",
    "could",
    "should",
    "will",
    "would",
    "does",
    "do",
    "clear",
    "cleared",
    "clearance",
    "check",
    "whether",
    "if",
    "the",
    "a",
    "an",
    "for",
    "on",
    "in",
    "to",
    "compete",
    "competing",
    "fight",
    "fighting",
    "fighter",
    "spar",
    "sparring",
    "bout",
    "card",
    "this",
    "that",
    "weekend",
    "week",
    "today",
    "tonight",
    "tomorrow",
    "saturday",
    "sunday",
    "friday",
    "ready",
    "safe",
    "his",
    "her",
    "show",
    "me",
    "about",
    "any",
    "and",
    "good",
    "go",
    "okay",
    "ok",
    "now",
    "us",
    "we",
}

_DAYS = "monday|tuesday|wednesday|thursday|friday|saturday|sunday"


@dataclass(frozen=True)
class ParsedRequest:
    fighter_query: str
    on_date: date | None
    target_jurisdiction: str | None


def parse_request(text: str, today: date | None = None) -> ParsedRequest:
    raw = text.strip()
    target = _find_jurisdiction(raw)
    on_date = _find_date(raw)

    cleaned = raw.lower()
    # strip an "in/for/at <jurisdiction>" phrase wherever it appears (not anchored)
    for kw in _JURISDICTIONS:
        cleaned = re.sub(rf"\b(in|for|at)\s+{re.escape(kw)}\b", " ", cleaned)
        cleaned = cleaned.replace(kw, " ")
    cleaned = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", cleaned)
    cleaned = re.sub(rf"\b({_DAYS})('s)?\b", " ", cleaned)
    cleaned = re.sub(r"[^\w\s'.-]", " ", cleaned)

    tokens = [t for t in cleaned.split() if t not in _STOPWORDS and not t.isdigit()]
    # rebuild from the ORIGINAL casing where possible (names look right in the card)
    fighter_query = _restore_casing(raw, tokens)
    return ParsedRequest(fighter_query=fighter_query, on_date=on_date, target_jurisdiction=target)


@dataclass(frozen=True)
class ParsedCard:
    fighters: list[str]
    on_date: date | None
    target_jurisdiction: str | None
    event: str | None


_VS = re.compile(r"\s+(?:vs\.?|v\.?|versus)\s+", re.IGNORECASE)


_LEADING_FRAMING = re.compile(
    r"^((?:check|clear|cleared|clearance|please|the|whole|entire|review|all|is|are|can"
    r"|could|will|would|my|these|this|card|lineup|line-up|slate|event|bouts?|fights?"
    r"|fighters?)\s+)+",
    re.IGNORECASE,
)


def parse_card(text: str) -> ParsedCard:
    """Extract every fighter slot from a card lineup ('A vs B, C vs D'). Every slot becomes a
    row, with NO dedup: two distinct fighters who share a display name (two real Bruno Silvas)
    must each be checked, and each fails closed to NEEDS PICK. Bouts split on comma/newline
    only (never the word 'and', which lives inside names like 'Anderson Silva'). Names are not
    keyword-stripped mid-name, so 'California Kid' survives intact."""
    raw = text.strip()
    target = _find_jurisdiction(raw)
    on_date = _find_date(raw)

    event: str | None = None
    body = raw
    m = re.match(r"\s*([A-Za-z][\w .'#-]{1,38}?)\s*:\s*(.+)", raw, re.DOTALL)
    if m:
        label, rest = m.group(1).strip(), m.group(2)
        looks_like_bouts = bool(_VS.search(rest)) or rest.count(",") >= 1
        if re.search(
            r"\b(card|lineup|line-up|slate|event|check|clear|bouts?|fights?)\b", label, re.I
        ):
            body = rest  # a framing prefix like "check this card:"
        elif looks_like_bouts and not _find_jurisdiction(label):
            event, body = label, rest  # an event label like "UFC 310:"
        elif looks_like_bouts:
            body = rest  # a jurisdiction-y prefix; drop it, no event

    # strip a TRAILING locative jurisdiction phrase ('... in Texas'), never mid-name
    for kw in _JURISDICTIONS:
        body = re.sub(rf"\b(in|for|at)\s+{re.escape(kw)}\b\s*$", " ", body, flags=re.IGNORECASE)
    body = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", body)

    fighters: list[str] = []
    for bout in re.split(r"[,\n;]", body):
        for side in _VS.split(bout):
            name = _clean_card_side(side)
            if len(name) >= 2:  # keep short legit names ('AJ'); only pure-empty sides drop out
                fighters.append(name)
    return ParsedCard(fighters=fighters, on_date=on_date, target_jurisdiction=target, event=event)


def _clean_card_side(side: str) -> str:
    """Clean a single bout side to a fighter name, never keyword-stripping mid-name:
    strip surrounding punctuation and a run of leading framing words only."""
    s = side.strip().strip("\"'()[]").strip()
    s = _LEADING_FRAMING.sub("", s)
    s = re.sub(r"[^\w\s'.-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _find_jurisdiction(text: str) -> str | None:
    low = text.lower()
    for kw, canon in _JURISDICTIONS.items():
        if re.search(rf"\b{re.escape(kw)}\b", low):
            return canon
    return None


def _find_date(text: str) -> date | None:
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def _restore_casing(raw: str, lowered_tokens: list[str]) -> str:
    wanted = set(lowered_tokens)
    out = [w for w in re.findall(r"[\w'.-]+", raw) if w.lower() in wanted]
    return " ".join(out).strip()
