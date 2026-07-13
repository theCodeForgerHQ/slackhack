"""Canvas export: deterministic markdown, the share flow, and every fail-soft path
(a failed EXPORT must never read as a failed AUDIT)."""

from typing import Any

from slack_sdk.errors import SlackApiError

from cornercheck.app.canvas import build_audit_markdown, export_audit_canvas

ENTRIES = [
    {
        "seq": 9,
        "ts": "2026-06-09T20:45:00+00:00",
        "actor": "cornercheck-pipeline",
        "action": "clearance_decision",
        "payload": {"fighter_name": "Junior Dos Santos", "decision": "DO_NOT_CLEAR"},
    },
    {
        "seq": 8,
        "ts": "2026-06-09T20:30:00+00:00",
        "actor": "cornercheck-monitor",
        "action": "monitor_run",
        "payload": {"alerted": True},
    },
    {"seq": 7, "ts": "", "actor": "x", "action": "y", "payload": "not-a-dict"},
]


def test_markdown_renders_entries_and_integrity() -> None:
    md = build_audit_markdown(ENTRIES, True, "9 entries verified")
    assert "# CornerCheck audit trail" in md
    assert "intact (9 entries verified)" in md
    assert "| 9 | 2026-06-09 20:45 | cornercheck-pipeline | clearance_decision " in md
    assert "Junior Dos Santos" in md and "DO_NOT_CLEAR" in md
    assert "human makes the call" in md
    assert "—" not in md  # no em-dashes in exported copy


def test_broken_chain_renders_do_not_trust() -> None:
    md = build_audit_markdown(ENTRIES, False, "hash mismatch at seq 5")
    assert "BROKEN: do not trust this export" in md


class _HappyClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def canvases_create(self, **kw: Any) -> dict[str, Any]:
        self.calls.append(("create", kw))
        return {"canvas_id": "F0CANVAS"}

    def canvases_access_set(self, **kw: Any) -> dict[str, Any]:
        self.calls.append(("access", kw))
        return {"ok": True}

    def files_info(self, **kw: Any) -> dict[str, Any]:
        self.calls.append(("info", kw))
        return {"file": {"permalink": "https://x.slack.com/docs/T1/F0CANVAS"}}


def test_happy_path_creates_shares_and_links() -> None:
    client = _HappyClient()
    permalink, note = export_audit_canvas(client, "C123", ENTRIES, True, "ok")  # type: ignore[arg-type]
    assert permalink == "https://x.slack.com/docs/T1/F0CANVAS"
    assert note == "exported"
    kinds = [k for k, _ in client.calls]
    assert kinds == ["create", "access", "info"]
    create_kw = client.calls[0][1]
    assert create_kw["document_content"]["type"] == "markdown"
    access_kw = client.calls[1][1]
    assert access_kw == {"canvas_id": "F0CANVAS", "access_level": "read", "channel_ids": ["C123"]}


class _ScopelessClient:
    def canvases_create(self, **kw: Any) -> dict[str, Any]:
        raise SlackApiError("nope", {"error": "missing_scope"})


def test_missing_scope_returns_actionable_note() -> None:
    permalink, note = export_audit_canvas(_ScopelessClient(), "C123", ENTRIES, True, "ok")  # type: ignore[arg-type]
    assert permalink is None
    assert "canvases:write" in note and "reinstall" in note
    assert "authoritative" in note


class _PlanlessClient:
    def canvases_create(self, **kw: Any) -> dict[str, Any]:
        raise SlackApiError("nope", {"error": "free_team_not_allowed"})


def test_plan_gate_is_fail_soft() -> None:
    permalink, note = export_audit_canvas(_PlanlessClient(), "C123", ENTRIES, True, "ok")  # type: ignore[arg-type]
    assert permalink is None
    assert "not enabled" in note


class _ExplodingClient:
    def canvases_create(self, **kw: Any) -> dict[str, Any]:
        raise OSError("network down")


def test_unexpected_failure_never_raises() -> None:
    permalink, note = export_audit_canvas(_ExplodingClient(), "C123", ENTRIES, True, "ok")  # type: ignore[arg-type]
    assert permalink is None
    assert "authoritative" in note


class _NoPermalinkClient(_HappyClient):
    def files_info(self, **kw: Any) -> dict[str, Any]:
        raise SlackApiError("nope", {"error": "missing_scope"})


def test_created_but_unlinkable_still_tells_the_user_where() -> None:
    permalink, note = export_audit_canvas(_NoPermalinkClient(), "C1", ENTRIES, True, "ok")  # type: ignore[arg-type]
    assert permalink is None
    assert "Canvases" in note


