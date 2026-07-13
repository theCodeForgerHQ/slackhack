"""Substance mode — the anti-workslop receipt.

Workslop (Stanford/BetterUp, HBR 2026): polished, plausible content with nothing
inside, offloading the reading cost onto the recipient (avg 1h56m per incident).

Design rule — NEVER score holistically. LLM judges have a verbosity bias: asked
"rate this doc", they reward exactly the padding this mode exists to catch.
Here the LLM only EXTRACTS and VERIFIES; the score is arithmetic over countable
parts, at temperature 0:

  density      — substantive units (decisions/asks/commitments/facts) per 100 words
  fluff        — filler-phrase density (pure wordlist arithmetic, no LLM)
  groundedness — fraction of checked facts that survive evidence
  novelty      — fraction of the content NOT already in the workspace record

score = 0.6*density + 0.2*groundedness + 0.2*novelty − 0.25*fluff

Design rule: only substance EARNS points; style only SUBTRACTS. A message with
zero concrete units can never score well merely by avoiding clichés — that
closed the 'polite vagueness' hole our adversarial benchmark cases exposed.
"""
import re
import json
from concurrent.futures import ThreadPoolExecutor

from llm import _chat, _parse, SYNTH, ROUTER
from tools import web_search, slack_search
import knowledge_graph as _kg
from judgment import filler_hits, _word_count

# ---------------------------------------------------------------------------
# Extraction (LLM, temperature 0 — reproducible)
# ---------------------------------------------------------------------------
_EXTRACT_SYSTEM = (
    "Extract the substantive content of a workplace message. Respond ONLY with JSON:\n"
    '"decisions" (array of strings: decisions stated or announced),\n'
    '"asks" (array: requests/questions needing an answer or action),\n'
    '"commitments" (array: promises with an owner),\n'
    '"facts" (array: specific checkable factual statements, each self-contained),\n'
    '"gist" (array of at most 4 short bullets: what the message actually says, '
    "no filler, telegraphic style).\n"
    "STRICT concreteness rule — an item ONLY counts if it names at least one "
    "SPECIFIC anchor: a person/team, a number, a date/deadline, or a named "
    "artifact (ticket, PR, doc, product, system). Apply it hard:\n"
    '- "Maya owns the migration script, due Aug 8" -> commitment (named owner+artifact+date)\n'
    '- "we\'ll keep pushing on the remaining pieces" -> NOTHING (no anchor)\n'
    '- "we should talk to a few more people" -> NOTHING\n'
    '- "a few sections could be tightened" -> NOTHING (no named section)\n'
    '- "signups 1,240, +18% WoW" -> fact\n'
    "Vague intentions, sentiments, and process talk produce EMPTY arrays — empty "
    "arrays are correct and common. Do NOT invent content."
)

_NOVELTY_SYSTEM = (
    "You compare NEW content bullets against PRIOR workspace messages. "
    "For each bullet decide if it is already established in the prior messages "
    "(restated) or genuinely new. Respond ONLY with JSON: "
    '"restated" (array of bullet indices, 0-based, that are already established), '
    '"note" (if any restated: one short sentence naming what they duplicate).'
)

_FACT_CHECK_SYSTEM = (
    "Quick fact-check. Given CLAIM and EVIDENCE, respond ONLY with JSON: "
    '"supported" (true if evidence backs the claim; false ONLY if evidence ACTIVELY '
    "CONTRADICTS it; null if the evidence simply doesn't address the claim — internal "
    "team facts often can't be verified externally, and that is null, not false), "
    '"note" (one short phrase).'
)


def _extract_units(text: str) -> dict:
    try:
        d = _parse(_chat(SYNTH[0], SYNTH[1], _EXTRACT_SYSTEM, text[:6000], temperature=0))
    except Exception:
        d = {}
    return {
        "decisions":   [str(x) for x in (d.get("decisions") or [])][:6],
        "asks":        [str(x) for x in (d.get("asks") or [])][:6],
        "commitments": [str(x) for x in (d.get("commitments") or [])][:6],
        "facts":       [str(x) for x in (d.get("facts") or [])][:6],
        "gist":        [str(x) for x in (d.get("gist") or [])][:4],
    }


# ---------------------------------------------------------------------------
# Component scores (arithmetic)
# ---------------------------------------------------------------------------
def _density_score(n_units: int, words: int) -> int:
    """3+ substantive units per 100 words = 100. Linear below."""
    if words == 0:
        return 0
    per100 = n_units * 100.0 / words
    return min(100, round(per100 / 3.0 * 100))


