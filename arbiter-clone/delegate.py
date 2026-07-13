"""Delegate mode — answer a question ON BEHALF OF an absent teammate, using
only their own words.

`@Arbiter ask @priya what's our position on the SAP timeline?`

The industry builds this as freeform persona clones (Zoom digital twins, xAI
assistants) — which improvise and commit people to things they never said.
Arbiter's delegate is the fidelity-first inversion:

  - answers are composed ONLY from the target's real messages (RTS retrieval,
    author-filtered), every claim cited with a permalink
  - if the record can't answer it, the delegate says so and ESCALATES —
    silence over speculation, exactly like Missing Voices
  - the represented person is always notified by DM: who asked, what was
    asked, what was answered on their behalf (monitor while you work)
  - every delegate answer lands in the audit trail

Never impersonation: the card is explicitly labeled as Arbiter speaking
*about* the person's record, not as the person.
"""
import re

from llm import _chat, _parse, SYNTH, ROUTER
from tools import slack_search
from arblog import get_logger

log = get_logger(__name__)

_FIDELITY_SYSTEM = (
    "You are a fidelity checker. Given an ANSWER written on someone's behalf and "
    "the QUOTES it was allowed to use, decide whether EVERY factual statement in "
    "the answer is directly supported by the quotes. Hedged statements ('not on "
    "record', 'they haven't said') are fine. Respond ONLY with JSON: "
    '"grounded" (boolean), "violation" (the unsupported statement, if any).'
)


def _fidelity_check(answer: str, quotes: list[dict]) -> bool:
    """Second-model verification: the delegate's 'never improvises' guarantee is
    enforced, not assumed. On any doubt (or checker failure) -> not grounded."""
    listing = "\n".join(f"[{i+1}] {c['quote']}" for i, c in enumerate(quotes))
    try:
        d = _parse(_chat(ROUTER[0], ROUTER[1], _FIDELITY_SYSTEM,
                         f"ANSWER:\n{answer}\n\nQUOTES:\n{listing}", temperature=0))
    except Exception as e:
        log.warning(f"fidelity check errored ({e}) — failing closed")
        return False
    if not bool(d.get("grounded")):
        log.info(f"fidelity gate blocked delegate answer: {str(d.get('violation'))[:120]}")
        return False
    return True

_DELEGATE_SYSTEM = (
    "You answer a question on behalf of an absent teammate, {name}, using ONLY "
    "their quoted Slack messages below. Rules:\n"
    "- Every statement in your answer must be directly supported by a quote; "
    "reference quotes as [1], [2] etc.\n"
    "- NEVER invent, extrapolate, or soften their position. If the quotes only "
    "partially answer, answer the part they cover and say what is not on record.\n"
    "- If the quotes cannot meaningfully answer the question, set answerable=false.\n"
    "{persona}"
    'Respond ONLY with JSON: "answerable" (boolean), '
    '"answer" (2-4 sentences with [n] citations; empty if not answerable), '
    '"used" (array of quote numbers actually cited).'
)

# Personality layer: style shapes the PHRASING, the record still owns the FACTS.
_PERSONA_SYSTEM = (
    "From these Slack messages all written by {name}, produce a compact persona "
    'brief. Respond ONLY with JSON: "style" (one sentence: how they write — tone, '
    'brevity, emoji habits, quirks), "priorities" (one sentence: what they '
    "consistently care about or push for)."
)

_persona_cache: dict[str, dict] = {}


def _persona_brief(full_name: str, names: list[str]) -> dict:
    """Learn how this specific person writes and what they care about, from
    their own messages — each delegate is unique to its human."""
    if full_name in _persona_cache:
        return _persona_cache[full_name]
    samples = []
    try:
        for m in slack_search(full_name, 10):
            if _is_target(_author_of(m), names):
                samples.append((m.get("content") or "")[:250])
    except Exception:
        pass
    brief = {}
    if len(samples) >= 2:
        try:
            d = _parse(_chat(SYNTH[0], SYNTH[1],
                             _PERSONA_SYSTEM.replace("{name}", full_name),
                             "\n---\n".join(samples[:8]), temperature=0))
            brief = {"style": str(d.get("style", ""))[:200],
                     "priorities": str(d.get("priorities", ""))[:200]}
        except Exception:
            brief = {}
    _persona_cache[full_name] = brief
    return brief


def _author_of(m: dict) -> str:
    """tools.slack_search titles messages as '{author} in #{channel}'."""
    return (m.get("title") or "").split(" in #")[0].strip()


def _is_target(author: str, names: list[str]) -> bool:
    """Match an RTS author to the target across known names — WITHOUT the
    substring trap ('Tim' must NOT match 'Timothy Jones'). We match on shared
    whole-word tokens: exact equality, or one name's token set is a subset of
    the other's (so 'Tim' == 'Tim Smith' but 'Tim' != 'Timothy Jones')."""
    def toks(s: str) -> set:
        return {t for t in re.split(r"\W+", (s or "").lower()) if t}
    a = toks(author)
    if not a:
        return False
    for n in names:
        nt = toks(n)
        if nt and (a == nt or a <= nt or nt <= a):
            return True
    return False


