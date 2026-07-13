"""Monitor end-to-end against the real DB and ledger: exact window boundaries, the
seq-watermark diff, the ledgered run, and fail-quiet pushing. Self-contained (CI's
Postgres is migrated but unseeded)."""

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta

import pytest

from cornercheck import monitor
from cornercheck.db.pool import get_pool
from cornercheck.ledger.store import append_entry
from cornercheck.monitor import Watermark, gather_findings, run_monitor_once

# Boundary roster: name -> days from today for end_date (None = indefinite).
# Window contracts: lapsing is [today, today+14] inclusive; lapsed is [today-7, today-1].
ROSTER: dict[str, int | None] = {
    "Zm End Today": 0,  # lapsing in 0d (today is IN, not lapsed)
    "Zm Edge Fourteen": 14,  # last day IN the lapsing window
    "Zm Edge Fifteen": 15,  # first day OUT
    "Zm Lapsed One": -1,  # most recent lapsed day
    "Zm Edge Seven": -7,  # last day IN the lapsed window
    "Zm Edge Eight": -8,  # first day OUT
    "Zm Far Future": 60,  # OUT of every window
    "Zm Until Cleared": None,  # indefinite: never window-tracked, counted instead
}


@pytest.fixture
def roster(db: str, clean_ledger: None) -> Iterator[None]:
    monitor._last_digest = None  # isolate the duplicate-push memo between tests
    fids: list[str] = []
    today = date.today()
    with get_pool().connection() as conn:
        for name, delta in ROSTER.items():
            fid = str(uuid.uuid4())
            fids.append(fid)
            conn.execute(
                "INSERT INTO fighters (id, full_name, wins, losses, draws, sport, source)"
                " VALUES (%s, %s, 0, 0, 0, 'mma', 'test-fixture')",
                (fid, name),
            )
            end = None if delta is None else today + timedelta(days=delta)
            conn.execute(
                "INSERT INTO suspensions (fighter_id, suspension_type, start_date, end_date,"
                " indefinite, jurisdiction, source_url)"
                " VALUES (%s, 'medical', %s, %s, %s, 'TEST (fixture)', 'https://example.test')",
                (fid, today - timedelta(days=30), end, delta is None),
            )
    try:
        yield
    finally:
        with get_pool().connection() as conn:
            for fid in fids:
                conn.execute("DELETE FROM fighters WHERE id = %s", (fid,))


def _since() -> Watermark:
    return Watermark(seq=0, ts=datetime.now(UTC) - timedelta(minutes=5))


def test_window_boundaries_are_exact(roster: None) -> None:
    f, watermark = gather_findings(date.today(), _since())
    lapsing = [w["fighter"] for w in f.lapsing if w["fighter"].startswith("Zm ")]
    lapsed = [w["fighter"] for w in f.lapsed if w["fighter"].startswith("Zm ")]
    assert lapsing == ["Zm End Today", "Zm Edge Fourteen"]  # sorted by end_date
    assert lapsed == ["Zm Edge Seven", "Zm Lapsed One"]
    out = {"Zm Edge Fifteen", "Zm Edge Eight", "Zm Far Future", "Zm Until Cleared"}
    assert out.isdisjoint(set(lapsing) | set(lapsed))
    assert f.indefinite_on_file >= 1
    new = [s["fighter"] for s in f.new_suspensions if s["fighter"].startswith("Zm ")]
    assert len(new) == len(ROSTER)  # all filed since 5 minutes ago
    assert watermark.seq >= 0 and watermark.ts is not None


def test_ledger_diffs_run_entry_and_watermark(
    roster: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    pushed: list[str] = []

    def capture(text: str) -> bool:
        pushed.append(text)
        return True

    monkeypatch.setattr(monitor, "post_ops_alert", capture)

    append_entry(
        "test",
        "clearance_decision",
        {
            "fighter_name": "Zm Blocked Fighter",
            "decision": "DO_NOT_CLEAR",
            "applied_rules": ["active_suspension"],
            "corroboration": {"status": "DISAGREED", "note": "live shows 27 vs 25 on file"},
        },
    )
    out = run_monitor_once()
    assert out["alerted"] is True and out["posted"] is True
    assert "Zm Blocked Fighter" in pushed[0]
    assert "Live-record disagreement" in pushed[0]
    assert "indefinite (until cleared)" in pushed[0]

    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT payload FROM ledger WHERE action = 'monitor_run' ORDER BY seq DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    payload = row[0]
    assert payload["alerted"] is True
    assert payload["watermark"]["seq"] > 0
    assert any(
        b["fighter"] == "Zm Blocked Fighter" for b in payload["findings"]["blocked_decisions"]
    )

    # A SECOND decision lands after the first run's watermark: the next run must report
    # exactly the new one (seq diff: no holes, no re-reports of the first).
    append_entry(
        "test",
        "clearance_decision",
        {
            "fighter_name": "Zm Second Blocked",
            "decision": "DO_NOT_CLEAR",
            "applied_rules": ["active_suspension"],
        },
    )
    out2 = run_monitor_once()
    assert out2["alerted"] is True
    with get_pool().connection() as conn:
        row2 = conn.execute(
            "SELECT payload FROM ledger WHERE action = 'monitor_run' ORDER BY seq DESC LIMIT 1"
        ).fetchone()
    assert row2 is not None
    blocked2 = [b["fighter"] for b in row2[0]["findings"]["blocked_decisions"]]
    assert blocked2 == ["Zm Second Blocked"]

    # Third run immediately: diff consumed, windows unchanged, digest text identical to
    # the second one EXCEPT the blocked line: it differs, so it posts. Then a FOURTH run
    # produces the identical text and the duplicate-push memo suppresses it.
    out3 = run_monitor_once()
    out4 = run_monitor_once()
    assert out3["alerted"] is True
    assert out4["alerted"] is True
    assert out4["posted"] is False  # identical digest suppressed


def test_unset_webhook_still_ledgers_the_run(
    db: str, clean_ledger: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monitor._last_digest = None

    class NoWebhook:
        ops_webhook_url = ""

    monkeypatch.setattr(monitor, "get_settings", lambda: NoWebhook())
    out = run_monitor_once()
    assert out["posted"] is False
    with get_pool().connection() as conn:
        row = conn.execute("SELECT count(*) FROM ledger WHERE action = 'monitor_run'").fetchone()
    assert row is not None and row[0] == 1


def test_missing_hmac_key_skips_instead_of_spamming(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_key() -> bytes:
        raise RuntimeError("CORNERCHECK_LEDGER_HMAC_KEY unset")

    monkeypatch.setattr(monitor, "hmac_key", no_key)
    out = run_monitor_once()
    assert out == {"skipped": "ledger-unavailable"}
