"""Neo4j AuraDB knowledge graph for Verdict — persists claims, verdicts, and
relationships across sessions. Falls back gracefully if Neo4j isn't configured.

Free tier at console.neo4j.io: 200K nodes / 400K relationships — more than enough.

Graph schema:
  (:Claim {hash, text, verdict, confidence, ts})
  (:Source {url, title, kind})
  (:Claim)-[:CITES]->(:Source)
  (:Claim)-[:CONTRADICTS]->(:Claim)   # same topic, opposite verdict
  (:Claim)-[:SUPPORTS]->(:Claim)      # same topic, same verdict
"""
import os
import hashlib
import time

from arblog import get_logger

_log = get_logger(__name__)
_driver = None


def _get_driver():
    global _driver
    if _driver is not None:
        return _driver
    uri = os.environ.get("NEO4J_URI", "")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    if not uri or not password:
        return None
    try:
        from neo4j import GraphDatabase
        d = GraphDatabase.driver(uri, auth=(user, password))
        d.verify_connectivity()
        _driver = d
        _init_schema()
        _log.info("Connected to Neo4j AuraDB")
        return _driver
    except Exception as e:
        _log.warning(f"Neo4j unavailable: {e} — running without cloud graph")
        return None


def _init_schema():
    """Create constraints once on first connect."""
    try:
        with _driver.session() as s:
            s.run("CREATE CONSTRAINT claim_hash IF NOT EXISTS FOR (c:Claim) REQUIRE c.hash IS UNIQUE")
            s.run("CREATE CONSTRAINT source_url IF NOT EXISTS FOR (s:Source) REQUIRE s.url IS UNIQUE")
    except Exception:
        pass


def _hash(text: str) -> str:
    return hashlib.sha256(text.lower().strip().encode()).hexdigest()[:16]


def save_claim(claim: str, verdict: str, confidence: int, sources: list[dict],
               author: str = "", permalink: str = "") -> None:
    """Persist a verified claim and its sources. Link to related prior claims.

    author/permalink (optional) power the credit ledger — "who said it first".
    """
    d = _get_driver()
    if not d:
        return
    try:
        h = _hash(claim)
        with d.session() as s:
            s.run(
                "MERGE (c:Claim {hash: $h}) "
                "SET c.text=$text, c.verdict=$verdict, c.confidence=$confidence, c.ts=$ts "
                + (", c.author=$author, c.permalink=$permalink" if author else ""),
                h=h, text=claim[:500], verdict=verdict,
                confidence=confidence, ts=time.time(),
                author=author[:80], permalink=permalink[:300],
            )
            for src in sources:
                url = src.get("url", "")
                if not url:
                    continue
                s.run(
                    "MERGE (s:Source {url: $url}) SET s.title=$title, s.kind=$kind "
                    "WITH s MATCH (c:Claim {hash: $h}) MERGE (c)-[:CITES]->(s)",
                    url=url, title=src.get("title", ""), kind=src.get("kind", "WEB"), h=h,
                )
            # Link to claims with the same rough topic but opposite verdict (CONTRADICTS)
            opp = "False" if verdict == "True" else ("True" if verdict == "False" else None)
            if opp:
                s.run(
                    "MATCH (other:Claim {verdict: $opp}) "
                    "WHERE other.hash <> $h AND other.ts > $cutoff "
                    "WITH other LIMIT 3 "
                    "MATCH (c:Claim {hash: $h}) MERGE (c)-[:CONTRADICTS]->(other)",
                    opp=opp, h=h, cutoff=time.time() - 30 * 24 * 3600,
                )
    except Exception:
        pass


def find_earlier(claim: str, author: str) -> dict | None:
    """Credit ledger: earliest similar claim by a DIFFERENT author, if any.

    Returns {author, text, ts, permalink} or None. Used to phrase credit as a
    gift ("Maya raised this June 2"), never as an accusation.
    """
    d = _get_driver()
    if not d:
        return None
    try:
        words = [w for w in claim.lower().split() if len(w) > 4][:5]
        if len(words) < 2:
            return None
        pattern = "|".join(words)
        with d.session() as s:
            row = s.run(
                "MATCH (c:Claim) WHERE c.author IS NOT NULL AND c.author <> '' "
                "AND c.author <> $author AND c.text =~ $pat "
                "RETURN c.author, c.text, c.ts, c.permalink ORDER BY c.ts ASC LIMIT 1",
                author=author, pat=f"(?i).*({pattern}).*",
            ).single()
        if row:
            return {"author": row["c.author"], "text": row["c.text"],
                    "ts": row["c.ts"], "permalink": row["c.permalink"] or ""}
    except Exception:
        pass
    return None


def find_related(claim: str, limit: int = 3) -> str:
    """Return a short summary of related previously verified claims — fed to synthesizer."""
    d = _get_driver()
    if not d:
        return ""
    try:
        h = _hash(claim)
        words = [w for w in claim.lower().split() if len(w) > 4][:5]
        if not words:
            return ""
        pattern = "|".join(words)
        with d.session() as s:
            rows = s.run(
                "MATCH (c:Claim) WHERE c.hash <> $h AND c.text =~ $pat "
                "RETURN c.text, c.verdict, c.confidence ORDER BY c.ts DESC LIMIT $limit",
                h=h, pat=f"(?i).*({pattern}).*", limit=limit,
            ).data()
        if not rows:
            return ""
        lines = "\n".join(
            f"- {r['c.verdict']} ({r['c.confidence']}%): {r['c.text'][:100]}"
            for r in rows
        )
        return f"[Related verified claims from knowledge graph]\n{lines}"
    except Exception:
        return ""
