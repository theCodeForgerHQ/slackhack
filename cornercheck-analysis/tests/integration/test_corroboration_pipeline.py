"""Corroboration through the REAL pipeline: tighten flips the verdict, the ledger keeps
the evidence, unavailable sources never block, MMA fighters never trigger a live call."""

import uuid
from collections.abc import Iterator

import pytest

from cornercheck.brain.pipeline import start_clearance
from cornercheck.db.pool import get_pool
from cornercheck.sources import boxing_data, corroborate

TEST_NAME = "Zz Corrobo Testboxer"
TEST_MMA_NAME = "Zz Corrobo Testgrappler"


def _insert_fighter(name: str, sport: str) -> str:
    fid = str(uuid.uuid4())
    with get_pool().connection() as conn:
        conn.execute(
            "INSERT INTO fighters (id, full_name, weight_class, wins, losses, draws,"
            " sport, primary_jurisdiction, source)"
            " VALUES (%s, %s, 'Lightweight', 10, 0, 0, %s, 'Texas', 'test-fixture')",
            (fid, name, sport),
        )
    return fid


def _delete_fighter(fid: str, name: str) -> None:
    with get_pool().connection() as conn:
        conn.execute("DELETE FROM fighters WHERE id = %s", (fid,))
        conn.execute("DELETE FROM boxing_search_cache WHERE query_name = %s", (name.casefold(),))


@pytest.fixture
def test_boxer(db: str) -> Iterator[str]:
    """A throwaway boxing fighter WITH a record on file (10-0-0) and no suspensions.
    Self-contained: CI's Postgres is migrated but unseeded."""
    fid = _insert_fighter(TEST_NAME, "boxing")
    try:
        yield fid
    finally:
        _delete_fighter(fid, TEST_NAME)


@pytest.fixture
def test_mma_fighter(db: str) -> Iterator[str]:
    fid = _insert_fighter(TEST_MMA_NAME, "mma")
    try:
        yield fid
    finally:
        _delete_fighter(fid, TEST_MMA_NAME)


def _live_hit(wins: int, losses: int = 0, draws: int = 0) -> list[dict]:
    return [{"name": TEST_NAME, "stats": {"wins": wins, "losses": losses, "draws": draws}}]


def test_disagreement_tightens_clear_and_is_ledgered(
    test_boxer: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Live shows 12 bouts vs 10 on file: the rule verdict is CLEAR (no suspensions),
    # the corroboration must withhold it.
    monkeypatch.setattr(
        corroborate, "cached_search", lambda name: (_live_hit(12), "live", "2026-06-09T00:00:00")
    )
    v = start_clearance("t#corr1", TEST_NAME)
    assert v.status == "DO_NOT_CLEAR"
    assert corroborate.DISAGREEMENT_RULE in v.applied_rules
    assert v.corroboration is not None and v.corroboration.status == "DISAGREED"

    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT payload FROM ledger WHERE action = 'clearance_decision'"
            " ORDER BY seq DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    payload = row[0]
    assert payload["decision"] == "DO_NOT_CLEAR"  # the FINAL decision, post-tighten
    assert payload["corroboration"]["status"] == "DISAGREED"


def test_unavailable_source_leaves_verdict_standing(
    test_boxer: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(corroborate, "cached_search", lambda name: (None, "none", None))
    v = start_clearance("t#corr2", TEST_NAME)
    assert v.status == "CLEAR"
    assert v.corroboration is not None and v.corroboration.status == "UNAVAILABLE"


def test_consistent_record_stays_clear_with_live_note(
    test_boxer: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        corroborate, "cached_search", lambda name: (_live_hit(10), "live", "2026-06-09T00:00:00")
    )
    v = start_clearance("t#corr3", TEST_NAME)
    assert v.status == "CLEAR"
    assert v.corroboration is not None and v.corroboration.status == "CONFIRMED"
    assert v.corroboration.live_record == "10-0-0"


def test_mma_fighter_never_triggers_a_live_call(
    test_mma_fighter: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(name: str) -> None:
        raise AssertionError("live source must not be called for MMA fighters")

    monkeypatch.setattr(corroborate, "cached_search", boom)
    v = start_clearance("t#corr4", TEST_MMA_NAME)
    assert v.status == "CLEAR"
    assert v.corroboration is not None and v.corroboration.status == "NOT_APPLICABLE"


def test_cache_roundtrip_avoids_second_live_call(
    test_boxer: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = {"n": 0}

    def fake_live(name: str) -> list[dict]:
        calls["n"] += 1
        return _live_hit(10)

    monkeypatch.setattr(boxing_data, "search_fighters", fake_live)
    hits1, origin1, _ = boxing_data.cached_search(TEST_NAME)
    hits2, origin2, fetched2 = boxing_data.cached_search(TEST_NAME)
    assert calls["n"] == 1
    assert (origin1, origin2) == ("live", "cache")
    assert hits1 == hits2
    assert fetched2 is not None
