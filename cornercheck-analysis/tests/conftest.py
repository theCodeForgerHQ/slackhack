"""Shared fixtures. CI provides a postgres:16 service; locally use docker compose up -d.

Integration tests SKIP when Postgres is unreachable locally, but FAIL in CI
(CI must never silently skip the database suite).
"""

import os

import psycopg
import pytest

# Must land before the first get_settings() call anywhere in the test session.
os.environ.setdefault("CORNERCHECK_LEDGER_HMAC_KEY", "test-only-hmac-key-not-a-secret")

from cornercheck.config import get_settings

get_settings.cache_clear()


@pytest.fixture(scope="session")
def db() -> str:
    url = get_settings().database_url
    try:
        psycopg.connect(url, connect_timeout=3).close()
    except Exception as exc:
        if os.environ.get("CI"):
            raise RuntimeError(f"CI requires Postgres but it is unreachable: {exc}") from exc
        pytest.skip(f"Postgres unavailable at {url}: {exc}")
    from cornercheck.db.migrate import apply_migrations

    apply_migrations()
    return url


_LOCAL_DB_HOSTS = ("localhost", "127.0.0.1", "::1", "db", "postgres")


@pytest.fixture
def clean_ledger(db: str) -> None:
    """Reset the ledger between tests, bypassing the append-only triggers.

    session_replication_role=replica disables ordinary triggers; this is the same
    documented bypass the tamper demo uses, and exactly what the hash chain exists
    to catch.

    PROD GUARD: one local pytest run with .env temporarily pointing at the production
    database (a real workflow during deploy debugging) would silently DESTROY the
    production audit ledger. Refuse to truncate anything that is not a local DB unless
    explicitly overridden.
    """
    from urllib.parse import urlsplit

    from cornercheck.db.pool import get_pool

    host = urlsplit(db).hostname or ""
    if host not in _LOCAL_DB_HOSTS and not (
        os.environ.get("CI") or os.environ.get("CORNERCHECK_ALLOW_TEST_TRUNCATE")
    ):
        raise RuntimeError(
            f"refusing to TRUNCATE the ledger on non-local host {host!r}; set "
            "CORNERCHECK_ALLOW_TEST_TRUNCATE=1 only if you are CERTAIN this is a test DB"
        )
    with get_pool().connection() as conn:
        conn.execute("SET session_replication_role = replica")
        conn.execute("TRUNCATE ledger RESTART IDENTITY")
        conn.execute("SET session_replication_role = DEFAULT")
