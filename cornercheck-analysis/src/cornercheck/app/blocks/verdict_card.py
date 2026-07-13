"""The clearance verdict card. header + colored emoji + fields + cited suspensions +
optional workspace injury signal + data-as-of/search-mode footer + audit-trail button.
(Normal-message blocks only; NOT the Alert block, which renders only in modals - report 19.)"""

from datetime import datetime
from typing import Any

from cornercheck.brain.schemas import ClearanceVerdict
from cornercheck.search.rts import InjuryHit

_STATUS = {
    "CLEAR": (":large_green_circle:", "CLEAR"),
    "DO_NOT_CLEAR": (":red_circle:", "DO NOT CLEAR"),
    "NOT_FOUND": (":white_circle:", "NO MATCH - REFUSING TO GUESS"),
}


def build_verdict_card(
    v: ClearanceVerdict,
    injury_hits: list[InjuryHit] | None = None,
    search_mode: str = "keyword",
    now: datetime | None = None,
    injury_scan_ok: bool = True,
) -> list[dict[str, Any]]:
    emoji, label = _STATUS.get(v.status, (":grey_question:", v.status))
    title = v.fighter_name or v.query or "Clearance check"
    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": f"CornerCheck: {title}"[:150]}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"{emoji} *{label}*"}},
    ]

    fields: list[dict[str, str]] = []
    if v.fighter_name:
        fields.append({"type": "mrkdwn", "text": f"*Fighter*\n{v.fighter_name}"})
    fields.append({"type": "mrkdwn", "text": f"*As of*\n{v.on_date.isoformat()}"})
    if fields:
        blocks.append({"type": "section", "fields": fields})

    if v.active_suspensions:
        blocks.append({"type": "divider"})
        for s in v.active_suspensions[:3]:
            ends = (
                "INDEFINITE (until cleared)"
                if s.indefinite or not s.end_date
                else (s.end_date.isoformat())
            )
            src = f"<{s.source_url}|source>" if s.source_url else ""
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*{s.suspension_type} suspension* - {s.jurisdiction}\n"
                            f"Ends: {ends}\n{s.reason} {src}".strip()
                        )[:3000],
                    },
                }
            )

    if v.consultation_note:
        blocks.append(
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f":scales: {v.consultation_note}"}],
            }
        )

    if v.corroboration and v.corroboration.status != "NOT_APPLICABLE":
        c = v.corroboration
        if c.status == "DISAGREED":
            alarm = f":rotating_light: *Live record disagreement* ({c.source})\n{c.note}"
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": alarm[:3000]},
                }
            )
        else:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f":satellite_antenna: Live check ({c.source}): {c.note}"[:3000],
                        }
                    ],
                }
            )

    if injury_hits:
        blocks.append({"type": "divider"})
        links = "\n".join(
            f"- <{h.permalink}|{h.author}>: {h.snippet}"
            if h.permalink
            else f"- {h.author}: {h.snippet}"
            for h in injury_hits[:3]
        )
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":mag: *Workspace injury signal* (from your team's Slack)\n{links}"[
                        :3000
                    ],
                },
            }
        )

    if not injury_scan_ok:
        # A failed scan must never render identically to "no injury chatter found":
        # the person making the safety call needs to know one of the three advertised
        # signals silently degraded.
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": ":mag: Workspace injury scan unavailable for this check.",
                    }
                ],
            }
        )

    if v.identity_note:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f":dart: Identity: {v.identity_note}"[:3000]}
                ],
            }
        )

    stamp = (now or datetime.now()).strftime("%Y-%m-%d %H:%M")
    footer = (
        f"Data as of {stamp} | RTS mode: {search_mode} | decision support, human makes the call"
    )
    if v.ledger_seq is not None:
        footer += f" | logged at seq {v.ledger_seq}"
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": footer}]})

    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View audit trail"},
                    "action_id": "view_audit_trail",
                    "value": str(v.ledger_seq or 0),
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "See the safety proof"},
                    "action_id": "view_safety_proof",
                    "value": str(v.ledger_seq or 0),
                },
            ],
        }
    )
    return blocks


def fallback_text(v: ClearanceVerdict) -> str:
    _, label = _STATUS.get(v.status, ("", v.status))
    return f"CornerCheck: {v.fighter_name or v.query} - {label} (as of {v.on_date.isoformat()})"
