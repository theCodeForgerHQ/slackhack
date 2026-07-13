"""Ledger against real Postgres: append, verify, tamper detection, append-only guards."""

import psycopg
import pytest

from cornercheck.db.pool import get_pool
from cornercheck.ledger.store import append_entry
from cornercheck.ledger.verify import verify_chain


@pytest.mark.usefixtures("clean_ledger")
def test_append_and_verify_intact() -> None:
    for i in range(5):
        append_entry("test", "clearance_decision", {"fighter": f"F{i}", "decision": "CLEAR"})
    result = verify_chain()
    assert result.ok and result.checked == 5


@pytest.mark.usefixtures("clean_ledger")
def test_tamper_is_reported_at_exact_seq() -> None:
    for i in range(5):
        append_entry("test", "clearance_decision", {"fighter": f"F{i}", "n": i})
    # Privileged bypass of the append-only triggers: exactly the attack the chain catches.
    with get_pool().connection() as conn:
        conn.execute("SET session_replication_role = replica")
        conn.execute("UPDATE ledger SET payload = jsonb_set(payload, '{n}', '999') WHERE seq = 3")
        conn.execute("SET session_replication_role = DEFAULT")
    result = verify_chain()
    assert not result.ok
    assert result.first_bad_seq == 3
    assert "seq 3" in result.detail


@pytest.mark.usefixtures("clean_ledger")
def test_update_blocked_by_trigger() -> None:
    append_entry("test", "clearance_decision", {"fighter": "F0"})
    with get_pool().connection() as conn, pytest.raises(psycopg.errors.RaiseException) as exc:
        conn.execute("UPDATE ledger SET actor = 'evil' WHERE seq = 1")
    assert "append-only" in str(exc.value)


@pytest.mark.usefixtures("clean_ledger")
def test_delete_blocked_by_trigger() -> None:
    append_entry("test", "clearance_decision", {"fighter": "F0"})
    with get_pool().connection() as conn, pytest.raises(psycopg.errors.RaiseException) as exc:
        conn.execute("DELETE FROM ledger WHERE seq = 1")
    assert "append-only" in str(exc.value)


def test_least_privilege_roles_exist(db: str) -> None:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT rolname FROM pg_roles"
            " WHERE rolname IN ('cornercheck_app', 'cornercheck_reader')"
        ).fetchall()
    assert {r[0] for r in rows} == {"cornercheck_app", "cornercheck_reader"}


def test_meta_stamp_catches_a_flipped_action_column(db: str, clean_ledger: None) -> None:
    """Pre-audit, the hash covered only prev_hash+payload: a privileged edit flipping a
    denial's action column to clearance_decision verified as intact."""
    from cornercheck.db.pool import get_pool
    from cornercheck.ledger.store import append_entry
    from cornercheck.ledger.verify import verify_chain

    e = append_entry("t", "clearance_write_denied", {"x": 1})
    assert e.payload["_meta"]["action"] == "clearance_write_denied"
    assert verify_chain().ok is True
    try:
        with get_pool().connection() as conn:
            conn.execute("ALTER TABLE ledger DISABLE TRIGGER USER")
            conn.execute("UPDATE ledger SET action = 'clearance_decision' WHERE seq = %s", (e.seq,))
            conn.execute("ALTER TABLE ledger ENABLE TRIGGER USER")
        r = verify_chain()
        assert r.ok is False and r.first_bad_seq == e.seq
        assert "actor/action column mismatch" in r.detail
    finally:
        # Restore even on assertion failure: a tamper test must not leave the shared
        # ledger broken for whichever test runs next (suite-audit order-dependence).
        with get_pool().connection() as conn:
            conn.execute("ALTER TABLE ledger DISABLE TRIGGER USER")
            conn.execute(
                "UPDATE ledger SET action = 'clearance_write_denied' WHERE seq = %s", (e.seq,)
            )
            conn.execute("ALTER TABLE ledger ENABLE TRIGGER USER")
    assert verify_chain().ok is True


def test_meta_stamp_catches_a_backdated_ts(db: str, clean_ledger: None) -> None:
    from cornercheck.db.pool import get_pool
    from cornercheck.ledger.store import append_entry
    from cornercheck.ledger.verify import verify_chain

    e = append_entry("t", "clearance_decision", {"x": 1})
    try:
        with get_pool().connection() as conn:
            conn.execute("ALTER TABLE ledger DISABLE TRIGGER USER")
            conn.execute("UPDATE ledger SET ts = ts - interval '30 days' WHERE seq = %s", (e.seq,))
            conn.execute("ALTER TABLE ledger ENABLE TRIGGER USER")
        r = verify_chain()
        assert r.ok is False and "ts column drift" in r.detail
    finally:
        with get_pool().connection() as conn:
            conn.execute("ALTER TABLE ledger DISABLE TRIGGER USER")
            conn.execute("UPDATE ledger SET ts = ts + interval '30 days' WHERE seq = %s", (e.seq,))
            conn.execute("ALTER TABLE ledger ENABLE TRIGGER USER")
    assert verify_chain().ok is True


def test_meta_key_is_reserved(db: str, clean_ledger: None) -> None:
    import pytest as _pytest

    from cornercheck.ledger.chain import UnsafePayloadError
    from cornercheck.ledger.store import append_entry

    with _pytest.raises(UnsafePayloadError, match="reserved"):
        append_entry("t", "x", {"_meta": {"actor": "spoof"}})
