"""PreToolUse gate (lock 2): the agent cannot write a clearance unless THIS thread
confirmed THIS fighter and the engine verdict recorded for the thread matches the
decision being written. Deterministic code; the model cannot talk its way around it."""

from typing import Any, cast

from claude_agent_sdk import HookCallback

from cornercheck.session.state import SessionStore

GATED_TOOL = "mcp__cornercheck__ledger_record_clearance"


def _deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def make_ledger_gate(store: SessionStore) -> HookCallback:
    async def gate(input_data: Any, tool_use_id: str | None, context: Any) -> dict[str, Any]:
        # Malformed payloads fail CLOSED: a false deny costs a retry, a false allow
        # costs an ungated ledger write (review finding M1).
        if not isinstance(input_data, dict):
            return _deny("malformed gate input (non-dict payload); refusing the write")
        tool_name = input_data.get("tool_name")
        if tool_name != GATED_TOOL:
            return {}
        args = input_data.get("tool_input")
        if not isinstance(args, dict):
            return _deny("malformed gate input (non-dict tool_input); refusing the write")
        # Scope note: this gate validates "this thread_key confirmed this fighter and
        # this verdict", with thread_key supplied by the model from its prompt. It is
        # lock 2 of 3; the in-tool engine re-check (lock 1) holds regardless.
        thread_key = str(args.get("thread_key", ""))
        fighter_id = str(args.get("fighter_id", ""))
        decision = str(args.get("decision", ""))
        st = store.snapshot(thread_key)
        if st.confirmed_fighter_id is None:
            return _deny(
                "no fighter has been confirmed in this thread; resolve and confirm identity first"
            )
        if st.confirmed_fighter_id != fighter_id:
            return _deny(
                f"fighter_id {fighter_id!r} is not the confirmed fighter for this thread"
                f" ({st.confirmed_fighter_name!r}); refusing the write"
            )
        if st.last_verdict_decision != decision:
            return _deny(
                f"decision {decision!r} does not match the rule-engine verdict recorded for"
                f" this thread ({st.last_verdict_decision!r}); refusing the write"
            )
        return {}

    return cast(HookCallback, gate)
