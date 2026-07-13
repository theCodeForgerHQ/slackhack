"""Whole-repo audit PR-B regressions: injury-scan tri-state, mention handler,
card-board buttons, ledger _meta coverage, fallback model, monitor anchor."""

from datetime import date
from typing import Any

from cornercheck.search.rts import injury_scan

ON = date(2026, 6, 10)


class _FakeResp:
    def __init__(self, data: Any) -> None:
        self.data = data


class _Client:
    def __init__(self, data: Any = None, raises: bool = False) -> None:
        self._data = data
        self._raises = raises

    def api_call(self, *a: Any, **k: Any) -> _FakeResp:
        if self._raises:
            raise OSError("rts down")
        return _FakeResp(self._data)

    def chat_getPermalink(self, **k: Any) -> dict[str, Any]:
        return {"permalink": "https://x.slack.com/p1"}


_GOOD = {
    "results": {
        "messages": [
            {
                "content": "JDS got rocked in sparring, bad knee",
                "channel_id": "C1",
                "message_ts": "1.0",
                "author_name": "coach",
            },
            {"content": "weather is nice", "channel_id": "C1", "message_ts": "2.0"},
            "not-a-dict",
        ]
    }
}


def test_scan_parses_recorded_shape_and_filters() -> None:
    r = injury_scan(_Client(_GOOD), "tok", "Junior dos Santos")  # type: ignore[arg-type]
    assert r.ok is True
    assert len(r.hits) == 1 and "rocked" in r.hits[0].snippet


def test_scan_shape_drift_is_marked_unavailable_not_empty() -> None:
    r = injury_scan(_Client({"matches": []}), "tok", "X")  # type: ignore[arg-type]
    assert r.ok is False and r.hits == []


def test_scan_api_failure_is_marked_unavailable() -> None:
    r = injury_scan(_Client(raises=True), "tok", "X")  # type: ignore[arg-type]
    assert r.ok is False


def test_scan_without_token_is_not_a_failure() -> None:
    r = injury_scan(_Client(_GOOD), None, "X")  # type: ignore[arg-type]
    assert r.ok is True and r.hits == []


def test_failed_scan_renders_unavailable_line_on_the_card() -> None:
    from cornercheck.app.blocks.verdict_card import build_verdict_card
    from cornercheck.brain.schemas import ClearanceVerdict

    v = ClearanceVerdict(status="CLEAR", query="X", fighter_name="X", on_date=ON)
    with_note = build_verdict_card(v, injury_scan_ok=False)
    without = build_verdict_card(v, injury_scan_ok=True)
    assert any("injury scan unavailable" in str(b) for b in with_note)
    assert not any("injury scan unavailable" in str(b) for b in without)


def test_card_board_carries_audit_and_proof_buttons() -> None:
    from cornercheck.app.blocks.card_board import build_card_board
    from cornercheck.brain.schemas import ClearanceVerdict

    v = ClearanceVerdict(status="CLEAR", query="X", fighter_name="X", on_date=ON)
    blocks = build_card_board([v])
    actions = next(b for b in blocks if b["type"] == "actions")
    ids = {e["action_id"] for e in actions["elements"]}
    assert ids == {"view_audit_trail", "view_safety_proof"}


def test_fallback_model_is_wired_into_options(monkeypatch: Any) -> None:
    from cornercheck import config
    from cornercheck.brain.agent import build_options

    monkeypatch.setenv("CORNERCHECK_MODEL_FALLBACK", "claude-haiku-4-5-20251001")
    config.get_settings.cache_clear()
    try:
        opts = build_options()
        assert opts.fallback_model == "claude-haiku-4-5-20251001"
    finally:
        config.get_settings.cache_clear()


def test_monitor_anchor_line_rides_the_digest() -> None:
    from cornercheck.monitor import Findings, format_alert

    f = Findings(
        lapsed=[{"fighter": "X", "type": "KO", "jurisdiction": "J", "end_date": "2026-06-05"}]
    )
    text = format_alert(f, ON, anchor="seq 13, head abcdef1234567890")
    assert text is not None and "Ledger anchor: seq 13, head abcdef1234567890" in text
    quiet = format_alert(Findings(), ON, anchor="seq 13, head x")
    assert quiet is None  # the anchor must never wake a quiet day


class _Recorder:
    def __init__(self) -> None:
        self.said: list[dict[str, Any]] = []

    def __call__(self, text: str | None = None, **kw: Any) -> None:
        self.said.append({"text": text, **kw})


def _mention_event(text: str) -> dict[str, Any]:
    return {"text": text, "ts": "111.222", "channel": "C9"}


def _run_mention(text: str, monkeypatch: Any, verdict: Any = None, boom: bool = False) -> _Recorder:
    from cornercheck.app import mentions

    if boom:

        def _raise(*a: Any, **k: Any) -> None:
            raise RuntimeError("db down")

        monkeypatch.setattr(mentions, "start_clearance", _raise)
    elif verdict is not None:
        monkeypatch.setattr(mentions, "start_clearance", lambda *a, **k: verdict)

    class FakeApp:
        def event(self, name: str) -> Any:
            assert name == "app_mention"

            def deco(fn: Any) -> Any:
                self.fn = fn
                return fn

            return deco

    app = FakeApp()
    mentions.register_mentions(app)  # type: ignore[arg-type]
    rec = _Recorder()
    app.fn(event=_mention_event(text), say=rec)
    return rec


def test_mention_clearance_renders_a_verdict_card_in_thread(monkeypatch: Any) -> None:
    from cornercheck.brain.schemas import ClearanceVerdict

    v = ClearanceVerdict(status="CLEAR", query="X", fighter_name="Curtis Blaydes", on_date=ON)
    rec = _run_mention("<@U1> is Curtis Blaydes cleared in Texas?", monkeypatch, verdict=v)
    assert rec.said and rec.said[0].get("blocks")
    assert rec.said[0]["thread_ts"] == "111.222"


def test_mention_smalltalk_gets_the_pointer(monkeypatch: Any) -> None:
    rec = _run_mention("<@U1> hello there!", monkeypatch)
    assert rec.said and "Assistant pane" in rec.said[0]["text"]


def test_mention_failure_is_fail_closed(monkeypatch: Any) -> None:
    rec = _run_mention("<@U1> is Curtis Blaydes cleared in Texas?", monkeypatch, boom=True)
    assert rec.said and "NOT cleared" in rec.said[0]["text"]
