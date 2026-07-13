"""The fail-closed disambiguation card: the signature CornerCheck moment.

When identity is ambiguous the agent REFUSES to decide and asks a human to pick, showing
DOB/weight/record/jurisdiction so the choice is recognition, not recall (report 19).
One section per candidate with a Select button carrying the fighter_id."""

from typing import Any

from cornercheck.brain.schemas import ClearanceVerdict


def build_disambiguation_card(v: ClearanceVerdict) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Which fighter? (refusing to guess)"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":warning: *{v.identity_note}*\n"
                    "Clearing the wrong fighter can be fatal, so CornerCheck will not decide "
                    "until you confirm exactly who this is."
                ),
            },
        },
        {"type": "divider"},
    ]
    for c in v.candidates[:5]:
        jx = c.jurisdiction or "jurisdiction unknown"
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{c.full_name}*\n"
                        f"{c.weight_class or 'weight class n/a'} | record {c.record} | "
                        f"{c.sport} | {jx}"
                    ),
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Select"},
                    "action_id": "select_fighter",
                    "value": _encode(c.fighter_id, v.query, v.on_date.isoformat()),
                },
            }
        )
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "CornerCheck refuses to clear an ambiguous identity. Pick one.",
                }
            ],
        }
    )
    return blocks


def _encode(fighter_id: str, query: str, on_date: str) -> str:
    # button value is opaque to the user; pipe-delimited, query truncated for the 2000-char cap
    return f"{fighter_id}|{on_date}|{query[:120]}"


def decode(value: str) -> tuple[str, str, str]:
    parts = value.split("|", 2)
    fighter_id = parts[0]
    on_date = parts[1] if len(parts) > 1 else ""
    query = parts[2] if len(parts) > 2 else ""
    return fighter_id, on_date, query
