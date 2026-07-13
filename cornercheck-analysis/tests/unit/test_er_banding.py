"""Banding golden fixtures: confirm/disambiguate/refuse behavior is pinned here."""

from cornercheck.er.thresholds import Candidate, band


def _c(name: str, score: float, fid: str = "x") -> Candidate:
    return Candidate(
        fighter_id=fid,
        full_name=name,
        weight_class="Welterweight",
        record="10-2-0",
        sport="mma",
        jurisdiction=None,
        score=score,
    )


def test_unique_high_confidence_confirms() -> None:
    r = band([_c("Merab Dvalishvili", 1.0, "a"), _c("Merab Dvalishvilo", 0.91, "b")])
    assert r.status == "CONFIRMED"
    assert r.candidates[0].fighter_id == "a"


def test_identical_names_always_disambiguate_even_at_perfect_score() -> None:
    r = band([_c("Bruno Silva", 1.0, "a"), _c("Bruno Silva", 1.0, "b")])
    assert r.status == "AMBIGUOUS"
    assert "human pick required" in r.note


def test_near_miss_lands_in_disambiguation_band() -> None:
    r = band([_c("Jon Smith", 0.90, "a"), _c("John Smith", 0.88, "b")])
    assert r.status == "AMBIGUOUS"


def test_close_runner_up_blocks_auto_confirm() -> None:
    r = band([_c("Jean Silva", 0.97, "a"), _c("Joan Silva", 0.96, "b")])
    assert r.status == "AMBIGUOUS"  # gap 0.01 < MARGIN


def test_garbage_refuses() -> None:
    r = band([_c("Completely Different", 0.40, "a")])
    assert r.status == "NOT_FOUND"
    assert "refusing to guess" in r.note


def test_empty_refuses() -> None:
    assert band([]).status == "NOT_FOUND"
