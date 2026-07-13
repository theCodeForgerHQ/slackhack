"""App Home dashboard: recent clearance decisions + live chain integrity."""

import logging
from typing import Any

from slack_bolt import App
from slack_sdk import WebClient

from cornercheck.db.pool import get_pool
from cornercheck.ledger.verify import verify_chain

log = logging.getLogger("cornercheck.home")


def register_home(app: App) -> None:
    @app.event("app_home_opened")
    def on_home_opened(event: dict, client: WebClient) -> None:
        # Build and publish fail separately so the fallback message matches the actual
        # failure: a ledger outage gets the honest "can't reach the ledger" view; a
        # Slack-side publish failure (block-schema drift) can only be logged.
        try:
            view = _home_view()
        except Exception:
            log.exception("home view build failed; publishing the fallback view")
            view = _fallback_view()
        try:
            client.views_publish(user_id=event["user"], view=view)
        except Exception:
            log.exception("views_publish failed")


def _home_view() -> dict[str, Any]:
    result = verify_chain()
    entries = _recent_decisions()
    integrity = ":lock: intact" if result.ok else ":rotating_light: BROKEN"
    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": "CornerCheck"}},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "Fighter-safety clearance for fight-operations teams. Cross-jurisdiction "
                    "suspensions, return windows, and your team's own injury chatter, with a "
                    "tamper-evident audit trail. *Decision support: a human makes the final call.*"
                ),
            },
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"Audit chain: {integrity} - {result.detail}"}],
        },
        {"type": "divider"},
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Data coverage, honestly stated"},
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": _coverage_text()}},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "A CLEAR means no recorded suspension matched the cited cases on file; "
                        "commissions remain the source of truth. Decision support over curated "
                        "records, not an exhaustive national registry."
                    ),
                }
            ],
        },
        {"type": "divider"},
        {"type": "header", "text": {"type": "plain_text", "text": "Recent decisions"}},
    ]
    if not entries:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "_No decisions recorded yet._"}}
        )
    for e in entries:
        p = e["payload"] or {}
        decision = p.get("decision", p.get("attempted_decision", "-"))
        if e["action"] == "clearance_write_denied":
            # A REFUSED write must never wear the attempted decision's colors: a denied
            # CLEAR rendering green invites misreading the denial as a clearance.
            emoji = ":no_entry:"
            headline = f"DENIED write attempt ({decision})"
        else:
            emoji = (
                ":red_circle:"
                if "DO_NOT" in str(decision)
                else (":large_green_circle:" if decision == "CLEAR" else ":white_circle:")
            )
            headline = str(decision)
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{emoji} *{p.get('fighter_name', 'unknown')}* - {headline}\n"
                        f"seq {e['seq']} | {e['action']} | {e['ts'][:16].replace('T', ' ')}"
                    ),
                },
            }
        )
    return {"type": "home", "blocks": blocks}


def _fallback_view() -> dict[str, Any]:
    return {
        "type": "home",
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "CornerCheck"}},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        ":rotating_light: CornerCheck cannot reach its audit ledger right "
                        "now, so this dashboard is unavailable. Clearance checks may also "
                        "be degraded; treat anything unconfirmed as NOT cleared."
                    ),
                },
            },
        ],
    }


def _coverage_text() -> str:
    """Live coverage stats. Fail-soft: the home view must render even if this query
    fails, just without the numbers."""
    try:
        with get_pool().connection() as conn:
            n_f = conn.execute("SELECT count(*) FROM fighters").fetchone()
            n_s = conn.execute("SELECT count(*) FROM suspensions").fetchone()
            n_j = conn.execute("SELECT count(DISTINCT jurisdiction) FROM suspensions").fetchone()
        ident = "identity on legacy bands (conformal calibration unavailable)"
        try:
            from cornercheck.er.conformal import load_gate

            gate = load_gate()
            if gate:
                ident = (
                    f"identity conformally calibrated at {gate.coverage_pct}% coverage (n={gate.n})"
                )
        except Exception:
            log.exception("conformal stat failed; coverage panel keeps the DB counts")
        return (
            f"*{n_s[0] if n_s else '?'}* source-cited suspension cases across "
            f"*{n_j[0] if n_j else '?'}* jurisdictions | "
            f"*{n_f[0]:,}* fighters on file | "
            f"live boxing-data corroboration (tighten-only) | {ident}"
            if n_f
            else "_Coverage stats unavailable right now._"
        )
    except Exception:
        log.exception("coverage stats failed")
        return "_Coverage stats unavailable right now._"


def _recent_decisions() -> list[dict[str, Any]]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT seq, ts, action, payload FROM ledger"
            " WHERE action IN ('clearance_decision', 'clearance_write_denied')"
            " ORDER BY seq DESC LIMIT 8"
        ).fetchall()
    return [{"seq": r[0], "ts": r[1].isoformat(), "action": r[2], "payload": r[3]} for r in rows]
