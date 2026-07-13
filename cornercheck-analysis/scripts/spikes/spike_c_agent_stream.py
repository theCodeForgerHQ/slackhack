"""Spike C: Claude Agent SDK message stream -> Slack chat streaming (say_stream).

Verifies (Stage 1 gate):
1. claude-agent-sdk runs headless with our API key + pinned model (drives local Claude Code CLI)
2. an SDK-MCP tool (in-process FastMCP-style) gets called by the agent
3. the SDK message stream maps onto Slack's say_stream/ChatStream (append/stop)
4. ToolUseBlock events surface as visible "thinking" lines (Stage 5 thinking-steps pattern)

Introspection facts (installed packages = truth):
- slack_bolt injects context["say_stream"]; SayStream() returns ChatStream with
  append(markdown_text=...) and stop(markdown_text=..., blocks=...)
- claude_agent_sdk exports query, ClaudeAgentOptions, tool, create_sdk_mcp_server,
  AssistantMessage/TextBlock/ToolUseBlock/ResultMessage

Run:  uv run python scripts/spikes/spike_c_agent_stream.py
Then: message the CornerCheck agent pane, e.g. "Is Dragan cleared?"
"""

import asyncio
import json
import logging
import os
import time
from collections import Counter
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)
from slack_bolt import App, Assistant, Say, SayStream, SetStatus

from cornercheck.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("spike_c")

settings = get_settings()
os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)

app = App(token=settings.slack_bot_token)
assistant = Assistant()


@tool(
    "lookup_fighter",
    "Look up a fighter's record and medical suspension status",
    {"name": str},
)
async def lookup_fighter(args: dict[str, Any]) -> dict[str, Any]:
    log.info("SPIKE-C tool lookup_fighter called with %s", args)
    data = {
        "name": args.get("name", "unknown"),
        "record": "24-1-0",
        "last_bout": "2026-04-26, KO loss, Nevada",
        "suspension": "60-day medical suspension (KO), expires 2026-06-25",
    }
    return {"content": [{"type": "text", "text": json.dumps(data)}]}


spike_server = create_sdk_mcp_server(name="spike", version="1.0.0", tools=[lookup_fighter])

options = ClaudeAgentOptions(
    model=settings.cornercheck_model,
    mcp_servers={"spike": spike_server},
    allowed_tools=["mcp__spike__lookup_fighter"],
    permission_mode="bypassPermissions",
    max_turns=3,
    system_prompt=(
        "You are CornerCheck spike C, a terse test agent. When asked about any fighter, "
        "ALWAYS call the lookup_fighter tool first, then answer in two short sentences "
        "based only on the tool result."
    ),
)


async def run_agent(text: str, stream: Any) -> str:
    t0 = time.monotonic()
    events: Counter[str] = Counter()
    prompt = f"User message: {text!r}. Look up the fighter mentioned (default 'Dragan')."
    async for message in query(prompt=prompt, options=options):
        events[type(message).__name__] += 1
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    stream.append(markdown_text=block.text)
                elif isinstance(block, ToolUseBlock):
                    stream.append(
                        markdown_text=f"\n:mag: calling `{block.name}` "
                        f"with `{json.dumps(block.input)[:120]}`...\n"
                    )
        elif isinstance(message, ResultMessage):
            cost = getattr(message, "total_cost_usd", None)
            log.info("SPIKE-C ResultMessage cost=%s", cost)
    summary = f"events: {dict(events)}; total {time.monotonic() - t0:.1f}s"
    log.info("SPIKE-C %s", summary)
    return summary


@assistant.thread_started
def on_thread_started(say: Say) -> None:
    say("Spike C online. Ask me about a fighter, e.g. 'Is Dragan cleared?'")


@assistant.user_message
def on_user_message(payload: dict, say: Say, say_stream: SayStream, set_status: SetStatus) -> None:
    set_status("running the agent brain...")
    text = payload.get("text", "")
    stream = None
    try:
        stream = say_stream()
        stream.append(markdown_text="_Spike C: agent starting..._\n\n")
        summary = asyncio.run(run_agent(text, stream))
        stream.stop(markdown_text=f"\n\n_{summary}_")
    except Exception as exc:
        log.exception("SPIKE-C FAILED")
        if stream is not None:
            stream.stop(markdown_text=f"\n\nSpike C FAILED: {exc}")
        else:
            say(f"Spike C FAILED: {exc}")


app.use(assistant)


if __name__ == "__main__":
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    log.info("SPIKE-C starting Socket Mode connection (model=%s)...", settings.cornercheck_model)
    SocketModeHandler(app, settings.slack_app_token).start()
