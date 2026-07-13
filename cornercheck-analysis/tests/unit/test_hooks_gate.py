"""The PreToolUse ledger gate (lock 2): deterministic denial paths."""

import asyncio
from typing import Any

from cornercheck.brain.hooks import GATED_TOOL, make_ledger_gate
from cornercheck.session.state import SessionStore


def _run(gate: Any, tool_name: str, args: dict) -> dict:
    payload = {"tool_name": tool_name, "tool_input": args}
    return asyncio.run(gate(payload, "tu_1", {}))


def _denied(out: dict) -> bool:
    return out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def test_other_tools_pass_through() -> None:
    gate = make_ledger_gate(SessionStore())
    assert _run(gate, "mcp__cornercheck__er_resolve_fighter", {"query": "x"}) == {}


def test_write_denied_without_confirmation() -> None:
    gate = make_ledger_gate(SessionStore())
    out = _run(gate, GATED_TOOL, {"thread_key": "t", "fighter_id": "f1", "decision": "CLEAR"})
    assert _denied(out)
    assert "no fighter has been confirmed" in str(out)


def test_write_denied_for_wrong_fighter() -> None:
    store = SessionStore()
    store.set_candidates("t", {"f1": "Fighter One"})
    store.confirm("t", "f1")
    store.record_verdict("t", "CLEAR")
    gate = make_ledger_gate(store)
    out = _run(gate, GATED_TOOL, {"thread_key": "t", "fighter_id": "f2", "decision": "CLEAR"})
    assert _denied(out)
    assert "not the confirmed fighter" in str(out)


def test_write_denied_for_verdict_mismatch() -> None:
    store = SessionStore()
    store.set_candidates("t", {"f1": "Fighter One"})
    store.confirm("t", "f1")
    store.record_verdict("t", "DO_NOT_CLEAR")
    gate = make_ledger_gate(store)
    # The agent "tries" to flip the verdict to CLEAR: blocked.
    out = _run(gate, GATED_TOOL, {"thread_key": "t", "fighter_id": "f1", "decision": "CLEAR"})
    assert _denied(out)
    assert "does not match the rule-engine verdict" in str(out)


def test_write_allowed_when_everything_matches() -> None:
    store = SessionStore()
    store.set_candidates("t", {"f1": "Fighter One"})
    store.confirm("t", "f1")
    store.record_verdict("t", "DO_NOT_CLEAR")
    gate = make_ledger_gate(store)
    out = _run(
        gate, GATED_TOOL, {"thread_key": "t", "fighter_id": "f1", "decision": "DO_NOT_CLEAR"}
    )
    assert out == {}
