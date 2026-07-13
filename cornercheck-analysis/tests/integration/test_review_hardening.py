"""Regression tests for the Stage 4 adversarial-review findings: every gate hole the
reviewers found stays closed forever."""

import asyncio
import json
from typing import Any

import pytest
from fastmcp import Client

from cornercheck.brain.hooks import GATED_TOOL, make_ledger_gate
from cornercheck.brain.pipeline import start_clearance
from cornercheck.mcp_server.server import mcp
from cornercheck.session.state import SESSION_STORE, SessionStore


def _call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    async def run() -> dict[str, Any]:
        async with Client(mcp) as client:
            result = await client.call_tool(tool, args)
            return json.loads(result.content[0].text)

    return asyncio.run(run())


# --- M1: malformed hook payloads fail CLOSED -------------------------------------


def _run_gate(gate: Any, payload: Any) -> dict[str, Any]:
    return dict(asyncio.run(gate(payload, "tu", {})))


def test_gate_denies_non_dict_payload() -> None:
    gate = make_ledger_gate(SessionStore())
    out = _run_gate(gate, "not a dict")
    assert out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def test_gate_denies_non_dict_tool_input() -> None:
    gate = make_ledger_gate(SessionStore())
    out = _run_gate(gate, {"tool_name": GATED_TOOL, "tool_input": "garbage"})
    assert out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


# --- I2/H2: malformed write inputs produce structured, LEDGERED refusals ----------


def test_record_clearance_refuses_garbage_fighter_id_and_ledgers_it(db: str) -> None:
    out = _call(
        "ledger_record_clearance",
        {"thread_key": "t-probe", "fighter_id": "not-a-uuid", "decision": "CLEAR"},
    )
    assert out["recorded"] is False
    assert "not a valid id" in out["refusal_reason"]
    assert "denial_seq" in out  # the probe left an audit trace
    recent = _call("ledger_recent_entries", {"limit": 1})
    assert recent["entries"][0]["action"] == "clearance_write_denied"


def test_record_clearance_refuses_garbage_date(db: str) -> None:
    out = _call(
        "ledger_record_clearance",
        {
            "thread_key": "t-date",
            "fighter_id": "00000000-0000-0000-0000-000000000000",
            "decision": "CLEAR",
            "on_date": "yesterday",
        },
    )
    assert out["recorded"] is False
    assert "ISO date" in out["refusal_reason"]


# --- H1: infrastructure failure becomes a typed ERROR envelope, never a clearance --


def test_tool_db_failure_returns_error_envelope(db: str, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(fighter_id: str) -> Any:
        raise RuntimeError("simulated datastore outage")

    monkeypatch.setattr("cornercheck.mcp_server.server.get_suspensions", boom)
    out = _call(
        "rules_evaluate_clearance",
        {"fighter_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert out["status"] == "ERROR"
    assert out["is_clearance"] is False
    assert "decision" not in out  # an error can never carry a decision


# --- H4: NOT_FOUND is terminal, the thread never waits on a phantom pick ----------


def test_not_found_resets_thread_state(db: str) -> None:
    v = start_clearance("th-notfound", "Zzyzx Qwerty Nonexistent")
    assert v.status == "NOT_FOUND"
    st = SESSION_STORE.get("th-notfound")
    assert st.stage == "new"
    assert st.candidate_ids == {}


# --- I1: gate reads a snapshot, never the live object ------------------------------


def test_snapshot_is_a_copy() -> None:
    store = SessionStore()
    store.set_candidates("t", {"f1": "Fighter One"})
    snap = store.snapshot("t")
    store.confirm("t", "f1")
    assert snap.confirmed_fighter_id is None  # snapshot is frozen in time
    assert store.get("t").confirmed_fighter_id == "f1"
