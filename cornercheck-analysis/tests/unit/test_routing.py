"""Routing classifier regression tests (review finding F1): whole-word matching so a
fighter name containing a meta-word substring still reaches the deterministic card."""

import pytest

from cornercheck.app.assistant import _is_clearance_request


@pytest.mark.parametrize(
    "text",
    [
        "Is Junior dos Santos cleared in Texas?",
        "Is Bruno Silva cleared to fight?",
        "Is Merab Dvalishvili good to go?",  # 'go' is not a cue word now; 'cleared'? no -> check
        "Is Howard cleared in Nevada?",  # 'how' substring must NOT misroute
        "Is Scanlon cleared to fight?",  # 'scan' substring must NOT misroute
        "Can Hollister compete on Saturday?",  # 'list' substring must NOT misroute
        "Is Whatley cleared?",  # 'what' substring must NOT misroute
    ],
)
def test_clearance_questions_route_to_deterministic_card(text: str) -> None:
    # All have a real cue word + extractable fighter and no whole-word meta keyword.
    assert _is_clearance_request(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "Is the audit chain intact?",
        "Why was Junior dos Santos refused?",
        "Scan for injury chatter this week",
        "Explain the suspension for Bruno Silva",
        "Show me the recent ledger entries",
        "What is the clearance status history?",
        "tell me about the audit trail",
    ],
)
def test_meta_questions_route_to_brain(text: str) -> None:
    assert _is_clearance_request(text) is False


def test_no_fighter_routes_to_brain() -> None:
    assert _is_clearance_request("can you help me") is False
