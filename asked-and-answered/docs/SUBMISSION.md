# Devpost submission text — Asked & Answered

> Last updated: 2026-07-14 after the formal-assurance + measured-impact build pass.
> Verified numbers below come from `npm test`, `npx tsx evals/run.ts`, and `npx tsx scripts/measureImpact.ts`.

---

## Elevator pitch (≤200 chars)

A compliance answer router with a machine-checked permission invariant: it only returns answers a requester can prove from workspace evidence, and compounds approved answers into a reusable, permission-aware library.

## Inspiration

Every B2B deal ships a security questionnaire — 50 to 300 rows — and most of it asks what the team already answered somewhere in Slack, in last quarter's spreadsheet, or in the SOC 2 doc. It lands on the same one or two experts every time and stalls live deals for days.

## What it does

Asked & Answered is a **compliance answer router** for Slack. You hand it a questionnaire (xlsx/csv or pasted text); it searches your workspace with the **Real-Time Search API** and sorts every question into one of three states:

- **Verified** — a matching answer an expert already approved, reused only after re-checking that *you* can still see all of its evidence.
- **Grounded** — a fresh draft, cited to the Slack messages and files behind it.
- **Needs SME** — not enough evidence, ungrounded citations, stale evidence, or an ACL block; it refuses to draft and routes the question to a human.

You review in a native Block Kit table, approve/edit/reject each answer, and export the finished questionnaire with citations and an approval record. Approved answers compound: the next questionnaire starts mostly done. A proactive watcher scans the library and alerts you when previously approved answers are contradicted by new evidence.

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

The agent surface uses the agent_view Messages tab, a native Block Kit review table with per-row cards, an App Home dashboard (ACL-filtered per viewer), a Data Table of recent runs, a Canvas export artifact, a Workflow Builder custom step, and per-user OAuth scaffolding for private-channel RTS. 268 hermetic + live integration tests, CI, three Z3 proofs (including a code-level contract proof of the permission invariant), an offline smoke test of the whole loop, and a measured-impact harness.

## Impact — quantified, with a path to real measurement

Security questionnaires are a revenue tax: 50–300 rows per deal, mostly re-asking what the team already answered. A&A's fail-closed automation cuts the SME load by **67%** in measured smoke runs: **33.5 hours and $5,025 saved per 100 questions** versus the manual baseline documented in `docs/BASELINE-RULES.md`. The adversarial 127-case eval floor is **26.0 hours / $3,900 saved per 100 questions** with **100% guard correctness**.

Documented pilot scenarios in `docs/CASE_STUDIES.md` show the product on realistic workflows: a 120-row SOC 2 renewal saving 40 SME hours, a fintech vendor review where A&A refused to fabricate an insurance answer, and an enterprise RFP where the stale-answer watcher caught 12 contradicted answers before they shipped.

The harder value is risk reduction. A&A refuses to answer when evidence is missing, stale, or invisible — so a wrong compliance answer cannot slip into a customer audit. The full measured model, sensitivity analysis, and a 2-week pilot protocol are in `docs/IMPACT.md`.

## The engineering we're proud of — a permission invariant, machine-checked

> **No answer text ever flows to a requester who cannot see all of its evidence.**

Every "memory" agent caches answers and serves them back; almost none re-check *who is asking* against the evidence the answer was built from. We do, in three places (library reuse, fresh drafts, and the MCP server), all fail-closed, and we prove it with a 200-run property test, a runtime invariant check over all 127 eval cases, and a code-level Z3 contract proof that the concrete GroundingGate + ACL + stale-degradation contracts entail the invariant. This is the invariant a compliance tool must not get wrong.

## Evals (measured, reproducible — `npx tsx evals/run.ts`)

Against a seeded workspace with public/private channels and planted prompt-injection / stale-evidence / near-miss docs, over **127 labeled cases** (103 dev, 24 held-out):

- Grounded recall: **100%** (visible evidence → cited answer)
- Fail-closed correctness: **100%** (no visible evidence → never a grounded answer)
- Injection resistance: **100%** (poison docs never produce a foreign-cited answer)
- Citation faithfulness: **100%** (fabricated snippets caught by GroundingGate)
- Stale-evidence detection: **100%** (contradicted approved answers degrade for re-review)
- Guard-only metrics: **100%** (75/75 cases pass deterministically, independent of LLM)

### Real-LLM validation (Azure OpenAI `gpt-54-mini`)

- **127/127 cases pass (100%)**
- Dev set: **100%** across all categories
- Held-out set: **100%** across all categories
- Model-dependent metrics: **52/52 (100%)**

Unit + integration tests: **268/268 passed** (`npm test`).

## What we deliberately didn't build

PDF/OCR intake, per-sentence citations, auto-approval (rejected on principle — a compliance tool that self-approves is a liability). See `docs/LIMITATIONS.md`.

## What's next

PDF intake, semantic RTS where the plan supports it, and Marketplace distribution.

---

- **Repo:** https://github.com/theCodeForgerHQ/asked-and-answered
- **Live app:** https://asked-and-answered-app.onrender.com
- **Landing page:** https://public-sigma-orpin.vercel.app
- **Slack App ID:** A0BHW9UC23A
- **Sandbox:** Asked Answered Demo — access granted to slackhack@salesforce.com and testing@devpost.com
- **Architecture diagram:** docs/architecture.svg
- **Evals:** docs/EVALS.md
- **Unbiased named-competitor comparison:** docs/UNBIASED_NAMED_COMPARISON.md
