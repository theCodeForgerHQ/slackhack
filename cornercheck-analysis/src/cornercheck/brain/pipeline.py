"""The deterministic clearance pipeline: Retrieve -> Disambiguate -> Clear.

This drives the Slack card. The LLM narrates around it; it never overrides it.
Fail closed: ambiguity or no-match never reaches the rule engine.
"""

from datetime import date

from cornercheck.brain.schemas import ClearanceVerdict, from_resolution, from_rule_verdict
from cornercheck.db.queries import evaluate_fighter_clearance, get_fighter
from cornercheck.er.live_match import resolve
from cornercheck.ledger.store import append_entry
from cornercheck.session.state import SESSION_STORE
from cornercheck.sources.corroborate import corroborate_fighter, tighten


def start_clearance(
    thread_key: str,
    query: str,
    on_date: date | None = None,
    target_jurisdiction: str | None = None,
) -> ClearanceVerdict:
    """Resolve the name. Unique high-confidence match proceeds straight to the verdict;
    anything else returns the fail-closed disambiguation/refusal card data."""
    d = on_date or date.today()
    r = resolve(query)
    if r.status == "CONFIRMED":
        c = r.candidates[0]
        SESSION_STORE.set_candidates(thread_key, {c.fighter_id: c.full_name})
        if not SESSION_STORE.confirm(thread_key, c.fighter_id):
            # State changed under us (concurrent reset): fail closed to disambiguation
            # rather than write anything. Never an assert: gates must survive -O.
            # The certified-singleton note must NOT ride along onto a refusal card.
            return from_resolution(query, d, r).model_copy(
                update={"identity_note": "session state changed during confirmation; retry"}
            )
        return _verdict_for(
            thread_key, query, c.fighter_id, d, target_jurisdiction, identity_note=r.note
        )
    if r.status == "AMBIGUOUS":
        SESSION_STORE.set_candidates(thread_key, {c.fighter_id: c.full_name for c in r.candidates})
    else:  # NOT_FOUND: terminal refusal, no pick is awaited
        SESSION_STORE.reset(thread_key)
    return from_resolution(query, d, r)


def clear_card(
    thread_key: str,
    fighters: list[str],
    on_date: date | None = None,
    target_jurisdiction: str | None = None,
) -> list[ClearanceVerdict]:
    """Clear a whole fight card at once: the real matchmaker workflow. Each fighter runs
    through the same fail-closed pipeline under an isolated sub-thread (so one fighter's
    disambiguation never clobbers another's), and the batch is summarized in the ledger.
    Every CLEAR/DO_NOT_CLEAR is individually ledgered by the per-fighter path."""
    d = on_date or date.today()
    verdicts = [
        start_clearance(f"{thread_key}#card{i}", name, d, target_jurisdiction)
        for i, name in enumerate(fighters)
    ]
    append_entry(
        "cornercheck-card",
        "card_check",
        {
            "thread_key": thread_key,
            "on_date": d.isoformat(),
            "target_jurisdiction": target_jurisdiction,
            "fighters": [
                {"query": v.query, "status": v.status, "fighter_id": v.fighter_id} for v in verdicts
            ],
        },
    )
    return verdicts


def confirm_candidate(
    thread_key: str,
    fighter_id: str,
    query: str = "",
    on_date: date | None = None,
    target_jurisdiction: str | None = None,
) -> ClearanceVerdict | None:
    """Human picked a candidate (Block Kit action). Self-contained and fail-closed: the
    button carries the original query, so we RE-RESOLVE it and require the picked fighter
    to be a genuine candidate of that query. This validates the pick deterministically
    without depending on cross-event in-memory thread state (which the interactivity
    payload's thread_key does not reliably share with the original message)."""
    if query:
        r = resolve(query)
        candidate_ids = {c.fighter_id for c in r.candidates}
        if fighter_id not in candidate_ids:
            return None
        SESSION_STORE.set_candidates(thread_key, {c.fighter_id: c.full_name for c in r.candidates})
    if not SESSION_STORE.confirm(thread_key, fighter_id):
        return None
    return _verdict_for(
        thread_key,
        query,
        fighter_id,
        on_date or date.today(),
        target_jurisdiction,
        identity_note="human pick (disambiguation)",
    )


def _verdict_for(
    thread_key: str,
    query: str,
    fighter_id: str,
    on_date: date,
    target_jurisdiction: str | None,
    identity_note: str = "",
) -> ClearanceVerdict:
    """Rule verdict, then second-source corroboration (boxing-data.com). Corroboration
    can only TIGHTEN: a live record disagreement withholds a CLEAR; unavailable/unmatched
    live data annotates and the verdict stands on the commission data on file. The ledger
    records the FINAL decision, the full corroboration evidence, and HOW the identity was
    certified (conformal singleton / legacy bands / human pick)."""
    v = evaluate_fighter_clearance(fighter_id, on_date, target_jurisdiction)
    fighter = get_fighter(fighter_id)
    name = fighter.full_name if fighter else "unknown"
    corr = corroborate_fighter(fighter) if fighter else None
    decision, extra_rule = tighten(v.decision, corr) if corr else (v.decision, None)
    applied = [*v.applied_rules, extra_rule] if extra_rule else v.applied_rules
    SESSION_STORE.record_verdict(thread_key, decision)
    entry = append_entry(
        "cornercheck-pipeline",
        "clearance_decision",
        {
            "thread_key": thread_key,
            "fighter_id": fighter_id,
            "fighter_name": name,
            "decision": decision,
            "on_date": on_date.isoformat(),
            "target_jurisdiction": target_jurisdiction,
            "applied_rules": applied,
            "corroboration": corr.model_dump() if corr else None,
            "identity": identity_note or None,
        },
    )
    SESSION_STORE.record_written(thread_key, entry.seq)
    verdict = from_rule_verdict(query, fighter_id, name, v, entry.seq)
    return verdict.model_copy(
        update={
            "status": decision,
            "applied_rules": applied,
            "corroboration": corr,
            "identity_note": identity_note,
        }
    )
