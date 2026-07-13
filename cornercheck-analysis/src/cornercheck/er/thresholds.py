"""Banding logic: the fail-closed identity gate.

Two layers, composed tighten-only:
- legacy bands: CONFIRMED only when the top score clears T_HIGH, beats the runner-up
  by MARGIN, and the name is unique among candidates; identical normalized names
  ALWAYS disambiguate (two real UFC "Bruno Silva"s); below T_LOW refuse (NOT_FOUND)
- conformal gate (er/conformal.py): a legacy CONFIRMED is certified only if the
  calibrated prediction set is a SINGLETON; a statistically plausible runner-up
  demotes to AMBIGUOUS. The gate can never promote, and when its artifact is
  unavailable the legacy bands stand alone (annotated).
"""

from dataclasses import dataclass, field
from typing import Literal

from cornercheck.er.conformal import ConformalGate, load_gate
from cornercheck.er.names import norm as _norm

T_HIGH = 0.95
T_LOW = 0.82
MARGIN = 0.04
MAX_CANDIDATES = 5


@dataclass(frozen=True)
class Candidate:
    fighter_id: str
    full_name: str
    weight_class: str | None
    record: str
    sport: str
    jurisdiction: str | None
    score: float


@dataclass(frozen=True)
class ResolutionResult:
    status: Literal["CONFIRMED", "AMBIGUOUS", "NOT_FOUND"]
    candidates: list[Candidate] = field(default_factory=list)
    note: str = ""


def band(candidates: list[Candidate], gate: ConformalGate | None = None) -> ResolutionResult:
    """gate=None loads the committed calibration artifact; tests inject their own.
    The conformal layer composes tighten-only: it can demote a CONFIRMED, never
    promote anything."""
    if gate is None:
        gate = load_gate()
    ranked = sorted(candidates, key=lambda c: c.score, reverse=True)[:MAX_CANDIDATES]
    if not ranked or ranked[0].score < T_LOW:
        return ResolutionResult(
            "NOT_FOUND",
            ranked,
            note="no candidate met the minimum match threshold; refusing to guess",
        )
    top = ranked[0]
    same_name = [c for c in ranked if _norm(c.full_name) == _norm(top.full_name)]
    if len(same_name) >= 2:
        return ResolutionResult(
            "AMBIGUOUS",
            ranked,
            note=f"{len(same_name)} fighters share the name {top.full_name!r}; human pick required",
        )
    runner_up_gap = top.score - ranked[1].score if len(ranked) > 1 else 1.0
    if top.score >= T_HIGH and runner_up_gap >= MARGIN:
        scores = [c.score for c in ranked]
        if gate is None:
            return ResolutionResult(
                "CONFIRMED",
                [top],
                note="unique high-confidence match (conformal calibration unavailable; "
                "legacy bands only)",
            )
        if not gate.certifies(scores):
            n_set = gate.prediction_set_size(scores)
            if n_set == 0:
                # Even the top candidate is outside the calibrated set: refuse, as the
                # conformal contract documents. Still a demotion, never a promotion.
                return ResolutionResult(
                    "NOT_FOUND",
                    ranked,
                    note=(
                        "even the top candidate falls outside the conformal prediction "
                        f"set at {gate.coverage_pct}% coverage; refusing to guess"
                    ),
                )
            return ResolutionResult(
                "AMBIGUOUS",
                ranked,
                note=(
                    f"{n_set} candidates fall inside the conformal prediction set at "
                    f"{gate.coverage_pct}% coverage; a runner-up is statistically "
                    "plausible, human pick required"
                ),
            )
        return ResolutionResult(
            "CONFIRMED",
            [top],
            note=(
                "unique high-confidence match; conformal singleton at "
                f"{gate.coverage_pct}% coverage (n={gate.n})"
            ),
        )
    return ResolutionResult("AMBIGUOUS", ranked, note="match confidence in the disambiguation band")
