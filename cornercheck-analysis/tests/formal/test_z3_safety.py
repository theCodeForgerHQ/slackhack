"""Z3 formal-verification tests.

These verify the clearance engine, not a tautology: the engine's membership formula is proven
EQUIVALENT to an independently-written safety spec over all inputs, the proof is shown to have
teeth (it catches mutations + the real malformed-range bug it surfaced), and a Hypothesis
bridge binds the REAL Python engine to the spec on random inputs including malformed ranges.
"""

from datetime import date, timedelta

import pytest
import z3
from hypothesis import given
from hypothesis import strategies as st

from cornercheck.rules.engine import Suspension, evaluate, suspension_interval
from cornercheck.verification import z3_safety
from cornercheck.verification.z3_safety import (
    counterexample_pre_fix_malformed_range,
    counterexample_when_start_boundary_loosened,
    prove_engine_equivalent_to_spec,
    prove_engine_refines_safety_spec,
    prove_identity_gate,
)


@pytest.mark.parametrize("n", [1, 2, 3])
def test_engine_refines_independent_safety_spec(n: int) -> None:
    assert prove_engine_refines_safety_spec(n).proven


def test_engine_membership_equivalent_to_spec() -> None:
    assert prove_engine_equivalent_to_spec().proven


def test_identity_gate_is_proven() -> None:
    assert prove_identity_gate().proven


# --- The proof has teeth: it catches the real bug and deliberate mutations ----------------


def test_pre_fix_malformed_range_is_caught() -> None:
    r = counterexample_pre_fix_malformed_range()
    assert r.status == "COUNTEREXAMPLE"
    # The witness is a malformed range (end < start) queried on/after start.
    assert r.counterexample["end"] < r.counterexample["start"]
    assert r.counterexample["d"] >= r.counterexample["start"]


def test_loosened_start_boundary_is_caught() -> None:
    assert counterexample_when_start_boundary_loosened().status == "COUNTEREXAMPLE"


def test_refinement_proof_is_NOT_vacuous(monkeypatch: pytest.MonkeyPatch) -> None:
    """Directly answers the adversarial finding: if the engine formula is corrupted, the
    refinement proof must FAIL (return a counterexample), not stay green. We mutate
    engine_active to drop the malformed-range fail-closed branch and confirm Z3 catches it."""

    def broken_active(d: z3.ArithRef, start: z3.ArithRef, end: z3.ArithRef, open_ended: z3.BoolRef):  # type: ignore[no-untyped-def]
        return z3.And(d >= start, z3.Or(open_ended, d <= end))  # dropped `end < start`

    monkeypatch.setattr(z3_safety, "engine_active", broken_active)
    assert prove_engine_refines_safety_spec(1).status == "COUNTEREXAMPLE"


# --- Bridge: the REAL Python engine matches the spec on random inputs (incl. malformed) ----

BASE = date(2026, 1, 1)


def _spec_safe_to_clear(start: date, end: date | None, open_ended: bool, probe: date) -> bool:
    """Plain-Python mirror of _spec_must_block: it is safe to clear iff the suspension has not
    started, or it properly ended (well-formed bounded range, probe past end)."""
    if probe < start:
        return True
    properly_ended = (not open_ended) and end is not None and end >= start and probe > end
    return properly_ended


@given(
    start_off=st.integers(min_value=-500, max_value=500),
    end_off=st.integers(min_value=-700, max_value=700),  # can land BEFORE start (malformed)
    open_ended=st.booleans(),
    probe_off=st.integers(min_value=-700, max_value=900),
)
def test_real_engine_matches_independent_spec(
    start_off: int, end_off: int, open_ended: bool, probe_off: int
) -> None:
    start = BASE + timedelta(days=start_off)
    end = None if open_ended else BASE + timedelta(days=end_off)
    probe = BASE + timedelta(days=probe_off)
    s = Suspension(
        suspension_type="KO",
        start_date=start,
        end_date=end,
        indefinite=open_ended,
        jurisdiction="Test",
        reason="bridge",
        source_url="https://example.test",
    )
    engine_clears = evaluate([s], probe).decision == "CLEAR"
    spec_safe = _spec_safe_to_clear(start, end, open_ended, probe)
    assert engine_clears == spec_safe
    # And membership agrees with "engine cleared".
    assert (probe not in suspension_interval(s)) == engine_clears


def test_malformed_range_fails_closed_after_fix() -> None:
    """The fix itself: a suspension with end before start blocks from start onward."""
    s = Suspension(
        suspension_type="KO",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 4, 1),  # malformed: end before start
        indefinite=False,
        jurisdiction="Test",
        reason="swapped dates",
        source_url="https://example.test",
    )
    assert evaluate([s], date(2026, 6, 1)).decision == "DO_NOT_CLEAR"  # after start: blocked
    assert evaluate([s], date(2026, 4, 15)).decision == "CLEAR"  # before start: not yet suspended
