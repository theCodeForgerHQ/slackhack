"""Corroboration logic against RECORDED REAL boxing-data.com responses (no network).

The fixtures under sources/fixtures/boxing_data/ are actual API responses captured
2026-06-09, so these tests pin the logic to the real upstream schema, including its
quirks (token-fuzzy search, optional stats keys, unreliable total_bouts)."""

import json
from pathlib import Path

import pytest

from cornercheck.brain.schemas import CorroborationOut
from cornercheck.db.queries import FighterRow
from cornercheck.sources import boxing_data, corroborate
from cornercheck.sources.corroborate import (
    DISAGREEMENT_RULE,
    corroborate_fighter,
    corroborate_from_hits,
    tighten,
)

FIXTURES = Path(boxing_data.__file__).parent / "fixtures" / "boxing_data"


def _row(name: str, sport: str = "boxing", w: int = 0, lo: int = 0, dr: int = 0) -> FighterRow:
    return FighterRow("00000000-0000-0000-0000-000000000001", name, None, w, lo, dr, sport, None)


def _hits(slug: str) -> list[dict]:
    return json.loads((FIXTURES / f"{slug}.json").read_text())["data"]


def test_mma_fighter_is_not_applicable_and_never_calls_the_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(name: str) -> None:
        raise AssertionError("the live source must not be queried for MMA fighters")

    monkeypatch.setattr(corroborate, "cached_search", boom)
    out = corroborate_fighter(_row("Merab Dvalishvili", sport="mma"))
    assert out.status == "NOT_APPLICABLE"


def test_source_down_is_unavailable_never_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(corroborate, "cached_search", lambda name: (None, "none", None))
    out = corroborate_fighter(_row("Ryan Garcia"))
    assert out.status == "UNAVAILABLE"
    assert tighten("CLEAR", out) == ("CLEAR", None)


def test_no_exact_match_is_unmatched_not_disagreed() -> None:
    # Real case: Hugo Alfredo Santillan is absent from the live source; the search
    # returns 5 other fighters. Absence of evidence must never read as disagreement.
    out = corroborate_from_hits(_row("Hugo Alfredo Santillan"), _hits("hugo_alfredo_santillan"))
    assert out.status == "UNMATCHED"
    assert tighten("CLEAR", out) == ("CLEAR", None)


def test_record_fill_when_no_record_on_file() -> None:
    # Real case: our boxing rows carry 0-0-0 (record not on file). The live 25-2-0
    # fills the gap; it does not contradict an empty record.
    out = corroborate_from_hits(_row("Ryan Garcia"), _hits("ryan_garcia"))
    assert out.status == "CONFIRMED"
    assert out.live_record == "25-2-0"


def test_consistent_record_confirms() -> None:
    out = corroborate_from_hits(_row("Ryan Garcia", w=25, lo=2, dr=0), _hits("ryan_garcia"))
    assert out.status == "CONFIRMED"


def test_live_more_bouts_than_file_disagrees_and_tightens() -> None:
    # File says 24-1-0 (25 bouts); live shows 27. A stale record is the Tim Hague
    # failure mode: the CLEAR must be withheld.
    out = corroborate_from_hits(_row("Ryan Garcia", w=24, lo=1, dr=0), _hits("ryan_garcia"))
    assert out.status == "DISAGREED"
    assert tighten("CLEAR", out) == ("DO_NOT_CLEAR", DISAGREEMENT_RULE)


def test_live_fewer_bouts_is_coverage_gap_not_disagreement() -> None:
    out = corroborate_from_hits(_row("Ryan Garcia", w=30, lo=2, dr=0), _hits("ryan_garcia"))
    assert out.status == "CONFIRMED"


def test_duplicate_exact_names_withhold_corroboration() -> None:
    hits = _hits("ryan_garcia")
    exact = next(h for h in hits if h["name"].casefold() == "ryan garcia")
    out = corroborate_from_hits(_row("Ryan Garcia"), [exact, dict(exact)])
    assert out.status == "UNMATCHED"


def test_missing_stats_keys_confirm_identity_without_comparison() -> None:
    # Real upstream quirk: stats keys are optional per fighter (total_bouts is also
    # inconsistent with w+l+d where present, which is why sums are computed).
    hits = _hits("ryan_garcia")
    exact = dict(next(h for h in hits if h["name"].casefold() == "ryan garcia"))
    exact["stats"] = {"wins": 25, "losses": 2}  # draws missing
    out = corroborate_from_hits(_row("Ryan Garcia", w=1, lo=0, dr=0), [exact])
    assert out.status == "CONFIRMED"
    assert out.live_record is None


