"""clear_card e2e: a whole card runs through the real fail-closed pipeline, each fighter
isolated, the batch ledgered."""

from collections.abc import Iterator
from datetime import date, timedelta

import pytest

from cornercheck.brain.pipeline import clear_card
from cornercheck.db.pool import get_pool

PREFIX = "ZZ-CardTest"


@pytest.fixture
def card_fixture(db: str) -> Iterator[dict[str, str]]:
    ids: dict[str, str] = {}
    with get_pool().connection() as conn:
        # Names chosen mutually distinct (pairwise Jaro-Winkler <= 0.89, below the
        # conformal floor): the gate correctly demotes near-identical fixture names,
        # and this test is about banding statuses, not near-tie demotion.
        for key, name in {
            "clean": f"{PREFIX} Amara Okafor",
            "held": f"{PREFIX} Brick Vandergelder",
            "dup_a": f"{PREFIX} Twin Card",
            "dup_b": f"{PREFIX} Twin Card",
        }.items():
            row = conn.execute(
                "INSERT INTO fighters (full_name, weight_class, wins, losses, draws, sport,"
                " source) VALUES (%s, 'Welterweight', 5, 1, 0, 'mma', 'card-test') RETURNING id",
                (name,),
            ).fetchone()
            assert row is not None
            ids[key] = str(row[0])
        conn.execute(
            "INSERT INTO suspensions (fighter_id, suspension_type, start_date, end_date,"
            " indefinite, jurisdiction, reason, source_url) VALUES"
            " (%s, 'KO', %s, %s, false, 'CSAC (test)', 'KO', 'https://example.test/csac')",
            (ids["held"], date.today() - timedelta(days=3), date.today() + timedelta(days=57)),
        )
    yield ids
    with get_pool().connection() as conn:
        conn.execute("DELETE FROM fighters WHERE full_name LIKE %s", (f"{PREFIX} %",))


def test_clear_card_bands_each_fighter(card_fixture: dict[str, str]) -> None:
    verdicts = clear_card(
        "card-thread",
        [f"{PREFIX} Amara Okafor", f"{PREFIX} Brick Vandergelder", f"{PREFIX} Twin Card"],
        target_jurisdiction="Texas",
    )
    by_status = {v.status for v in verdicts}
    assert verdicts[0].status == "CLEAR"
    assert verdicts[1].status == "DO_NOT_CLEAR"
    assert verdicts[1].active_suspensions[0].source_url == "https://example.test/csac"
    assert verdicts[2].status == "NEEDS_DISAMBIGUATION"  # two share the name, fail closed
    assert by_status == {"CLEAR", "DO_NOT_CLEAR", "NEEDS_DISAMBIGUATION"}


def test_clear_card_logs_a_batch_entry(card_fixture: dict[str, str]) -> None:
    clear_card("card-thread-2", [f"{PREFIX} Amara Okafor", f"{PREFIX} Brick Vandergelder"])
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT payload FROM ledger WHERE action = 'card_check' ORDER BY seq DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    payload = row[0]
    assert len(payload["fighters"]) == 2
