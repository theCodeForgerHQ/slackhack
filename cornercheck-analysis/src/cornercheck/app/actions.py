"""Block Kit interactivity: the disambiguation pick, the live safety-proof button,
the audit-trail view, and the Canvas export."""

import logging
from datetime import date

from slack_bolt import Ack, App
from slack_sdk import WebClient

from cornercheck.app.blocks.audit_table import build_audit_table, fallback_text
from cornercheck.app.blocks.disambiguation_card import decode
from cornercheck.app.blocks.proof_card import build_proof_card
from cornercheck.app.blocks.proof_card import fallback_text as proof_fallback
from cornercheck.app.blocks.verdict_card import build_verdict_card
from cornercheck.app.blocks.verdict_card import fallback_text as verdict_fallback
from cornercheck.app.canvas import export_audit_canvas
from cornercheck.app.context import action_token
from cornercheck.brain.pipeline import confirm_candidate
from cornercheck.db.pool import get_pool
from cornercheck.ledger.verify import verify_chain
from cornercheck.search.rts import InjuryScanResult, injury_scan
from cornercheck.verification.z3_safety import (
    counterexample_when_start_boundary_loosened,
    prove_engine_equivalent_to_spec,
)

log = logging.getLogger("cornercheck.actions")

# A thrown error after ack() would silently do nothing (the spinner clears); on the
# safety-critical confirm path we must instead post an explicit non-clearance.
_FAIL_CLOSED = (
    ":rotating_light: CornerCheck could not complete that. Treat as NOT cleared and re-run."
)


def register_actions(app: App) -> None:
    @app.action("select_fighter")
    def on_select_fighter(ack: Ack, body: dict, client: WebClient) -> None:
        ack()
        channel, thread_ts = _thread_coords(body)
        try:
            value = body["actions"][0]["value"]
            fighter_id, on_date_s, query = decode(value)
            thread_key = f"{channel}:{thread_ts}"
            on_date = date.fromisoformat(on_date_s) if on_date_s else None
            from cornercheck.app.parse import parse_request

            target = parse_request(query).target_jurisdiction if query else None
            verdict = confirm_candidate(thread_key, fighter_id, query, on_date, target)
            if verdict is None:
                _reply(
                    client,
                    channel,
                    thread_ts,
                    "That selection didn't match a candidate I offered. Please re-run.",
                )
                return
            scan = (
                injury_scan(client, _action_token(body), verdict.fighter_name or "")
                if verdict.fighter_name
                else InjuryScanResult()
            )
            _reply(
                client,
                channel,
                thread_ts,
                verdict_fallback(verdict),
                build_verdict_card(verdict, injury_hits=scan.hits, injury_scan_ok=scan.ok),
            )
        except Exception:
            log.exception("select_fighter failed: %s", body.get("actions"))
            _reply(client, channel, thread_ts, _FAIL_CLOSED)

    @app.action("view_safety_proof")
    def on_view_proof(ack: Ack, body: dict, client: WebClient) -> None:
        """Runs the REAL Z3 proof live (milliseconds) plus the non-vacuity control."""
        ack()
        channel, thread_ts = _thread_coords(body)
        try:
            positive = prove_engine_equivalent_to_spec()
            control = counterexample_when_start_boundary_loosened()
            _reply(
                client,
                channel,
                thread_ts,
                proof_fallback(positive),
                build_proof_card(positive, control),
            )
        except Exception:
            log.exception("view_safety_proof failed")
            _reply(
                client,
                channel,
                thread_ts,
                ":rotating_light: Could not run the safety proof right now. Treat the logic "
                "as unproven and retry.",
            )

    @app.action("view_audit_trail")
    def on_view_audit(ack: Ack, body: dict, client: WebClient) -> None:
        ack()
        channel, thread_ts = _thread_coords(body)
        try:
            result = verify_chain()
            _reply(
                client,
                channel,
                thread_ts,
                fallback_text(result.ok),
                build_audit_table(_recent_entries(), result.ok, result.detail),
            )
        except Exception:
            log.exception("view_audit_trail failed")
            _reply(
                client,
                channel,
                thread_ts,
                ":rotating_light: Could not read the audit ledger right now. Please retry.",
            )

    @app.action("export_audit_canvas")
    def on_export_canvas(ack: Ack, body: dict, client: WebClient) -> None:
        """Chain-verify, then export the trail to a shareable Canvas. A failed export
        never reads as a failed audit: the table stays authoritative."""
        ack()
        channel, thread_ts = _thread_coords(body)
        user_id = str((body.get("user") or {}).get("id") or "") or None
        try:
            result = verify_chain()
            permalink, note = export_audit_canvas(
                client, channel, _recent_entries(), result.ok, result.detail, user_id=user_id
            )
            if permalink:
                text = (
                    f":memo: Audit trail exported to a Canvas: <{permalink}|open it here>. "
                    "Durable and shareable; chain-verified at export time."
                )
            else:
                text = f":warning: {note}"
            _reply(client, channel, thread_ts, text)
        except Exception:
            log.exception("export_audit_canvas failed")
            _reply(
                client,
                channel,
                thread_ts,
                ":rotating_light: Could not export the Canvas. The in-Slack audit table "
                "remains authoritative.",
            )


def _thread_coords(body: dict) -> tuple[str, str]:
    """The assistant thread root, so replies render INLINE in the main chat (not a
    nested side-thread). thread_ts identifies the assistant conversation."""
    container = body.get("container", {})
    channel = container.get("channel_id") or body.get("channel", {}).get("id", "")
    thread_ts = container.get("thread_ts") or container.get("message_ts", "")
    return channel, thread_ts


def _reply(
    client: WebClient, channel: str, thread_ts: str, text: str, blocks: list[dict] | None = None
) -> None:
    client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=text, blocks=blocks)


def _action_token(body: dict) -> str | None:
    return action_token(body)


def _recent_entries() -> list[dict]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT seq, ts, actor, action, payload FROM ledger ORDER BY seq DESC LIMIT 20"
        ).fetchall()
    return [
        {"seq": r[0], "ts": r[1].isoformat(), "actor": r[2], "action": r[3], "payload": r[4]}
        for r in rows
    ]
