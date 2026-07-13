"""Rule engine matrix: windows from YAML, overlays longest-wins, active/expired logic,
cross-jurisdiction consultation note, and proof the rules are data (YAML override changes
outcomes with zero Python changes)."""

from datetime import date
from pathlib import Path

import pytest

from cornercheck.rules.engine import (
    CONSULTATION_NOTE_BOXING,
    CONSULTATION_NOTE_MMA,
    Rules,
    Suspension,
    evaluate,
    load_rules,
    restricted_interval,
    suspension_interval,
    window_days,
)

RULES = load_rules()


def _susp(
    start: str,
    end: str | None,
    indefinite: bool = False,
    jurisdiction: str = "Nevada",
    stype: str = "KO",
) -> Suspension:
    return Suspension(
        suspension_type=stype,
        start_date=date.fromisoformat(start),
        end_date=date.fromisoformat(end) if end else None,
        indefinite=indefinite,
        jurisdiction=jurisdiction,
        reason="test",
        source_url="https://example.test/source",
    )


@pytest.mark.parametrize(
    ("outcome", "expected_days"),
    [("TKO", 30), ("KO", 60), ("KO_LOC", 90)],
)
def test_base_competition_windows_match_abc_minimums(outcome: str, expected_days: int) -> None:
    days, applied = window_days(RULES, outcome)  # type: ignore[arg-type]
    assert days == expected_days
    assert any("arp_base" in a for a in applied)


def test_bsi_headshot_overlay_wins_for_tko() -> None:
    days, applied = window_days(RULES, "TKO", cause="head_shot_stoppage")
    assert days == 45  # overlay 45 > base 30
    assert any("abc_bsi_headshot" in a for a in applied)


def test_overlay_does_not_apply_without_matching_cause() -> None:
    days, _ = window_days(RULES, "TKO", cause=None)
    assert days == 30


def test_sparring_overlay_uses_own_table_and_attribution() -> None:
    days, applied = window_days(RULES, "KO", sparring=True)
    assert days == 45
    assert any("not an ABC mandate" in a for a in applied)


def test_active_bounded_suspension_blocks() -> None:
    v = evaluate([_susp("2026-05-16", "2026-11-12")], date(2026, 6, 7))
    assert v.decision == "DO_NOT_CLEAR"
    assert len(v.active) == 1


def test_expired_suspension_clears() -> None:
    v = evaluate([_susp("2019-07-13", "2019-08-27")], date(2026, 6, 7))
    assert v.decision == "CLEAR"


def test_indefinite_suspension_blocks_forever_until_cleared() -> None:
    v = evaluate([_susp("2026-05-16", None, indefinite=True)], date(2030, 1, 1))
    assert v.decision == "DO_NOT_CLEAR"


def test_boundary_dates_inclusive() -> None:
    s = _susp("2026-05-16", "2026-07-15")
    assert evaluate([s], date(2026, 5, 16)).decision == "DO_NOT_CLEAR"
    assert evaluate([s], date(2026, 7, 15)).decision == "DO_NOT_CLEAR"
    assert evaluate([s], date(2026, 7, 16)).decision == "CLEAR"


def test_cross_jurisdiction_note_is_sport_aware() -> None:
    args = (
        [_susp("2026-05-16", "2026-11-12", jurisdiction="Nevada")],
        date(2026, 6, 7),
    )
    # MMA (default): no federal equivalent framing.
    mma = evaluate(*args, target_jurisdiction="Texas")
    assert mma.decision == "DO_NOT_CLEAR"
    assert mma.consultation_note == CONSULTATION_NOTE_MMA
    assert "no federal equivalent" in mma.consultation_note
    # Boxing: §6306(b) is binding.
    boxing = evaluate(*args, target_jurisdiction="Texas", sport="boxing")
    assert boxing.consultation_note == CONSULTATION_NOTE_BOXING
    assert "for professional boxing" in boxing.consultation_note


def test_same_jurisdiction_no_consultation_note() -> None:
    v = evaluate(
        [_susp("2026-05-16", "2026-11-12", jurisdiction="Texas (TDLR)")],
        date(2026, 6, 7),
        target_jurisdiction="Texas",
    )
    assert v.decision == "DO_NOT_CLEAR"
    assert v.consultation_note is None


