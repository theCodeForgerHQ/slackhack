"""Audit-ledger view as a Data Table block (renders on desktop + mobile, verified spike D),
with a section-fields fallback for surfaces that don't support the table block."""

from typing import Any


def _rows_from_entries(entries: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    header = [
        {"type": "raw_text", "text": "Seq"},
        {"type": "raw_text", "text": "When (UTC)"},
        {"type": "raw_text", "text": "Action"},
        {"type": "raw_text", "text": "Fighter"},
        {"type": "raw_text", "text": "Decision"},
    ]
    rows = [header]
    for e in entries[:20]:
        p = e.get("payload") or {}
        if not isinstance(p, dict):
            p = {}  # a malformed row must never take the whole audit view down
        when = (e.get("ts") or "")[:16].replace("T", " ")
        rows.append(
            [
                # raw_text, NOT raw_number: Slack's table-cell schema rejected
                # raw_number with invalid_blocks in prod (platform drift, 2026-06-10 UTC).
                {"type": "raw_text", "text": str(e.get("seq", ""))},
                {"type": "raw_text", "text": when},
                {"type": "raw_text", "text": e.get("action", "")},
                {"type": "raw_text", "text": str(p.get("fighter_name", "-"))},
                {
                    "type": "raw_text",
                    "text": str(p.get("decision", p.get("attempted_decision", "-"))),
                },
            ]
        )
    return rows


def build_audit_table(
    entries: list[dict[str, Any]], chain_ok: bool, chain_detail: str
) -> list[dict[str, Any]]:
    integrity = ":lock: chain intact" if chain_ok else ":rotating_light: CHAIN BROKEN"
    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": "Audit ledger (tamper-evident)"}},
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"{integrity} - {chain_detail}"}],
        },
    ]
    if entries:
        blocks.append(
            {
                "type": "table",
                "rows": _rows_from_entries(entries),
                "column_settings": [
                    {"align": "right"},
                    {"align": "left"},
                    {"align": "left"},
                    {"align": "left", "is_wrapped": True},
                    {"align": "center"},
                ],
            }
        )
    else:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "_No ledger entries yet._"}}
        )
    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Export to Canvas"},
                    "action_id": "export_audit_canvas",
                    "value": "audit",
                }
            ],
        }
    )
    return blocks


def fallback_text(chain_ok: bool) -> str:
    return f"Audit ledger ({'intact' if chain_ok else 'BROKEN'})"
