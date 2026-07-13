"""Whole-card parsing + the card-board Block Kit builder."""

from datetime import date

from cornercheck.app.blocks.card_board import build_card_board
from cornercheck.app.parse import parse_card
from cornercheck.brain.schemas import ActiveSuspensionOut, ClearanceVerdict

ON = date(2026, 6, 8)


def test_parse_card_splits_matchups_and_jurisdiction() -> None:
    p = parse_card(
        "Card in Texas: Merab Dvalishvili vs Junior dos Santos, Bruno Silva vs Geoff Neal"
    )
    assert p.target_jurisdiction == "Texas"
    assert [f.lower() for f in p.fighters] == [
        "merab dvalishvili",
        "junior dos santos",
        "bruno silva",
        "geoff neal",
    ]


def test_parse_card_event_label() -> None:
    p = parse_card("UFC 310: Merab Dvalishvili vs Petr Yan, Junior dos Santos vs Tom Aspinall")
    assert p.event == "UFC 310"
    assert len(p.fighters) == 4


def test_parse_card_newline_list_without_vs() -> None:
    p = parse_card("clear my card:\nMerab Dvalishvili\nBruno Silva\nGeoff Neal")
    assert len(p.fighters) == 3


def test_parse_card_single_fighter_is_not_a_card() -> None:
    # one name, no matchup: not a card (the single-clearance path handles it)
    p = parse_card("Is Junior dos Santos cleared for Saturday's card?")
    assert len(p.fighters) <= 1


# --- Adversarial-review regressions: every parser fail-open stays closed ------------------


def test_same_name_distinct_fighters_are_not_deduped() -> None:
    # two real Bruno Silvas in different bouts: BOTH slots kept (no dedup); each fails closed
    p = parse_card("Card: Bruno Silva vs Geoff Neal, Bruno Silva vs Cain Velasquez")
    assert [f.lower() for f in p.fighters].count("bruno silva") == 2
    assert len(p.fighters) == 4


def test_name_with_jurisdiction_word_is_not_mangled() -> None:
    # 'California' is part of the name here, not a jurisdiction to strip mid-name
    assert "California Kid" in parse_card("Card: California Kid vs Geoff Neal").fighters


def test_short_names_are_kept_not_dropped() -> None:
    assert [f.lower() for f in parse_card("Card: AJ vs Bo").fighters] == ["aj", "bo"]


def test_and_is_not_a_bout_separator() -> None:
    # 'and' lives inside names; it must never fragment one into phantom fighters
    p = parse_card("Card: Tom and Jerry vs Jon Jones")
    assert "Tom and Jerry" in p.fighters
    assert "Tom" not in p.fighters


def test_routing_single_vs_question_is_not_a_card() -> None:
    from cornercheck.app.assistant import _is_card_request

    assert _is_card_request("Is Merab Dvalishvili good to fight vs Petr Yan?") is False
    assert _is_card_request("Card: Ann vs Bob, Cal vs Dan") is True
    assert _is_card_request("Merab Dvalishvili vs Petr Yan, Bruno Silva vs Geoff Neal") is True


def _v(status: str, name: str, **kw) -> ClearanceVerdict:  # type: ignore[no-untyped-def]
    return ClearanceVerdict(status=status, query=name, on_date=ON, fighter_name=name, **kw)


def test_card_board_renders_mixed_results() -> None:
    verdicts = [
        _v("CLEAR", "Merab Dvalishvili", fighter_id="a"),
        _v(
            "DO_NOT_CLEAR",
            "Junior dos Santos",
            fighter_id="b",
            active_suspensions=[
                ActiveSuspensionOut(
                    suspension_type="KO",
                    start_date=date(2026, 5, 16),
                    end_date=None,
                    indefinite=True,
                    jurisdiction="CSAC",
                    reason="neuro hold",
                    source_url="https://example.test/src",
                )
            ],
            consultation_note="MMA has no federal equivalent",
        ),
        ClearanceVerdict(
            status="NEEDS_DISAMBIGUATION", query="Bruno Silva", on_date=ON, candidates=[]
        ),
    ]
    blocks = build_card_board(verdicts, event="UFC 310", on_date=ON)
    assert blocks[0]["type"] == "header"
    assert "UFC 310" in blocks[0]["text"]["text"]
    flat = str(blocks)
    assert "1 clear, 1 do not clear" in flat
    assert "need a human pick" in flat
    assert any(b.get("type") == "table" for b in blocks)
    # the table has a header row + 3 fighter rows
    table = next(b for b in blocks if b.get("type") == "table")
    assert len(table["rows"]) == 4
    # the blocker is cited below the board
    assert "example.test/src" in flat
    assert "MMA has no federal equivalent" in flat