def test_restricted_interval_unions_overlaps() -> None:
    total = restricted_interval(
        [_susp("2026-01-01", "2026-03-01"), _susp("2026-02-01", "2026-04-01")]
    )
    assert date(2026, 2, 15) in total
    assert date(2026, 5, 1) not in total
    assert total.atomic  # the two overlapping windows collapsed into one


def test_indefinite_interval_is_open_ended() -> None:
    iv = suspension_interval(_susp("2026-05-16", None, indefinite=True))
    assert date(2099, 1, 1) in iv


def test_rules_are_data_yaml_override_changes_outcome(tmp_path: Path) -> None:
    """Changing ONLY YAML changes verdict windows: zero Python edits."""
    custom = tmp_path / "base.yaml"
    custom.write_text(
        "version: 1\n"
        "competition_windows_days:\n  TKO: 7\n  KO: 8\n  KO_LOC: 9\n"
        "rule_notes: {}\n"
        "sparring_overlay:\n  enabled: true\n  attribution: test\n"
        "  no_contact_days:\n    TKO: 1\n    KO: 2\n    KO_LOC: 3\n"
    )
    overlays = tmp_path / "overlays.yaml"
    overlays.write_text("version: 1\noverlays: {}\n")
    custom_rules: Rules = load_rules(custom, overlays)
    assert window_days(custom_rules, "KO")[0] == 8
    assert window_days(custom_rules, "KO_LOC", sparring=True)[0] == 3


# --- Whole-repo audit regressions: the rules tables must fail CLOSED at load -----------


def _write_tables(tmp_path, base: str, overlays: str):  # type: ignore[no-untyped-def]
    b = tmp_path / "base.yaml"
    o = tmp_path / "overlays.yaml"
    b.write_text(base)
    o.write_text(overlays)
    return b, o


GOOD_BASE = """
competition_windows_days: {TKO: 30, KO: 60, KO_LOC: 90}
rule_notes: {TKO: x, KO: y, KO_LOC: z}
sparring_overlay:
  attribution: test
  no_contact_days: {TKO: 30, KO: 45, KO_LOC: 60}
"""
GOOD_OVERLAYS = "overlays: {}\n"


def test_missing_sparring_overlay_refuses_to_load(tmp_path) -> None:  # type: ignore[no-untyped-def]
    # Pre-fix, a missing/typo'd key silently became a 0-day no-contact window after a KO.
    import pytest as _pytest

    from cornercheck.rules.engine import load_rules

    base = "competition_windows_days: {TKO: 30, KO: 60, KO_LOC: 90}\n"
    b, o = _write_tables(tmp_path, base, GOOD_OVERLAYS)
    with _pytest.raises(ValueError, match="sparring_overlay"):
        load_rules(b, o)


def test_missing_outcome_day_refuses_to_load(tmp_path) -> None:  # type: ignore[no-untyped-def]
    import pytest as _pytest

    from cornercheck.rules.engine import load_rules

    base = GOOD_BASE.replace("KO_LOC: 60}", "}").replace("{TKO: 30, KO: 45, }", "{TKO: 30, KO: 45}")
    b, o = _write_tables(tmp_path, base, GOOD_OVERLAYS)
    with _pytest.raises(ValueError, match="KO_LOC"):
        load_rules(b, o)


def test_quoted_string_days_refuse_to_load(tmp_path) -> None:  # type: ignore[no-untyped-def]
    import pytest as _pytest

    from cornercheck.rules.engine import load_rules

    b, o = _write_tables(tmp_path, GOOD_BASE.replace("KO: 45", 'KO: "45"'), GOOD_OVERLAYS)
    with _pytest.raises(ValueError, match="KO"):
        load_rules(b, o)


def test_misspelled_overlays_key_refuses_to_load(tmp_path) -> None:  # type: ignore[no-untyped-def]
    import pytest as _pytest

    from cornercheck.rules.engine import load_rules

    b, o = _write_tables(tmp_path, GOOD_BASE, "overlay: {}\n")
    with _pytest.raises(ValueError, match="overlays"):
        load_rules(b, o)


def test_committed_tables_still_load_and_validate() -> None:
    from cornercheck.rules.engine import load_rules

    rules = load_rules()
    for oc in ("TKO", "KO", "KO_LOC"):
        assert rules.competition_windows_days[oc] > 0
        assert rules.sparring_no_contact_days[oc] > 0
