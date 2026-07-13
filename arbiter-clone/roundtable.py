"""Roundtable mode — "act as @A @B @C on <topic>".

Each named teammate is voiced by an agent whose personality is drawn from that
person's REAL Slack messages (their tone, what they push for, how they argue).
The agents open, then react to each other in one round of cross-talk
(Free-MAD-style: engage the others, don't just repeat yourself), and a neutral
facilitator states where the group lands.

This is the deliberation counterpart to the delegate: the delegate answers *one*
person's question from their quotes; the roundtable convenes *several* people to
talk a fresh topic through and reach a conclusion.
"""
from concurrent.futures import ThreadPoolExecutor

from llm import _chat, _parse, DEBATERS, SYNTH
from tools import slack_search
from delegate import _is_target, _author_of, _persona_brief
from arblog import get_logger

log = get_logger(__name__)


def _gather(target_names: list[str], k: int = 8) -> list[dict]:
    """Real messages authored by this person (author-filtered RTS retrieval)."""
    full = max(target_names, key=len)
    out, seen = [], set()
    for q in (full, f"{full} plan priority concern position"):
        try:
            for m in slack_search(q, 10):
                url = m.get("url", "")
                if url and url not in seen and _is_target(_author_of(m), target_names):
                    seen.add(url)
                    out.append({"quote": (m.get("content") or "")[:260], "url": url})
        except Exception:
            continue
    return out[:k]


_OPEN_SYSTEM = (
    "You are role-playing {name} in a team roundtable. Below are {name}'s REAL "
    "Slack messages — mirror how they think, what they prioritise, and their tone. "
    "Give {name}'s honest opening take on the TOPIC, the way {name} would actually "
    "argue it. Stay fully in character; be specific, not generic. 2-4 sentences, "
    "first person.{persona} Respond ONLY with JSON: \"position\" (their stance in "
    "their voice), \"priorities\" (array of what they're pushing for)."
)

_REACT_SYSTEM = (
    "You are still {name}. The other people in the roundtable just spoke (below). "
    "React as {name} would: agree where you'd genuinely agree, push back where "
    "you'd disagree, and sharpen your stance. Reference them by name. Stay in "
    "character and consistent with {name}'s real messages. 2-3 sentences, first "
    "person. Respond ONLY with JSON: \"position\" (your updated stance), "
    "\"moved\" (boolean: did you shift at all)."
)

_CONCLUDE_SYSTEM = (
    "You are a neutral facilitator. {names} just deliberated a topic in character. "
    "From their final positions, state where the group lands — be decisive and "
    "practical, not wishy-washy. Respond ONLY with JSON: \"conclusion\" (3-5 "
    "sentences: the group's answer or recommendation), \"consensus\" (one line "
    "they'd all sign off on), \"tension\" (one line naming the unresolved "
    "disagreement, or empty string if they fully agreed)."
)


def _persona_block(p: dict) -> str:
    b = p.get("brief") or {}
    bits = []
    if b.get("style"):
        bits.append(f"style: {b['style']}")
    if b.get("priorities"):
        bits.append(f"cares about: {b['priorities']}")
    extra = f" ({'; '.join(bits)})" if bits else ""
    quotes = "\n".join(f"- {q['quote']}" for q in p["quotes"][:6]) or "(little on record)"
    return f"{p['display']}'s real messages{extra}:\n{quotes}"


def _open(p: dict, topic: str) -> dict:
    b = p.get("brief") or {}
    persona = ""
    if b.get("style") or b.get("priorities"):
        persona = (f" Write in {p['display']}'s voice — {b.get('style', '')}; "
                   f"they care about {b.get('priorities', 'n/a')}.")
    sys = _OPEN_SYSTEM.replace("{name}", p["display"]).replace("{persona}", persona)
    usr = f"TOPIC: {topic[:500]}\n\n{_persona_block(p)}"
    try:
        d = _parse(_chat(p["pm"][0], p["pm"][1], sys, usr))
    except Exception as e:
        log.warning(f"roundtable open failed for {p['display']}: {e}")
        d = {}
    return {"position": str(d.get("position", "")).strip()}


def _react(p: dict, topic: str, others_text: str) -> dict:
    sys = _REACT_SYSTEM.replace("{name}", p["display"])
    usr = (f"TOPIC: {topic[:400]}\n\n{_persona_block(p)}\n\n"
           f"WHAT THE OTHERS SAID:\n{others_text[:1600]}")
    try:
        d = _parse(_chat(p["pm"][0], p["pm"][1], sys, usr))
    except Exception as e:
        log.warning(f"roundtable react failed for {p['display']}: {e}")
        d = {}
    return {"position": str(d.get("position", "")).strip()}


def deliberate(participants: list[dict], topic: str) -> dict:
    """participants: [{'display': str, 'names': [str, ...]}].

    Grounds each person in their real messages, runs opening + one cross-talk
    round, then a facilitator conclusion. Returns a render-ready dict.
    """
    # 1. ground each person in their own record + learn their persona
    for i, p in enumerate(participants):
        p["quotes"] = _gather(p["names"])
        p["brief"] = _persona_brief(max(p["names"], key=len), p["names"])
        p["pm"] = DEBATERS[i % len(DEBATERS)] if DEBATERS else SYNTH

    # 2. opening positions (parallel, each in their own voice)
    with ThreadPoolExecutor(max_workers=max(1, len(participants))) as ex:
        for p, o in zip(participants, ex.map(lambda x: _open(x, topic), participants)):
            p["position"] = o["position"]

    # 3. one round of cross-talk — each engages what the others actually said
    def _others(idx: int) -> str:
        return "\n\n".join(
            f"{participants[j]['display']}: {participants[j]['position']}"
            for j in range(len(participants))
            if j != idx and participants[j].get("position"))

    with ThreadPoolExecutor(max_workers=max(1, len(participants))) as ex:
        reacts = list(ex.map(lambda i: _react(participants[i], topic, _others(i)),
                             range(len(participants))))
    for p, r in zip(participants, reacts):
        if r["position"]:
            p["position"] = r["position"]

    # 4. facilitator states where they land
    names = ", ".join(p["display"] for p in participants)
    positions = "\n\n".join(f"{p['display']}: {p['position']}"
                            for p in participants if p.get("position"))
    try:
        c = _parse(_chat(SYNTH[0], SYNTH[1],
                         _CONCLUDE_SYSTEM.replace("{names}", names),
                         f"TOPIC: {topic[:500]}\n\nFINAL POSITIONS:\n{positions}"))
    except Exception as e:
        log.warning(f"roundtable conclude failed: {e}")
        c = {}

    return {
        "topic": topic,
        "participants": [{"display": p["display"], "position": p.get("position", ""),
                          "quotes": p.get("quotes", [])[:2]} for p in participants],
        "conclusion": str(c.get("conclusion", "")).strip(),
        "consensus": str(c.get("consensus", "")).strip(),
        "tension": str(c.get("tension", "")).strip(),
    }
