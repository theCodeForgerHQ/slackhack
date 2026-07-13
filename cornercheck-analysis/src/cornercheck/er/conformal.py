"""Split-conformal certification of the identity gate.

The Z3 proof formally backs the RULES half of the fail-closed claim (an active
suspension can never yield CLEAR). This module statistically backs the IDENTITY half:
the match threshold stops being hand-tuned and becomes a calibrated quantile with a
finite-sample, distribution-free coverage guarantee (split conformal prediction:
Vovk et al.; Angelopoulos & Bates 2023, "Conformal Prediction: A Gentle Introduction").

Construction: for calibration pairs (query variant, true fighter) drawn from the real
fighters table, the nonconformity score is 1 - name_similarity. q_hat is the
ceil((n+1)(1-alpha))-th smallest calibration score; the prediction set at inference is
every candidate with similarity >= 1 - q_hat. With probability >= 1-alpha (marginal,
over exchangeable queries), the true fighter is in that set. So:
- a SINGLETON set certifies the identity at the 1-alpha level;
- a set with 2+ members means a runner-up is statistically plausible: fail closed to
  a human pick (Chow's reject rule, with a calibrated threshold);
- an empty set means even the top candidate is implausible: refuse.

Scope, stated honestly: the guarantee is marginal (not per-query) and conditional on
the true fighter being among the retrieved candidates (retrieval is deliberately
high-recall). The calibration artifact is committed and regenerated deterministically
by scripts/calibrate_er.py against the real database.

Fail-closed composition: this gate can only DEMOTE a legacy CONFIRMED (set not a
singleton), never promote. Too little calibration data yields q_hat = infinity, and
load_gate refuses any artifact with q_hat outside [0, 1), disabling the gate entirely
(legacy bands only, annotated): an unusable quantile would otherwise put EVERY
candidate in the prediction set and mint meaningless singleton certifications.
A missing/corrupt artifact disables the gate the same way.
"""

import json
import logging
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

log = logging.getLogger("cornercheck.conformal")

_ARTIFACT = Path(__file__).parent / "calibration.json"


def conformal_quantile(scores: list[float], alpha: float) -> float:
    """The finite-sample split-conformal quantile: the ceil((n+1)(1-alpha))-th smallest
    nonconformity score. Returns inf when n is too small for the level; load_gate
    rejects such an artifact and disables the gate (constructing a ConformalGate with
    an infinite q_hat directly would certify every single-candidate retrieval, the
    OPPOSITE of fail-closed, which is why validation lives at load time)."""
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")
    n = len(scores)
    if n == 0:
        return float("inf")
    k = math.ceil((n + 1) * (1.0 - alpha))
    if k > n:
        return float("inf")
    return sorted(scores)[k - 1]


@dataclass(frozen=True)
class ConformalGate:
    """A calibrated identity gate. score_floor is the similarity a candidate needs to
    enter the prediction set."""

    alpha: float
    n: int
    q_hat: float

    @property
    def score_floor(self) -> float:
        return 1.0 - self.q_hat

    @property
    def coverage_pct(self) -> int:
        return round((1.0 - self.alpha) * 100)

    def prediction_set_size(self, scores: list[float]) -> int:
        return sum(1 for s in scores if s >= self.score_floor)

    def certifies(self, scores: list[float]) -> bool:
        """True only when exactly ONE candidate is statistically plausible."""
        return self.prediction_set_size(scores) == 1


def gate_from_artifact(doc: dict[str, Any]) -> ConformalGate:
    return ConformalGate(alpha=float(doc["alpha"]), n=int(doc["n"]), q_hat=float(doc["q_hat"]))


@lru_cache
def load_gate() -> ConformalGate | None:
    """The committed calibration artifact, or None (gate disabled, annotated) when it
    is missing or unreadable. The legacy bands stay in force either way; this layer
    only ever tightens."""
    try:
        doc = json.loads(_ARTIFACT.read_text())
        gate = gate_from_artifact(doc)
    except Exception as e:
        log.warning(
            "conformal calibration artifact unavailable (%s: %s); identity gate runs on "
            "legacy bands only",
            type(e).__name__,
            e,
        )
        return None
    if not (0.0 < gate.alpha < 1.0) or gate.n <= 0 or not (0.0 <= gate.q_hat < 1.0):
        # Nonconformity is 1 - similarity, so a usable q_hat lives in [0, 1). Anything
        # outside (inf from too little data, a corrupt 2.0, a negative) would put every
        # candidate in the set or none: a single retrieved candidate would then read as
        # a meaningless "singleton certification", or every confirmation would silently
        # mass-demote. Disable the gate instead (the comparison also rejects NaN).
        log.warning("conformal artifact has unusable values (%s); gate disabled", doc)
        return None
    return gate
