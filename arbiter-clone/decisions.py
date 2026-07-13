"""Decision mode (Missing Voices) — when a decision is forming, bring in the
three voices the thread is missing:

  1. The Absent  — people affected but not in the thread. STRICTLY quote-first:
                   we surface their real messages (via RTS) with permalinks and a
                   relevance gate; we never generate a position for them.
  2. The Record  — related past decisions/claims from the workspace record and
                   the knowledge graph (the Chesterton's-Fence check).
  3. The Adversary — the strongest counter-case, argued once, grounded in the
                   retrieved evidence (contrarian prompt re-aimed at decisions).

Silence over speculation: any leg that finds nothing conclusive is omitted
rather than padded.
"""
import re
from concurrent.futures import ThreadPoolExecutor

from llm import _chat, _parse, SYNTH, ROUTER
from tools import web_search, slack_search
import knowledge_graph as _kg

_TOPIC_SYSTEM = (
    "A team is making a decision. Respond ONLY with JSON:\n"
    '"topic" (3-6 word noun phrase naming what is being decided),\n'
    '"search_terms" (array of 2-3 short keyword queries to find workspace messages '
    "from people this decision affects — think: who uses/depends on/objected to this),\n"
    '"reversal_terms" (one short keyword query to find why the current state exists '
    "or when this was decided before)."
)

_RELEVANCE_SYSTEM = (
    "A team is deciding: DECISION. Below are workspace messages from people NOT in "
    "the thread. For each message decide if it is genuinely relevant — the author "
    "said something this decision would affect or contradict. Respond ONLY with JSON: "
    '"relevant" (array of message indices, 0-based, that are genuinely relevant), '
    '"why" (object mapping each relevant index to ONE short clause tying that '
    "message to the decision — reference only what the message actually says)."
)

_COUNTER_SYSTEM = (
    "You are the devil's advocate on a decision-review panel. A team is about to "
    "commit to a decision. Using ONLY the evidence provided (workspace record, "
    "related past claims, web), argue the STRONGEST single counter-case: the risk "
    "nobody in the thread has raised, or the past experience that suggests caution. "
    "If the evidence gives you nothing concrete, say so honestly. Respond ONLY with "
    'JSON: "counter" (2-3 sentences, concrete, no hedging filler), '
    '"grounded" (boolean: true only if your counter cites something from the evidence).'
)


def _topic(decision_text: str) -> dict:
    try:
        d = _parse(_chat(ROUTER[0], ROUTER[1], _TOPIC_SYSTEM,
                         f"DECISION MESSAGE:\n{decision_text[:2000]}", temperature=0))
    except Exception:
        d = {}
    return {
        "topic":          str(d.get("topic", ""))[:80],
        "search_terms":   [str(x) for x in (d.get("search_terms") or [])][:3],
        "reversal_terms": str(d.get("reversal_terms", ""))[:80],
    }


def _absent_voices(decision_text: str, search_terms: list[str],
                   participant_names: set[str]) -> list[dict]:
    """Real quotes from affected people who are NOT in the thread."""
    candidates, seen = [], set()
    for term in search_terms or [decision_text[:80]]:
        try:
            for m in slack_search(term, 4):
                url = m.get("url", "")
                author = (m.get("title", "").split(" in #")[0] or "?").strip()
                if not url or url in seen or author in participant_names:
                    continue
                seen.add(url)
                candidates.append({"author": author, "title": m.get("title", ""),
                                   "quote": m.get("content", "")[:280], "url": url})
        except Exception:
            continue
    if not candidates:
        return []

    # Relevance gate — an LLM may only SELECT and TIE quotes, never speak for people
    listing = "\n".join(f"[{i}] {c['title']}: {c['quote']}"
                        for i, c in enumerate(candidates[:8]))
    try:
        d = _parse(_chat(ROUTER[0], ROUTER[1],
                         _RELEVANCE_SYSTEM.replace("DECISION", decision_text[:300]),
                         f"MESSAGES:\n{listing}", temperature=0))
    except Exception:
        return []  # no gate, no quotes — silence over speculation
    why = d.get("why") or {}
    out = []
    for i in (d.get("relevant") or []):
        try:
            c = candidates[int(i)]
            c["why"] = str(why.get(str(i)) or why.get(int(i)) or "")[:150]
            out.append(c)
        except Exception:
            continue
    return out[:3]


def _record(topic: str, reversal_terms: str) -> list[dict]:
    """Past decisions / related verified claims — the Chesterton's-Fence check."""
    out, seen = [], set()
    for q in filter(None, [f"decided {topic}", reversal_terms]):
        try:
            for m in slack_search(q, 3):
                url = m.get("url", "")
                if url and url not in seen:
                    seen.add(url)
                    out.append({"title": m.get("title", ""),
                                "quote": m.get("content", "")[:220], "url": url})
        except Exception:
            continue
    kg_ctx = _kg.find_related(topic, 3)
    if kg_ctx:
        out.append({"title": "knowledge graph", "quote": kg_ctx[:400], "url": ""})
    return out[:4]


def _counter_case(decision_text: str, record: list[dict]) -> dict:
    ev_parts = [f"- {r['title']}: {r['quote']}" for r in record]
    try:
        for w in web_search(decision_text[:120], 2):
            ev_parts.append(f"- [WEB] {w['title']}: {w['content'][:250]}")
    except Exception:
        pass
    ev = "\n".join(ev_parts) or "(no evidence retrieved)"
    try:
        d = _parse(_chat(SYNTH[0], SYNTH[1], _COUNTER_SYSTEM,
                         f"DECISION: {decision_text[:500]}\n\nEVIDENCE:\n{ev[:3000]}"))
    except Exception:
        d = {}
    return {"counter": str(d.get("counter", ""))[:400],
            "grounded": bool(d.get("grounded"))}


def analyze(decision_text: str, participant_names: set[str] | None = None) -> dict:
    """Run all three legs. Legs that find nothing return empty — the card builder
    omits them (silence over speculation)."""
    participant_names = participant_names or set()
    t = _topic(decision_text)

    with ThreadPoolExecutor(max_workers=2) as ex:
        absent_fut = ex.submit(_absent_voices, decision_text,
                               t["search_terms"], participant_names)
        record_fut = ex.submit(_record, t["topic"], t["reversal_terms"])
        absent = absent_fut.result()
        record = record_fut.result()

    counter = _counter_case(decision_text, record)

    has_signal = bool(absent or record
                      or (counter["grounded"] and counter["counter"]))
    return {"topic": t["topic"], "absent": absent, "record": record,
            "counter": counter, "has_signal": has_signal}
