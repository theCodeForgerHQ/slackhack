# Architecture

Asked & Answered is a Slack agent that answers security questionnaires from
evidence that already lives in your workspace — fail-closed, evidence-cited,
tamper-evidently logged, and now deterministically grounded.

## The one diagram

```
                         Slack (agent_view Messages tab)
                                    │
                 upload xlsx/csv  ┌─┴─┐  stream plan · review table · /verify
                                  │app│  (src/app.ts — Bolt listeners & actions)
                                  └─┬─┘
        ┌───────────────┬──────────┼───────────────┬─────────────────┬─────────────────┐
        ▼               ▼          ▼               ▼                 ▼                 ▼
    parse.ts       QueryPlanner  Jury            DraftingPipeline   AnswerLibrary      LedgerV2
  (questions)      (RTS budget)  (multi-agent    (3-state, fail-    (approved answers  (event-sourced,
                        │         panel)          closed, guards)    + ACL invariant)   hash-chained)
                        ▼               │                 │                 │                │
              ┌─────────────────┐       ▼                 │                 │                │
              │ Real-Time Search│   GroundingGate         │                 │                │
              │  (assistant.    │   (snippet-level        │                 │                │
              │  search.context)│    verification)        │                 │                │
              └─────────────────┘                         │                 │                │
                                                          ▼                 ▼                ▼
                                              EvidenceGraph      asked-answered-mcp    /aa verify
                                            (SUPPORTS /          (search_answers,      (tamper check)
                                             CONTRADICTS /       get_answer_provenance,
                                             SUPERSEDES)         propose_answer)
```

## Where each qualifying technology sits

| Technology | Module | Role — and why it is load-bearing |
|---|---|---|
| **Real-Time Search API** | `src/slack/rts.ts`, `src/core/planner.ts` | The *only* evidence source. Remove it and every question becomes Needs-SME — there is nothing to ground answers in. The Query Planner is what makes it usable under the 10-req/min budget. |
| **Slack AI capabilities** | `src/app.ts`, `src/slack/blocks.ts` | The agent surface: agent_view Messages tab, streamed plan, Block Kit review table + cards + `feedback_buttons`. This is the entire frontend and the human-in-the-loop approval UX. |
| **MCP** | `src/mcp/server.ts`, `src/mcp/serverV2.ts` | Ships `asked-answered-mcp`, exposing the approved-answer library to Claude/Cursor/Slackbot as identity-bound read-only tools. `serverV2.ts` adds a human-gated `propose_answer` write path that logs pending proposals in LedgerV2 without auto-approving. |

## Data flow, one question at a time

1. **Parse** (`core/parse.ts`) — xlsx/csv/text → deduped `Question[]`.
2. **Retrieve** (`core/planner.ts` → `slack/rts.ts`) — per-question RTS search,
   rate-budgeted; `include_context_messages` supplies surrounding context.
3. **Draft** (`core/pipeline.ts` + `core/jury.ts`) — three outcomes, fail-closed by construction:
   - **Verified** — a matching SME-approved answer exists *and* every one of its
     citations is visible to this requester right now (`core/library.ts` + `core/conformal.ts`).
   - **Grounded** — the Jury drafts from evidence; GroundingGate verifies that every
     cited snippet actually appears in the retrieved evidence; cited channels are
     re-checked against the requester before any text is released.
   - **Needs SME** — no evidence, failed search, model refusal, invalid
     citations, ungrounded snippets, stale evidence, or an ACL block. No answer text is produced.
4. **Review** (`slack/flows.ts`, `slack/blocks.ts`) — the human approves / edits /
   rejects / routes. Approvals append to LedgerV2 and feed the library.
5. **Export** (`core/export.ts`) — xlsx with citations and approval records.

## The deterministic safety shell

Most agents trust the LLM to cite evidence honestly. We don't:

- **GroundingGate** (`core/grounding.ts`) NFKC-normalizes the answer text and each
  cited snippet, then requires exact or high-trigram-overlap substring match. A
  fabricated citation is automatically downgraded to Needs-SME.
- **EvidenceGraph** (`core/evidenceGraph.ts`) tracks SUPPORTS / CONTRADICTS /
  SUPERSEDES relationships. A previously Verified answer is degraded to Needs-SME
  when newer evidence contradicts its supporting claims.
- **ConformalMatcher** (`core/conformal.ts`) replaces hand-tuned similarity
  thresholds with split-conformal prediction, so a question is only matched to a
  single verified answer when the prediction set is a singleton.

## The invariant

> **No answer text ever flows to a requester who cannot see all of its evidence.**

Enforced in three places and property-tested (`tests/library.test.ts`,
`tests/review-fixes.test.ts`, `tests/invariant.test.ts`):

- **Library reuse** re-validates every citation against the current requester
  and degrades to Needs-SME on any miss.
- **Grounded drafts** re-check each cited channel against the requester before
  releasing text; GroundingGate additionally verifies the cited snippet exists.
- **The MCP server** redacts any evidence-backed answer whose evidence the
  bound identity cannot verify. It **fails closed by default**: an unconfigured
  server (no visibility supplied) redacts every evidence-backed answer;
  disclosure is opt-in (`AA_MCP_TRUST_LOCAL=1` for a local single-operator run,
  or an injected `VisibilityChecker`).

All three fail *closed*: a visibility-check error, or an unconfigured checker,
counts as "not visible."

## Trust & integrity

- **Zero-copy.** The library stores app-authored approved answers plus permalink
  *pointers* — never copied Slack content. The ledger stores keyed HMAC content
  hashes, not answer text.
- **Tamper-evident.** LedgerV2 stores full DomainEvents in a hash chain; any
  mutation to either stored columns or payload JSON breaks `verify()`.
- **Injection-resistant.** Evidence is quoted as untrusted data; the model is
  told to ignore instructions inside it; output is strict JSON (anything else
  fails closed); cited snippets are re-validated against retrieved evidence, so
  a fully-hijacked reply still cannot smuggle a foreign citation.

## Testing

- `npm test` — 146 hermetic tests (no network, no Slack), incl. a 200-run
  fast-check property suite on the invariant.
- `npm run smoke` — the full loop offline: parse → plan → draft → review →
  compounding reuse → tamper detection → export.
- `npx tsx evals/run.ts` — 60-case labeled eval (see `docs/EVALS.md`).