def answer_as(target_names: list[str], question: str) -> dict:
    """Compose a cited, record-only answer for the target, or escalate.

    target_names: all known names for the person (display + real name).
    """
    full_name = max(target_names, key=len)
    candidates, seen = [], set()
    for q in (question, f"{full_name} {question}"):
        try:
            for m in slack_search(q, 10):
                url = m.get("url", "")
                if url and url not in seen and _is_target(_author_of(m), target_names):
                    seen.add(url)
                    candidates.append({"quote": (m.get("content") or "")[:300],
                                       "url": url, "title": m.get("title", "")})
        except Exception:
            continue
    candidates = candidates[:6]

    if not candidates:
        return {"answerable": False, "answer": "", "quotes": []}

    brief = _persona_brief(full_name, target_names)
    persona_rule = ""
    if brief.get("style") or brief.get("priorities"):
        persona_rule = (
            f"- Phrase the answer the way {full_name} characteristically would "
            f"(style: {brief.get('style', 'n/a')}; cares about: "
            f"{brief.get('priorities', 'n/a')}) — but personality shapes WORDING "
            "only; every fact still needs a quote.\n")

    listing = "\n".join(f"[{i+1}] {c['quote']}" for i, c in enumerate(candidates))
    d = _parse(_chat(SYNTH[0], SYNTH[1],
                     _DELEGATE_SYSTEM.replace("{name}", full_name)
                                     .replace("{persona}", persona_rule),
                     f"QUESTION: {question[:400]}\n\n{full_name}'S MESSAGES:\n{listing}",
                     temperature=0))

    answerable = bool(d.get("answerable")) and bool(str(d.get("answer", "")).strip())
    used_idx = []
    for n in (d.get("used") or []):
        try:
            i = int(n) - 1
            if 0 <= i < len(candidates):
                used_idx.append(i)
        except Exception:
            continue
    quotes = [candidates[i] for i in used_idx] or (candidates[:2] if answerable else [])
    answer = str(d.get("answer", ""))[:900]

    # Fidelity gate: an answer that can't be verified against the quotes is
    # treated as unanswerable — silence over speculation, enforced.
    if answerable and not _fidelity_check(answer, candidates):
        return {"answerable": False, "answer": "", "quotes": []}

    return {"answerable": answerable, "answer": answer, "quotes": quotes}


_INFER_SYSTEM = (
    "Below are {name}'s real Slack messages. The question CANNOT be answered "
    "directly from them, but you are asked to INFER — as a clearly-labelled best "
    "guess — how {name} would likely lean, based on the priorities, values, and "
    "patterns visible in their messages. This is speculation, NOT their stated "
    "position. Ground your reasoning in observable patterns; cite the messages "
    "([n]) that inform the inference. Respond ONLY with JSON: "
    '"guess" (2-3 sentences, hedged: \'would likely…\', \'appears to prioritise…\'), '
    '"basis" (array of message numbers that informed it).'
)


def infer_as(target_names: list[str], question: str) -> dict:
    """OPT-IN speculation: infer how the person would likely lean from their
    style/patterns, clearly labelled as a guess (never their stated position).
    Only invoked when a human explicitly clicks the 'best guess' pill."""
    full_name = max(target_names, key=len)
    candidates, seen = [], set()
    for q in (question, f"{full_name} {question}", full_name):
        try:
            for m in slack_search(q, 8):
                url = m.get("url", "")
                if url and url not in seen and _is_target(_author_of(m), target_names):
                    seen.add(url)
                    candidates.append({"quote": (m.get("content") or "")[:280],
                                       "url": url, "title": m.get("title", "")})
        except Exception:
            continue
    candidates = candidates[:6]
    if not candidates:
        return {"guess": "", "quotes": []}
    listing = "\n".join(f"[{i+1}] {c['quote']}" for i, c in enumerate(candidates))
    try:
        d = _parse(_chat(SYNTH[0], SYNTH[1], _INFER_SYSTEM.replace("{name}", full_name),
                         f"QUESTION: {question[:400]}\n\n{full_name}'S MESSAGES:\n{listing}",
                         temperature=0))
    except Exception as e:
        log.warning(f"infer_as failed: {e}")
        return {"guess": "", "quotes": []}
    idx = [int(n) - 1 for n in (d.get("basis") or [])
           if isinstance(n, int) and 0 <= int(n) - 1 < len(candidates)]
    return {"guess": str(d.get("guess", ""))[:700],
            "quotes": [candidates[i] for i in idx] or candidates[:2]}
