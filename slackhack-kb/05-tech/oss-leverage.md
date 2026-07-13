# OSS Leverage + Marketplace 48h Feasibility (verified via GitHub API, 2026-07-11)

## Official repos — start here (MIT unless noted)
| Repo | Stars | Pushed | What it gives |
|---|---|---|---|
| slack-samples/**bolt-python-support-agent** | 5 | 2026-07-10 | **"Casey"** — the challenge's canonical `slack create agent` template. IT helpdesk agent; Claude Agent SDK / OpenAI Agents SDK / Pydantic AI variants; App Home, DM threads, @mentions, reacji status; pre-wired for Slack MCP server |
| slack-samples/**bolt-js-support-agent** | 11 | 2026-07-10 | Casey in JS |
| slack-samples/**bolt-python-starter-agent** | 20 | 2026-07-09 | Minimal blank-canvas agent, 3 LLM frameworks |
| slack-samples/**bolt-python-assistant-template** | 63 | 2026-07-10 | Suggested prompts, setStatus/setTitle, streaming, feedback blocks |
| slack-samples/**bolt-js-slack-mcp-server** | 9 | 2026-07-01 | End-to-end Slack MCP server consumption: manifest, OAuth user tokens, OpenAI Responses MCP tool call, canvas/message actions |
| slack-samples/**bolt-js-examples** & bolt-python-examples | 1/1 | 2026-07-09 | `ai/slackbot-mcp-client/` no-auth + slack-identity MCP-client reference implementations (Unlicense) |
| slack-samples/**bolt-python-ai-chatbot** | 114 | 2026-07-01 | Most-starred AI chatbot sample |
| slackapi/**slack-mcp-plugin** | 81 | 2026-07-10 | Official Claude Code plugin: hosted-MCP config + 6 dev skills (slack-cli, create-slack-app, block-kit…) — **accelerates OUR build workflow** |
| slack-samples bolt-*-search-template | 1–3 | 2026-07 | Enterprise-search surface patterns |

Skip: deno-* templates (legacy workflow platform; coded workflows barred from Marketplace).

## Community repos
| Repo | Stars | License | Notes |
|---|---|---|---|
| korotovsky/slack-mcp-server | 1,718 | MIT | Most popular Slack↔MCP bridge; uses browser tokens — NOT challenge/Marketplace-aligned, but great tool-design reference |
| ubie-oss/slack-mcp-server | 110 | Apache-2.0 | Clean official-API Slack MCP server |
| **duolingo/slack-ai-agent** | 38 | Apache-2.0 | Production-grade Claude-Code-SDK Slack agent: streaming, thread context, MCP manager, role-based tool allowlists, channel configs — **best architecture reference for a serious entry** |
| agno-agi/agno (tools/slack.py) | — | MPL-2.0 | Rare OSS consumer of `assistant.search.context` (RTS) |

**RTS code in the wild is scarce** → deep RTS usage is differentiated by default. (Typed `assistant.search.*` support was still an open request: slackapi/node-slack-sdk#2607.)

Rules explicitly permit OSS bases if licenses are complied with AND we enhance/build on top.

## Marketplace feasibility in 48h (Organizations track) — VERDICT
Process: (1) automated pre-submission checks → (2) preliminary review ≤10 business days → (3) functional review ≤10 weeks.
- **5-active-workspaces rule is a SUBMISSION GATE, not just listing:** "Apps that do not meet this requirement will be **blocked from submitting**." Active = used in past 28 days. Sandboxes don't count.
- Also required to submit: public landing page, public support page (2-business-day SLA), privacy policy, listing assets (icon, 1600×1000 screenshot, descriptions), per-scope justifications, **AI disclosures** (model, retention, tenancy, LLM disclaimer, free-plan degradation, ≤25-word agent overview), real multi-workspace OAuth distribution (Socket Mode single-workspace shortcuts won't pass), test credentials, collaborator.
- Approval by Jul 13 impossible; **valid submission (App ID) technically achievable but gated on 5 genuinely active workspaces** — the single most likely blocker; "apps without any customers don't belong" per review guide.
- **Strategic read: Organizations track pays the same $8k but adds ~1 day of bureaucracy + a hard gate we can't guarantee. Higher-EV: New Slack Agent or Agent-for-Good with flawless RTS+MCP.**
