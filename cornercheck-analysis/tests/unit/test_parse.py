"""Deterministic request parsing: names extracted, jurisdictions canonicalized, dates."""

from datetime import date

import pytest

from cornercheck.app.parse import parse_request


@pytest.mark.parametrize(
    ("text", "name", "jx"),
    [
        (
            "Is Junior dos Santos cleared for Saturday's card in Texas?",
            "Junior dos Santos",
            "Texas",
        ),
        ("Is Dragan Petrovic cleared for Saturday's card in Texas?", "Dragan Petrovic", "Texas"),
        ("Can Bruno Silva fight in Nevada?", "Bruno Silva", "Nevada"),
        ("Is Merab Dvalishvili good to go?", "Merab Dvalishvili", None),
        ("check Julio Cesar Chavez Jr in California", "Julio Cesar Chavez Jr", "California"),
        ("is nate diaz cleared", "nate diaz", None),
    ],
)
def test_parse_extracts_name_and_jurisdiction(text: str, name: str, jx: str | None) -> None:
    parsed = parse_request(text)
    assert parsed.fighter_query.lower() == name.lower()
    assert parsed.target_jurisdiction == jx


def test_parse_extracts_iso_date() -> None:
    parsed = parse_request("Is Geoff Neal cleared on 2026-07-01 in Texas?")
    assert parsed.on_date == date(2026, 7, 1)
    assert "Geoff Neal" in parsed.fighter_query


def test_parse_no_date_defaults_none() -> None:
    assert parse_request("Is Geoff Neal cleared?").on_date is None


def test_jurisdiction_synonyms() -> None:
    assert parse_request("clear him for vegas").target_jurisdiction == "Nevada"
    assert parse_request("CSAC check").target_jurisdiction == "California"
    assert parse_request("TDLR booking").target_jurisdiction == "Texas"
