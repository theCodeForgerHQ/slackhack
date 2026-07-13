"""Spike A: Bolt Assistant middleware over Socket Mode.

Verifies (Stage 1 gate):
1. assistant_thread_started fires when a user opens the CornerCheck agent pane
2. handler path is fast (Bolt auto-acks socket envelopes; we log handler latency)
3. follow-up messages land in the assistant thread (say, set_status, suggested prompts)

Run:  uv run python scripts/spikes/spike_a_assistant.py
Then: in the CornerCheck sandbox, open the CornerCheck agent and send any message.
"""

import logging
import time

from slack_bolt import App, Assistant, Say, SetStatus, SetSuggestedPrompts, SetTitle

from cornercheck.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("spike_a")

settings = get_settings()
app = App(token=settings.slack_bot_token)
assistant = Assistant()


@assistant.thread_started
def on_thread_started(say: Say, set_suggested_prompts: SetSuggestedPrompts) -> None:
    t0 = time.monotonic()
    say("CornerCheck spike A online. Send me any message.")
    set_suggested_prompts(prompts=[{"title": "Ping the spike", "message": "ping"}])
    log.info("SPIKE-A thread_started handled in %.3fs", time.monotonic() - t0)


@assistant.user_message
def on_user_message(payload: dict, say: Say, set_status: SetStatus, set_title: SetTitle) -> None:
    t0 = time.monotonic()
    set_status("checking the spike...")
    text = payload.get("text", "")
    say(f"Echo from spike A: {text!r}. Handler latency so far {time.monotonic() - t0:.3f}s.")
    set_title("Spike A verified")
    log.info("SPIKE-A user_message %r handled in %.3fs", text, time.monotonic() - t0)


app.use(assistant)


if __name__ == "__main__":
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    log.info("SPIKE-A starting Socket Mode connection...")
    SocketModeHandler(app, settings.slack_app_token).start()
