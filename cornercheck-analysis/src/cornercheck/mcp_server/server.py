"""CornerCheck MCP server (stdio). Tool contracts are FROZEN in docs/decisions.md.

Run standalone: python -m cornercheck.mcp_server.server
The Claude Agent SDK launches this as a stdio MCP server; fastmcp.Client can connect
in-process for tests. Every tool returns JSON-safe dicts; every refusal explains itself.
Infrastructure failures return a typed ERROR envelope that can never read as a clearance.
"""

import functools
import logging
import uuid as uuidlib
from collections.abc import Callable
from datetime import date
from typing import Any

from fastmcp import FastMCP

from cornercheck.db.queries import get_fighter, get_suspensions
from cornercheck.er.live_match import resolve
from cornercheck.ledger.store import append_entry
from cornercheck.ledger.verify import verify_chain
from cornercheck.rules.engine import Outcome, evaluate, load_rules, window_days
from cornercheck.sources.corroborate import corroborate_fighter, tighten

log = logging.getLogger("cornercheck.mcp")

# NOTE: this server runs as its own stdio subprocess. It shares NO memory with the
# brain's SessionStore; its fail-closed lock is the deterministic engine re-check below.
# Thread-confirmation enforcement lives in the brain's PreToolUse hook (lock 2).

mcp: FastMCP = FastMCP("cornercheck")

_RULES = load_rules()


