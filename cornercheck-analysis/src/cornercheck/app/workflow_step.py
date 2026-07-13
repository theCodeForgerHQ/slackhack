"""Workflow Builder custom step: "Check fighter clearance".

A workflow creator drags this step into any Slack workflow (a booking form, an intake
flow) and gets the SAME deterministic verdict the assistant gives: CLEAR, DO_NOT_CLEAR,
NEEDS_PICK, or NOT_FOUND, with the blocking record cited in the detail output.

The fail-closed contract for automation: this step NEVER auto-clears and never resolves
ambiguity itself. NEEDS_PICK and NOT_FOUND come back as explicit statuses a workflow can
branch on (and the detail says to pick a candidate in the assistant), and any internal
error calls fail(), which HALTS the workflow: a halted workflow cannot book a fighter.
Every verdict this step produces is ledgered by the same pipeline as every other surface.
"""

import logging
import uuid

from slack_bolt import Ack, App, Complete, Fail

from cornercheck.brain.pipeline import start_clearance
from cornercheck.brain.schemas import ClearanceVerdict

log = logging.getLogger("cornercheck.workflow_step")

STEP_CALLBACK_ID = "check_fighter_clearance"

_STATUS_OUT = {
    "CLEAR": "CLEAR",
    "DO_NOT_CLEAR": "DO_NOT_CLEAR",
    "NEEDS_DISAMBIGUATION": "NEEDS_PICK",
    "NOT_FOUND": "NOT_FOUND",
}


def outputs_for(v: ClearanceVerdict) -> dict[str, str]:
    """Map the deterministic verdict to the step's outputs. Pure and unit-tested."""
    if v.status not in _STATUS_OUT:
        # A future status must surface loudly while staying fail-closed.
        log.warning("unmapped verdict status %r coerced to NOT_FOUND", v.status)
    status = _STATUS_OUT.get(v.status, "NOT_FOUND")
    if v.status == "DO_NOT_CLEAR":
        if v.active_suspensions:
            s = v.active_suspensions[0]
            ends = (
                "INDEFINITE (until cleared)" if s.indefinite or not s.end_date else str(s.end_date)
            )
            detail = (
                f"Blocked: {s.suspension_type} suspension, {s.jurisdiction}, ends {ends}. "
                f"Source: {s.source_url}"
            )
        else:
            detail = "Blocked. See the verdict notes in the CornerCheck assistant."
        if v.consultation_note:
            detail += f" Note: {v.consultation_note}"
    elif v.status == "CLEAR":
        detail = (
            "No recorded suspension matched the cited cases on file. Decision support; "
            "a human makes the final call and commissions remain the source of truth."
        )
        if v.corroboration and v.corroboration.live_record:
            detail += f" Live record: {v.corroboration.live_record}."
    elif v.status == "NEEDS_DISAMBIGUATION":
        detail = (
            f"{len(v.candidates)} fighters match this name. NOT cleared. Open the "
            "CornerCheck assistant in Slack and pick the exact fighter."
        )
    else:
        detail = "No confident identity match. NOT cleared; refusing to guess."
    return {
        "status": status,
        "detail": detail[:1500],
        "fighter": v.fighter_name or v.query or "",
    }


def _fail_quietly(fail: Fail, message: str) -> None:
    """fail() is itself a Slack API call and can raise when Slack is already down; the
    handler must never let its own remedy escape (the platform times the step out)."""
    try:
        fail(message)
    except Exception:
        log.exception("could not deliver fail() to Slack; execution times out platform-side")


def register_workflow_step(app: App) -> None:
    @app.function(STEP_CALLBACK_ID)
    def on_check_clearance(ack: Ack, inputs: dict, complete: Complete, fail: Fail) -> None:
        ack()
        thread_key = f"wfstep:{uuid.uuid4()}"
        verdict = None
        try:
            raw_name = inputs.get("fighter_name")
            if raw_name is not None and not isinstance(raw_name, str):
                _fail_quietly(fail, "fighter_name must be text. Treat as NOT cleared.")
                return
            fighter_name = str(raw_name or "").strip()
            jurisdiction = str(inputs.get("jurisdiction") or "").strip() or None
            if not fighter_name:
                _fail_quietly(fail, "No fighter name was provided to the clearance step.")
                return
            verdict = start_clearance(thread_key, fighter_name, None, jurisdiction)
            complete(outputs=outputs_for(verdict))
        except Exception as e:
            # fail() HALTS the workflow: the fail-closed direction for automation. The
            # log distinguishes "pipeline crashed" from "verdict computed and ledgered
            # but delivery failed" so a ledgered decision is reconcilable later.
            log.exception(
                "workflow step failed for inputs=%s (ledgered_seq=%s)",
                inputs,
                getattr(verdict, "ledger_seq", None),
            )
            _fail_quietly(
                fail, f"Clearance check failed ({type(e).__name__}). Treat as NOT cleared."
            )
        finally:
            # Single-shot key: nothing ever reads it again; without this an unattended
            # workflow leaks one session entry per execution for the process lifetime.
            from cornercheck.session.state import SESSION_STORE

            SESSION_STORE.discard(thread_key)
