# Asked & Answered

> *"Objection — asked and answered."* Every security questionnaire asks questions your team already answered. This agent proves it.

**Asked & Answered** is a Slack-native agent that turns your team's Slack history into completed security questionnaires, RFPs, and vendor forms — every answer evidence-cited, SME-approved, and tamper-evidently logged.

**It never invents a compliance answer.** No evidence → no answer → a human gets asked instead.

## How it works

1. Upload a questionnaire (xlsx/csv, or paste questions) to the agent in Slack.
2. It streams a plan, then searches your workspace for evidence using the **Real-Time Search API** — scoped to what *you* can see.
3. Every question lands in one of three states:
   - **Verified** — matches an answer an SME already approved (re-checked against *your* permissions before reuse)
   - **Grounded** — a new draft, cited to Slack messages/files you can see
   - **Needs SME** — insufficient evidence; the agent refuses to draft and routes to the right human
4. Review in a native table; **confirm then approve** (two distinct human gates), edit, or reject per row. Every action appends to a hash-chained, event-sourced ledger (`verify ledger` proves it).
5. Export the finished questionnaire (xlsx, Canvas, or Workflow Builder step) with citations and approval records. Approved answers compound: the next questionnaire starts mostly done.

## The invariant

**No answer text ever flows to a requester who cannot see all of its evidence.** Enforced by permission revalidation on every reuse and a property-based test suite. See `ARCHITECTURE.md`.

## Built with (Slack Agent Builder Challenge)

- **Slack AI capabilities** — agent_view surface, App Home dashboard, Data Table, Canvas export, Workflow Builder custom step
- **Real-Time Search API** — the evidence engine, scoped per user with action tokens and optional per-user OAuth for private-channel search
- **MCP** — ships `asked-answered-mcp`, exposing the approved-answer library to Claude/Cursor/Slackbot as read-only tools; write path is human-gated

## Development

[![CI](https://github.com/theCodeForgerHQ/asked-and-answered/actions/workflows/ci.yml/badge.svg)](https://github.com/theCodeForgerHQ/asked-and-answered/actions/workflows/ci.yml)

```bash
npm install
npm test          # 214 hermetic tests — no network, no Slack
npm run typecheck
npm run smoke     # full loop offline: parse → draft → review → confirm → approve → tamper → export
npx tsx evals/run.ts   # 127-case measured eval with held-out set (default: deterministic fake LLM)
npx tsx scripts/verifyInvariantZ3.ts  # machine-checked permission invariant
npx tsx scripts/verifyPipelineCodeLevel.ts  # code-level Z3 proof tied to actual pipeline guards
npx tsx scripts/runCounterfactual.ts  # simulated impact numbers
npx tsx scripts/runLoadBenchmark.ts   # throughput benchmark
```

## Run against a real sandbox
1. Create the Slack app from `slack/manifest.json`, install to a Developer Program sandbox.
2. Copy `.env.example` → `.env`, fill in Slack tokens + your LLM credentials (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `AZURE_OPENAI_*`).
3. `npm run dev` (Socket Mode). Seed evidence with `scripts/seed-sandbox.ts`.

## Docs
- `docs/ARCHITECTURE.md` — the diagram + where Slack AI / RTS / MCP sit
- `docs/EVALS.md` — what's measured and how to reproduce
- `docs/JUDGE_WALKTHROUGH.md` — 5-minute judge path
- `docs/LIMITATIONS.md` — deliberate scope cuts
- `docs/HANDOFF.md` — deployment + submission checklist

License: MIT