def test_tighten_never_loosens_and_only_flips_clear() -> None:
    disagreed = CorroborationOut(status="DISAGREED", note="x")
    assert tighten("DO_NOT_CLEAR", disagreed) == ("DO_NOT_CLEAR", None)
    for status in ("CONFIRMED", "UNMATCHED", "UNAVAILABLE", "NOT_APPLICABLE"):
        assert tighten("CLEAR", CorroborationOut(status=status, note="x")) == ("CLEAR", None)
        assert tighten("DO_NOT_CLEAR", CorroborationOut(status=status, note="x")) == (
            "DO_NOT_CLEAR",
            None,
        )


def test_cached_origin_is_labeled_in_the_note(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        corroborate,
        "cached_search",
        lambda name: (_hits("ryan_garcia"), "cache", "2026-06-09T18:54:31+00:00"),
    )
    out = corroborate_fighter(_row("Ryan Garcia"))
    assert out.data_origin == "cache"
    assert "cached live data from 2026-06-09" in out.note


def test_demo_fixture_origin_never_claims_to_be_live(monkeypatch: pytest.MonkeyPatch) -> None:
    """Demo Evidence Rule (2026-06-10): a recorded fixture must say so on the card.

    Regression pin: this path used to render '(cached live data from ...)' for
    origin=demo-fixture, presenting a recorded response as live-derived."""
    monkeypatch.setattr(
        corroborate,
        "cached_search",
        lambda name: (_hits("ryan_garcia"), "demo-fixture", "2026-06-09T18:54:31+00:00"),
    )
    out = corroborate_fighter(_row("Ryan Garcia"))
    assert out.data_origin == "demo-fixture"
    assert "recorded real response from 2026-06-09" in out.note
    assert "live check unavailable" in out.note
    assert "cached live data" not in out.note


def test_chavez_fixture_record_fill() -> None:
    out = corroborate_from_hits(_row("Julio Cesar Chavez Jr."), _hits("julio_cesar_chavez_jr"))
    assert out.status == "CONFIRMED"
    assert out.live_record == "54-7-1"


# --- Adversarial-review regressions: shape-garbage and crash paths stay closed ----------


def test_non_dict_hits_are_ignored_not_crashing() -> None:
    # Valid JSON of the wrong shape (strings in the data list) must not crash a verdict.
    hits = ["some upstream error string", 42, None, *_hits("ryan_garcia")]
    out = corroborate_from_hits(_row("Ryan Garcia"), hits)
    assert out.status == "CONFIRMED"
    assert out.live_record == "25-2-0"


def test_non_dict_stats_routes_to_no_comparison() -> None:
    exact = dict(next(h for h in _hits("ryan_garcia") if h["name"].casefold() == "ryan garcia"))
    exact["stats"] = "25-2-0"  # truthy non-dict
    out = corroborate_from_hits(_row("Ryan Garcia", w=1, lo=0, dr=0), [exact])
    assert out.status == "CONFIRMED"
    assert out.live_record is None


def test_bool_and_negative_stats_never_compare() -> None:
    # isinstance(True, int) is True in Python; bools and negatives are upstream garbage
    # and must produce neither a fake CONFIRMED-consistent nor a garbage DISAGREED block.
    exact = dict(next(h for h in _hits("ryan_garcia") if h["name"].casefold() == "ryan garcia"))
    for garbage in (
        {"wins": True, "losses": False, "draws": False},
        {"wins": -50, "losses": 0, "draws": 0},
    ):
        exact["stats"] = garbage
        out = corroborate_from_hits(_row("Ryan Garcia", w=1, lo=0, dr=0), [exact])
        assert out.status == "CONFIRMED"
        assert out.live_record is None
        assert tighten("CLEAR", out) == ("CLEAR", None)


def test_corroborate_fighter_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # A corroboration crash must never destroy a verdict: ANY exception degrades to
    # UNAVAILABLE (also keeps a poisoned multi-day cache entry from blocking every check).
    def boom(name: str) -> None:
        raise RuntimeError("synthetic corroboration crash")

    monkeypatch.setattr(corroborate, "cached_search", boom)
    out = corroborate_fighter(_row("Ryan Garcia"))
    assert out.status == "UNAVAILABLE"
    assert tighten("CLEAR", out) == ("CLEAR", None)
