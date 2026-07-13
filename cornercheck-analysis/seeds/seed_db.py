"""Seed Postgres with real data: ~4,100 UFC fighters (MIT-licensed dataset) plus
54 verified, source-cited suspension cases (see seeds/data/curated_suspensions.json).

Dataset: github.com/KgKevin0/UFC-Stats UFC_fighters.csv, MIT license (verified
2026-06-07). Downloaded at seed time into seeds/data/downloads/ (gitignored),
never committed.

Run: uv run python seeds/seed_db.py [--force]
"""

import csv
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

from cornercheck.db.migrate import apply_migrations
from cornercheck.db.pool import get_pool
from cornercheck.er.names import fold
from cornercheck.ledger.store import append_entry

DATA_DIR = Path(__file__).parent / "data"
DOWNLOADS = DATA_DIR / "downloads"
CSV_URL = "https://raw.githubusercontent.com/KgKevin0/UFC-Stats/main/UFC_fighters.csv"
CSV_PATH = DOWNLOADS / "UFC_fighters.csv"

# Stage 5 demo scenario mapping (every scenario = a named, really-seeded fighter)
DEMO_CLEAN_FIGHTER = "Merab Dvalishvili"  # CLEAR card
DEMO_CROSS_JX = "Julio Cesar Chavez Jr."  # cross-jurisdiction DO NOT CLEAR
DEMO_AMBIGUOUS = "Bruno Silva"  # two real UFC Bruno Silvas -> disambiguation
DEMO_ACTIVE_SUSPENSION = "Junior dos Santos"  # indefinite, active right now
DEMO_RTS_CHATTER = "Geoff Neal"  # injury-chatter seed messages reference him


def download_dataset() -> Path:
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists():
        print(f"downloading {CSV_URL} ...")
        urllib.request.urlretrieve(CSV_URL, CSV_PATH)
    return CSV_PATH


def seed(force: bool) -> None:
    apply_migrations()
    pool = get_pool()

    with pool.connection() as conn:
        count = conn.execute("SELECT count(*) FROM fighters").fetchone()
        assert count is not None
        if count[0] > 0:
            if not force:
                print(f"fighters table already has {count[0]} rows; use --force to reseed")
                return
            conn.execute("DELETE FROM suspensions")
            conn.execute("DELETE FROM fighters")

    path = download_dataset()
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    fighter_rows = [
        (
            f"{r['First Name']} {r['Last Name']}".strip(),
            r.get("Weight Class") or None,
            int(r["W"] or 0),
            int(r["L"] or 0),
            int(r["D"] or 0),
            "mma",
            "ufcstats.com via github.com/KgKevin0/UFC-Stats (MIT)",
        )
        for r in rows
        if f"{r['First Name']} {r['Last Name']}".strip()
    ]

    cases = json.loads((DATA_DIR / "curated_suspensions.json").read_text())["cases"]

    with pool.connection() as conn, conn.transaction():
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO fighters (full_name, weight_class, wins, losses, draws, sport,"
                " source) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                fighter_rows,
            )
        inserted_suspensions = 0
        for c in cases:
            fighter_id = _case_fighter_id(conn, c)
            conn.execute(
                "INSERT INTO suspensions (fighter_id, suspension_type, start_date, end_date,"
                " indefinite, jurisdiction, reason, source_url, source_quote)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (fighter_id, start_date, jurisdiction) DO NOTHING",
                (
                    fighter_id,
                    c["suspension_type"],
                    c["start_date"],
                    c["end_date"],
                    c["indefinite"],
                    c["jurisdiction"],
                    c["reason"],
                    c["source_url"],
                    c["source_quote"],
                ),
            )
            inserted_suspensions += 1

    verify_demo_mapping()

    append_entry(
        "seed",
        "db_seeded",
        {"fighters": len(fighter_rows), "suspensions": inserted_suspensions, "source": CSV_URL},
    )
    print(f"seeded {len(fighter_rows)} fighters + {inserted_suspensions} cited suspensions")


def _fold(name: str) -> str:
    """The shared punctuation/diacritic-insensitive key; semantics live in er/names.py."""
    return fold(name)


