"""Process-wide Postgres connection pool."""

from functools import lru_cache

from psycopg_pool import ConnectionPool

from cornercheck.config import get_settings


@lru_cache
def get_pool() -> ConnectionPool:
    """Lazy singleton pool. Tests can call get_pool.cache_clear() to rebuild.
    check= heals connections severed by a Postgres restart (Render maintenance) instead
    of surfacing them as one-off user-facing failures."""
    return ConnectionPool(
        get_settings().database_url,
        min_size=1,
        max_size=5,
        open=True,
        check=ConnectionPool.check_connection,
    )
