"""Persistent feedback log — Neo4j primary, local JSON fallback.

👍/👎 on a verdict is persisted across deploys so Verdict can track agreement.
`@Verdict stats` shows the running totals.
"""
import os
import json
import time

_F = os.path.join(os.path.dirname(__file__), "feedback.json")


def _get_neo4j():
    from memory import _get_neo4j as _neo4j
    return _neo4j()


# ---------------------------------------------------------------------------
# Neo4j backend
# ---------------------------------------------------------------------------
def _neo4j_log(claim: str, verdict: str, vote: str) -> bool:
    d = _get_neo4j()
    if not d:
        return False
    try:
        with d.session() as s:
            s.run(
                "CREATE (:Feedback {claim: $claim, verdict: $verdict, vote: $vote, ts: $ts})",
                claim=(claim or "")[:500], verdict=verdict, vote=vote, ts=time.time(),
            )
        return True
    except Exception:
        return False


def _neo4j_stats() -> tuple[int, int, int] | None:
    d = _get_neo4j()
    if not d:
        return None
    try:
        with d.session() as s:
            row = s.run(
                "MATCH (f:Feedback) "
                "RETURN sum(CASE f.vote WHEN 'up' THEN 1 ELSE 0 END) AS up, "
                "       sum(CASE f.vote WHEN 'down' THEN 1 ELSE 0 END) AS down, "
                "       count(f) AS total"
            ).single()
        if row:
            return int(row["up"]), int(row["down"]), int(row["total"])
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Local JSON fallback
# ---------------------------------------------------------------------------
def _json_log(claim: str, verdict: str, vote: str) -> None:
    try:
        data = json.load(open(_F)) if os.path.exists(_F) else []
    except Exception:
        data = []
    data.append({"claim": (claim or "")[:500], "verdict": verdict, "vote": vote, "ts": time.time()})
    try:
        json.dump(data, open(_F, "w"))
    except Exception:
        pass


def _json_stats() -> tuple[int, int, int]:
    try:
        data = json.load(open(_F)) if os.path.exists(_F) else []
    except Exception:
        data = []
    up   = sum(1 for d in data if d.get("vote") == "up")
    down = sum(1 for d in data if d.get("vote") == "down")
    return up, down, len(data)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def log_feedback(claim: str, verdict: str, vote: str) -> None:
    if not _neo4j_log(claim, verdict, vote):
        _json_log(claim, verdict, vote)


def stats() -> tuple[int, int, int]:
    """Return (up, down, total)."""
    return _neo4j_stats() or _json_stats()