def _case_fighter_id(conn: Any, c: dict) -> str:
    """Map a case to its fighter, fail-closed against identity splits. A spelling variant
    of an existing fighter ('T.J.' vs 'TJ', 'Peña' vs 'Pena') must attach to the REAL row,
    never mint a shadow identity that carries the suspension while the real fighter reads
    clean (adversarial review demonstrated exactly that false-CLEAR path). Ambiguous 2+
    matches refuse loudly: a suspension on an arbitrary twin lets the other twin slip."""
    rows = conn.execute(
        "SELECT id FROM fighters WHERE lower(full_name) = lower(%s) ORDER BY created_at, id",
        (c["fighter_name"],),
    ).fetchall()
    if len(rows) > 1:
        raise RuntimeError(
            f"case {c['fighter_name']!r} matches {len(rows)} roster fighters; "
            "ambiguous mapping needs a manual decision, refusing"
        )
    if rows:
        return str(rows[0][0])

    key = _fold(c["fighter_name"])
    folded = [
        (fid, name)
        for fid, name in conn.execute("SELECT id, full_name FROM fighters").fetchall()
        if _fold(name) == key
    ]
    if len(folded) > 1:
        raise RuntimeError(
            f"case {c['fighter_name']!r} fold-matches {len(folded)} fighters; refusing"
        )
    if folded:
        print(f"  case {c['fighter_name']!r} attached to roster spelling {folded[0][1]!r}")
        return str(folded[0][0])

    frow = conn.execute(
        "INSERT INTO fighters (full_name, sport, source) VALUES (%s, %s, %s) RETURNING id",
        (c["fighter_name"], c["sport"], c["source_url"]),
    ).fetchone()
    if frow is None:
        raise RuntimeError(f"fighter insert returned no id for {c['fighter_name']!r}")
    return str(frow[0])


def top_up_cases() -> int:
    """Insert any curated cases not yet in the DB, matched by (fighter name, start_date,
    jurisdiction). ADDITIVE-ONLY and idempotent: a deployed instance converges on newly
    curated cited cases at boot without wiping fighters or touching existing rows.
    Corrections to an existing case (end_date, reason, sources) do NOT propagate through
    this path; they require a --force reseed. The unique index from migration 007 plus
    ON CONFLICT DO NOTHING makes concurrent boots race-safe."""
    cases = json.loads((DATA_DIR / "curated_suspensions.json").read_text())["cases"]
    added = 0
    pool = get_pool()
    with pool.connection() as conn, conn.transaction():
        for c in cases:
            present = conn.execute(
                "SELECT 1 FROM suspensions s JOIN fighters f ON f.id = s.fighter_id"
                " WHERE lower(f.full_name) = lower(%s) AND s.start_date = %s"
                " AND s.jurisdiction = %s",
                (c["fighter_name"], c["start_date"], c["jurisdiction"]),
            ).fetchone()
            if present is not None:
                continue
            fighter_id = _case_fighter_id(conn, c)
            result = conn.execute(
                "INSERT INTO suspensions (fighter_id, suspension_type, start_date, end_date,"
                " indefinite, jurisdiction, reason, source_url, source_quote)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (fighter_id, start_date, jurisdiction) DO NOTHING",
                (
                    fighter_id,
                    c["suspension_type"],
                    c["start_date"],
                    c["end_date"],
                    c["indefinite"],
                    c["jurisdiction"],
                    c["reason"],
                    c["source_url"],
                    c["source_quote"],
                ),
            )
            added += result.rowcount if result.rowcount and result.rowcount > 0 else 0
    if added:
        try:
            append_entry("seed", "cases_topped_up", {"added": added, "total_cases": len(cases)})
        except Exception as e:
            # The data is committed; a lost audit entry must be LOUD, never silent.
            print(
                f"ERROR: topped up {added} cases but the ledger entry failed "
                f"({type(e).__name__}: {e}); record this top-up manually"
            )
        print(f"topped up {added} new cited suspension cases")
    return added


def verify_demo_mapping() -> None:
    """Every Stage 5 demo scenario must map to a named, really-seeded fighter."""
    checks = {
        "CLEAR demo": DEMO_CLEAN_FIGHTER,
        "cross-jurisdiction demo": DEMO_CROSS_JX,
        "active-suspension demo": DEMO_ACTIVE_SUSPENSION,
        "RTS-chatter demo": DEMO_RTS_CHATTER,
    }
    with get_pool().connection() as conn:
        for label, name in checks.items():
            row = conn.execute(
                "SELECT count(*) FROM fighters WHERE lower(full_name) = lower(%s)", (name,)
            ).fetchone()
            assert row is not None and row[0] >= 1, f"{label}: {name} missing from seed"
            print(f"  {label}: {name} present ({row[0]} row(s))")
        amb = conn.execute(
            "SELECT count(*) FROM fighters WHERE lower(full_name) = lower(%s)",
            (DEMO_AMBIGUOUS,),
        ).fetchone()
        assert amb is not None and amb[0] >= 2, (
            f"disambiguation demo needs >=2 fighters named {DEMO_AMBIGUOUS}, found {amb}"
        )
        print(f"  disambiguation demo: {DEMO_AMBIGUOUS} present x{amb[0]}")
        sus = conn.execute("SELECT count(*) FROM suspensions").fetchone()
        assert sus is not None and sus[0] >= 10, f"need >=10 suspensions, found {sus}"
        print(f"  suspensions seeded: {sus[0]} (>=10 required)")


if __name__ == "__main__":
    seed(force="--force" in sys.argv)
