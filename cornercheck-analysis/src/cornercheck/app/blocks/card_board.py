"""The whole-card review board: a Data Table of every bout's clearance, the blockers
cited below it. The matchmaker's real workflow, not a one-at-a-time lookup."""

from datetime import date, datetime
from typing import Any

from cornercheck.brain.schemas import ClearanceVerdict

_LABEL = {
    "CLEAR": "CLEAR",
    "DO_NOT_CLEAR": "DO NOT CLEAR",
    "NEEDS_DISAMBIGUATION": "NEEDS PICK",
    "NOT_FOUND": "NO MATCH",
}
_EMOJI = {
    "CLEAR": ":large_green_circle:",
    "DO_NOT_CLEAR": ":red_circle:",
    "NEEDS_DISAMBIGUATION": ":warning:",
    "NOT_FOUND": ":white_circle:",
}


def _name(v: ClearanceVerdict) -> str:
    return v.fighter_name or v.query or "unknown"


def _detail(v: ClearanceVerdict) -> str:
    if v.status == "DO_NOT_CLEAR":
        if v.active_suspensions:
            s = v.active_suspensions[0]
            return f"{s.suspension_type} hold, {s.jurisdiction}"
        if v.corroboration and v.corroboration.status == "DISAGREED":
            return "live record disagreement"
        return "blocked, see notes"
    if v.status == "NEEDS_DISAMBIGUATION":
        return f"{len(v.candidates)} share this name, human pick required"
    if v.status == "NOT_FOUND":
        return "no confident match"
    return "no active suspension"


def build_card_board(
    verdicts: list[ClearanceVerdict],
    event: str | None = None,
    on_date: date | None = None,
    search_mode: str = "keyword",
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    d = on_date or date.today()
    n_clear = sum(1 for v in verdicts if v.status == "CLEAR")
    n_block = sum(1 for v in verdicts if v.status == "DO_NOT_CLEAR")
    n_pick = sum(1 for v in verdicts if v.status == "NEEDS_DISAMBIGUATION")
    n_none = sum(1 for v in verdicts if v.status == "NOT_FOUND")

    title = f"Card review: {event}" if event else "Card review"
    summary = (
        f"*{len(verdicts)} fighters* on {d.isoformat()}: {n_clear} clear, {n_block} do not clear"
    )
    if n_pick:
        summary += f", {n_pick} need a human pick"
    if n_none:
        summary += f", {n_none} no match"

    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": title[:150]}},
        {"type": "section", "text": {"type": "mrkdwn", "text": summary}},
    ]

    rows = [
        [
            {"type": "raw_text", "text": "Fighter"},
            {"type": "raw_text", "text": "Verdict"},
            {"type": "raw_text", "text": "Detail"},
        ]
    ]
    for v in verdicts[:20]:
        rows.append(
            [
                {"type": "raw_text", "text": _name(v)},
                {"type": "raw_text", "text": _LABEL.get(v.status, v.status)},
                {"type": "raw_text", "text": _detail(v)},
            ]
        )
    blocks.append(
        {
            "type": "table",
            "rows": rows,
            "column_settings": [
                {"align": "left", "is_wrapped": True},
                {"align": "center"},
                {"align": "left", "is_wrapped": True},
            ],
        }
    )

    # Cited blockers below the board, so the table stays scannable and the evidence is kept.
    blockers = [
        v
        for v in verdicts
        if v.status == "DO_NOT_CLEAR"
        and (v.active_suspensions or (v.corroboration and v.corroboration.status == "DISAGREED"))
    ]
    if blockers:
        blocks.append({"type": "divider"})
        for v in blockers[:6]:
            note = f"\n:scales: {v.consultation_note}" if v.consultation_note else ""
            if v.active_suspensions:
                s = v.active_suspensions[0]
                ends = (
                    "INDEFINITE (until cleared)"
                    if s.indefinite or not s.end_date
                    else s.end_date.isoformat()
                )
                src = f"<{s.source_url}|source>" if s.source_url else ""
                text = (
                    f"{_EMOJI['DO_NOT_CLEAR']} *{_name(v)}* - {s.suspension_type} "
                    f"suspension, {s.jurisdiction}\nEnds: {ends}\n{s.reason} {src}{note}"
                )
            else:  # corroboration-tightened: no suspension on file, the live source disagreed
                c = v.corroboration
                text = (
                    f"{_EMOJI['DO_NOT_CLEAR']} *{_name(v)}* - live record disagreement "
                    f"({c.source if c else 'live source'})\n{c.note if c else ''}{note}"
                )
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text[:3000]}})

    if n_pick:
        names = ", ".join(_name(v) for v in verdicts if v.status == "NEEDS_DISAMBIGUATION")
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f":warning: Ask me about each one to pick the fighter: {names}",
                    }
                ],
            }
        )

    stamp = (now or datetime.now()).strftime("%Y-%m-%d %H:%M")
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"Data as of {stamp} | RTS mode: {search_mode} | decision support, "
                        "human makes the call"
                    ),
                }
            ],
        }
    )
    # The same one-click evidence the single verdict card offers (audit DISC-1: the
    # board was the one verdict surface without them).
    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View audit trail"},
                    "action_id": "view_audit_trail",
                    "value": "card_board",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "See the safety proof"},
                    "action_id": "view_safety_proof",
                    "value": "card_board",
                },
            ],
        }
    )
    return blocks


def fallback_text(verdicts: list[ClearanceVerdict]) -> str:
    n_block = sum(1 for v in verdicts if v.status == "DO_NOT_CLEAR")
    return f"Card review: {len(verdicts)} fighters, {n_block} do not clear"
