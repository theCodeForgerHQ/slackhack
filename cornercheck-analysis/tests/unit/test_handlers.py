"""Handler-level coverage for the Slack glue layer: the only code a judge's clicks
execute that CI previously never executed (suite-audit top gap). Recorder pattern;
every dependency below the glue is monkeypatched, so these pin the COMPOSITION."""

from datetime import date
from typing import Any

from cornercheck.brain.schemas import ClearanceVerdict

ON = date(2026, 6, 10)


def _v(status: str, **kw: Any) -> ClearanceVerdict:
    return ClearanceVerdict(status=status, query="X", on_date=ON, **kw)


def _valid_blocks(blocks: list[dict]) -> None:
    """Local copy of the structural validator (tests/ is not an importable package)."""
    assert isinstance(blocks, list) and blocks
    assert len(blocks) <= 50  # Slack message block cap
    for b in blocks:
        assert "type" in b
        if b["type"] == "header":
            assert len(b["text"]["text"]) <= 150
        if b["type"] == "section" and "fields" in b:
            assert len(b["fields"]) <= 10


class _Say:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, text: str | None = None, **kw: Any) -> None:
        self.calls.append({"text": text, **kw})


_BODY = {"event": {"assistant_thread": {"action_token": None}}}


def _run_clearance(monkeypatch: Any, verdict: Any = None, boom: bool = False) -> _Say:
    from cornercheck.app import assistant as mod

    if boom:

        def _raise(*a: Any, **k: Any) -> None:
            raise RuntimeError("db down")

        monkeypatch.setattr(mod, "start_clearance", _raise)
    else:
        monkeypatch.setattr(mod, "start_clearance", lambda *a, **k: verdict)
    say = _Say()
    mod._handle_clearance(
        "t#h",
        "Is Curtis Blaydes cleared in Texas?",
        _BODY,
        say,  # type: ignore[arg-type]
        lambda s: None,  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
    )
    return say


def test_clearance_handler_posts_a_verdict_card(monkeypatch: Any) -> None:
    say = _run_clearance(monkeypatch, _v("CLEAR", fighter_name="Curtis Blaydes"))
    final = say.calls[-1]
    assert final.get("blocks") and "Curtis Blaydes" in str(final["blocks"])


def test_clearance_handler_posts_the_picker_on_ambiguity(monkeypatch: Any) -> None:
    from cornercheck.brain.schemas import CandidateOut

    cands = [
        CandidateOut(
            fighter_id=f"00000000-0000-0000-0000-00000000000{i}",
            full_name="Bruno Silva",
            weight_class="MW",
            record="23-9-0",
            sport="mma",
            jurisdiction=None,
            score=0.99,
        )
        for i in (1, 2)
    ]
    say = _run_clearance(monkeypatch, _v("NEEDS_DISAMBIGUATION", candidates=cands))
    final = say.calls[-1]
    assert "won't guess" in str(final.get("text"))
    assert any("select_fighter" in str(b) for b in final["blocks"])


def test_clearance_handler_fails_closed_on_crash(monkeypatch: Any) -> None:
    say = _run_clearance(monkeypatch, boom=True)
    assert "NOT cleared" in str(say.calls[-1]["text"])


def test_card_handler_posts_the_board(monkeypatch: Any) -> None:
    from cornercheck.app import assistant as mod

    verdicts = [_v("CLEAR", fighter_name="A"), _v("DO_NOT_CLEAR", fighter_name="B")]
    monkeypatch.setattr(mod, "clear_card", lambda *a, **k: verdicts)
    say = _Say()
    mod._handle_card(
        "t#c",
        "Check this card in Texas: Alpha Beta vs Gamma Delta, Epsilon Zeta vs Eta Theta",
        say,  # type: ignore[arg-type]
        lambda s: None,  # type: ignore[arg-type]
    )
    final = say.calls[-1]
    assert any(b.get("type") == "table" for b in final["blocks"])


def test_freeform_timeout_gets_the_friendly_fallback(monkeypatch: Any) -> None:
    from cornercheck.app import assistant as mod
    from cornercheck.brain.agent import BrainTimeoutError

    class _Brain:
        def ask(self, *a: Any, **k: Any) -> str:
            raise BrainTimeoutError("slow")

    monkeypatch.setattr(mod, "get_brain", lambda: _Brain())
    say = _Say()
    mod._handle_freeform(
        "t#f",
        "tell me a story",
        _BODY,
        say,  # type: ignore[arg-type]
        lambda s: None,  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
    )
    assert "took too long" in str(say.calls[-1]["text"])


