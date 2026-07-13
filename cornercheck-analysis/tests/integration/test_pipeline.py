"""Deterministic pipeline e2e: Retrieve -> Disambiguate -> Clear, fail closed."""

from collections.abc import Iterator
from datetime import date, timedelta

import pytest

from cornercheck.brain.pipeline import confirm_candidate, start_clearance
from cornercheck.db.pool import get_pool
from cornercheck.session.state import SESSION_STORE

PREFIX = "ZZ-PipeTest"


@pytest.fixture
def pipe_fixture(db: str) -> Iterator[dict[str, str]]:
    ids: dict[str, str] = {}
    with get_pool().connection() as conn:
        for key, name in {
            "dup_a": f"{PREFIX} Twin Fighter",
            "dup_b": f"{PREFIX} Twin Fighter",
            "clean": f"{PREFIX} Solo Fighter",
        }.items():
            row = conn.execute(
                "INSERT INTO fighters (full_name, weight_class, wins, losses, draws, sport,"
                " source) VALUES (%s, 'Welterweight', 7, 2, 0, 'mma', 'pipe-test') RETURNING id",
                (name,),
            ).fetchone()
            assert row is not None
            ids[key] = str(row[0])
        conn.execute(
            "INSERT INTO suspensions (fighter_id, suspension_type, start_date, end_date,"
            " indefinite, jurisdiction, reason, source_url) VALUES"
            " (%s, 'KO', %s, %s, false, 'CSAC (test)', 'KO', 'https://example.test/csac')",
            (ids["dup_b"], date.today() - timedelta(days=3), date.today() + timedelta(days=57)),
        )
    yield ids
    with get_pool().connection() as conn:
        conn.execute("DELETE FROM fighters WHERE full_name LIKE %s", (f"{PREFIX} %",))


def test_ambiguous_name_fails_closed_to_disambiguation(pipe_fixture: dict[str, str]) -> None:
    v = start_clearance("th-amb", f"{PREFIX} Twin Fighter")
    assert v.status == "NEEDS_DISAMBIGUATION"
    assert len([c for c in v.candidates if "Twin Fighter" in c.full_name]) == 2
    assert v.fighter_id is None  # nothing decided; gate holds


def test_forged_confirmation_is_rejected(pipe_fixture: dict[str, str]) -> None:
    start_clearance("th-forge", f"{PREFIX} Twin Fighter")
    # A fighter_id not among the query's real candidates is rejected even with the query.
    assert (
        confirm_candidate(
            "th-forge", "00000000-0000-0000-0000-000000000000", query=f"{PREFIX} Twin Fighter"
        )
        is None
    )


def test_confirmation_validates_against_the_query_not_stale_state(
    pipe_fixture: dict[str, str],
) -> None:
    # Self-contained: a DIFFERENT thread_key still works because the button carries the
    # query, which we re-resolve to validate membership (fixes the live Select bug).
    v = confirm_candidate(
        "a-totally-different-thread",
        pipe_fixture["dup_b"],
        query=f"{PREFIX} Twin Fighter",
        target_jurisdiction="Texas",
    )
    assert v is not None and v.status == "DO_NOT_CLEAR"


def test_human_pick_completes_clearance_with_citation(pipe_fixture: dict[str, str]) -> None:
    start_clearance("th-pick", f"{PREFIX} Twin Fighter")
    v = confirm_candidate(
        "th-pick",
        pipe_fixture["dup_b"],
        query=f"{PREFIX} Twin Fighter",
        target_jurisdiction="Texas",
    )
    assert v is not None
    assert v.status == "DO_NOT_CLEAR"
    assert v.active_suspensions[0].source_url == "https://example.test/csac"
    assert v.consultation_note is not None
    assert v.ledger_seq is not None  # decision landed in the audit chain
    assert SESSION_STORE.get("th-pick").last_verdict_decision == "DO_NOT_CLEAR"


def test_unique_match_goes_straight_to_verdict(pipe_fixture: dict[str, str]) -> None:
    v = start_clearance("th-clean", f"{PREFIX} Solo Fighter")
    assert v.status == "CLEAR"
    assert v.fighter_name == f"{PREFIX} Solo Fighter"
    assert v.ledger_seq is not None
