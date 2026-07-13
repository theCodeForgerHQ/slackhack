"""Persistent verdict memory — cloud-first, local fallback.

Primary:  Neo4j AuraDB (free tier) — survives deploys, shared across instances
Fallback: SQLite (local dev only — lost on redeploy)

Two things stored:
- Verdict cache: same claim within TTL returns instantly without hitting the pipeline
- Recent context: last N verdicts fed to the synthesizer as background knowledge
"""
import os
import json
import time
import hashlib

from arblog import get_logger

_log = get_logger(__name__)
_TTL = 7 * 24 * 3600  # 7 days


def _hash(claim: str) -> str:
    return hashlib.sha256(claim.lower().strip().encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Neo4j backend (cloud, preferred)
# ---------------------------------------------------------------------------
_neo4j_driver = None
_neo4j_tried  = False


def _get_neo4j():
    global _neo4j_driver, _neo4j_tried
    if _neo4j_tried:
        return _neo4j_driver
    _neo4j_tried = True
    uri      = os.environ.get("NEO4J_URI", "")
    user     = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    if not uri or not password:
        return None
    try:
        from neo4j import GraphDatabase
        d = GraphDatabase.driver(uri, auth=(user, password))
        d.verify_connectivity()
        # Ensure unique constraint exists
        with d.session() as s:
            s.run("CREATE CONSTRAINT mem_hash IF NOT EXISTS "
                  "FOR (m:MemCache) REQUIRE m.hash IS UNIQUE")
        _neo4j_driver = d
        return d
    except Exception as e:
        _log.warning(f"Neo4j unavailable ({e}) — using local SQLite cache")
        return None


def _neo4j_lookup(claim: str) -> dict | None:
    d = _get_neo4j()
    if not d:
        return None
    try:
        with d.session() as s:
            row = s.run(
                "MATCH (m:MemCache {hash: $h}) WHERE m.ts > $cutoff "
                "RETURN m.verdict, m.confidence, m.reasoning, m.sources, m.ts",
                h=_hash(claim), cutoff=time.time() - _TTL,
            ).single()
        if row:
            return {
                "verdict":          row["m.verdict"],
                "confidence":       row["m.confidence"],
                "reasoning":        row["m.reasoning"] + "\n_(cached)_",
                "sources_resolved": json.loads(row["m.sources"] or "[]"),
                "panel": [], "route": "cached", "cached": True,
            }
    except Exception:
        pass
    return None


def _neo4j_save(claim: str, data: dict) -> bool:
    d = _get_neo4j()
    if not d:
        return False
    try:
        with d.session() as s:
            s.run(
                "MERGE (m:MemCache {hash: $h}) "
                "SET m.claim=$claim, m.verdict=$verdict, m.confidence=$confidence, "
                "    m.reasoning=$reasoning, m.sources=$sources, m.ts=$ts",
                h=_hash(claim), claim=claim[:500],
                verdict=str(data.get("verdict")),
                confidence=int(data.get("confidence") or 0),
                reasoning=str(data.get("reasoning", "")),
                sources=json.dumps(data.get("sources_resolved", [])),
                ts=time.time(),
            )
        return True
    except Exception:
        return False


def _neo4j_recent(n: int) -> str:
    d = _get_neo4j()
    if not d:
        return ""
    try:
        with d.session() as s:
            rows = s.run(
                "MATCH (m:MemCache) RETURN m.claim, m.verdict, m.confidence "
                "ORDER BY m.ts DESC LIMIT $n", n=n
            ).data()
        if not rows:
            return ""
        lines = "\n".join(
            f"- {r['m.verdict']} ({r['m.confidence']}%): {r['m.claim'][:100]}"
            for r in rows
        )
        return f"[Recent workspace verdicts]\n{lines}"
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# SQLite backend (local fallback)
# ---------------------------------------------------------------------------
import sqlite3
_DB = os.path.join(os.path.dirname(__file__), "verdict_memory.db")


def _sql_conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB)
    c.execute("""CREATE TABLE IF NOT EXISTS verdicts (
        claim_hash TEXT PRIMARY KEY, claim TEXT, verdict TEXT,
        confidence INTEGER, reasoning TEXT, sources TEXT, ts REAL
    )""")
    c.commit()
    return c


def _sql_lookup(claim: str) -> dict | None:
    try:
        row = _sql_conn().execute(
            "SELECT verdict, confidence, reasoning, sources, ts "
            "FROM verdicts WHERE claim_hash=?", (_hash(claim),)
        ).fetchone()
        if row and (time.time() - row[4]) < _TTL:
            return {
                "verdict":          row[0],
                "confidence":       row[1],
                "reasoning":        row[2] + "\n_(cached)_",
                "sources_resolved": json.loads(row[3] or "[]"),
                "panel": [], "route": "cached", "cached": True,
            }
    except Exception:
        pass
    return None


def _sql_save(claim: str, data: dict) -> None:
    try:
        c = _sql_conn()
        c.execute(
            "INSERT OR REPLACE INTO verdicts VALUES (?,?,?,?,?,?,?)",
            (_hash(claim), claim[:500], str(data.get("verdict")),
             int(data.get("confidence") or 0), str(data.get("reasoning", "")),
             json.dumps(data.get("sources_resolved", [])), time.time()),
        )
        c.commit()
    except Exception:
        pass


def _sql_recent(n: int) -> str:
    try:
        rows = _sql_conn().execute(
            "SELECT claim, verdict, confidence FROM verdicts ORDER BY ts DESC LIMIT ?", (n,)
        ).fetchall()
        if not rows:
            return ""
        lines = "\n".join(f"- {r[1]} ({r[2]}%): {r[0][:100]}" for r in rows)
        return f"[Recent workspace verdicts]\n{lines}"
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Public API — tries Neo4j first, falls back to SQLite
# ---------------------------------------------------------------------------
def lookup(claim: str) -> dict | None:
    return _neo4j_lookup(claim) or _sql_lookup(claim)


def save(claim: str, data: dict) -> None:
    if not _neo4j_save(claim, data):
        _sql_save(claim, data)


def recent_context(n: int = 5) -> str:
    return _neo4j_recent(n) or _sql_recent(n)