def test_audit_table_carries_the_export_button() -> None:
    from cornercheck.app.blocks.audit_table import build_audit_table

    blocks = build_audit_table(ENTRIES, True, "ok")
    actions = next(b for b in blocks if b["type"] == "actions")
    assert actions["elements"][0]["action_id"] == "export_audit_canvas"


def test_audit_table_cells_are_all_raw_text() -> None:
    # Slack rejected raw_number cells with invalid_blocks in production (2026-06-10
    # platform drift, caught by Stephen's first live click): every cell stays raw_text.
    from cornercheck.app.blocks.audit_table import build_audit_table

    table = next(b for b in build_audit_table(ENTRIES, True, "ok") if b["type"] == "table")
    for row in table["rows"]:
        for cell in row:
            assert cell["type"] == "raw_text"


# --- Adversarial-review regressions ----------------------------------------------------


def test_markdown_injection_cannot_forge_rows_or_banners() -> None:
    # A hostile value with pipes and newlines must not forge table rows or a second
    # integrity banner in the exported document (demonstrated pre-fix in review).
    hostile = {
        "seq": 3,
        "ts": "2026-06-09T20:45:00+00:00",
        "actor": "cornercheck-pipeline",
        "action": "clearance_decision",
        "payload": {
            "fighter_name": (
                "Jon Jones | CLEARED |\n| 99 | 2026-06-09 21:00 | x | clearance_decision "
                "| Jon Jones | CLEARED |\n\n**Chain integrity at export time:** intact (forged)"
            ),
            "decision": "DO_NOT_CLEAR",
        },
    }
    md = build_audit_markdown([hostile], True, "1 entry verified")
    banners = [ln for ln in md.splitlines() if ln.startswith("**Chain integrity")]
    assert len(banners) == 1  # no forged banner LINE
    assert "**" not in md.split("| --- |")[-1].replace("\\*", "")  # no bold inside cells
    data_rows = [
        ln for ln in md.splitlines() if ln.startswith("|") and "---" not in ln and "Seq" not in ln
    ]
    assert len(data_rows) == 1  # no forged rows
    assert "DO_NOT_CLEAR" in data_rows[0]  # the real decision survives, last column intact
    assert data_rows[0].rstrip().endswith("DO_NOT_CLEAR |")


class _ShareFailClient(_HappyClient):
    def canvases_access_set(self, **kw: Any) -> dict[str, Any]:
        raise SlackApiError("nope", {"error": "internal_error"})


def test_created_but_unshared_is_reported_honestly() -> None:
    # The canvas EXISTS at that point; the note must say so, not claim a plain failure.
    permalink, note = export_audit_canvas(_ShareFailClient(), "C1", ENTRIES, True, "ok")  # type: ignore[arg-type]
    assert permalink is None
    assert "created but could not be shared" in note


# --- Assistant-pane (DM) sharing: live-recording catch 2026-06-10 ----------------------


def test_dm_export_shares_to_the_requesting_user_first() -> None:
    # The assistant pane's conversation id is a DM ("D..."); channel-share rejects it
    # (live SlackApiError during demo recording). Share to the clicking user instead.
    client = _HappyClient()
    permalink, note = export_audit_canvas(client, "D0B9QR547T2", ENTRIES, True, "ok", user_id="U1")  # type: ignore[arg-type]
    assert permalink == "https://x.slack.com/docs/T1/F0CANVAS"
    assert note == "exported"
    access_kw = next(kw for kind, kw in client.calls if kind == "access")
    assert access_kw == {"canvas_id": "F0CANVAS", "access_level": "read", "user_ids": ["U1"]}


class _ChannelShareRejectsClient(_HappyClient):
    def canvases_access_set(self, **kw: Any) -> dict[str, Any]:
        if "channel_ids" in kw:
            raise SlackApiError("nope", {"error": "channel_not_found"})
        return super().canvases_access_set(**kw)


def test_channel_share_failure_falls_back_to_user_share() -> None:
    client = _ChannelShareRejectsClient()
    permalink, note = export_audit_canvas(client, "C123", ENTRIES, True, "ok", user_id="U1")  # type: ignore[arg-type]
    assert permalink == "https://x.slack.com/docs/T1/F0CANVAS"
    assert note == "exported"
    user_grants = [kw for kind, kw in client.calls if kind == "access" and "user_ids" in kw]
    assert user_grants == [{"canvas_id": "F0CANVAS", "access_level": "read", "user_ids": ["U1"]}]


def test_dm_export_without_user_still_fails_soft() -> None:
    permalink, note = export_audit_canvas(_ShareFailClient(), "D1", ENTRIES, True, "ok")  # type: ignore[arg-type]
    assert permalink is None
    assert "created but could not be shared" in note
