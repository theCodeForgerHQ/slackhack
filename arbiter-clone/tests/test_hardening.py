"""Security & robustness primitives: mention-injection escaping, event dedup,
and the Lists control-char guard. These are the guarantees that keep the bot
safe on hostile input."""
import importlib


def _app():
    # app.py imports heavy modules; only load once, tolerate slow import
    return importlib.import_module("app")


class TestEscaping:
    def test_broadcast_injection_escaped(self):
        app = _app()
        out = app._esc("<!channel> everyone")
        assert "<!channel>" not in out
        assert "&lt;!channel&gt;" in out

    def test_ampersand_escaped(self):
        app = _app()
        assert "&amp;" in app._esc("Tom & Jerry")

    def test_truncates_long_input(self):
        app = _app()
        out = app._esc("x" * 5000, 100)
        assert len(out) <= 101  # 100 + ellipsis

    def test_plain_text_unchanged(self):
        app = _app()
        assert app._esc("hello world") == "hello world"


class TestDedup:
    def test_same_event_id_is_duplicate(self):
        app = _app()
        body = {"event_id": "Ev123ABC"}
        assert app._is_duplicate(body) is False  # first time
        assert app._is_duplicate(body) is True   # redelivery

    def test_missing_event_id_never_duplicate(self):
        app = _app()
        assert app._is_duplicate({}) is False
        assert app._is_duplicate({}) is False


class TestListsGuard:
    def test_hard_fail_detects_missing_scope(self):
        import lists_sync
        assert lists_sync._hard_fail("missing_scope") is True
        assert lists_sync._hard_fail("paid_teams_only") is True

    def test_hard_fail_ignores_transient(self):
        import lists_sync
        assert lists_sync._hard_fail("ratelimited") is False

    def test_rich_text_truncates(self):
        import lists_sync
        block = lists_sync._rich("y" * 500)
        text = block[0]["elements"][0]["elements"][0]["text"]
        assert len(text) <= 250
