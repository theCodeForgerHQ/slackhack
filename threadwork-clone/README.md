# Threadwork

Turn any messy Slack thread into a structured work post - decisions, tasks, owners, related history, and a supervised agent action - without leaving Slack.
Entry for the **Slack Agent Builder Challenge** (New Slack Agent track). Qualifying tech: **Real-Time Search API + Slack AI/agent capabilities + MCP integration** (all three).

Threadwork is not a summarizer.
@mention it in a thread and it produces durable work objects: a Canvas work post (decisions with evidence links, open questions), a Slack List of tasks (owners, due dates, checkboxes), permalink-cited related past discussions found semantically via RTS, and an **Agent Run Card** - the agent proposes one task, executes only after a human clicks Approve, and the card records who approved what and where the output lives.

## Setup

1. Create a Slack app at https://api.slack.com/apps → "Create New App" → "From a manifest" → paste [manifest.json](manifest.json). Install it to your workspace.
2. In app settings: create an app-level token with `connections:write` (Socket Mode page) and enable the Agents & AI Apps toggle.
3. `cp .env.example .env` and fill in the tokens (Slack bot + app tokens, signing secret, OpenRouter API key).
4. `npm install`
5. `npm run spike` - one-shot capability probe (RTS / Lists / Canvas availability on your workspace plan). Optional but recommended on a new workspace.
6. Add the bot to your channels (channel → Integrations → Add apps → Threadwork).
7. `npm run seed` - posts demo threads (set `SEED_*` channel ids in `.env`). **Seed at least a day before demoing: Slack's search index needs time before RTS can find the seeded history.**
8. `npm start` - run the bot. Then mention `@Threadwork structure this` inside any thread.

## Env vars (see .env.example)

| Var | What |
|---|---|
| `SLACK_BOT_TOKEN` / `SLACK_APP_TOKEN` / `SLACK_SIGNING_SECRET` | Slack app credentials |
| `LLM_API_KEY` / `LLM_MODEL` | OpenRouter key; default model `anthropic/claude-sonnet-5` |
| `SPIKE_CHANNEL_ID`, `SEED_*_ID` | channel ids for the spike and seed scripts |

## Graceful degradation (plan-restricted workspaces)

Capability checks at startup set feature flags; every restricted feature has a fallback and no failure is ever shown in the channel:

- **Lists unavailable** → tasks render as a checklist inside the Canvas; the List button is hidden.
- **Standalone Canvas unavailable** → falls back to a channel canvas, then to a formatted message.
- **RTS unavailable / no relevant results** → the "Previously discussed" section is omitted silently. On workspaces without AI Search, RTS runs in keyword mode automatically.

## Keeping it running (judging window)

Socket Mode needs the process alive. For an always-on setup: `npm i -g pm2 && pm2 start src/app.js --name threadwork && pm2 save`.
(HTTP Events API is a supported alternative to Socket Mode if you deploy behind a public URL; this repo ships Socket Mode for zero-infra setup.)

## Repo map

`src/app.js` routing · `src/pipeline.js` the 6-step flow · `src/llm.js` extraction/drafting · `src/canvas.js` work post · `src/lists.js` tasks · `src/rts.js` related history · `src/mcp.js` MCP client (files approved tasks via `scripts/mcp-tracker-server.js`) · `src/blocks.js` all Block Kit · `src/store.js` JSON state · `scripts/seed.js` demo data · `scripts/spike.js` capability probe.
