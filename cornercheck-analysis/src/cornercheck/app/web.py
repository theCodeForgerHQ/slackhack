"""Public dashboard + health HTTP server.

A Socket Mode Slack app has no inbound HTTP, but a Render web service must bind $PORT.
This stdlib server serves the LIVE public dashboard (real stats from the real DB, the
audit chain verified at load, and a run-the-Z3-proof-now endpoint), so the deployed URL
shows a living, self-verifying system. Real interaction happens in Slack.
"""

import contextlib
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

log = logging.getLogger("cornercheck.web")

_DASHBOARD = Path(__file__).parent / "static" / "dashboard.html"


_FALLBACK = (
    b"<!doctype html><meta charset='utf-8'><title>CornerCheck</title>"
    b"<body style='font-family:monospace;background:#0a0c10;color:#e8e4da;padding:48px'>"
    b"<h1>CornerCheck</h1><p>Fail-closed fighter-safety clearance. Live.</p>"
    b"<p><a style='color:#d4a843' href='/healthz'>healthz</a></p>"
)
_page_cache: bytes | None = None


def _dashboard_bytes() -> bytes:
    """The page is a committed static file. ONLY the success path is memoized: a
    transient read failure must serve the fallback once, not poison the cache with it
    for the process lifetime (caught in adversarial review)."""
    global _page_cache
    if _page_cache is not None:
        return _page_cache
    try:
        _page_cache = _DASHBOARD.read_bytes()
        return _page_cache
    except Exception as e:
        log.error("dashboard.html unreadable (%s: %s); serving fallback", type(e).__name__, e)
        return _FALLBACK


class _Handler(BaseHTTPRequestHandler):
    # The defaults advertise the exact Python version on every response; say nothing.
    server_version = "CornerCheck"
    sys_version = ""

    def _route(self) -> tuple[int, str, bytes, bool]:
        if self.path == "/healthz":
            return 200, "application/json", json.dumps({"status": "ok"}).encode(), False
        if self.path == "/api/stats":
            from cornercheck.app.dashboard import stats_payload

            return 200, "application/json", json.dumps(stats_payload()).encode(), True
        if self.path == "/api/proof":
            from cornercheck.app.dashboard import proof_payload

            return 200, "application/json", json.dumps(proof_payload()).encode(), True
        if self.path in ("/", ""):
            return 200, "text/html; charset=utf-8", _dashboard_bytes(), False
        return 404, "application/json", b'{"error": "not found"}', False

    def do_GET(self) -> None:
        try:
            code, ctype, body, nostore = self._route()
            self._send(code, ctype, body, nostore=nostore)
        except Exception:
            # A handler crash must never kill the worker thread or leak a stack trace.
            log.exception("dashboard request failed: %s", self.path)
            with contextlib.suppress(Exception):
                self._send(500, "application/json", b'{"error": "internal"}')

    def do_HEAD(self) -> None:
        """Uptime monitors commonly probe with HEAD; answer headers-only, never 501."""
        try:
            code, ctype, body, nostore = self._route()
            self._send(code, ctype, body, nostore=nostore, head_only=True)
        except Exception:
            log.exception("dashboard HEAD failed: %s", self.path)
            with contextlib.suppress(Exception):
                self._send(500, "application/json", b"", head_only=True)

    def _send(
        self,
        code: int,
        content_type: str,
        body: bytes,
        nostore: bool = False,
        head_only: bool = False,
    ) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if nostore else "max-age=60")
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def log_message(self, *args: Any) -> None:
        pass  # keep the worker logs clean


def start_health_server(port: int) -> None:
    server = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    threading.Thread(target=server.serve_forever, name="health-server", daemon=True).start()
    log.info("health/landing server bound on 0.0.0.0:%d", port)
