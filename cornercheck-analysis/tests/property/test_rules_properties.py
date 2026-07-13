"""The fail-closed property in Hypothesis form: for ANY set of suspensions and ANY date,
CLEAR is returned if and only if NO suspension is active on that date."""

from datetime import date, timedelta

from hypothesis import given
from hypothesis import strategies as st

from cornercheck.rules.engine import Suspension, evaluate, suspension_interval

BASE = date(2026, 1, 1)

suspension_strategy = st.builds(
    Suspension,
    suspension_type=st.sampled_from(["KO", "TKO", "medical", "administrative"]),
    start_date=st.integers(min_value=-720, max_value=720).map(lambda d: BASE + timedelta(days=d)),
    end_date=st.just(None),
    indefinite=st.just(True),
    jurisdiction=st.sampled_from(["Nevada", "Texas (TDLR)", "CSAC", "Germany (BDB)"]),
    reason=st.just("prop"),
    source_url=st.just("https://example.test"),
)


def _bounded(s: Suspension, duration_days: int) -> Suspension:
    return Suspension(
        suspension_type=s.suspension_type,
        start_date=s.start_date,
        end_date=s.start_date + timedelta(days=duration_days),
        indefinite=False,
        jurisdiction=s.jurisdiction,
        reason=s.reason,
        source_url=s.source_url,
    )


mixed_suspensions = st.lists(
    st.tuples(suspension_strategy, st.integers(min_value=0, max_value=365), st.booleans()).map(
        lambda t: t[0] if t[2] else _bounded(t[0], t[1])
    ),
    max_size=6,
)
probe_dates = st.integers(min_value=-800, max_value=1200).map(lambda d: BASE + timedelta(days=d))


@given(mixed_suspensions, probe_dates)
def test_clear_iff_no_active_suspension(suspensions: list[Suspension], on: date) -> None:
    verdict = evaluate(suspensions, on)
    any_active = any(on in suspension_interval(s) for s in suspensions)
    if any_active:
        assert verdict.decision == "DO_NOT_CLEAR"
        assert len(verdict.active) >= 1
    else:
        assert verdict.decision == "CLEAR"
        assert verdict.active == []


@given(mixed_suspensions, probe_dates)
def test_every_active_suspension_is_cited(suspensions: list[Suspension], on: date) -> None:
    verdict = evaluate(suspensions, on)
    for s in verdict.active:
        assert s.source_url  # every blocking suspension carries its citation
