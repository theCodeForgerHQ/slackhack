"""Council — Arbiter's debate engine, rebuilt on the Lymerorium doctrine.

Lymerorium (the author's prior system: a 3-node local debate swarm, +26pp MMLU
over single-model, McNemar p=0.0023) contributed four mechanisms, re-implemented
here for cloud models and evidence-grounded fact-checking:

  1. Multi-round debate with CONVERGENCE EARLY-STOP — unanimous panels return
     after round 1 (fast path preserved); split panels go a second round.
  2. FREE-MAD anti-conformity (round 2): each agent must critique every other
     position step-by-step, and may NOT use majority opinion as evidence —
     "if you cannot definitively prove others correct, RETAIN your conclusion."
  3. DART (Disagreement-triggered tool recruitment): when the panel splits,
     one targeted web search fires on the exact pair of opposed positions,
     and its result is injected into round 2 as fresh evidence.
  4. Structured turns: every agent reports verdict + confidence + reasoning +
     a pre-emptive rebuttal, so the synthesizer sees arguments, not vibes.

Enabled by default; set ARBITER_COUNCIL=0 to fall back to the single-round
panel. Council output is shape-compatible with the classic panel, so the
synthesizer, self-consistency voting, and Block Kit cards work unchanged.
"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from arblog import get_logger

log = get_logger(__name__)

COUNCIL_ENABLED = os.environ.get("ARBITER_COUNCIL", "1") == "1"
_SUBSTANTIVE = ("True", "False", "Misleading")


def _free_mad_suffix(others: list[dict]) -> str:
    """Lymerorium's anti-conformity block, adapted to verdict debates."""
    listing = "\n".join(
        f"- {p.get('role', '?').upper()}: {p.get('verdict')} "
        f"({p.get('confidence')}%) — {p.get('reasoning', '')[:200]}"
        for p in others)
    return (
        f"\n\nOTHER PANELISTS' ROUND-1 POSITIONS:\n{listing}\n\n"
        "MANDATORY CRITIQUE (do all steps):\n"
        "1. Restate your own round-1 claim and reasoning.\n"
        "2. For each other panelist: name one concrete error OR one valid point.\n"
        "3. Check: do their errors exist in your own reasoning?\n"
        "4. Decide: RETAIN or REVISE your verdict, one-sentence justification.\n"
        "CRITICAL: majority opinion is NOT evidence. If you cannot definitively "
        "prove the others correct, RETAIN your own conclusion. "
        "Respond with the same JSON format as before."
    )


def _dart_search(split: list[dict]) -> str:
    """One targeted search on the most opposed pair — no extra LLM calls,
    exactly like Lymerorium's dispute recruitment."""
    from tools import web_search
    by_verdict: dict[str, dict] = {}
    for p in split:
        v = str(p.get("verdict"))
        if v in _SUBSTANTIVE and v not in by_verdict:
            by_verdict[v] = p
    sides = list(by_verdict.values())
    if len(sides) < 2:
        return ""
    q = f"{sides[0].get('reasoning', '')[:80]} versus {sides[1].get('reasoning', '')[:80]}"
    try:
        results = web_search(q, 3)
    except Exception as e:
        log.warning(f"DART search failed: {e}")
        return ""
    if not results:
        return ""
    log.info(f"DART fired on split: {sides[0].get('verdict')} vs {sides[1].get('verdict')}")
    body = "\n".join(f"- {r['title']}: {r['content'][:220]}" for r in results)
    return f"\n\nDISPUTE-RESOLUTION EVIDENCE (fetched because the panel split):\n{body}"


def run_council(base_msg: str) -> dict:
    """Run the council on a prepared debate message. Returns
    {"panel": [...], "meta": {"rounds", "converged_round", "dart_fired"}}."""
    from llm import DEBATERS, _run_debater, _ROLES

    roles = (_ROLES * ((len(DEBATERS) // len(_ROLES)) + 1))[:len(DEBATERS)]

    # ---- Round 1: independent, parallel (no anchoring — Free-MAD principle) ----
    with ThreadPoolExecutor(max_workers=len(DEBATERS)) as ex:
        futs = {ex.submit(_run_debater, pm, base_msg, role): (pm, role)
                for pm, role in zip(DEBATERS, roles)}
        panel = []
        for fut in as_completed(futs):
            try:
                panel.append(fut.result())
            except Exception as e:
                pm, role = futs[fut]
                panel.append({"model": pm[1].split("/")[-1], "role": role,
                              "verdict": "Error", "confidence": 0,
                              "reasoning": str(e)[:100]})

    verdicts = {p["verdict"] for p in panel if p.get("verdict") in _SUBSTANTIVE}
    if len(verdicts) <= 1:
        # Unanimous (or nothing substantive to argue about) — early stop.
        return {"panel": panel,
                "meta": {"rounds": 1, "converged_round": 1, "dart_fired": False}}

    # ---- Split panel: DART evidence + Free-MAD round 2 ----
    dart_block = _dart_search(panel)
    round2_msgs = {}
    for p in panel:
        others = [q for q in panel if q is not p and not q.get("error")]
        round2_msgs[p["role"]] = base_msg + dart_block + _free_mad_suffix(others)

    with ThreadPoolExecutor(max_workers=len(DEBATERS)) as ex:
        futs = {ex.submit(_run_debater, pm, round2_msgs.get(role, base_msg), role):
                (pm, role) for pm, role in zip(DEBATERS, roles)}
        panel2 = []
        for fut in as_completed(futs):
            try:
                panel2.append(fut.result())
            except Exception:
                pass

    # Keep round-2 answers where they parsed; fall back to round 1 per-role.
    final = []
    r2_by_role = {p["role"]: p for p in panel2 if p.get("verdict") != "Error"}
    for p in panel:
        final.append(r2_by_role.get(p["role"], p))

    return {"panel": final,
            "meta": {"rounds": 2, "converged_round": None,
                     "dart_fired": bool(dart_block)}}
