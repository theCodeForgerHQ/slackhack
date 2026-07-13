"""Deterministic corroboration of a fighter's identity and record against the live
boxing-data.com source. Pure rules, no LLM anywhere. The one safety invariant:
a corroboration can TIGHTEN a verdict (a live disagreement withholds a CLEAR) but can
never loosen one; absence of live data (MMA fighters, API down, no exact match) only
annotates, because absence of evidence is not disagreement."""

import logging
from typing import Any

from cornercheck.brain.schemas import CorroborationOut
from cornercheck.db.queries import FighterRow
from cornercheck.sources.boxing_data import cached_search

log = logging.getLogger("cornercheck.corroborate")

DISAGREEMENT_RULE = "live_record_disagreement(boxing-data.com)"


def corroborate_fighter(fighter: FighterRow) -> CorroborationOut:
    """The full check: sport gate, cached live search, deterministic comparison.

    Never raises: ANY unexpected failure (including upstream data of a shape the
    comparison does not expect) degrades to UNAVAILABLE so the verdict stands on
    commission data. A corroboration crash must not destroy a verdict."""
    if fighter.sport.strip().lower() != "boxing":
        return CorroborationOut(
            status="NOT_APPLICABLE",
            note="live corroboration covers boxing only; not queried for this fighter",
        )
    try:
        hits, origin, fetched_at = cached_search(fighter.full_name)
        if hits is None:
            return CorroborationOut(
                status="UNAVAILABLE",
                note="live record check unavailable; verdict rests on commission data on file",
            )
        out = corroborate_from_hits(fighter, hits)
    except Exception:
        log.exception("corroboration failed for %r; degrading to UNAVAILABLE", fighter.full_name)
        return CorroborationOut(
            status="UNAVAILABLE",
            note="live record check failed; verdict rests on commission data on file",
        )
    note = out.note
    # Provenance must be exact on the card: a Postgres-cached LIVE response may say
    # "cached live data"; a recorded demo fixture may not call itself live at all.
    if origin == "cache" and fetched_at:
        note = f"{note} (cached live data from {fetched_at[:10]})"
    elif origin == "demo-fixture" and fetched_at:
        note = f"{note} (recorded real response from {fetched_at[:10]}; live check unavailable)"
    return out.model_copy(update={"data_origin": origin, "checked_at": fetched_at, "note": note})


def corroborate_from_hits(fighter: FighterRow, hits: list[Any]) -> CorroborationOut:
    """Pure comparison logic, unit-testable against recorded real responses.

    hits is list[Any] on purpose: upstream JSON can contain anything, and non-dict
    elements are filtered rather than crashing a verdict. The live search is token-fuzzy
    (a full-name query returns many partial matches), so identity requires an exact
    casefolded name match, and exactly one of them. Records compare on computed
    wins+losses+draws sums on BOTH sides: the upstream total_bouts field is unreliable
    (absent for some fighters, inconsistent with w+l+d for others).
    """
    target = fighter.full_name.strip().casefold()
    exact = [
        h
        for h in hits
        if isinstance(h, dict) and str(h.get("name") or "").strip().casefold() == target
    ]
    if not exact:
        return CorroborationOut(
            status="UNMATCHED",
            note="no exact live-source name match; identity not independently corroborated",
        )
    if len(exact) > 1:
        return CorroborationOut(
            status="UNMATCHED",
            note=(
                f"{len(exact)} live-source fighters share this exact name; "
                "corroboration withheld (fail closed)"
            ),
        )
    raw_stats = exact[0].get("stats")
    stats = raw_stats if isinstance(raw_stats, dict) else {}
    w, lo, dr = stats.get("wins"), stats.get("losses"), stats.get("draws")
    # type(x) is int rejects bools (isinstance(True, int) is True in Python); negative
    # counts are upstream garbage. Either way: no comparison, never a fake CONFIRMED
    # and never a garbage-driven DISAGREED block.
    if not (
        type(w) is int and type(lo) is int and type(dr) is int and w >= 0 and lo >= 0 and dr >= 0
    ):
        return CorroborationOut(
            status="CONFIRMED",
            note="live source matched this fighter; upstream record incomplete, no comparison",
        )
    live = f"{w}-{lo}-{dr}"
    api_total = w + lo + dr
    db_total = fighter.wins + fighter.losses + fighter.draws
    if db_total == 0:
        # An empty record on file means "not recorded locally", never "never fought":
        # the live source fills the gap, it does not contradict anything.
        return CorroborationOut(
            status="CONFIRMED",
            live_record=live,
            note=f"live record {live}; no record on file locally, live source fills the gap",
        )
    if api_total > db_total:
        return CorroborationOut(
            status="DISAGREED",
            live_record=live,
            note=(
                f"live source shows {api_total} bouts vs {db_total} on file: record on "
                "file is stale; CLEAR withheld pending commission verification"
            ),
        )
    # Live source showing FEWER bouts is an upstream coverage gap, not a safety signal.
    return CorroborationOut(
        status="CONFIRMED",
        live_record=live,
        note=f"live record {live}, consistent with the record on file",
    )


def tighten(decision: str, corr: CorroborationOut) -> tuple[str, str | None]:
    """The fail-closed composition rule: DISAGREED withholds a CLEAR; nothing loosens."""
    if corr.status == "DISAGREED" and decision == "CLEAR":
        return "DO_NOT_CLEAR", DISAGREEMENT_RULE
    return decision, None