def _safe_tool(fn: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    """Fail-closed error envelope: an infra failure is unmistakably NOT a clearance
    (review finding H1). The system prompt forbids inferring anything from ERROR."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            # The envelope serves the model; this log line serves the operator. Without
            # it a persistent DB outage in this subprocess is invisible in server logs.
            log.exception("tool %s failed", fn.__name__)
            return {
                "status": "ERROR",
                "error_kind": type(exc).__name__,
                "message": str(exc)[:300],
                "is_clearance": False,
            }

    return wrapper


def _suspension_dict(s: Any) -> dict[str, Any]:
    return {
        "type": s.suspension_type,
        "start": s.start_date.isoformat(),
        "end": s.end_date.isoformat() if s.end_date else None,
        "indefinite": s.indefinite,
        "jurisdiction": s.jurisdiction,
        "reason": s.reason,
        "source_url": s.source_url,
    }


@mcp.tool(
    description="Resolve a fighter name to candidates. CONFIRMED only on a unique"
    " high-confidence match; identical names always come back AMBIGUOUS for a human pick;"
    " low confidence refuses (NOT_FOUND). Never guess past this tool."
)
@_safe_tool
def er_resolve_fighter(query: str) -> dict[str, Any]:
    r = resolve(query)
    return {
        "status": r.status,
        "note": r.note,
        "candidates": [
            {
                "fighter_id": c.fighter_id,
                "full_name": c.full_name,
                "weight_class": c.weight_class,
                "record": c.record,
                "sport": c.sport,
                "jurisdiction": c.jurisdiction,
                "score": round(c.score, 3),
            }
            for c in r.candidates
        ],
    }


@mcp.tool(
    description="Full detail for one fighter: profile plus every suspension on record,"
    " each with its source citation."
)
@_safe_tool
def er_fighter_details(fighter_id: str) -> dict[str, Any]:
    f = get_fighter(fighter_id)
    if f is None:
        return {
            "status": "ERROR",
            "error_kind": "UnknownFighter",
            "message": f"no fighter with id {fighter_id}",
            "is_clearance": False,
        }
    return {
        "fighter": {
            "fighter_id": f.id,
            "full_name": f.full_name,
            "weight_class": f.weight_class,
            "record": f"{f.wins}-{f.losses}-{f.draws}",
            "sport": f.sport,
            "jurisdiction": f.primary_jurisdiction,
        },
        "suspensions": [_suspension_dict(s) for s in get_suspensions(fighter_id)],
    }


@mcp.tool(
    description="THE clearance decision: deterministic rule engine over recorded"
    " suspensions. DO_NOT_CLEAR lists every active suspension with citations and, for"
    " cross-jurisdiction holds, a sport-aware consultation note (15 U.S.C. 6306(b) is"
    " binding for boxing; MMA has no federal equivalent)."
)
@_safe_tool
def rules_evaluate_clearance(
    fighter_id: str, on_date: str | None = None, target_jurisdiction: str | None = None
) -> dict[str, Any]:
    d = date.fromisoformat(on_date) if on_date else date.today()
    fighter = get_fighter(fighter_id)
    if fighter is None:
        # An unknown id with zero suspension rows would otherwise evaluate to CLEAR:
        # absence of a record is not absence of a suspension. Raise into the ERROR
        # envelope (is_clearance: False), never a default verdict.
        raise LookupError(f"no fighter with id {fighter_id!r}; refusing to evaluate clearance")
    v = evaluate(get_suspensions(fighter_id), d, target_jurisdiction, fighter.sport)
    return {
        "decision": v.decision,
        "on_date": v.on_date.isoformat(),
        "active": [_suspension_dict(s) for s in v.active],
        "applied_rules": v.applied_rules,
        "consultation_note": v.consultation_note,
    }


@mcp.tool(
    description="Mandated minimum window (days) after a bout outcome: TKO, KO, or KO_LOC"
    " (KO with loss of consciousness). cause='head_shot_stoppage' applies the ABC BSI"
    " overlay; sparring=true returns the CornerCheck no-contact layer (not an ABC mandate)."
)
@_safe_tool
def rules_outcome_window(
    outcome: Outcome, cause: str | None = None, sparring: bool = False
) -> dict[str, Any]:
    days, applied = window_days(_RULES, outcome, cause=cause, sparring=sparring)
    return {"days": days, "applied_rules": applied}


@mcp.tool(
    description="Record a clearance decision in the tamper-evident audit ledger."
    " GUARDED: the server re-runs the rule engine and refuses any decision that"
    " contradicts it; refusals are themselves ledgered. Requires the thread_key"
    " provided in the conversation context."
)
@_safe_tool
def ledger_record_clearance(
    thread_key: str,
    fighter_id: str,
    decision: str,
    on_date: str | None = None,
    target_jurisdiction: str | None = None,
    actor: str = "cornercheck-agent",
) -> dict[str, Any]:
    def refusal(reason: str, extra: dict[str, Any]) -> dict[str, Any]:
        """Structured refusal; the attempt itself is ledgered whenever possible
        (review findings I2/M2: probes leave a trace, dropped denials are visible)."""
        out: dict[str, Any] = {"recorded": False, "refusal_reason": reason}
        try:
            denial = append_entry(
                actor,
                "clearance_write_denied",
                {"thread_key": thread_key, "refusal_reason": reason, **extra},
            )
            out["denial_seq"] = denial.seq
        except Exception as exc:
            out["audit_warning"] = f"denial could not be ledgered: {exc}"
        return out

    try:
        uuidlib.UUID(fighter_id)
    except ValueError:
        return refusal(
            f"fighter_id {fighter_id!r} is not a valid id; refusing the write",
            {"attempted_fighter_id": fighter_id, "attempted_decision": decision},
        )
    try:
        d = date.fromisoformat(on_date) if on_date else date.today()
    except ValueError:
        return refusal(
            f"on_date {on_date!r} is not an ISO date (YYYY-MM-DD); refusing the write",
            {"fighter_id": fighter_id, "attempted_decision": decision},
        )

    fighter = get_fighter(fighter_id)
    if fighter is None:
        # A ghost id has zero suspension rows and would re-check as CLEAR: "no record
        # of this fighter" must never validate a clearance write.
        return refusal(
            f"no fighter with id {fighter_id!r}; refusing the write",
            {"fighter_id": fighter_id, "attempted_decision": decision},
        )

    engine_verdict = evaluate(get_suspensions(fighter_id), d, target_jurisdiction, fighter.sport)
    # LOCK 1 (in-tool): the written decision must equal the FINAL composed decision,
    # the same tighten-only composition the pipeline applies. Comparing against the raw
    # engine verdict deadlocked corroboration-tightened cases against lock 2 (the hook
    # validates the tightened value): no decision could satisfy both locks.
    corr = corroborate_fighter(fighter)
    expected, _ = tighten(engine_verdict.decision, corr)
    if decision != expected:
        return refusal(
            f"decision {decision!r} contradicts the composed verdict"
            f" (engine {engine_verdict.decision}, after corroboration {expected});"
            " attempt ledgered",
            {
                "fighter_id": fighter_id,
                "attempted_decision": decision,
                "engine_decision": engine_verdict.decision,
                "expected_decision": expected,
                "corroboration_status": corr.status,
                "on_date": d.isoformat(),
            },
        )

    entry = append_entry(
        actor,
        "clearance_decision",
        {
            "thread_key": thread_key,
            "fighter_id": fighter_id,
            "fighter_name": fighter.full_name,
            "decision": decision,
            "on_date": d.isoformat(),
            "target_jurisdiction": target_jurisdiction,
            "applied_rules": engine_verdict.applied_rules,
            "corroboration": corr.model_dump(),
        },
    )
    return {"recorded": True, "seq": entry.seq, "hash": entry.hash}


@mcp.tool(description="Most recent audit-ledger entries, newest first.")
@_safe_tool
def ledger_recent_entries(limit: int = 10) -> dict[str, Any]:
    from cornercheck.db.pool import get_pool

    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT seq, ts, actor, action, payload FROM ledger ORDER BY seq DESC LIMIT %s",
            (min(limit, 50),),
        ).fetchall()
    return {
        "entries": [
            {"seq": r[0], "ts": r[1].isoformat(), "actor": r[2], "action": r[3], "payload": r[4]}
            for r in rows
        ]
    }


@mcp.tool(
    description="Verify the entire hash chain; reports the FIRST broken seq exactly."
    " Scope, honestly: catches edited payloads, edited actor/action/ts columns on"
    " stamped rows, and reordering. Tail TRUNCATION is outside this in-table check;"
    " it is caught by the head anchor in the most recent POSTED ops digest (requires"
    " the ops webhook to be configured; quiet stretches extend that window)."
)
@_safe_tool
def ledger_verify_chain() -> dict[str, Any]:
    r = verify_chain()
    return {"ok": r.ok, "checked": r.checked, "first_bad_seq": r.first_bad_seq, "detail": r.detail}


if __name__ == "__main__":
    # The subprocess inherits no logging config from the Bolt process; without this,
    # every failure in here is invisible to the operator (stderr reaches Render logs).
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    mcp.run()