# --- Block Kit action handlers ----------------------------------------------------------


class _Client:
    def __init__(self) -> None:
        self.posts: list[dict[str, Any]] = []

    def chat_postMessage(self, **kw: Any) -> None:
        self.posts.append(kw)


def _action_body(value: str) -> dict[str, Any]:
    return {
        "actions": [{"value": value}],
        "container": {"channel_id": "C9", "thread_ts": "111.222"},
    }


def _register(monkeypatch: Any) -> dict[str, Any]:
    from cornercheck.app import actions as mod

    handlers: dict[str, Any] = {}

    class FakeApp:
        def action(self, action_id: str) -> Any:
            def deco(fn: Any) -> Any:
                handlers[action_id] = fn
                return fn

            return deco

    mod.register_actions(FakeApp())  # type: ignore[arg-type]
    return handlers


def test_select_fighter_replies_in_the_thread(monkeypatch: Any) -> None:
    from cornercheck.app import actions as mod
    from cornercheck.app.blocks.disambiguation_card import _encode

    monkeypatch.setattr(
        mod, "confirm_candidate", lambda *a, **k: _v("CLEAR", fighter_name="Bruno Silva")
    )
    handlers = _register(monkeypatch)
    client = _Client()
    value = _encode("00000000-0000-0000-0000-000000000001", "Bruno Silva", "2026-06-10")
    handlers["select_fighter"](ack=lambda: None, body=_action_body(value), client=client)
    assert client.posts and client.posts[0]["thread_ts"] == "111.222"
    assert "Bruno Silva" in str(client.posts[0]["blocks"])


def test_select_fighter_fails_closed_when_confirm_crashes(monkeypatch: Any) -> None:
    from cornercheck.app import actions as mod

    def _raise(*a: Any, **k: Any) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(mod, "confirm_candidate", _raise)
    handlers = _register(monkeypatch)
    client = _Client()
    handlers["select_fighter"](ack=lambda: None, body=_action_body("x|y|z"), client=client)
    assert "NOT cleared" in str(client.posts[0]["text"])


def test_export_canvas_failure_keeps_the_table_authoritative(monkeypatch: Any) -> None:
    from cornercheck.app import actions as mod

    def _raise() -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(mod, "verify_chain", _raise)
    handlers = _register(monkeypatch)
    client = _Client()
    handlers["export_audit_canvas"](ack=lambda: None, body=_action_body("x"), client=client)
    assert "authoritative" in str(client.posts[0]["text"])


# --- App Home views render valid blocks -------------------------------------------------


def test_home_view_blocks_are_valid_including_denials(monkeypatch: Any) -> None:
    from cornercheck.app import home as mod
    from cornercheck.ledger.chain import VerifyResult

    monkeypatch.setattr(mod, "verify_chain", lambda: VerifyResult(True, 5, None, "ok"))
    monkeypatch.setattr(mod, "_coverage_text", lambda: "stats")
    entries = [
        {
            "seq": 5,
            "ts": "2026-06-10T00:00:00+00:00",
            "action": "clearance_decision",
            "payload": {"fighter_name": "A", "decision": "CLEAR"},
        },
        {
            "seq": 4,
            "ts": "2026-06-10T00:00:00+00:00",
            "action": "clearance_write_denied",
            "payload": {"fighter_name": "B", "attempted_decision": "CLEAR"},
        },
    ]
    monkeypatch.setattr(mod, "_recent_decisions", lambda: entries)
    view = mod._home_view()
    _valid_blocks(view["blocks"])
    text = str(view["blocks"])
    # The denied CLEAR must not wear green; it renders as an explicit denial.
    assert "DENIED write attempt" in text and ":no_entry:" in text


def test_home_fallback_view_is_valid_and_honest() -> None:
    from cornercheck.app.home import _fallback_view

    view = _fallback_view()
    _valid_blocks(view["blocks"])
    assert "NOT cleared" in str(view["blocks"])


def test_assistant_pane_mention_is_stripped_before_parsing() -> None:
    """Caught live: '@CornerCheck is Jon Jones cleared in California?' typed in the
    assistant pane sent the raw user-id token into the fighter query (NO MATCH)."""
    from cornercheck.app.assistant import _is_clearance_request
    from cornercheck.app.context import strip_mentions
    from cornercheck.app.parse import parse_request

    raw = "<@U0B8F1V1KSB> is Jon Jones cleared in California?"
    text = strip_mentions(raw)
    assert _is_clearance_request(text)
    parsed = parse_request(text)
    assert parsed.fighter_query == "Jon Jones"
    assert parsed.target_jurisdiction == "California"
