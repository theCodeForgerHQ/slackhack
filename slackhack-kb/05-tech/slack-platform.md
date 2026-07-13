# Slack Agent Platform — 2026 Technical State (researched 2026-07-11, live docs)

*Sources: docs.slack.dev, api.slack.com, GitHub API. All API names verified against live documentation.*

## The stack in one paragraph
"Slack AI capabilities" for third-party devs in mid-2026 = the **Agents feature** (app-level toggle granting `assistant:write`), the **`assistant.*` Web API family**, **streaming message APIs**, **agent-specific Block Kit blocks**, the **Real-Time Search API**, and the **Slack MCP server/client pair**. Anchored at [docs.slack.dev/ai](https://docs.slack.dev/ai); core guide: [developing-agents](https://docs.slack.dev/ai/developing-agents).

## `slack create agent` (the challenge's advertised on-ramp)
- Quickstart: docs.slack.dev/ai/agent-quickstart. CLI install → `slack login` → `slack create agent` scaffolds **"Casey"** (IT support agent) with parallel implementations for **Claude Agent SDK, OpenAI Agents SDK, Pydantic AI** (Python) / Claude + OpenAI (JS). Run with `slack run`.
- Template picker via `slack create --list` (CLI v3.13.0, Feb 19 2026). Public sample: slack-samples/bolt-python-support-agent + bolt-js-support-agent.

## Two messaging experiences (CHANGED June 30 2026 — critical)
- **`agent_view` (new, required for new apps):** conversations in the app's Messages tab with thread timeline. Events: **`app_home_opened`** (check `tab === "messages"`), **`app_context_changed`**, **`message.im`**. `app_context_changed` delivers an `entities` array (e.g. `slack#/types/channel_id`) describing what the user is viewing.
- **`assistant_view` (legacy, deprecating):** `assistant_thread_started` etc. **Manifest switch to `agent_view` is irreversible.** Old docs/templates mix both — beware.

## Key API methods (exact names)
| Purpose | Method |
|---|---|
| Status / "thinking" | `assistant.threads.setStatus` (empty string clears) |
| Thread titles | `assistant.threads.setTitle` |
| Suggested prompts | `assistant.threads.setSuggestedPrompts` |
| Streaming | `chat.startStream` → `chat.appendStream` → `chat.stopStream` (Bolt `say_stream`/`sayStream`); Blocks only on stopStream; unfurls disabled during stream; `task_display_mode: "plan"` |
| Workspace search | `assistant.search.context`, `assistant.search.info` |
| Replies | `chat.postMessage` w/ `thread_ts`; `chat.update` ≤ ~1/3s |

Agent-specific Block Kit: **task card block, plan block, `context_actions` block, `feedback_buttons` element, `icon_button` element, markdown block** (renders standard markdown — the LLM-output fix), new container block (2026-06-29). Full response-loop example (status → stream plan → RTS search → `conversations.replies` drill-down → LLM → Block Kit) in developing-agents#full-example.

## Constraints
- **Paid plan required** for AI features; free path = **Slack Developer Program sandbox** (api.slack.com/developer-program).
- **Guests cannot use AI-enabled apps.** Free-plan workspaces get no agent container — degrade gracefully (Marketplace review item).
- **Zero-copy policy:** never store Slack data; store metadata, fetch real-time. No LLM training on Slack data.
- Prompt-injection guidance mandatory: docs.slack.dev/concepts/security#prompt-injection.
- Since May 29 2025: non-Marketplace commercially-distributed apps get `conversations.history`/`replies` at **Tier 1: 1 req/min, 15 objects** — the "read-everything bot" is dead; RTS/MCP are the sanctioned context paths.

## MCP in Slack — two directions

### A. Slack's own MCP server (your agent consumes Slack)
- Endpoint `https://mcp.slack.com/mcp` — JSON-RPC 2.0 over **Streamable HTTP only**. Announced Feb 17 2026.
- Confidential OAuth (app client_id/secret), RFC 8414 metadata, user-token endpoints `slack.com/oauth/v2_user/authorize` + `oauth.v2.user.access`, PKCE.
- **Only Marketplace-published or internal apps may use it** (unlisted distributed prohibited). Enable: app settings → Agents → toggle MCP Server.
- Tools: search messages/files/users/channels/emoji; send/draft messages; read channels/threads; create conversations; reactions; canvases CRUD; profiles; members. Per-tool rate limits mirror Web API tiers.
- OpenAI Responses API wiring example in slack-samples/bolt-js-slack-mcp-server:
  `tools: [{ type: 'mcp', server_label: 'slack', server_url: 'https://mcp.slack.com/mcp', headers: { Authorization: Bearer ${context.userToken} }, require_approval: 'never' }]`

### B. Slackbot MCP Client (Slack consumes YOUR MCP server) — newest surface, announced Jun 18 2026
- Docs: docs.slack.dev/ai/slackbot-mcp-client. **Gated rollout** — check for "MCP Servers" under Features in app settings.
- Manifest: bot scope **`mcp:connect`** + **`mcp_servers`** block (`url`, `auth_type` ∈ no_auth | slack_identity_auth | dynamic_client_registration | manual_auth). Slackbot auto-discovers tools, invokes from natural language.
- Slack signs every request (verify signing secret); `slack_identity_auth` passes caller identity in `_meta.slack`.
- Max 5 active MCP servers/user; write-classified tools (no `readOnlyHint`) get extra consent friction.
- Rich responses via **MCP Apps** (interactive HTML/JS iframes).
- Working code: slack-samples/bolt-js-examples `ai/slackbot-mcp-client/` (+ python equivalent).

## Real-Time Search (RTS) API
- Methods: `assistant.search.context` (messages, files, channels, users) + `assistant.search.info` (capability report incl. semantic search availability). Evolved from Data Access API.
- Scopes (granular; legacy `search:read` banned): `search:read.public` (required), `.private`, `.mpim`, `.im` (user token only), `.files` (+`files:read`), `.users`.
- **`action_token`** required for bot-token calls — harvested from fresh `message.im`/`message.mpim`/`message.groups`/`message.channels`/`app_mention` events. User-token (xoxp) calls don't need it.
- **Restricted to Marketplace-published or internal apps.** Works in Developer Program sandbox. **Semantic search** needs Slack AI Search plan (Business+/Enterprise+; sandbox access via partnerships request) — **keyword search is what judges' sandboxes will exercise**; don't demo semantic-only.
- Params: `channel_types`, `content_types`, `include_context_messages`, `include_message_blocks`, `term_clauses`/`keywords_clauses`, `modifiers`, search-bar filters in query (`type:pdf`, `threads:all`, `with:<@U>`, `is:dm`, `creator:`…), `OR`, `before`/`after`, `sort`, `cursor` (max 20/page), `disable_semantic_search`.
- **Rate limits (the #1 design constraint):** ~10+ req/min per workspace (scales to 400+ for large teams), hard per-user 10 req/min, pagination counts. Supplemental user-token `conversations.history`/`replies`: 5 req/min, 100 msgs. Design ≤10 calls per user inquiry.
- Permission model: results scoped to what the searching user can see; Slack Connect → invoking channel only; guests excluded.
- Policy: zero-copy, no training, no unrelated scraping; user-token `*:history` RTS apps must NOT also subscribe to user-level message events.
- **RTS code in the wild is SCARCE** (GitHub search for `assistant.search.context` → mostly SDK bindings; agno-agi/agno toolkit is a rare consumer). **Deep RTS usage is differentiated by default.**

## Known pain points = project opportunities
1. **RTS rate limits brutal for agent loops** → rate-limit-aware planned/batched retrieval (OR-consolidation, metadata caching) is compliant + demo-ably smart.
2. **May 2025 rate-limit crackdown** killed read-everything bots → fixing broken workflows via RTS/MCP is a strong pitch.
3. **Marketplace chicken-and-egg** (5 active workspaces to submit; listing needed for MCP/RTS distribution) — widely felt.
4. **mrkdwn vs markdown**: streaming+blocks awkward (blocks only on stopStream; bolt-js#2752, #2696, #2073).
5. **Assistant framework bugs**: bolt-js#2802 (thread_started not fired), bolt-python#1368/#1452 (get_thread_context None), bolt-js#2668 (infinite loop), bolt-python#1346 (middleware bypass) — hand-roll workarounds.
6. **Migration whiplash** assistant_view→agent_view (one-way, event model changes).
7. **Slackbot MCP client gated rollout**; 5-server cap; consent fatigue on write tools.
8. **Semantic search plan-gated** → build for keyword fallback.
9. **action_token plumbing confuses people** → clean abstraction = genuine DX win.
10. **Guests + free plans excluded** from AI apps — never claim "works for everyone."

## Synthesis: where a winning entry sits
Combine ALL THREE qualifying technologies in one loop: an `agent_view` app that streams a plan (`chat.startStream` + task cards), grounds itself with `assistant.search.context` (+ context drill-down), acts through the Slack MCP server on the user's behalf, optionally exposes its own tools back via the Slackbot MCP client — while visibly solving a pain point (rate-limit-aware retrieval, mrkdwn-safe streaming, cross-system context assembly). Maximizes the Technological Implementation rubric line, which explicitly scores usage of the three technologies.
