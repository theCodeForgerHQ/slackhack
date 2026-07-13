# Devpost submission text — Asked & Answered

> Last updated: 2026-07-13 after v3 deployment to Render.
> Verified numbers below come from `npm test` and `npx tsx evals/run.ts`.

---

## Elevator pitch (≤200 chars)

Your Slack already answered this. Asked & Answered turns workspace history into completed security questionnaires — every answer cited, approved, and fail-closed.

## Inspiration

Every B2B deal ships a security questionnaire — 50 to 300 rows — and most of it asks what the team already answered somewhere in Slack, in last quarter's spreadsheet, or in the SOC 2 doc. It lands on the same one or two experts every time and stalls live deals for days.

## What it does

Asked & Answered is a Slack agent. You hand it a questionnaire (xlsx/csv or pasted text); it searches your workspace for evidence with the **Real-Time Search API** and sorts every question into one of three states:

- **Verified** — a matching answer an expert already approved, reused only after re-checking that *you* can still see all of its evidence.
- **Grounded** — a fresh draft, cited to the Slack messages and files behind it.
- **Needs SME** — not enough evidence, ungrounded citations, stale evidence, or an ACL block; it refuses to draft and routes the question to a human.

You review in a native Block Kit table, approve/edit/reject each answer, and export the finished questionnaire with citations and an approval record. Approved answers compound: the next questionnaire starts mostly done.

**It never invents a compliance answer.** No evidence, no answer — a human gets asked.

## Why it needs the Real-Time Search API

RTS is the entire evidence engine. Remove it and every question becomes Needs-SME — there is nothing to ground answers in. It also does the security work for us: results are scoped to what the requesting user can see, which is how we guarantee an answer never surfaces evidence you don't have access to. Our Query Planner is built around the RTS rate budget.

## Why it needs MCP

We ship `asked-answered-mcp`, a read-only MCP server that exposes the approved-answer library to Claude, Cursor, or the Slackbot MCP client — so the compliance knowledge your experts approved in Slack is reachable from wherever you work, without ever bypassing the permission checks. A human-gated `propose_answer` write path logs agent proposals as pending events; it never auto-approves.

## Why it's a Slack agent (not a standalone tool)

The evidence already lives in Slack. The experts already live in Slack. The approval already happens in Slack. External questionnaire tools bolt a separate knowledge base onto the side and make you maintain it. We make the workspace itself the answer library — zero-copy, citation-first, permission-aware.

## How we built it

TypeScript + Bolt. A small, sharp core:

- **Query Planner** — rate-aware RTS search.
- **Multi-agent Jury** — heterogeneous panel of drafters (Anthropic / OpenAI / Azure) reconciled behind the same interface.
- **GroundingGate** — deterministic snippet-level citation verification (exact + trigram Jaccard fallback).
- **DraftingPipeline** — three-state, fail-closed, with citation-subset and ACL guards.
- **EvidenceGraph** — typed SUPPORTS / CONTRADICTS / SUPERSEDES edges; stale approved answers degrade automatically.
- **ConformalMatcher** — split-conformal prediction for question matching instead of a magic threshold.
- **AnswerLibrary** — approved answers with ACL revalidation.
- **LedgerV2** — event-sourced, hash-chained approval lifecycle with live `verify`.
- **xlsx export** — finished questionnaire with citations and approval records.

The agent surface uses the agent_view Messages tab, a native Block Kit review table with per-row cards, an App Home dashboard (ACL-filtered per viewer), a Data Table of recent runs, a Canvas export artifact, a Workflow Builder custom step, and per-user OAuth scaffolding for private-channel RTS. 214 hermetic tests, CI, and an offline smoke test of the whole loop.

## The engineering we're proud of — a permission invariant, machine-checked

> **No answer text ever flows to a requester who cannot see all of its evidence.**

Every "memory" agent caches answers and serves them back; almost none re-check *who is asking* against the evidence the answer was built from. We do, in three places (library reuse, fresh drafts, and the MCP server), all fail-closed, and we prove it with a 200-run property test. This is the invariant a compliance tool must not get wrong.

## Evals (measured, reproducible — `npx tsx evals/run.ts`)

Against a seeded workspace with public/private channels and planted prompt-injection / stale-evidence / near-miss docs, over **127 labeled cases** (103 dev, 24 held-out):

- Grounded recall: **100%** (visible evidence → cited answer)
- Fail-closed correctness: **100%** (no visible evidence → never a grounded answer)
- Injection resistance: **100%** (poison docs never produce a foreign-cited answer)
- Citation faithfulness: **100%** (fabricated snippets caught by GroundingGate)
- Stale-evidence detection: **100%** (contradicted approved answers degrade for re-review)
- Guard-only metrics: **100%** (75/75 cases pass deterministically, independent of LLM)

Unit tests: **214/214 passed** (`npm test`).

## What we deliberately didn't build

PDF/OCR intake, per-sentence citations, auto-approval (rejected on principle — a compliance tool that self-approves is a liability). See `docs/LIMITATIONS.md`.

## What's next

PDF intake, semantic RTS where the plan supports it, and Marketplace distribution.

---

- **Repo:** https://github.com/theCodeForgerHQ/asked-and-answered
- **Live app:** https://asked-and-answered-app.onrender.com
- **Slack App ID:** A0BHW9UC23A
- **Sandbox:** Asked Answered Demo — access granted to slackhack@salesforce.com and testing@devpost.com
- **Architecture diagram:** docs/architecture.svg
- **Evals:** docs/EVALS.md
