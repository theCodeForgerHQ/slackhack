"""The conformal identity gate: exact quantile math, tighten-only composition, and the
fail-closed degenerate paths."""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cornercheck.er import thresholds
from cornercheck.er.conformal import ConformalGate, conformal_quantile, load_gate
from cornercheck.er.thresholds import Candidate, band

# A synthetic gate with a floor just under T_HIGH (the committed artifact's shape),
# injected so these tests stay pinned regardless of recalibration.
GATE = ConformalGate(alpha=0.05, n=4197, q_hat=0.053)


def _cand(name: str, score: float) -> Candidate:
    return Candidate(
        fighter_id=f"id-{name}-{score}",
        full_name=name,
        weight_class=None,
        record="0-0-0",
        sport="mma",
        jurisdiction=None,
        score=score,
    )


# --- the quantile itself ---------------------------------------------------------------


def test_quantile_exact_small_cases() -> None:
    # k = ceil((n+1)(1-alpha)); n=3, alpha=0.25 -> k=3 -> third smallest
    assert conformal_quantile([0.3, 0.1, 0.2], 0.25) == 0.3
    # n=3, alpha=0.5 -> k=2 -> second smallest
    assert conformal_quantile([0.3, 0.1, 0.2], 0.5) == 0.2


def test_quantile_insufficient_data_is_infinite() -> None:
    assert conformal_quantile([], 0.05) == float("inf")
    # n=1, alpha=0.05 -> k=2 > n -> inf (certify nothing, the fail-closed direction)
    assert conformal_quantile([0.1], 0.05) == float("inf")


def test_quantile_rejects_nonsense_alpha() -> None:
    for alpha in (0.0, 1.0, -0.1, 2.0):
        with pytest.raises(ValueError):
            conformal_quantile([0.1], alpha)


@given(
    scores=st.lists(st.floats(min_value=0.0, max_value=1.0), min_size=1, max_size=200),
    a1=st.floats(min_value=0.01, max_value=0.98),
    a2=st.floats(min_value=0.01, max_value=0.98),
)
def test_quantile_monotone_in_alpha_and_from_the_sample(
    scores: list[float], a1: float, a2: float
) -> None:
    lo, hi = sorted((a1, a2))
    q_strict, q_loose = conformal_quantile(scores, lo), conformal_quantile(scores, hi)
    # Stricter coverage (smaller alpha) can only raise the quantile.
    assert q_strict >= q_loose
    for q in (q_strict, q_loose):
        assert q == float("inf") or q in scores


# --- the gate --------------------------------------------------------------------------


def test_gate_certifies_only_singletons() -> None:
    assert GATE.score_floor == pytest.approx(0.947)
    assert GATE.certifies([0.99, 0.90])  # runner-up below the floor
    assert not GATE.certifies([0.99, 0.948])  # runner-up statistically plausible
    assert not GATE.certifies([0.90])  # top itself below the floor


# --- tighten-only composition in band() ------------------------------------------------


def test_band_demotes_legacy_confirmed_when_runner_up_is_plausible() -> None:
    # Legacy says CONFIRMED (top >= 0.95, gap >= 0.04, unique name); the conformal set
    # has 2 members, so the gate must demote to AMBIGUOUS.
    r = band([_cand("Alpha Fighter", 0.99), _cand("Alphonse Fightir", 0.948)], gate=GATE)
    assert r.status == "AMBIGUOUS"
    assert "conformal prediction set" in r.note


def test_band_certifies_when_set_is_singleton() -> None:
    r = band([_cand("Alpha Fighter", 0.99), _cand("Someone Else", 0.90)], gate=GATE)
    assert r.status == "CONFIRMED"
    assert "conformal singleton at 95% coverage" in r.note


def test_band_never_promotes() -> None:
    # Same normalized name: ALWAYS ambiguous, no matter what the gate says.
    r = band([_cand("Bruno Silva", 1.0), _cand("Bruno Silva", 1.0)], gate=GATE)
    assert r.status == "AMBIGUOUS"
    # Below T_LOW: refusal stands.
    assert band([_cand("Distant Name", 0.5)], gate=GATE).status == "NOT_FOUND"
    # In the legacy disambiguation band: stays AMBIGUOUS even with a singleton set.
    r = band([_cand("Alpha Fighter", 0.94), _cand("Someone Else", 0.80)], gate=GATE)
    assert r.status == "AMBIGUOUS"


def test_band_refuses_when_even_the_top_is_outside_the_set() -> None:
    # A stricter recalibration can push the floor above T_HIGH; an empty prediction set
    # must refuse with a truthful note, not offer a pick list of implausible candidates.
    strict = ConformalGate(alpha=0.05, n=5000, q_hat=0.01)  # floor 0.99
    r = band([_cand("Alpha Fighter", 0.96), _cand("Someone Else", 0.80)], gate=strict)
    assert r.status == "NOT_FOUND"
    assert "refusing to guess" in r.note


def test_band_without_gate_annotates_legacy_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(thresholds, "load_gate", lambda: None)
    r = band([_cand("Alpha Fighter", 0.99), _cand("Someone Else", 0.90)])
    assert r.status == "CONFIRMED"
    assert "conformal calibration unavailable" in r.note


def test_committed_artifact_loads_and_is_sane() -> None:
    load_gate.cache_clear()
    gate = load_gate()
    assert gate is not None
    assert gate.alpha == 0.05
    assert gate.n > 1000
    assert math.isfinite(gate.q_hat)
    assert 0.90 < gate.score_floor < 1.0


@pytest.mark.parametrize(
    "doc",
    [
        '{"alpha": 0.05, "n": 1, "q_hat": Infinity}',  # inf: meaningless singletons
        '{"alpha": 0.05, "n": 100, "q_hat": 1.5}',  # floor <= 0: everything "in set"
        '{"alpha": 0.05, "n": 100, "q_hat": -0.5}',  # floor > 1: silent mass-demotion
        '{"alpha": 0.05, "n": 100, "q_hat": NaN}',  # NaN
        '{"alpha": 0.0, "n": 100, "q_hat": 0.05}',  # nonsense alpha
        '{"alpha": 0.05, "n": 0, "q_hat": 0.05}',  # no calibration data
        "not json at all",
    ],
)
def test_unusable_artifacts_disable_the_gate(
    doc: str, monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    from pathlib import Path

    from cornercheck.er import conformal

    bad = Path(str(tmp_path)) / "calibration.json"
    bad.write_text(doc)
    monkeypatch.setattr(conformal, "_ARTIFACT", bad)
    load_gate.cache_clear()
    try:
        assert load_gate() is None
    finally:
        load_gate.cache_clear()
