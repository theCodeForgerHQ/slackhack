"""Slack MCP server client — persistent session to avoid re-handshaking on every call."""
import os
import json
import httpx

_URL = "https://mcp.slack.com/mcp"
_client: httpx.Client | None = None
_sid:    str | None           = None


def _headers(sid: str | None = None) -> dict:
    h = {
        "Authorization": f"Bearer {os.environ['SLACK_USER_TOKEN']}",
        "Content-Type":  "application/json",
        "Accept":        "application/json, text/event-stream",
    }
    if sid:
        h["Mcp-Session-Id"] = sid
    return h


def _parse(r: httpx.Response):
    if "text/event-stream" in r.headers.get("content-type", ""):
        for line in r.text.splitlines():
            if line.startswith("data:"):
                try:
                    return json.loads(line[5:].strip())
                except Exception:
                    pass
        return None
    try:
        return r.json()
    except Exception:
        return None


def _get_session() -> tuple[httpx.Client, str | None]:
    """Return (client, session_id), initialising once and reusing thereafter."""
    global _client, _sid
    if _client is None:
        _client = httpx.Client(timeout=20)
    if _sid:
        return _client, _sid
    try:
        r = _client.post(_URL, headers=_headers(), json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "verdict", "version": "1.0"}}})
        sid = r.headers.get("mcp-session-id")
        if sid:
            _client.post(_URL, headers=_headers(sid),
                         json={"jsonrpc": "2.0", "method": "notifications/initialized"})
            _sid = sid
    except Exception:
        pass
    return _client, _sid


def call_tool(name: str, arguments: dict, timeout: float = 20) -> tuple[bool, object]:
    """Call a Slack MCP tool. Reuses the persistent session; resets on error."""
    global _sid
    try:
        c, sid = _get_session()
        d = _parse(c.post(_URL, headers=_headers(sid), json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": name, "arguments": arguments}})) or {}
        if "error" in d:
            _sid = None  # stale session — force re-init next call
            return False, d["error"]
        return True, d.get("result")
    except Exception as e:
        _sid = None
        return False, str(e)


def add_reaction(channel_id: str, message_ts: str, emoji: str) -> tuple[bool, object]:
    return call_tool("slack_add_reaction",
                     {"channel_id": channel_id, "message_ts": message_ts, "emoji": emoji})


def send_message(channel_id: str, message: str, thread_ts: str | None = None) -> tuple[bool, object]:
    args = {"channel_id": channel_id, "message": message}
    if thread_ts:
        args["thread_ts"] = thread_ts
    return call_tool("slack_send_message", args)


def create_canvas(title: str, content: str) -> tuple[bool, object]:
    return call_tool("slack_create_canvas", {"title": title, "content": content})
