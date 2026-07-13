"""Deterministic clearance evaluation over YAML decision tables + portion intervals.

The LLM never decides clearance. This engine does, from data:
- active-suspension check: a fighter with ANY suspension interval containing the target
  date is DO_NOT_CLEAR, with every active suspension cited (source_url included)
- cross-jurisdiction note: when an active suspension comes from a different jurisdiction
  than the target, the verdict carries a sport-aware consultation note (15 U.S.C. §6306(b)
  is binding for boxing; MMA has no federal equivalent, which is the gap this surfaces)
- outcome windows: TKO/KO/KO_LOC minimum days come from arp_base.yaml with
  longest-rule-wins overlays from state_overlays.yaml
"""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Literal

import portion as P
import yaml

TABLES_DIR = Path(__file__).parent / "decision_tables"

Outcome = Literal["TKO", "KO", "KO_LOC"]

# The 15 U.S.C. §6306(b) consult-first requirement is BOXING-only (Muhammad Ali Boxing
# Reform Act). MMA has no federal equivalent, so the note is sport-aware: a binding citation
# for boxing, and for MMA the gap CornerCheck closes by applying the same discipline.
CONSULTATION_NOTE_BOXING = (
    "15 U.S.C. §6306(b): for professional boxing, the licensing commission must consult the"
    " suspending commission before this fighter competes. CornerCheck supports that step; it"
    " never replaces it."
)
CONSULTATION_NOTE_MMA = (
    "Different commission from the active suspension. Federal law (15 U.S.C. §6306(b)) requires"
    " this consult-first step for professional boxing; MMA has no federal equivalent, so"
    " CornerCheck applies the same discipline. It supports that consult; it never replaces it."
)


def consultation_note_for(sport: str) -> str:
    return CONSULTATION_NOTE_BOXING if sport.lower() == "boxing" else CONSULTATION_NOTE_MMA


@dataclass(frozen=True)
class Rules:
    competition_windows_days: dict[str, int]
    rule_notes: dict[str, str]
    sparring_no_contact_days: dict[str, int]
    sparring_attribution: str
    overlays: dict[str, dict]


def _require_outcome_days(table: Any, label: str) -> dict[str, int]:
    """Every Outcome must map to a positive int. A missing or typo'd key must refuse to
    LOAD, never default to a 0-day window (adversarial review demonstrated a single
    misspelled YAML key silently turning a 45-day no-contact hold into 'cleared to spar
    now' while still printing a sourced-looking rule id)."""
    if not isinstance(table, dict):
        raise ValueError(f"rules table {label!r} missing or not a mapping; refusing to load")
    for oc in ("TKO", "KO", "KO_LOC"):
        v = table.get(oc)
        if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
            raise ValueError(
                f"rules table {label!r} has missing/invalid days for {oc!r}: {v!r}; "
                "refusing to load (fail closed)"
            )
    return {str(k): int(v) for k, v in table.items()}


def load_rules(base_path: Path | None = None, overlays_path: Path | None = None) -> Rules:
    base = yaml.safe_load((base_path or TABLES_DIR / "arp_base.yaml").read_text())
    over = yaml.safe_load((overlays_path or TABLES_DIR / "state_overlays.yaml").read_text())
    if "sparring_overlay" not in base:
        raise ValueError("arp_base.yaml is missing 'sparring_overlay'; refusing to load")
    sparring = base["sparring_overlay"]
    if "overlays" not in over:
        raise ValueError("state_overlays.yaml is missing 'overlays'; refusing to load")
    overlays = dict(over["overlays"])
    for name, overlay in overlays.items():
        for tbl in ("competition_windows_days", "no_contact_days"):
            if tbl in overlay:
                for oc, v in overlay[tbl].items():
                    if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
                        raise ValueError(
                            f"overlay {name!r} table {tbl!r} has invalid days for "
                            f"{oc!r}: {v!r}; refusing to load (fail closed)"
                        )
    return Rules(
        competition_windows_days=_require_outcome_days(
            base.get("competition_windows_days"), "competition_windows_days"
        ),
        rule_notes=dict(base.get("rule_notes", {})),
        sparring_no_contact_days=_require_outcome_days(
            sparring.get("no_contact_days"), "sparring_overlay.no_contact_days"
        ),
        sparring_attribution=str(sparring.get("attribution", "")),
        overlays=overlays,
    )


