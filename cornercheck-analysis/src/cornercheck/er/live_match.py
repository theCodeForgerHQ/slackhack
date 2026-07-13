"""High-recall live retrieval: pg_trgm candidates re-scored with Jaro-Winkler.

Retrieve is deliberately loose (never miss a true match); the banding layer in
thresholds.py decides confirm/disambiguate/refuse.
"""

import jellyfish

from cornercheck.db.pool import get_pool
from cornercheck.er.names import norm
from cornercheck.er.thresholds import Candidate, ResolutionResult, band

_RETRIEVE_SQL = """
SELECT id, full_name, weight_class, wins, losses, draws, sport, primary_jurisdiction
FROM fighters
WHERE full_name %% %(q)s
   OR full_name ILIKE '%%' || %(q)s || '%%'
   OR lower(full_name) = lower(%(q)s)
ORDER BY (lower(full_name) = lower(%(q)s)) DESC, similarity(full_name, %(q)s) DESC
LIMIT 50
"""
# The ORDER BY is load-bearing for fail-closed identity: exact-name matches sort FIRST,
# so two fighters sharing the queried name can never be split by the LIMIT (an adversarial
# review demonstrated that an unordered LIMIT let a crowd of partial matches push a
# same-name twin out of the candidate set, and the banding layer then "confirmed" the
# survivor as unique). Trigram similarity orders the rest.


def score_names(query: str, name: str) -> float:
    """The one name-similarity function: used live for banding and offline by
    scripts/calibrate_er.py, so the conformal guarantee calibrates the exact score
    it gates."""
    q, n = norm(query), norm(name)
    if q == n:
        return 1.0
    return float(jellyfish.jaro_winkler_similarity(q, n))


def retrieve_candidates(query: str) -> list[Candidate]:
    with get_pool().connection() as conn:
        rows = conn.execute(_RETRIEVE_SQL, {"q": query}).fetchall()
    return [
        Candidate(
            fighter_id=str(r[0]),
            full_name=r[1],
            weight_class=r[2],
            record=f"{r[3]}-{r[4]}-{r[5]}",
            sport=r[6],
            jurisdiction=r[7],
            score=score_names(query, r[1]),
        )
        for r in rows
    ]


def resolve(query: str) -> ResolutionResult:
    """Retrieve -> band. The caller (agent brain) must honor AMBIGUOUS/NOT_FOUND."""
    return band(retrieve_candidates(query))
