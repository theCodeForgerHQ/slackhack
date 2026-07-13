# Slack AI Agent

A Node.js application that uses **Slack Bolt for JavaScript** and the **Real-Time Search (RTS) API** to build an AI agent that answers questions grounded in live workspace context and automates workflows.

## Architecture

```
src/
├── app.js                      # Entry point — initializes Bolt app
├── config/
│   └── index.js                # Environment configuration
├── services/
│   ├── rtsClient.js            # Real-Time Search API client (assistant.search.context)
│   ├── aiAgent.js              # AI agent — orchestrates RTS + LLM (OpenAI/Anthropic)
│   ├── conversationStore.js    # Supabase persistence for conversation history
│   └── workflowAutomation.js   # Scheduled task execution
└── handlers/
    ├── mentionHandler.js       # @mention event handler
    ├── messageHandler.js       # Direct message handler
    └── slashCommands.js        # /ask, /search, /agent-stats commands
```

## How It Works

1. **User asks a question** — via @mention, DM, or slash command
2. **RTS search** — `assistant.search.context` retrieves permission-aware context from Slack (messages, files, channels, users)
3. **AI generation** — the LLM (OpenAI/Anthropic) generates a response grounded in the RTS results
4. **Response posted** — the agent replies in the same thread
5. **Conversation logged** — every exchange is stored in Supabase for analytics and context continuity

## Setup

### 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Add the following **Bot Token Scopes**:
   - `app_mentions:read`
   - `chat:write`
   - `search:read.public`
   - `search:read.private`
   - `search:read.files`
   - `search:read.users`
   - `commands`
3. Enable **Socket Mode** (recommended) or set up a public Request URL
4. Subscribe to bot events: `app_mention`, `message.im`
5. Create slash commands: `/ask`, `/search`, `/agent-stats`

### 2. Configure Environment

```bash
cp .env.example .env
# Fill in your Slack credentials and AI API key
```

### 3. Install & Run

```bash
npm install
npm start
```

## Modes

### Socket Mode (Development)
Set `SLACK_SOCKET_MODE=true` and provide `SLACK_APP_TOKEN`. No public URL needed — uses WebSocket.

### HTTP Mode (Production)
Set `SLACK_SOCKET_MODE=false`. The app runs an Express server on `PORT` (default 3000) with a `/health` endpoint. Point your Slack app's Request URL to `https://your-domain.com/slack/events`.

## AI Provider Fallback

If no `AI_API_KEY` is configured, the agent falls back to a **rule-based mode** that returns formatted RTS search results directly — useful for testing the Slack integration without an LLM.

## Workflow Automation

Register scheduled workflows in `src/app.js`:

```javascript
workflows.register({
  name: 'Daily Standup Summary',
  intervalMs: 86400000, // 24 hours
  channelId: 'C12345678',
  query: 'standup updates from today',
  prompt: 'Summarize the team standup updates',
});
```

## Required Slack Scopes

| Scope | Purpose |
|-------|---------|
| `app_mentions:read` | Listen for @mentions |
| `chat:write` | Post messages |
| `search:read.public` | RTS: search public channels |
| `search:read.private` | RTS: search private channels |
| `search:read.files` | RTS: search files |
| `search:read.users` | RTS: search users |
| `commands` | Slash commands |

## Tech Stack

- **Slack Bolt for JavaScript** — official SDK for building Slack apps
- **Real-Time Search API** — `assistant.search.context` for permission-aware workspace search
- **Supabase** — conversation history persistence
- **OpenAI / Anthropic** — LLM providers for response generation
