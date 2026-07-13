"""Native Slack Lists mirror - predictions + decision register.

Uses the Lists API (slackLists.*, Sept 2025). Two lists, auto-created on first
use with the bot token:

  "Arbiter - Prediction Ledger"  : prediction / author / resolve by / status
  "Arbiter - Decision Register"  : decision topic / channel / date

Lists are a paid-plan feature: on the first hard failure (missing scope, free
plan, unknown method) this module disables itself for the session and the
text-based ledger remains the source of truth. Everything here is best-effort;
nothing raises.
"""
import os
import json
import datetime as _dt

from slack_sdk import WebClient

from arblog import get_logger

log = get_logger(__name__)
_client: WebClient | None = None
_disabled = False
_team_id: str | None = None


def _get_client() -> WebClient | None:
    global _client
    if _client is None and os.environ.get("SLACK_BOT_TOKEN"):
        _client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    return _client


def _state_file() -> str:
    """Per-workspace state — a List created in one workspace must never be
    written to from another (dev vs judging sandbox share this codebase)."""
    global _team_id
    if _team_id is None:
        try:
            _team_id = _get_client().auth_test().get("team_id", "unknown")
        except Exception:
            _team_id = "unknown"
    return os.path.join(os.path.dirname(__file__), f"lists_state_{_team_id}.json")


def _load_state() -> dict:
    try:
        return json.load(open(_state_file()))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    try:
        json.dump(state, open(_state_file(), "w"))
    except Exception:
        pass


def _rich(text: str) -> list:
    return [{"type": "rich_text", "elements": [
        {"type": "rich_text_section", "elements": [{"type": "text", "text": text[:250] or "-"}]}]}]


def _hard_fail(err: str) -> bool:
    return any(k in err for k in ("missing_scope", "not_allowed", "unknown_method",
                                  "paid_teams_only", "feature_not_enabled",
                                  "not_authed", "invalid_auth"))


def _ensure_list(kind: str) -> dict | None:
    """Return {"list_id", "cols": {key: column_id}, "opts": {value: option_id}} or None."""
    global _disabled
    if _disabled:
        return None
    state = _load_state()
    if state.get(kind, {}).get("list_id"):
        return state[kind]
    c = _get_client()
    if not c:
        return None

    if kind == "predictions":
        name = "Arbiter — Prediction Ledger"
        schema = [
            {"key": "prediction", "name": "Prediction", "type": "text", "is_primary_column": True},
            {"key": "author", "name": "Author", "type": "text"},
            {"key": "resolve_by", "name": "Resolve by", "type": "date"},
            {"key": "status", "name": "Status", "type": "select", "options": {
                "format": "single_select",
                "choices": [{"value": "open", "label": "Open", "color": "blue"},
                            {"value": "hit", "label": "Hit", "color": "green"},
                            {"value": "miss", "label": "Miss", "color": "red"}]}},
        ]
    else:  # decisions
        name = "Arbiter — Decision Register"
        schema = [
            {"key": "topic", "name": "Decision topic", "type": "text", "is_primary_column": True},
            {"key": "channel", "name": "Channel", "type": "text"},
            {"key": "date", "name": "Date", "type": "date"},
        ]

    try:
        resp = c.api_call("slackLists.create", json={"name": name, "schema": schema})
        if not resp.get("ok"):
            if _hard_fail(str(resp.get("error", ""))):
                _disabled = True
                log.warning(f"lists: disabled: {resp.get('error')}")
            return None
        list_id = resp.get("list_id") or (resp.get("list_metadata") or {}).get("id")
        cols, opts = {}, {}
        for col in (resp.get("list_metadata") or {}).get("schema", []):
            cols[col.get("key")] = col.get("id")
            if col.get("key") == "status":
                for ch in (col.get("options") or {}).get("choices", []):
                    opts[ch.get("value")] = ch.get("id") or ch.get("value")
        entry = {"list_id": list_id, "cols": cols, "opts": opts, "items": {}}
        state[kind] = entry
        _save_state(state)
        log.info(f"lists: created '{name}' ({list_id})")
        return entry
    except Exception as e:
        if _hard_fail(str(e)):
            _disabled = True
            log.warning(f"lists: disabled: {e}")
        return None


def _item_id_from(resp: dict) -> str:
    for k in ("item", "record"):
        v = resp.get(k) or {}
        if isinstance(v, dict) and v.get("id"):
            return v["id"]
    return resp.get("item_id") or resp.get("record_id") or ""


def add_prediction(prediction: str, author: str, resolve_by: str | None) -> None:
    entry = _ensure_list("predictions")
    c = _get_client()
    if not entry or not c:
        return
    cols, opts = entry["cols"], entry["opts"]
    fields = [{"column_id": cols.get("prediction"), "rich_text": _rich(prediction)},
              {"column_id": cols.get("author"), "rich_text": _rich(author)}]
    if resolve_by:
        fields.append({"column_id": cols.get("resolve_by"), "date": [resolve_by]})
    if cols.get("status") and opts.get("open"):
        fields.append({"column_id": cols["status"], "select": [opts["open"]]})
    fields = [f for f in fields if f.get("column_id")]
    try:
        resp = c.api_call("slackLists.items.create",
                          json={"list_id": entry["list_id"], "initial_fields": fields})
        if resp.get("ok"):
            item_id = _item_id_from(resp)
            if item_id:
                state = _load_state()
                state.setdefault("predictions", entry).setdefault("items", {})[prediction[:120]] = item_id
                _save_state(state)
    except Exception as e:
        log.warning(f"lists: add_prediction failed: {e}")


def mark_prediction(prediction: str, outcome: str) -> None:
    """Flip a prediction row's status to hit/miss."""
    state = _load_state()
    entry = state.get("predictions") or {}
    item_id = (entry.get("items") or {}).get(prediction[:120])
    c = _get_client()
    if not (entry.get("list_id") and item_id and c):
        return
    opt = (entry.get("opts") or {}).get(outcome)
    col = (entry.get("cols") or {}).get("status")
    if not (opt and col):
        return
    try:
        c.api_call("slackLists.items.update", json={
            "list_id": entry["list_id"], "id": item_id,
            "cells": [{"column_id": col, "row_id": item_id, "select": [opt]}]})
    except Exception as e:
        log.warning(f"lists: mark_prediction failed: {e}")


def add_decision(topic: str, channel: str) -> None:
    entry = _ensure_list("decisions")
    c = _get_client()
    if not entry or not c:
        return
    cols = entry["cols"]
    fields = [{"column_id": cols.get("topic"), "rich_text": _rich(topic)},
              {"column_id": cols.get("channel"), "rich_text": _rich(channel)},
              {"column_id": cols.get("date"), "date": [_dt.date.today().isoformat()]}]
    fields = [f for f in fields if f.get("column_id")]
    try:
        c.api_call("slackLists.items.create",
                   json={"list_id": entry["list_id"], "initial_fields": fields})
    except Exception as e:
        log.warning(f"lists: add_decision failed: {e}")
