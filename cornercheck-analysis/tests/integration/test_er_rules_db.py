"""ER + rules against real Postgres with pg_trgm. Uses throwaway 'ZZ-Test' fighters so
it works on both an empty CI database and a fully seeded local database."""

from collections.abc import Iterator
from datetime import date, timedelta

import pytest

from cornercheck.db.pool import get_pool
from cornercheck.db.queries import evaluate_fighter_clearance, get_suspensions
from cornercheck.er.live_match import resolve

PREFIX = "ZZ-Test"


@pytest.fixture
def er_fixture(db: str) -> Iterator[dict[str, str]]:
    fighters = {
        "clean": f"{PREFIX} Merab Unique",
        "bruno_a": f"{PREFIX} Bruno Silva",
        "bruno_b": f"{PREFIX} Bruno Silva",
        "suspended": f"{PREFIX} Suspended Fighter",
    }
    ids: dict[str, str] = {}
    with get_pool().connection() as conn:
        for key, name in fighters.items():
            row = conn.execute(
                "INSERT INTO fighters (full_name, weight_class, wins, losses, draws, sport,"
                " source) VALUES (%s, 'Lightweight', 5, 1, 0, 'mma', 'integration-test')"
                " RETURNING id",
                (name,),
            ).fetchone()
            assert row is not None
            ids[key] = str(row[0])
        conn.execute(
            "INSERT INTO suspensions (fighter_id, suspension_type, start_date, end_date,"
            " indefinite, jurisdiction, reason, source_url) VALUES"
            " (%s, 'KO', %s, %s, false, 'Nevada (test)', 'KO loss', 'https://example.test')",
            (
                ids["suspended"],
                date.today() - timedelta(days=10),
                date.today() + timedelta(days=50),
            ),
        )
    yield ids
    with get_pool().connection() as conn:
        conn.execute("DELETE FROM fighters WHERE full_name LIKE %s", (f"{PREFIX} %",))


def test_exact_unique_name_confirms(er_fixture: dict[str, str]) -> None:
    r = resolve(f"{PREFIX} Merab Unique")
    assert r.status == "CONFIRMED"
    assert r.candidates[0].fighter_id == er_fixture["clean"]


def test_duplicate_real_names_disambiguate(er_fixture: dict[str, str]) -> None:
    r = resolve(f"{PREFIX} Bruno Silva")
    assert r.status == "AMBIGUOUS"
    ids = {c.fighter_id for c in r.candidates}
    assert {er_fixture["bruno_a"], er_fixture["bruno_b"]} <= ids


def test_typo_retrieves_into_disambiguation_not_refusal(er_fixture: dict[str, str]) -> None:
    r = resolve(f"{PREFIX} Bruno Sylva")
    # CONFIRMED here would mean one twin got dropped from retrieval, the exact crowding
    # bug the suite exists to catch: identical-name twins must ALWAYS disambiguate.
    assert r.status == "AMBIGUOUS"
    names = {c.full_name for c in r.candidates}
    assert any("Bruno Silva" in n for n in names)


def test_garbage_name_refuses(db: str) -> None:
    r = resolve("Zzyzx Qwerty Nonexistent")
    assert r.status == "NOT_FOUND"


def test_suspended_fixture_fighter_blocks_with_citation(er_fixture: dict[str, str]) -> None:
    verdict = evaluate_fighter_clearance(
        er_fixture["suspended"], date.today(), target_jurisdiction="Texas"
    )
    assert verdict.decision == "DO_NOT_CLEAR"
    assert verdict.active[0].source_url == "https://example.test"
    assert verdict.consultation_note is not None  # Nevada hold, Texas booking


def test_clean_fixture_fighter_clears(er_fixture: dict[str, str]) -> None:
    assert get_suspensions(er_fixture["clean"]) == []
    verdict = evaluate_fighter_clearance(er_fixture["clean"], date.today())
    assert verdict.decision == "CLEAR"
