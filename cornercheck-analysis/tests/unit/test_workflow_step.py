"""The Workflow Builder step: verdict-to-outputs mapping and the fail-closed handler."""

from datetime import date
from typing import Any

from cornercheck.app import workflow_step
from cornercheck.app.workflow_step import outputs_for
from cornercheck.brain.schemas import ActiveSuspensionOut, ClearanceVerdict, CorroborationOut

ON = date(2026, 6, 9)


def _v(status: str, **kw: Any) -> ClearanceVerdict:
    return ClearanceVerdict(status=status, query="X", on_date=ON, **kw)


def test_blocked_output_cites_the_record() -> None:
    v = _v(
        "DO_NOT_CLEAR",
        fighter_name="Junior dos Santos",
        active_suspensions=[
            ActiveSuspensionOut(
                suspension_type="medical",
                start_date=ON,
                end_date=None,
                indefinite=True,
                jurisdiction="CSAC",
                reason="pending neurological clearance",
                source_url="https://example.test/csac",
            )
        ],
        consultation_note="consult CSAC first",
    )
    out = outputs_for(v)
    assert out["status"] == "DO_NOT_CLEAR"
    assert "INDEFINITE" in out["detail"] and "CSAC" in out["detail"]
    assert "https://example.test/csac" in out["detail"]
    assert "consult CSAC first" in out["detail"]
    assert out["fighter"] == "Junior dos Santos"


def test_clear_output_stays_decision_support() -> None:
    v = _v(
        "CLEAR",
        fighter_name="Ryan Garcia",
        corroboration=CorroborationOut(status="CONFIRMED", note="x", live_record="25-2-0"),
    )
    out = outputs_for(v)
    assert out["status"] == "CLEAR"
    assert "human makes the final call" in out["detail"]
    assert "25-2-0" in out["detail"]


def test_ambiguity_gates_to_a_human_never_resolves_itself() -> None:
    v = _v("NEEDS_DISAMBIGUATION", candidates=[])
    out = outputs_for(v)
    assert out["status"] == "NEEDS_PICK"
    assert "NOT cleared" in out["detail"]
    assert "pick" in out["detail"]


def test_not_found_refuses() -> None:
    out = outputs_for(_v("NOT_FOUND"))
    assert out["status"] == "NOT_FOUND"
    assert "refusing to guess" in out["detail"]


class _Recorder:
    def __init__(self) -> None:
        self.completed: dict[str, Any] | None = None
        self.failed: str | None = None

    def complete(self, outputs: dict[str, Any]) -> None:
        self.completed = outputs

    def fail(self, error: str) -> None:
        self.failed = error


def _run_handler(
    inputs: dict[str, Any], monkeypatch: Any, verdict: Any = None, custom: Any = None
) -> _Recorder:
    rec = _Recorder()
    if custom is not None:
        monkeypatch.setattr(workflow_step, "start_clearance", custom)
    elif verdict is not None:
        monkeypatch.setattr(workflow_step, "start_clearance", lambda *a, **k: verdict)
    else:

        def boom(*a: Any, **k: Any) -> None:
            raise RuntimeError("db exploded")

        monkeypatch.setattr(workflow_step, "start_clearance", boom)

    class FakeApp:
        def function(self, cid: str) -> Any:
            def deco(fn: Any) -> Any:
                self.fn = fn
                return fn

            return deco

    app = FakeApp()
    workflow_step.register_workflow_step(app)  # type: ignore[arg-type]
    app.fn(ack=lambda: None, inputs=inputs, complete=rec.complete, fail=rec.fail)
    return rec


def test_handler_completes_with_the_verdict(monkeypatch: Any) -> None:
    rec = _run_handler({"fighter_name": "X"}, monkeypatch, verdict=_v("CLEAR", fighter_name="X"))
    assert rec.completed is not None and rec.completed["status"] == "CLEAR"
    assert rec.failed is None


def test_handler_fails_closed_on_crash(monkeypatch: Any) -> None:
    # fail() HALTS the workflow: the safe direction for automation.
    rec = _run_handler({"fighter_name": "X"}, monkeypatch)
    assert rec.completed is None
    assert rec.failed is not None and "NOT cleared" in rec.failed


def test_handler_refuses_empty_name(monkeypatch: Any) -> None:
    rec = _run_handler({}, monkeypatch, verdict=_v("CLEAR"))
    assert rec.completed is None
    assert rec.failed is not None and "No fighter name" in rec.failed


def test_handler_never_leaks_session_entries(monkeypatch: Any) -> None:
    # An unattended workflow can execute thousands of times; each run must discard its
    # single-shot session key (review measured ~409 bytes leaked per run pre-fix).
    from cornercheck.session.state import SESSION_STORE

    def fake_clearance(thread_key: str, *a: Any, **k: Any) -> ClearanceVerdict:
        SESSION_STORE.reset(thread_key)  # simulate the pipeline touching the store
        return _v("CLEAR")

    monkeypatch.setattr(workflow_step, "start_clearance", fake_clearance)
    before = len(SESSION_STORE._threads)
    rec = _run_handler({"fighter_name": "X"}, monkeypatch, verdict=None, custom=fake_clearance)
    assert rec.completed is not None
    assert len(SESSION_STORE._threads) == before  # nothing leaked


def test_fail_raising_never_escapes_the_handler(monkeypatch: Any) -> None:
    def boom(*a: Any, **k: Any) -> None:
        raise RuntimeError("db exploded")

    monkeypatch.setattr(workflow_step, "start_clearance", boom)

    def fail_raises(error: str) -> None:
        raise OSError("slack is down too")

    class FakeApp:
        def function(self, cid: str) -> Any:
            def deco(fn: Any) -> Any:
                self.fn = fn
                return fn

            return deco

    app = FakeApp()
    workflow_step.register_workflow_step(app)  # type: ignore[arg-type]
    # Must not raise even when the remedy itself raises.
    app.fn(
        ack=lambda: None, inputs={"fighter_name": "X"}, complete=lambda **k: None, fail=fail_raises
    )


def test_non_string_input_is_an_input_error_not_a_garbage_query(monkeypatch: Any) -> None:
    rec = _run_handler({"fighter_name": {"text": "JDS"}}, monkeypatch, verdict=_v("CLEAR"))
    assert rec.completed is None
    assert rec.failed is not None and "must be text" in rec.failed


def test_manifest_declares_the_step_and_runtime() -> None:
    import json
    from pathlib import Path

    m = json.loads((Path(__file__).parents[2] / "slack" / "manifest.json").read_text())
    fn = m["functions"]["check_fighter_clearance"]
    assert fn["input_parameters"]["fighter_name"]["is_required"] is True
    assert set(fn["output_parameters"]) == {"status", "detail", "fighter"}
    assert m["settings"]["function_runtime"] == "remote"
    assert "pins:write" in m["oauth_config"]["scopes"]["bot"]