@dataclass(frozen=True)
class Suspension:
    """Database-shape suspension record (subset the engine needs)."""

    suspension_type: str
    start_date: date
    end_date: date | None
    indefinite: bool
    jurisdiction: str
    reason: str
    source_url: str


def suspension_interval(s: Suspension) -> P.Interval:
    if s.indefinite or s.end_date is None:
        return P.closedopen(s.start_date, P.inf)
    if s.end_date < s.start_date:
        # Malformed range (end before start). P.closed(start, end) would be EMPTY, so the
        # fighter would never be active and silently CLEAR: a fail-OPEN hole on a corrupt or
        # date-swapped row (surfaced by the Z3 refinement proof). Fail closed instead: treat
        # it as an open-ended suspension from start, blocking the fighter until a human fixes
        # the record. Wrong "cleared" can be fatal; wrong "blocked" costs a phone call.
        return P.closedopen(s.start_date, P.inf)
    return P.closed(s.start_date, s.end_date)


def restricted_interval(suspensions: list[Suspension]) -> P.Interval:
    """Union of all suspension intervals (overlaps collapse automatically)."""
    total = P.empty()
    for s in suspensions:
        total = total | suspension_interval(s)
    return total


@dataclass(frozen=True)
class RuleVerdict:
    decision: Literal["CLEAR", "DO_NOT_CLEAR"]
    on_date: date
    active: list[Suspension] = field(default_factory=list)
    applied_rules: list[str] = field(default_factory=list)
    consultation_note: str | None = None


def evaluate(
    suspensions: list[Suspension],
    on_date: date,
    target_jurisdiction: str | None = None,
    sport: str = "mma",
) -> RuleVerdict:
    """Fail-closed core: ANY active suspension on the date blocks clearance."""
    active = [s for s in suspensions if on_date in suspension_interval(s)]
    if not active:
        return RuleVerdict("CLEAR", on_date, applied_rules=["no-active-suspension"])
    note = None
    # Substring containment is deliberate: targets are canonical state names from the
    # parser ("Texas"), jurisdictions are full commission strings ("Texas Department of
    # Licensing and Regulation (TDLR)"). Note-only either way: the DECISION never
    # depends on this comparison.
    if target_jurisdiction is not None and any(
        target_jurisdiction.lower() not in s.jurisdiction.lower() for s in active
    ):
        note = consultation_note_for(sport)
    return RuleVerdict(
        "DO_NOT_CLEAR",
        on_date,
        active=active,
        applied_rules=[f"active-suspension:{s.jurisdiction}" for s in active],
        consultation_note=note,
    )


def window_days(
    rules: Rules, outcome: Outcome, cause: str | None = None, sparring: bool = False
) -> tuple[int, list[str]]:
    """Longest-rule-wins window for a bout outcome; returns (days, applied rule ids)."""
    table = "no_contact_days" if sparring else "competition_windows_days"
    if sparring:
        # [outcome], never .get(outcome, 0): a gap must raise into the fail-closed
        # envelope, not clear a fighter to spar with a zero-day window.
        days = rules.sparring_no_contact_days[outcome]
        applied = [f"sparring-overlay:{outcome} ({rules.sparring_attribution})"]
    else:
        days = rules.competition_windows_days[outcome]
        applied = [f"arp_base:{outcome} ({rules.rule_notes.get(outcome, '')})"]
    for name, overlay in rules.overlays.items():
        applies_when = overlay.get("applies_when", {})
        if applies_when.get("cause") and applies_when["cause"] != cause:
            continue
        overlay_days = overlay.get(table, {}).get(outcome)
        if overlay_days is not None and overlay_days > days:
            days = overlay_days
            applied.append(f"overlay:{name} ({overlay.get('source', 'unsourced')})")
    return days, applied
