"""Tiny ordered-SQL migration runner.

CI applies the same files via psql against a fresh database; this runner is for
local/dev and remote (Render) databases, tracking applied files in
schema_migrations so it is idempotent.
"""

from pathlib import Path

from cornercheck.db.pool import get_pool

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def apply_migrations() -> list[str]:
    applied: list[str] = []
    with get_pool().connection() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " filename text PRIMARY KEY,"
            " applied_at timestamptz NOT NULL DEFAULT now())"
        )
        done = {r[0] for r in conn.execute("SELECT filename FROM schema_migrations").fetchall()}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                continue
            try:
                conn.execute(path.read_text())  # no params -> simple protocol, multi-stmt OK
            except Exception as exc:
                # The whole batch rolls back atomically; name the file so the operator
                # is not left diffing eight migrations against a bare SQL error.
                raise RuntimeError(f"migration {path.name} failed") from exc
            conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
            applied.append(path.name)
    return applied


if __name__ == "__main__":
    print("applied:", apply_migrations() or "nothing (up to date)")
