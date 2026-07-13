"""Calibrate the conformal identity gate against the REAL fighters table.

Deterministic (seeded): rerunning produces an identical artifact for the same data.
For every fighter we generate realistic query variants (the exact name, a one-edit
typo, and a dropped middle token where the name has one), score each variant against
the TRUE name with the exact same score the live gate uses (er.live_match.score_names),
and take nonconformity = 1 - score. Fighters are split alternately into a calibration
half (yields q_hat) and a holdout half (empirical coverage check, recorded in the
artifact); splitting BY FIGHTER keeps variants of one fighter out of both halves.

Run:  uv run python scripts/calibrate_er.py          # writes src/cornercheck/er/calibration.json
      uv run python scripts/calibrate_er.py --check  # recompute + verify the committed artifact
"""

import argparse
import json
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

from cornercheck.db.pool import get_pool
from cornercheck.er.conformal import conformal_quantile
from cornercheck.er.live_match import score_names

ALPHA = 0.05
SEED = 42
ARTIFACT = Path(__file__).resolve().parents[1] / "src" / "cornercheck" / "er" / "calibration.json"

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def typo(name: str, rng: random.Random) -> str:
    """One realistic single-edit typo, deterministic under the seeded rng."""
    s = list(name)
    if len(s) < 4:
        return name
    kind = rng.randrange(4)
    i = rng.randrange(1, len(s) - 1)
    if kind == 0:  # deletion
        del s[i]
    elif kind == 1:  # substitution
        s[i] = rng.choice(_ALPHABET)
    elif kind == 2:  # transposition
        s[i], s[i - 1] = s[i - 1], s[i]
    else:  # insertion
        s.insert(i, rng.choice(_ALPHABET))
    return "".join(s)


def variants(name: str, rng: random.Random) -> list[str]:
    out = [name, typo(name, rng)]
    tokens = name.split()
    if len(tokens) >= 3:
        out.append(" ".join(tokens[:1] + tokens[2:]))  # drop the second token
    return out


def build() -> dict[str, object]:
    with get_pool().connection() as conn:
        # COLLATE "C": byte-order sort, identical on every machine. The rng stream pairs
        # with the name sequence, so a collation-dependent order would make --check
        # report phantom drift across differently-configured databases.
        rows = conn.execute(
            'SELECT full_name FROM fighters ORDER BY full_name COLLATE "C"'
        ).fetchall()
    names = [r[0] for r in rows]
    if len(names) < 100:
        sys.exit(f"refusing to calibrate on {len(names)} fighters; seed the DB first")

    rng = random.Random(SEED)
    calib_scores: list[float] = []
    holdout_scores: list[float] = []
    for i, name in enumerate(names):
        bucket = calib_scores if i % 2 == 0 else holdout_scores
        for v in variants(name, rng):
            bucket.append(1.0 - score_names(v, name))

    q_hat = conformal_quantile(calib_scores, ALPHA)
    floor = 1.0 - q_hat
    covered = sum(1 for s in holdout_scores if (1.0 - s) >= floor)
    coverage = covered / len(holdout_scores)
    return {
        "alpha": ALPHA,
        "n": len(calib_scores),
        "q_hat": q_hat,
        "score_floor": floor,
        "holdout_n": len(holdout_scores),
        "holdout_coverage": round(coverage, 4),
        "seed": SEED,
        "fighters": len(names),
        "variant_scheme": "exact + one-edit typo + middle-token drop (names with 3+ tokens)",
        "score_fn": "er.live_match.score_names (normalized exact -> 1.0, else Jaro-Winkler)",
        "generated": datetime.now(UTC).isoformat(timespec="seconds"),
        "guarantee": (
            "split conformal: P(true fighter's score >= score_floor) >= 1 - alpha, "
            "marginal over exchangeable queries, conditional on retrieval"
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the committed artifact")
    args = ap.parse_args()
    doc = build()
    summary = (
        f"alpha={doc['alpha']} n={doc['n']} q_hat={doc['q_hat']:.6f} "
        f"floor={doc['score_floor']:.6f} holdout_coverage={doc['holdout_coverage']}"
    )
    if args.check:
        if not ARTIFACT.exists():
            sys.exit(f"no committed artifact at {ARTIFACT}; run without --check first")
        committed = json.loads(ARTIFACT.read_text())
        stable_keys = ["alpha", "n", "q_hat", "score_floor", "holdout_n", "holdout_coverage"]
        mismatch = [k for k in stable_keys if committed.get(k) != doc[k]]
        if mismatch:
            sys.exit(f"artifact DRIFTED on {mismatch}: recompute gave {summary}")
        print(f"artifact verified: {summary}")
        return
    ARTIFACT.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"wrote {ARTIFACT.name}: {summary}")


if __name__ == "__main__":
    main()
