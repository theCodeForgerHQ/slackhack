"""Spike B: Real-Time Search (assistant.search.context) keyword mode.

Verifies (Stage 1 gate):
1. where the action_token lives (recursive hunt over the full event envelope)
2. assistant.search.context (keyword mode) returns a freshly posted real message
3. assistant.search.info reports search capability (run 1 found: is_ai_search_enabled=true)

Doc (docs.slack.dev RTS page, fetched live 2026-06-07): app_mention carries
event.action_token; message.* events carry it too; bot tokens REQUIRE action_token;
search:read.public minimum scope. slack_sdk 3.42.0 has no wrapper: raw api_call().

Run:  uv run python scripts/spikes/spike_b_rts.py
Then: 1) add @CornerCheck to #general (Slack's "Add Them" button or /invite)
      2) message the CornerCheck agent pane, AND @CornerCheck ping in #general
"""

import json
import logging
import time

from slack_bolt import App, Assistant, Say, SetStatus
from slack_sdk import WebClient

from cornercheck.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("spike_b")

SEED_TEXT = (
    "Heads up: Dragan got rocked in sparring on Tuesday, we sat him down for the week. "
    "(spike B seed message)"
)
SEED_CHANNEL = "#general"

settings = get_settings()
app = App(token=settings.slack_bot_token)
assistant = Assistant()


def _redact(token: str) -> str:
    return f"{token[:12]}... ({len(token)} chars)"


def find_action_tokens(node: object, path: str = "body") -> dict[str, str]:
    """Recursively locate every key containing 'action_token' anywhere in the envelope."""
    found: dict[str, str] = {}
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}.{k}"
            if "action_token" in str(k) and isinstance(v, str):
                found[p] = v
            found.update(find_action_tokens(v, p))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            found.update(find_action_tokens(v, f"{path}[{i}]"))
    return found


def post_seed(client: WebClient) -> str:
    try:
        resp = client.chat_postMessage(channel=SEED_CHANNEL, text=SEED_TEXT)
        log.info("SPIKE-B seed posted to %s ts=%s", SEED_CHANNEL, resp["ts"])
        return "seed posted"
    except Exception as exc:
        log.warning("SPIKE-B seed post FAILED: %s", exc)
        return f"seed post failed: {exc}"


def run_rts_test(body: dict, client: WebClient, say, source: str) -> None:
    t0 = time.monotonic()

    tokens = find_action_tokens(body)
    log.info(
        "SPIKE-B [%s] action_token paths: %s",
        source,
        {k: _redact(v) for k, v in tokens.items()} or "NOT FOUND",
    )
    event = body.get("event", {})
    if "assistant_thread" in event:
        log.info(
            "SPIKE-B [%s] assistant_thread keys: %s",
            source,
            sorted(event["assistant_thread"].keys()),
        )
    action_token = next(iter(tokens.values()), None)

    seed_status = post_seed(client)

    try:
        info = client.api_call("assistant.search.info", json={})
        info_summary = json.dumps(info.data)
        log.info("SPIKE-B [%s] search.info: %s", source, info_summary)
    except Exception as exc:
        info_summary = f"search.info failed: {exc}"
        log.warning("SPIKE-B [%s] %s", source, info_summary)

    try:
        req: dict = {"query": "rocked sparring", "limit": 5, "content_types": ["messages"]}
        if action_token:
            req["action_token"] = action_token
        result = client.api_call("assistant.search.context", json=req)
        messages = (result.data.get("results") or {}).get("messages", [])
        log.info(
            "SPIKE-B [%s] search.context ok=%s hits=%d",
            source,
            result.data.get("ok"),
            len(messages),
        )
        for m in messages[:3]:
            log.info("SPIKE-B [%s] hit: %s", source, json.dumps(m)[:200])
        search_summary = f"{len(messages)} hit(s) for 'rocked sparring'"
        if messages:
            search_summary += f"; first: {json.dumps(messages[0])[:120]}"
    except Exception as exc:
        search_summary = f"search.context failed: {exc}"
        log.warning("SPIKE-B [%s] %s", source, search_summary)

    say(
        f"Spike B [{source}] results:\n"
        f"- action_token paths: {', '.join(tokens) if tokens else 'NOT FOUND'}\n"
        f"- seed: {seed_status}\n"
        f"- search.info: {info_summary[:200]}\n"
        f"- search.context: {search_summary[:400]}\n"
        f"- total {time.monotonic() - t0:.2f}s"
    )
    log.info("SPIKE-B [%s] handler done in %.2fs", source, time.monotonic() - t0)


@assistant.thread_started
def on_thread_started(say: Say) -> None:
    say("Spike B v2 online. Add me to #general, then message me here AND @mention me there.")


@assistant.user_message
def on_user_message(body: dict, client: WebClient, say: Say, set_status: SetStatus) -> None:
    set_status("running RTS spike...")
    run_rts_test(body, client, say, source="assistant user_message")


@app.event("app_mention")
def on_app_mention(body: dict, client: WebClient, say) -> None:
    run_rts_test(body, client, say, source="app_mention")


app.use(assistant)


if __name__ == "__main__":
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    log.info("SPIKE-B v2 starting Socket Mode connection...")
    SocketModeHandler(app, settings.slack_app_token).start()
