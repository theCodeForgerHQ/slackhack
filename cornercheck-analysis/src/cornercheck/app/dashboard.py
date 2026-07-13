"""Data layer for the public dashboard: live stats and the run-it-now proof.

Everything here is FAIL-SOFT per section: the page must render and the server must
answer even with the database down; a missing number renders as unavailable, never as
an error page. The proof endpoint runs the REAL Z3 checks (milliseconds) and reports
healthy only on the exact (PROVEN, COUNTEREXAMPLE) pair, the same contract as the
in-Slack proof card: a failed proof must never read as reassurance."""

import logging
import threading
import time
from typing import Any

log = logging.getLogger("cornercheck.dashboard")


def _chain_status() -> dict[str, Any]:
    """Best-effort + time-bounded: never let a slow/absent DB hang the page. The detail
    string is PUBLIC: exception text stays in the server log, never in the response
    (a raw connect error can carry the DB host and port)."""
    result: dict[str, Any] = {"ok": None, "detail": "chain status unavailable"}

    def check() -> None:
        try:
            from cornercheck.ledger.verify import verify_chain

            r = verify_chain()
            result.update({"ok": r.ok, "checked": r.checked, "detail": r.detail})
        except Exception as exc:
            log.warning("chain status failed (%s: %s)", type(exc).__name__, exc)
            result.update({"ok": None, "detail": "chain status unavailable"})

    t = threading.Thread(target=check, daemon=True)
    t.start()
    t.join(timeout=3.0)
    if t.is_alive():
        return {"ok": None, "detail": "chain status check timed out"}
    return result


def _db_counts() -> dict[str, Any]:
    from cornercheck.db.pool import get_pool

    # timeout=2: a public-endpoint read must fail soft fast, never park on the shared
    # pool's 30s wait queue ahead of the Slack clearance pipeline.
    with get_pool().connection(timeout=2) as conn:
        fighters = conn.execute("SELECT count(*) FROM fighters").fetchone()
        cases = conn.execute("SELECT count(*) FROM suspensions").fetchone()
        jx = conn.execute("SELECT count(DISTINCT jurisdiction) FROM suspensions").fetchone()
        decisions = conn.execute(
            "SELECT count(*) FROM ledger WHERE action = 'clearance_decision'"
        ).fetchone()
        monitor = conn.execute(
            "SELECT ts, payload FROM ledger WHERE action = 'monitor_run' ORDER BY seq DESC LIMIT 1"
        ).fetchone()
    out: dict[str, Any] = {
        "fighters": fighters[0] if fighters else None,
        "cases": cases[0] if cases else None,
        "jurisdictions": jx[0] if jx else None,
        "decisions": decisions[0] if decisions else None,
    }
    if monitor and isinstance(monitor[1], dict):
        f = monitor[1].get("findings") or {}
        out["monitor"] = {
            "at": monitor[0].isoformat()[:16].replace("T", " ") + " UTC",
            "lapsing": len(f.get("lapsing") or []),
            "lapsed": len(f.get("lapsed") or []),
            "alerted": bool(monitor[1].get("alerted")),
        }
    return out


# 30s result cache: an unauthenticated public endpoint must not be a lever that floods
# the shared DB pool (count(*) scans + a full chain re-verification per request would
# let a cheap GET flood starve the Slack clearance pipeline; adversarial review
# demonstrated the amplification). One refresh per window, everyone else gets the copy.
_STATS_TTL_S = 30.0
_stats_cache: dict[str, Any] | None = None
_stats_cached_at = 0.0
_stats_lock = threading.Lock()


def stats_payload() -> dict[str, Any]:
    """Everything the dashboard shows, each section independently fail-soft, cached."""
    global _stats_cache, _stats_cached_at
    with _stats_lock:
        if _stats_cache is not None and (time.monotonic() - _stats_cached_at) < _STATS_TTL_S:
            return _stats_cache
    payload: dict[str, Any] = {"generated_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}
    try:
        payload.update(_db_counts())
    except Exception as e:
        log.warning("dashboard counts unavailable (%s: %s)", type(e).__name__, e)
        payload["db"] = "unavailable"
    payload["chain"] = _chain_status()
    try:
        from cornercheck.er.conformal import load_gate

        gate = load_gate()
        if gate:
            payload["conformal"] = {"coverage_pct": gate.coverage_pct, "n": gate.n}
    except Exception as e:
        log.warning("dashboard conformal stat unavailable (%s: %s)", type(e).__name__, e)
    with _stats_lock:
        _stats_cache = payload
        _stats_cached_at = time.monotonic()
    return payload


def proof_payload() -> dict[str, Any]:
    """Run the REAL equivalence proof plus the non-vacuity control, timed. healthy is
    true ONLY for the exact (PROVEN, COUNTEREXAMPLE) pair; anything else is an alarm."""
    try:
        from cornercheck.verification.z3_safety import (
            counterexample_when_start_boundary_loosened,
            prove_engine_equivalent_to_spec,
        )

        t0 = time.monotonic()
        positive = prove_engine_equivalent_to_spec()
        control = counterexample_when_start_boundary_loosened()
        ms = max(1, round((time.monotonic() - t0) * 1000))
        return {
            "healthy": positive.proven and control.status == "COUNTEREXAMPLE",
            "proof": positive.status,
            "proof_detail": positive.detail,
            "control": control.status,
            "ms": ms,
        }
    except Exception as e:
        log.exception("dashboard proof run failed")
        return {
            "healthy": False,
            "proof": "ERROR",
            "proof_detail": f"{type(e).__name__}: the proof could not run; treat as unproven",
            "control": "ERROR",
            "ms": 0,
        }
