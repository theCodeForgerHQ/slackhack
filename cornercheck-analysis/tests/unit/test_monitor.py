"""Monitor digest formatting and the fail-quiet webhook push (no DB, no network)."""

import json
from datetime import date
from typing import Any

import pytest

from cornercheck import monitor
from cornercheck.monitor import Findings, format_alert, post_ops_alert

TODAY = date(2026, 6, 9)


def test_quiet_day_produces_no_message() -> None:
    assert format_alert(Findings(), TODAY) is None


def test_every_finding_type_renders() -> None:
    f = Findings(
        lapsing=[
            {
                "fighter": "A Lapsing",
                "type": "medical",
                "jurisdiction": "CSAC",
                "end_date": "2026-06-20",
            }
        ],
        lapsed=[
            {"fighter": "B Lapsed", "type": "KO", "jurisdiction": "TDLR", "end_date": "2026-06-06"}
        ],
        new_suspensions=[
            {
                "fighter": "C New",
                "type": "administrative",
                "jurisdiction": "NSAC",
                "end_date": None,
                "indefinite": True,
            }
        ],
        blocked_decisions=[{"fighter": "D Blocked", "rules": ["active_suspension"]}],
        disagreements=[{"fighter": "E Disagreed", "note": "live source shows 27 bouts vs 25"}],
        indefinite_on_file=2,
    )
    text = format_alert(f, TODAY)
    assert text is not None
    assert "lapsing in 11d" in text and "A Lapsing" in text
    assert "lapsed 3d ago" in text and "Do not assume cleared" in text
    assert "New suspension on file" in text and "INDEFINITE" in text
    assert "1 DO NOT CLEAR verdict(s)" in text and "D Blocked" in text
    assert "Live-record disagreement" in text and "E Disagreed" in text
    assert "2 indefinite (until cleared)" in text
    assert "human makes the call" in text
    assert "—" not in text  # no em-dashes in ops copy


def test_indefinite_count_alone_keeps_the_day_quiet() -> None:
    # Informational only: a standing count must never trigger a digest by itself.
    assert format_alert(Findings(indefinite_on_file=5), TODAY) is None


def test_webhook_unset_is_quietly_false(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSettings:
        ops_webhook_url = ""

    monkeypatch.setattr(monitor, "get_settings", lambda: FakeSettings())
    assert post_ops_alert("anything") is False


def test_webhook_posts_json_text(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSettings:
        ops_webhook_url = "https://hooks.slack.example/services/T000/B000/x"

    sent: dict[str, Any] = {}

    class FakeResp:
        status = 200

        def __enter__(self) -> "FakeResp":
            return self

        def __exit__(self, *a: object) -> None:
            return None

    def fake_urlopen(req: Any, timeout: float) -> FakeResp:
        sent["url"] = req.full_url
        sent["body"] = json.loads(req.data)
        return FakeResp()

    monkeypatch.setattr(monitor, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(monitor.urllib.request, "urlopen", fake_urlopen)
    assert post_ops_alert("digest text") is True
    assert sent["body"] == {"text": "digest text"}


def test_webhook_failure_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSettings:
        ops_webhook_url = "https://hooks.slack.example/services/T000/B000/x"

    def boom(req: Any, timeout: float) -> None:
        raise OSError("network down")

    monkeypatch.setattr(monitor, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(monitor.urllib.request, "urlopen", boom)
    assert post_ops_alert("digest text") is False
