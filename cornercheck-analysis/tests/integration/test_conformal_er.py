"""Conformal gate through the REAL resolve() path. Self-contained (CI's Postgres is
migrated but unseeded): every fighter used here is inserted by the test."""

import uuid
from collections.abc import Iterator

import pytest

from cornercheck.db.pool import get_pool
from cornercheck.er.live_match import resolve


@pytest.fixture
def fighters(db: str) -> Iterator[None]:
    rows = [
        (str(uuid.uuid4()), "Zz Conformal Unique"),
        (str(uuid.uuid4()), "Zz Clash Twin"),
        (str(uuid.uuid4()), "Zz Clash Twin"),
    ]
    with get_pool().connection() as conn:
        for fid, name in rows:
            conn.execute(
                "INSERT INTO fighters (id, full_name, weight_class, wins, losses, draws,"
                " sport, primary_jurisdiction, source)"
                " VALUES (%s, %s, NULL, 0, 0, 0, 'mma', NULL, 'test-fixture')",
                (fid, name),
            )
    try:
        yield
    finally:
        with get_pool().connection() as conn:
            for fid, _ in rows:
                conn.execute("DELETE FROM fighters WHERE id = %s", (fid,))


def test_unique_exact_name_is_certified_by_the_conformal_gate(fighters: None) -> None:
    r = resolve("Zz Conformal Unique")
    assert r.status == "CONFIRMED"
    assert "conformal singleton at 95% coverage" in r.note


def test_real_same_name_collision_still_fails_closed(fighters: None) -> None:
    r = resolve("Zz Clash Twin")
    assert r.status == "AMBIGUOUS"
    assert "share the name" in r.note


@pytest.fixture
def crowded_twins(db: str) -> Iterator[None]:
    """Two identical-name fighters buried under 60 partial-match decoys: an adversarial
    review showed an unordered retrieval LIMIT could drop one twin and let the survivor
    be 'confirmed' as unique. The exact-name-first ORDER BY must keep both visible."""
    rows = [(str(uuid.uuid4()), "Zq Crowd Twin"), (str(uuid.uuid4()), "Zq Crowd Twin")]
    rows += [(str(uuid.uuid4()), f"Aaa{i:02d} Zq Crowd Twin") for i in range(60)]
    with get_pool().connection() as conn:
        for fid, name in rows:
            conn.execute(
                "INSERT INTO fighters (id, full_name, weight_class, wins, losses, draws,"
                " sport, primary_jurisdiction, source)"
                " VALUES (%s, %s, NULL, 0, 0, 0, 'mma', NULL, 'test-fixture')",
                (fid, name),
            )
    try:
        yield
    finally:
        with get_pool().connection() as conn:
            for fid, _ in rows:
                conn.execute("DELETE FROM fighters WHERE id = %s", (fid,))


def test_same_name_twins_survive_retrieval_crowding(crowded_twins: None) -> None:
    r = resolve("Zq Crowd Twin")
    assert r.status == "AMBIGUOUS"
    assert "share the name" in r.note
