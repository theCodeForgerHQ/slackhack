"""Audit trail exported to a Slack Canvas: a durable, shareable document a matchmaker
can hand to a promoter or commission. Generated deterministically from the ledger at
export time, chain-verified first, never from model prose.

Fail-soft by design: a failed EXPORT must never read as a failed AUDIT. The in-Slack
audit table stays authoritative; every failure path returns an actionable note instead
of raising into the listener."""

import logging
from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

log = logging.getLogger("cornercheck.canvas")

_AUTHORITATIVE = "the in-Slack audit table above stays authoritative"


def _cell(v: object) -> str:
    """Markdown-table cell sanitizer. Pipes and newlines in a ledger value could forge
    rows or a fake integrity banner in the exported document (adversarial review
    demonstrated exactly that with a hostile fighter name), and asterisks could render
    bold fake-banner text inside a cell; neutralize all of them."""
    return str(v).replace("|", "\\|").replace("*", "\\*").replace("\r", " ").replace("\n", " ")


def build_audit_markdown(entries: list[dict[str, Any]], chain_ok: bool, chain_detail: str) -> str:
    integrity = (
        f"intact ({_cell(chain_detail)})"
        if chain_ok
        else f"BROKEN: do not trust this export ({_cell(chain_detail)})"
    )
    lines = [
        "# CornerCheck audit trail",
        "",
        f"**Chain integrity at export time:** {integrity}",
        "",
        "Every entry is HMAC-SHA256 hash-chained in an append-only ledger; the chain was "
        "verified immediately before this export was generated.",
        "",
        "| Seq | When (UTC) | Actor | Action | Fighter | Decision |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for e in entries[:50]:
        p = e.get("payload") or {}
        if not isinstance(p, dict):
            p = {}
        when = (e.get("ts") or "")[:16].replace("T", " ")
        fighter = p.get("fighter_name") or "-"
        decision = p.get("decision") or p.get("attempted_decision") or "-"
        lines.append(
            f"| {_cell(e.get('seq', ''))} | {_cell(when)} | {_cell(e.get('actor', ''))} "
            f"| {_cell(e.get('action', ''))} | {_cell(fighter)} | {_cell(decision)} |"
        )
    lines += ["", "_Deterministic export. Decision support; a human makes the call._"]
    return "\n".join(lines)


def export_audit_canvas(
    client: WebClient,
    channel: str,
    entries: list[dict[str, Any]],
    chain_ok: bool,
    chain_detail: str,
    user_id: str | None = None,
) -> tuple[str | None, str]:
    """Create the canvas, grant read access, return (permalink, note).
    permalink None means there is no link to hand out; the note says what actually
    happened (not created / created but unshared / created+shared but unlinkable).

    The assistant pane's conversation id is a DM ("D..."), which the canvas
    channel-share API rejects, so there the canvas is shared to the requesting USER
    first; each share path falls back to the other before admitting defeat."""
    md = build_audit_markdown(entries, chain_ok, chain_detail)
    try:
        created = client.canvases_create(
            title="CornerCheck audit trail",
            document_content={"type": "markdown", "markdown": md},
        )
        canvas_id = str(created["canvas_id"])
        by_user: dict[str, Any] = {"user_ids": [user_id]} if user_id else {}
        by_channel: dict[str, Any] = {"channel_ids": [channel]}
        attempts = [by_user, by_channel] if channel.startswith("D") else [by_channel, by_user]
        shared = False
        for grant in attempts:
            if not grant:
                continue
            try:
                client.canvases_access_set(canvas_id=canvas_id, access_level="read", **grant)
                shared = True
                break
            except SlackApiError as e:
                err = str(e.response.get("error") or "") if e.response is not None else ""
                log.warning(
                    "canvas share via %s failed (%s)", next(iter(grant)), err or "api error"
                )
            except Exception as e:
                log.warning("canvas share via %s failed (%s)", next(iter(grant)), type(e).__name__)
        if not shared:
            # The canvas EXISTS at this point; reporting a plain failure would be a lie
            # and would leave an orphaned document nobody was told about.
            return None, (
                "Canvas was created but could not be shared to this channel "
                f"automatically; an admin can find it in the workspace. {_AUTHORITATIVE}."
            )
        permalink = ""
        try:
            info = client.files_info(file=canvas_id)
            permalink = str(info["file"].get("permalink") or "")
        except Exception as e:
            log.warning("canvas created but permalink lookup failed (%s)", type(e).__name__)
        if permalink:
            return permalink, "exported"
        return None, (
            "Canvas created and shared to this channel (look under the channel's "
            "Canvases); a direct link was not available."
        )
    except SlackApiError as e:
        err = ""
        if e.response is not None:
            err = str(e.response.get("error") or "")
        if err == "missing_scope":
            return None, (
                "Canvas export needs the canvases:write and files:read scopes: update the "
                "app from slack/manifest.json, reinstall it to the workspace, and retry. "
                f"Until then {_AUTHORITATIVE}."
            )
        if err in (
            "feature_not_enabled",
            "canvas_disabled_user_team",
            "free_team_not_allowed",
            "free_teams_cannot_create_non_tabbed_canvases",
        ):
            return None, f"Canvas is not enabled on this workspace plan; {_AUTHORITATIVE}."
        log.warning("canvas export failed (%s)", err or type(e).__name__)
        return None, f"Canvas export failed ({err or 'api error'}); {_AUTHORITATIVE}."
    except Exception as e:
        log.warning("canvas export failed (%s: %s)", type(e).__name__, e)
        return None, f"Canvas export failed; {_AUTHORITATIVE}."
