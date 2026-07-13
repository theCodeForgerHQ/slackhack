"""Typed read queries used by the rule engine and entity resolution."""

from dataclasses import dataclass
from datetime import date

from cornercheck.db.pool import get_pool
from cornercheck.rules.engine import RuleVerdict, Suspension, evaluate


@dataclass(frozen=True)
class FighterRow:
    id: str
    full_name: str
    weight_class: str | None
    wins: int
    losses: int
    draws: int
    sport: str
    primary_jurisdiction: str | None


def get_fighter(fighter_id: str) -> FighterRow | None:
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT id, full_name, weight_class, wins, losses, draws, sport,"
            " primary_jurisdiction FROM fighters WHERE id = %s",
            (fighter_id,),
        ).fetchone()
    if row is None:
        return None
    return FighterRow(str(row[0]), row[1], row[2], row[3], row[4], row[5], row[6], row[7])


def get_suspensions(fighter_id: str) -> list[Suspension]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT suspension_type, start_date, end_date, indefinite, jurisdiction,"
            " coalesce(reason, ''), source_url FROM suspensions WHERE fighter_id = %s"
            " ORDER BY start_date",
            (fighter_id,),
        ).fetchall()
    return [
        Suspension(
            suspension_type=r[0],
            start_date=r[1],
            end_date=r[2],
            indefinite=r[3],
            jurisdiction=r[4],
            reason=r[5],
            source_url=r[6],
        )
        for r in rows
    ]


def evaluate_fighter_clearance(
    fighter_id: str, on_date: date, target_jurisdiction: str | None = None
) -> RuleVerdict:
    fighter = get_fighter(fighter_id)
    if fighter is None:
        # "We have no record of this fighter" must NEVER read as "this fighter has no
        # suspensions": a nonexistent id with zero suspension rows would evaluate to
        # CLEAR (live-reproduced in adversarial review). Refuse instead; every caller
        # converts the raise into its fail-closed surface.
        raise LookupError(f"no fighter with id {fighter_id!r}; refusing to evaluate clearance")
    return evaluate(get_suspensions(fighter_id), on_date, target_jurisdiction, fighter.sport)
