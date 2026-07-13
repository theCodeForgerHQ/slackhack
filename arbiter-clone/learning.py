"""Closed-loop preference learning — the honest, minimal version.

Feedback isn't just logged and displayed; it CHANGES behavior. Each judgment
mode carries a confidence threshold: a message must clear it before Arbiter
intervenes. Thumbs-down on a mode's output nudges that mode's threshold UP
(Arbiter becomes more reserved with a kind of intervention people reject);
thumbs-up nudges it back DOWN (toward its baseline).

This is a one-dimensional contextual bandit over intervention types: the arm is
the mode, the reward is human feedback, the action is how selective to be.
State lives in the Neo4j graph (same store as claims, predictions, and
interventions) as (:Learning {mode, offset}) nodes, with a per-workspace JSON
fallback — so it survives restarts and accumulates over time.

Bounded so it can never silence a mode entirely or fire on everything:
threshold stays within [baseline-10, baseline+25].
"""
import json
import os

from arblog import get_logger

log = get_logger(__name__)

# Per-mode baseline confidence to intervene (0-100). Substance is inverted
# (lower score = worse), handled by its own <45 gate, so it's excluded here.
BASELINES = {"claim": 80, "decision": 70, "delegate": 60}
_STEP_DOWN = 6   # a 👎 makes the mode this-many points more reserved
_STEP_UP = 3     # a 👍 relaxes it back toward baseline
_MIN_OFF, _MAX_OFF = -10, 25   # threshold can't drift outside baseline +/- this

_team_id = None
_cache: dict | None = None


def _team():
    global _team_id
    if _team_id is None:
        try:
            from slack_sdk import WebClient
            _team_id = WebClient(token=os.environ["SLACK_BOT_TOKEN"]).auth_test().get(
                "team_id", "unknown")
        except Exception:
            _team_id = "unknown"
    return _team_id


def _file():
    return os.path.join(os.path.dirname(__file__), f"learning_{_team()}.json")


def _load() -> dict:
    """mode -> offset. Neo4j primary (shared graph), JSON fallback."""
    global _cache
    if _cache is not None:
        return _cache
    # graph first
    try:
        from memory import _get_neo4j
        d = _get_neo4j()
        if d:
            with d.session() as s:
                rows = s.run("MATCH (l:Learning {team: $t}) RETURN l.mode, l.offset",
                             t=_team()).data()
            _cache = {r["l.mode"]: int(r["l.offset"]) for r in rows}
            return _cache
    except Exception:
        pass
    # json fallback
    try:
        _cache = json.load(open(_file()))
    except Exception:
        _cache = {}
    return _cache


def _save() -> None:
    """Persist current cache to the graph (per-mode nodes), else JSON."""
    try:
        from memory import _get_neo4j
        d = _get_neo4j()
        if d:
            with d.session() as s:
                for mode, off in (_cache or {}).items():
                    s.run("MERGE (l:Learning {team: $t, mode: $m}) SET l.offset = $o",
                          t=_team(), m=mode, o=int(off))
            return
    except Exception as e:
        log.warning(f"learning graph save failed ({e}) — JSON fallback")
    try:
        json.dump(_cache, open(_file(), "w"))
    except Exception:
        pass


def threshold(mode: str) -> int:
    """Current confidence threshold for a mode = baseline + learned offset."""
    base = BASELINES.get(mode)
    if base is None:
        return 0
    off = _load().get(mode, 0)
    return max(0, min(100, base + off))


def record(mode: str, vote: str) -> None:
    """Update a mode's offset from one 👍/👎. Bounded, persisted."""
    if mode not in BASELINES:
        return
    c = _load()
    off = c.get(mode, 0)
    off += _STEP_DOWN if vote == "down" else (-_STEP_UP if vote == "up" else 0)
    off = max(_MIN_OFF, min(_MAX_OFF, off))
    c[mode] = off
    _save()
    log.info(f"learning: {mode} threshold offset -> {off:+d} "
             f"(now {threshold(mode)}) after 👎/👍={vote}")


def summary() -> str:
    """Human-readable current state — for the audit/stats surfaces."""
    c = _load()
    if not any(c.get(m) for m in BASELINES):
        return "learning: at baseline (no preference signal yet)"
    parts = [f"{m} {threshold(m)}" + (f" ({c.get(m):+d})" if c.get(m) else "")
             for m in BASELINES]
    return "learned thresholds: " + " · ".join(parts)