def _fluff_score(text: str, words: int) -> tuple[int, list[str]]:
    """Filler phrases per 100 words → 0-100 penalty scale (pure wordlist, no LLM)."""
    hits = filler_hits(text)
    if words == 0:
        return 0, hits
    per100 = len(hits) * 100.0 / words
    return min(100, round(per100 / 1.5 * 100)), hits  # 1.5 fillers/100w = max penalty


def _check_fact(fact: str) -> dict:
    """One cheap grounding pass: workspace first, then web. Single LLM call."""
    ev_parts = []
    try:
        for m in slack_search(fact, 2):
            ev_parts.append(f"[SLACK] {m['title']}: {m['content'][:300]}")
    except Exception:
        pass
    kg_ctx = _kg.find_related(fact, 2)
    if kg_ctx:
        ev_parts.append(kg_ctx)
    try:
        for w in web_search(fact, 2):
            ev_parts.append(f"[WEB] {w['title']}: {w['content'][:300]}")
    except Exception:
        pass
    ev = "\n".join(ev_parts) or "(no evidence found)"
    try:
        d = _parse(_chat(ROUTER[0], ROUTER[1], _FACT_CHECK_SYSTEM,
                         f"CLAIM: {fact}\n\nEVIDENCE:\n{ev[:2500]}", temperature=0))
    except Exception:
        d = {}
    return {"fact": fact, "supported": d.get("supported"),
            "note": str(d.get("note", ""))[:120]}


def _groundedness(facts: list[str]) -> tuple[int, list[dict]]:
    """Check up to 3 facts in parallel. No facts → neutral 50 (nothing to ground)."""
    to_check = facts[:3]
    if not to_check:
        return 50, []
    with ThreadPoolExecutor(max_workers=len(to_check)) as ex:
        checks = list(ex.map(_check_fact, to_check))
    supported = sum(1 for c in checks if c["supported"] is True)
    refuted   = sum(1 for c in checks if c["supported"] is False)
    judged    = supported + refuted
    if judged == 0:
        return 50, checks  # nothing conclusive either way
    return round(100 * supported / judged), checks


def _novelty(gist: list[str], query_hint: str) -> tuple[int, str]:
    """What fraction of the gist is NOT already in the workspace record?"""
    if not gist:
        return 50, ""
    try:
        prior = slack_search(query_hint or " ".join(gist)[:200], 5)
    except Exception:
        prior = []
    if not prior:
        return 100, ""  # nothing on record — all of it is new
    prior_text = "\n".join(f"- {m['title']}: {m['content'][:250]}" for m in prior)
    bullets = "\n".join(f"[{i}] {b}" for i, b in enumerate(gist))
    try:
        d = _parse(_chat(ROUTER[0], ROUTER[1], _NOVELTY_SYSTEM,
                         f"NEW BULLETS:\n{bullets}\n\nPRIOR MESSAGES:\n{prior_text[:3000]}",
                         temperature=0))
    except Exception:
        return 50, ""  # neutral — a failed call must never zero the score
    restated = [i for i in (d.get("restated") or []) if isinstance(i, int) and 0 <= i < len(gist)]
    novel_frac = 1.0 - len(restated) / len(gist)
    return round(100 * novel_frac), str(d.get("note", ""))[:150]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def score(text: str) -> dict:
    """Full substance receipt for a message or document."""
    words = _word_count(text)
    units = _extract_units(text)
    n_units = sum(len(units[k]) for k in ("decisions", "asks", "commitments", "facts"))

    density = _density_score(n_units, words)
    fluff, fillers = _fluff_score(text, words)
    grounded, checks = _groundedness(units["facts"])
    novelty, novelty_note = _novelty(units["gist"], " ".join(units["gist"])[:200])

    # Substance earns; style subtracts. Zero units ⇒ score ≤ 40 by construction.
    final = round(0.6 * density + 0.2 * grounded + 0.2 * novelty - 0.25 * fluff)
    final = max(0, min(100, final))

    return {
        "score":        final,
        "words":        words,
        "units":        units,
        "n_units":      n_units,
        "components":   {"density": density, "fluff": fluff,
                         "groundedness": grounded, "novelty": novelty},
        "fillers":      fillers[:6],
        "fact_checks":  checks,
        "novelty_note": novelty_note,
        "unsupported":  [c for c in checks if c["supported"] is False],
    }


def grade(s: int) -> tuple[str, str]:
    """(emoji, label) for a substance score."""
    if s >= 75:
        return "🟢", "high substance"
    if s >= 45:
        return "🟡", "some substance"
    return "🔴", "low substance"
