"""Persistent Claude Agent SDK brain with a sync facade for Bolt handlers.

One ClaudeSDKClient (one bundled-CLI subprocess), per-Slack-thread session_id, an
asyncio loop in a daemon thread, and the PreToolUse ledger gate wired in. Events are
surfaced through a callback so the Slack layer can stream thinking steps.
"""

import asyncio
import contextlib
import os
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from cornercheck.brain.hooks import GATED_TOOL, make_ledger_gate
from cornercheck.config import get_settings
from cornercheck.session.state import SESSION_STORE

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system.md").read_text()

ALLOWED_TOOLS = [
    "mcp__cornercheck__er_resolve_fighter",
    "mcp__cornercheck__er_fighter_details",
    "mcp__cornercheck__rules_evaluate_clearance",
    "mcp__cornercheck__rules_outcome_window",
    "mcp__cornercheck__ledger_record_clearance",
    "mcp__cornercheck__ledger_recent_entries",
    "mcp__cornercheck__ledger_verify_chain",
]


@dataclass(frozen=True)
class BrainEvent:
    kind: str  # text | tool_use | result
    text: str = ""
    tool_name: str = ""
    tool_input: dict | None = None
    cost_usd: float | None = None


EventCallback = Callable[[BrainEvent], None]


def build_options() -> ClaudeAgentOptions:
    settings = get_settings()
    server_env = {
        "DATABASE_URL": settings.database_url,
        "CORNERCHECK_LEDGER_HMAC_KEY": settings.cornercheck_ledger_hmac_key,
        "PATH": os.environ.get("PATH", ""),
    }
    return ClaudeAgentOptions(
        model=settings.cornercheck_model,
        fallback_model=settings.cornercheck_model_fallback or None,
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={
            "cornercheck": {
                "type": "stdio",
                "command": sys.executable,
                "args": ["-m", "cornercheck.mcp_server.server"],
                "env": server_env,
            }
        },
        allowed_tools=ALLOWED_TOOLS,
        permission_mode="bypassPermissions",
        max_turns=10,
        hooks={
            "PreToolUse": [HookMatcher(matcher=GATED_TOOL, hooks=[make_ledger_gate(SESSION_STORE)])]
        },
    )


class BrainTimeoutError(RuntimeError):
    """Raised when an ask exceeds its deadline; the client is rebuilt afterwards."""


class Brain:
    """Sync facade over one persistent async SDK client.

    Concurrency model (review findings C1/C2): the SDK client's receive stream is a
    single shared queue with no per-session demultiplexing, so the ENTIRE
    query+receive span is serialized by one asyncio.Lock created ON the loop thread.
    A timed-out ask cancels its coroutine and poisons the client so the next ask gets
    a fresh subprocess instead of someone else's response tail.
    """

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="brain-loop", daemon=True
        )
        self._thread.start()
        self._client: ClaudeSDKClient | None = None
        self._poisoned = False
        self._ask_lock: asyncio.Lock | None = None  # created lazily ON the loop thread

    async def _get_ask_lock(self) -> asyncio.Lock:
        if self._ask_lock is None:
            self._ask_lock = asyncio.Lock()
        return self._ask_lock

    async def _ensure_client(self) -> ClaudeSDKClient:
        if self._poisoned and self._client is not None:
            with contextlib.suppress(Exception):  # the old subprocess may already be gone
                await self._client.disconnect()
            self._client = None
            self._poisoned = False
        if self._client is None:
            client = ClaudeSDKClient(options=build_options())
            await client.connect()
            self._client = client
        return self._client

    async def _ask(self, thread_key: str, prompt: str, on_event: EventCallback) -> str:
        lock = await self._get_ask_lock()
        async with lock:  # one ask owns the shared stream at a time
            client = await self._ensure_client()
            try:
                full_prompt = f"thread_key: {thread_key}\n\n{prompt}"
                await client.query(full_prompt, session_id=thread_key)
                final_text: list[str] = []
                async for message in client.receive_response():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                final_text.append(block.text)
                                on_event(BrainEvent(kind="text", text=block.text))
                            elif isinstance(block, ToolUseBlock):
                                on_event(
                                    BrainEvent(
                                        kind="tool_use",
                                        tool_name=block.name,
                                        tool_input=dict(block.input or {}),
                                    )
                                )
                    elif isinstance(message, ResultMessage):
                        on_event(
                            BrainEvent(
                                kind="result",
                                cost_usd=getattr(message, "total_cost_usd", None),
                            )
                        )
                return "".join(final_text).strip()
            except BaseException:
                # ANY abnormal exit mid-stream (a raising on_event callback, an SDK
                # error, cancellation) abandons this response's tail on the shared
                # stream; without poisoning, the NEXT ask reads that stale tail as its
                # own answer (cross-thread leakage). Timeout was the only poisoned
                # path before the audit; now every escape poisons.
                self._poisoned = True
                raise

    def ask(
        self, thread_key: str, prompt: str, on_event: EventCallback, timeout: float = 180.0
    ) -> str:
        """Blocking call for Bolt handlers (which already run off the ack path)."""
        future = asyncio.run_coroutine_threadsafe(
            self._ask(thread_key, prompt, on_event), self._loop
        )
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()  # detach the abandoned coroutine from the shared stream
            self._poisoned = True  # next ask rebuilds the client on the loop thread
            raise BrainTimeoutError(
                f"brain timed out after {timeout:.0f}s for thread {thread_key};"
                " no answer was produced (the deterministic pipeline result still stands)"
            ) from None

    def close(self) -> None:
        if self._client is not None:
            fut = asyncio.run_coroutine_threadsafe(self._client.disconnect(), self._loop)
            fut.result(timeout=10)
        self._loop.call_soon_threadsafe(self._loop.stop)


_brain: Brain | None = None
_brain_init_lock = threading.Lock()


def get_brain() -> Brain:
    global _brain
    with _brain_init_lock:
        if _brain is None:
            _brain = Brain()
        return _brain
