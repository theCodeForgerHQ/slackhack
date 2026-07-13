"""Credit & prediction ledger — two views over the claim graph.

Credit ("who said it first"): when a claim Arbiter verifies matches an earlier
claim by a different author, surface the original author — phrased as a gift,
never an accusation.

Predictions (Oracle): claims about the future get logged with a resolution date.
`@Arbiter ledger` lists open predictions; `resolve_due()` fact-checks the ones
whose date has passed and records hit/miss. Over time the workspace gets an
honest calibration record.

Storage: Neo4j (Prediction nodes) with a local JSON fallback, same pattern as
feedback.py.
"""
import os
import json
import time
import datetime as _dt

from llm import _chat, _parse, ROUTER
import knowledge_graph as _kg
from memory import _get_neo4j

_F = os.path.join(os.path.dirname(__file__), "predictions.json")

_PREDICTION_SYSTEM = (
    "Does this message contain a concrete prediction — a checkable statement about "
    "a FUTURE event or outcome with at least a rough timeframe? Respond ONLY with "
    'JSON: "is_prediction" (boolean), '
    '"prediction" (the prediction as one self-contained sentence), '
    '"resolve_by" (ISO date YYYY-MM-DD when it can be judged; null if unclear).'
)


# ---------------------------------------------------------------------------
# Credit
# ---------------------------------------------------------------------------
def credit_line(claim: str, author: str) -> str:
    """A short credit note if someone else raised this first, else ''."""
    if not author:
        return ""
    earlier = _kg.find_earlier(claim, author)
    if not earlier:
        return ""
    when = _dt.datetime.fromtimestamp(earlier["ts"]).strftime("%b %-d") \
        if os.name != "nt" else _dt.datetime.fromtimestamp(earlier["ts"]).strftime("%b %d")
    link = f" (<{earlier['permalink']}|original>)" if earlier.get("permalink") else ""
    return f"🪙 {earlier['author']} raised this first on {when}{link}"


# ---------------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------------
def detect_prediction(text: str) -> dict | None:
    """Return {prediction, resolve_by} if the text contains one, else None."""
    try:
        d = _parse(_chat(ROUTER[0], ROUTER[1], _PREDICTION_SYSTEM,
                         f"MESSAGE: {text[:1500]}", temperature=0))
    except Exception:
        return None
    if not d.get("is_prediction") or not d.get("prediction"):
        return None
    return {"prediction": str(d["prediction"])[:400],
            "resolve_by": str(d.get("resolve_by") or "")[:10] or None}


def log_prediction(prediction: str, author: str, resolve_by: str | None,
                   permalink: str = "") -> None:
    rec = {"prediction": prediction[:400], "author": author[:80],
           "resolve_by": resolve_by, "permalink": permalink[:300],
           "ts": time.time(), "outcome": None}
    try:  # mirror into the native Slack List (best-effort)
        import lists_sync
        lists_sync.add_prediction(rec["prediction"], rec["author"], resolve_by)
    except Exception:
        pass
    d = _get_neo4j()
    if d:
        try:
            with d.session() as s:
                s.run("CREATE (:Prediction {prediction:$prediction, author:$author, "
                      "resolve_by:$resolve_by, permalink:$permalink, ts:$ts, outcome:null})",
                      **{k: rec[k] for k in
                         ("prediction", "author", "resolve_by", "permalink", "ts")})
            return
        except Exception:
            pass
    _json_append(rec)


def open_predictions(limit: int = 8) -> list[dict]:
    d = _get_neo4j()
    if d:
        try:
            with d.session() as s:
                rows = s.run(
                    "MATCH (p:Prediction) WHERE p.outcome IS NULL "
                    "RETURN p.prediction, p.author, p.resolve_by, p.ts "
                    "ORDER BY p.ts DESC LIMIT $n", n=limit).data()
            return [{"prediction": r["p.prediction"], "author": r["p.author"],
                     "resolve_by": r["p.resolve_by"], "ts": r["p.ts"]} for r in rows]
        except Exception:
            pass
    return [r for r in _json_load() if r.get("outcome") is None][:limit]


def resolve_due(verify_fn) -> list[dict]:
    """Fact-check predictions whose resolve_by date has passed.

    verify_fn: callable(claim) -> verdict dict (llm.verify_claim, injected to
    avoid a circular import). Returns the resolved records.
    """
    today = _dt.date.today().isoformat()
    resolved = []
    for rec in open_predictions(20):
        rb = rec.get("resolve_by")
        if not rb or rb > today:
            continue
        try:
            data = verify_fn(rec["prediction"])
            verdict = str(data.get("verdict", "Unverifiable"))
        except Exception:
            continue
        if verdict in ("True", "False"):
            outcome = "hit" if verdict == "True" else "miss"
            _mark_outcome(rec, outcome)
            resolved.append({**rec, "outcome": outcome})
    return resolved


def scoreboard() -> tuple[int, int]:
    """(hits, misses) across resolved predictions."""
    d = _get_neo4j()
    if d:
        try:
            with d.session() as s:
                row = s.run(
                    "MATCH (p:Prediction) WHERE p.outcome IS NOT NULL "
                    "RETURN sum(CASE p.outcome WHEN 'hit' THEN 1 ELSE 0 END) AS h, "
                    "       sum(CASE p.outcome WHEN 'miss' THEN 1 ELSE 0 END) AS m"
                ).single()
            if row:
                return int(row["h"] or 0), int(row["m"] or 0)
        except Exception:
            pass
    data = _json_load()
    return (sum(1 for r in data if r.get("outcome") == "hit"),
            sum(1 for r in data if r.get("outcome") == "miss"))


def _mark_outcome(rec: dict, outcome: str) -> None:
    try:  # flip the native Slack List row too (best-effort)
        import lists_sync
        lists_sync.mark_prediction(rec["prediction"], outcome)
    except Exception:
        pass
    d = _get_neo4j()
    if d:
        try:
            with d.session() as s:
                s.run("MATCH (p:Prediction {prediction:$p}) WHERE p.outcome IS NULL "
                      "SET p.outcome=$o", p=rec["prediction"], o=outcome)
            return
        except Exception:
            pass
    data = _json_load()
    for r in data:
        if r.get("prediction") == rec["prediction"] and r.get("outcome") is None:
            r["outcome"] = outcome
    _json_dump(data)


# ---------------------------------------------------------------------------
# JSON fallback helpers
# ---------------------------------------------------------------------------
def _json_load() -> list[dict]:
    try:
        return json.load(open(_F)) if os.path.exists(_F) else []
    except Exception:
        return []


def _json_dump(data: list[dict]) -> None:
    try:
        json.dump(data, open(_F, "w"))
    except Exception:
        pass


def _json_append(rec: dict) -> None:
    data = _json_load()
    data.append(rec)
    _json_dump(data)
