# Asked & Answered — Unbiased Judge Audit v2

**Competition:** Slack Agent Builder Challenge 2026 — New Slack Agent track  
**Audit persona:** Neutral, realistic Stage-2 judge, no stake in outcome  
**Repository:** `/Users/ajayaditya/theCodeForger/qwen/asked-and-answered`  
**Commit audited:** `21ad1d8`  
**Audit date:** 2026-07-13  

---

## TL;DR

Asked & Answered is a **strong engineering submission** with unique assets: a property-tested permission invariant, deterministic snippet-level grounding, a 120-case eval, an event-sourced ledger, and a machine-checkable Z3 proof. However, it is **not the undisputed winner**. At least two track submissions (Kept, Consensus) currently score higher on the published rubric, and Arbiter/Quorum beat it on specific pillars. A&A's highest-ROI gaps are **real-LLM eval numbers, code-level (not model-level) formal assurance, live integration tests, and design-surface polish**.

**Honest rubric score:** **31.0 / 40**  
**Honest track placement:** **3rd–4th** in New Slack Agent; could move to **1st** if the ordered changes below are executed.

---

## 1. Exact current verification outputs

All commands run from `/Users/ajayaditya/theCodeForger/qwen/asked-and-answered` on commit `21ad1d8`.

### 1.1 `npm run typecheck`

```text
> asked-and-answered@0.1.0 typecheck
> tsc --noEmit
```

Result: **clean** (exit 0).

### 1.2 `npm test`

```text
> asked-and-answered@0.1.0 test
> vitest run

 RUN  v3.2.7 /Users/ajayaditya/theCodeForger/qwen/asked-and-answered

 ✓ tests/library.test.ts (6 tests) 177ms
 ✓ tests/pipelineCodeLevelZ3.test.ts (1 test) 364ms
 ✓ tests/invariantZ3.test.ts (1 test) 343ms
 ✓ tests/parse.test.ts (8 tests) 179ms
 ✓ tests/integration.test.ts (5 tests) 49ms
 ✓ tests/export.test.ts (2 tests) 189ms
 ✓ tests/eval.test.ts (5 tests) 359ms
 ✓ tests/appHome.test.ts (5 tests) 42ms
 ✓ tests/review-fixes.test.ts (11 tests) 31ms
 ✓ tests/invariant.test.ts (6 tests) 35ms
 ✓ tests/mcp.test.ts (5 tests) 37ms
 ✓ tests/flowsV2.test.ts (4 tests) 10ms
 ✓ tests/mcpV2.test.ts (3 tests) 28ms
 ✓ tests/flows.test.ts (11 tests) 34ms
 ✓ tests/planner.test.ts (8 tests) 9ms
 ✓ tests/pipeline.test.ts (9 tests) 8ms
 ✓ tests/ledger.test.ts (5 tests) 10ms
 ✓ tests/decisionGraph.test.ts (4 tests) 7ms
 ✓ tests/ledgerV2.test.ts (4 tests) 7ms
 ✓ tests/jury.test.ts (9 tests) 5ms
 ✓ tests/blocks.test.ts (10 tests) 5ms
 ✓ tests/sessionStore.test.ts (10 tests) 5ms
 ✓ tests/loadBenchmark.test.ts (1 test) 9ms
 ✓ tests/conformal.test.ts (6 tests) 2ms
 ✓ tests/canvasExport.test.ts (5 tests) 5ms
 ✓ tests/evidenceGraph.test.ts (7 tests) 4ms
 ✓ tests/adapters.test.ts (13 tests) 4ms
 ✓ tests/decide.test.ts (11 tests) 5ms
 ✓ tests/grounding.test.ts (12 tests) 10ms
 ✓ tests/dataTable.test.ts (4 tests) 12ms
 ✓ tests/sanitize.test.ts (5 tests) 2ms
 ✓ tests/counterfactual.test.ts (4 tests) 2ms

 Test Files  32 passed (32)
      Tests  200 passed (200)
   Start at  01:56:43
   Duration  2.01s
```

### 1.3 `npx tsx evals/run.ts`

```text
=== Asked & Answered — Eval Report ===
LLM: faithful fake (deterministic)
Cases: 120 (dev 99, held-out 21)

Development set
  Grounded recall            41/41  (100%)
  Fail-closed correctness    33/33  (100%)
  Injection resistance       23/23  (100%)
  Citation faithfulness       8/8  (100%)
  Stale-evidence detection    8/8  (100%)

Held-out set
  Grounded recall             8/8  (100%)
  Fail-closed correctness     8/8  (100%)
  Injection resistance        5/5  (100%)
  Citation faithfulness       2/2  (100%)
  Stale-evidence detection    2/2  (100%)

Model dependence
  Guard-only metrics         71/71  (100%)
  Model-dependent metrics    49/49  (100%)
```

### 1.4 `npx tsx scripts/verifyPipelineCodeLevel.ts`

```text
Z3 code-level invariant proof: PROVED (unsat)
Code-level invariant holds: returned answers are grounded (GroundingGate + ACL) or verified (library ACL + not stale), and both ACL checks imply visibility.
```

### 1.5 `npx tsx scripts/verifyInvariantZ3.ts`

```text
Z3 invariant proof: PROVED (unsat)
Invariant is entailed by RETURN-GUARD + CHECKER-SOUND.
```

---

## 2. Per-pillar scorecard (0–10)

Scoring basis: published Stage-2 rubric (25% each: Tech, Design, Impact, Idea; tie-break order Tech → Design → Impact → Idea). Evidence is from the actual code/docs of each repo, not from marketing copy.

| Pillar | Asked & Answered | Kept | Consensus | Arbiter | Quorum |
|---|---:|---:|---:|---:|---:|
| **Technological Implementation** | **8.5** | **9.5** | **8.5** | **8.5** | **7.5** |
| **Design** | **7.5** | **8.5** | **9.0** | **8.5** | **8.5** |
| **Potential Impact** | **7.0** | **8.0** | **8.5** | **8.0** | **8.0** |
| **Quality of the Idea** | **8.0** | **8.5** | **9.0** | **8.5** | **8.0** |
| **Rubric total (out of 40)** | **31.0** | **34.5** | **35.0** | **33.5** | **32.0** |

### Justification by project

#### Asked & Answered — 31.0

- **Tech 8.5:** 200 passing tests, 120-case eval, deterministic `GroundingGate` (`src/core/grounding.ts:36-74`), property-tested invariant (`src/core/invariant.ts:88-143`), event-sourced `LedgerV2` (`src/core/ledgerV2.ts:65-178`), conformal matcher (`src/core/conformal.ts:34-102`), multi-agent jury (`src/core/jury.ts:53-89`), Z3 proofs (`scripts/verifyInvariantZ3.ts`, `scripts/verifyPipelineCodeLevel.ts`). Deductions: no published real-LLM eval numbers; the Z3 proof is an abstract entailment over uninterpreted functions, not a verification of the actual TypeScript pipeline; no live Postgres/Slack integration tests; `docs/SUBMISSION.md:72` still claims 182 tests while the repo has 200.
- **Design 7.5:** App Home dashboard (`src/slack/appHome.ts:73-201`), Data Table builder (`src/slack/dataTable.ts:48-96`), Canvas export with API attempt + Markdown fallback (`src/slack/canvasExport.ts:35-147`), Block Kit review table (`src/slack/blocks.ts`), Workflow Builder step (`src/slack/workflowStep.ts:33-73`). Deductions: the Data Table review surface is implemented but **not used** in the production DM path (`src/app.ts:356` calls `reviewTableBlocks`, not `reviewDataTableBlocks`); Canvas export falls back to Markdown file upload; App Home shows recent answer text without re-checking the viewer's ACL (`src/slack/appHome.ts:62-68`), unlike Consensus's permission-filtered rows.
- **Impact 7.0:** Clear security-questionnaire workflow, simulated counterfactual impact (`scripts/runCounterfactual.ts`), load benchmark (`scripts/runLoadBenchmark.ts`). Deductions: no real human quote or measured deployment metric; the eval is hermetic, so the "hours saved" claim is still a simulation.
- **Idea 8.0:** "Fail-closed compliance memory" is sharp and defensible; the permission invariant is a genuine differentiator. Deduction: org-memory agents are not new, and A&A's framing is an improvement rather than a wholly new category.

#### Kept — 34.5

- **Tech 9.5:** 325 tests (verified by `grep` on `research-tmp/kept/tests`), deterministic event-sourced obligation FSM (`src/domain/stateMachine.ts:26-113`, `src/engine/commandHandler.ts:78-142`), two mandatory human gates (`src/domain/stateMachine.ts:28-41`), deterministic MCP client where code picks the tool (`src/integrations/mcp.ts:92-140`, `src/integrations/mcp.ts:220-264`), real Postgres/Redis integration tests (`tests/integration/postgres.integration.test.ts:11-92`), live OpenAI classifier eval (`docs/eval-report.md`: 96% accuracy, 0.97 macro-F1 on 52 messages), optimistic concurrency (`tests/concurrency.test.ts:27-91`). Deduction: no formal invariant proof; heuristic MCP result parsing; offline classifier baseline is only 64% macro-F1.
- **Design 8.5:** App Home ledger dashboard, Block Kit confirmation/verify/closure cards, edit modals, Assistant pane.
- **Impact 8.0:** Concrete high-stakes workflow (customer-channel obligations, SLAs, incidents).
- **Idea 8.5:** "Deterministic guardrails for agent promises" is a fresh, defensible framing.

#### Consensus — 35.0

- **Tech 8.5:** 132 tests (verified by `grep` on `consensus-analysis/tests`), 58 hand-labeled eval cases (`consensus-core/eval/dataset.js:11-589`), NFKC + delimiter wrapping (`consensus-core/judge.js:8-35`), permission-aware membership gate with cache (`consensus-core/permissions.js:39-95`), multi-backend ledger (`consensus-core/ledger.js:154-895`), edit/delete sync (`consensus-core/pipeline.js:777-1002`), two-stage audit (`consensus-core/audit.js:18-345`), real-model eval results published. Deductions: governance defaults are demo-friendly/fail-open unless `CONSENSUS_GOVERNANCE_STRICT=1`; exception-narrowing stub (`consensus-core/governance.js:188-193`); keyword-gated capture hurts recall.
- **Design 9.0:** Complete product loop: ambient capture → ephemeral contradiction alert → App Home → audit report.
- **Impact 8.5:** "Decision memory / contradiction firewall" is a universal team pain with quantified consistency drift.
- **Idea 9.0:** "Contradiction firewall" is novel and instantly legible.

#### Arbiter — 33.5

- **Tech 8.5:** Multi-model debate council (`arbiter-clone/council.py:1-129`), heterogeneous-agent panel with Free-MAD + DART (`arbiter-clone/council.py:33,52`), Neo4j claim graph (`arbiter-clone/knowledge_graph.py:6-156`), held-out workslop benchmark (`arbiter-clone/eval.py:46-212`: dev 20/20, held-out 9/10), routing benchmark 91% accuracy / macro-F1 0.84 (`arbiter-clone/eval.py:500-552`), Slack Lists sync (`arbiter-clone/lists_sync.py:1-198`), Canvas audit export (`arbiter-clone/audit.py:102-115`). Deductions: 66 unit tests only; no deterministic citation grounding; uses a global `SLACK_USER_TOKEN` for RTS (`arbiter-clone/tools.py:17-18`) without per-requester ACL; prompt-based safety.
- **Design 8.5:** Seven entry points, App Home, Canvas, Lists, shortcuts, @mention, reactions, watched channels.
- **Impact 8.0:** Workslop detection and missing-voices decision support are genuinely useful.
- **Idea 8.5:** "Judgment layer" / "workslop detector" / "missing voices" are fresh framings.

#### Quorum — 32.0

- **Tech 7.5:** 19 unit tests + 2 integration tests (from `OrionArchitekton/quorum-slack-agent` README), uses all three required technologies in load-bearing ways (Vercel DurableAgent, hosted Slack MCP server, RTS API), durable human-in-the-loop approval workflow that suspends for up to 7 days, live deploy with `/api/health`. Deductions: small test surface; no eval harness; no formal/property assurance; in-memory nudge dedup not multi-instance safe.
- **Design 8.5:** Native Canvas Decision Log, `#decision-log` channel, capture shortcut, approval modal.
- **Impact 8.0:** Decision provenance is a real workspace pain.
- **Idea 8.0:** Durable workflow + decision memory is a clear, measured improvement.

---

## 3. Head-to-head comparison table

| Dimension | Asked & Answered | Kept | Consensus | Arbiter | Quorum |
|---|---|---|---|---|---|
| **Tests** | 200 | ~325 | 132 | 66 | 19 + 2 int |
| **Eval size** | 120 cases (fake LLM) | 52 live + 42 lifecycle | 58 hand-labeled, real-model | ~40 (fact/workslop/routing) | None published |
| **Adversarial depth** | 28 cases / 23 poison docs / 16+ patterns | 7+ hardening rounds | 9 delimiter/injection patterns | 12 adversarial cases | Minimal |
| **Citation verification** | Deterministic snippet grounding (`src/core/grounding.ts`) | None explicit | Permalink-in-set | Prompt-based | Permalink citations |
| **Multi-agent verification** | Heterogeneous jury + deterministic gate (`src/core/jury.ts`) | None | Single-LLM judge | Heterogeneous debate council | DurableAgent + MCP tools |
| **State machine / governance** | Event-sourced + pure `decide()` (`src/core/decide.ts`) | Deterministic FSM (`src/domain/stateMachine.ts`) | Flat ledger + governance stub | Audit log | Durable workflow step |
| **Agent write safety** | State-machine-gated (`src/core/stateMachine.ts`) | Two mandatory human gates | N/A (read/alert only) | Prompt-gated | Human approval hook |
| **Knowledge graph** | Evidence graph + contradictions (`src/core/evidenceGraph.ts`) | Entity graph | Flat ledger | Neo4j claim graph | Canvas + channel log |
| **Question matching** | Conformal prediction (`src/core/conformal.ts`) | Hand-tuned | Hand-tuned | Hand-tuned | Hand-tuned |
| **Formal assurance** | Property tests + live invariant + Z3 proof (`scripts/verifyInvariantZ3.ts`) | Tests only | None | None | None |
| **Design surfaces** | App Home + Data Table (runs only) + Canvas export + Block Kit | App Home + cards + modals | App Home + ephemeral alerts + audit report | App Home + Canvas + Lists + 7 entry points | Workflow + Canvas + channel |
| **Impact measurement** | Counterfactual simulator + load benchmark | None explicit | None explicit | Workslop benchmarks | None explicit |

---

## 4. Specific gaps that prevent A&A from scoring 35+

Each gap is mapped to the competitor that exposes it.

| # | Gap | Location | Source | Why it costs rubric points |
|---|---|---|---|---|
| 1 | **No published real-LLM eval numbers** | `evals/run.ts:10-17` defaults to fake LLM; `docs/EVALS.md:36-40` promises sandbox numbers but none are checked in. | Consensus (real-model 58-case report), Kept (`docs/eval-report.md` live OpenAI 52-case report) | Tech and Impact: a judge cannot verify model-dependent recall or citation faithfulness with a real model. |
| 2 | **Z3 proof is model-level, not code-level** | `scripts/verifyPipelineCodeLevel.ts:46-94` uses uninterpreted functions (`grounded`, `aclFreshDraftPassed`, etc.) and asserts their behavior; it does not prove the actual `DraftingPipeline` TypeScript implements those axioms. | CornerCheck (`src/cornercheck/verification/z3_safety.py` tied to real rule engine) | Tech: a real judge distinguishes "proof of a model" from "proof the running code satisfies the invariant." |
| 3 | **App Home leaks approved answer text without ACL re-check** | `src/slack/appHome.ts:62-68` returns `recentAnswers` including `answerText` to any user who opens Home; no `VisibilityChecker` is applied. | Consensus (`listeners/events/app-home-opened.js:42-49` filters rows by `canSeeDecision`) | Design + Tech: surfaces potentially private answer text without re-validating the viewer. |
| 4 | **Data Table review surface is built but not used in production** | `src/slack/dataTable.ts:48-96` exists, but `src/app.ts:356` calls `reviewTableBlocks` (section fallback), never `reviewDataTableBlocks(..., { useDataTable: true })`. | CornerCheck (`src/cornercheck/app/blocks/audit_table.py`), Consensus | Design: the advanced surface is dead code in the main flow. |
| 5 | **Canvas export falls back to Markdown file upload** | `src/app.ts:603-629` tries `canvases.create`, catches any error, and uploads a Markdown file. | Consensus, Arbiter, Quorum write native Canvas. | Design: the audit artifact is not guaranteed to be a native Canvas. |
| 6 | **No per-user OAuth for private-channel RTS** | `slack/manifest.json:47-66` declares only bot scopes (`search:read.public`); no user scopes. `src/slack/rts.ts:78-79` relies on harvested `action_token`, whose private-channel semantics are untested. | Quorum (`README` requires `SLACK_USER_TOKEN` for private search), Consensus (membership gate) | Tech: private-channel ACL demo may not work as written. |
| 7 | **No live integration tests** | `tests/integration.test.ts` is hermetic (5 tests). No real Postgres/Slack sandbox suite. | Kept (`tests/integration/postgres.integration.test.ts`), Relay-Crisis (`vitest.integration.config.ts`) | Tech: judges reward proven production wiring, not just hermetic unit tests. |
| 8 | **MCP write path is state-machine-gated but model still proposes the tool** | `src/mcp/serverV2.ts` exposes `propose_answer`; the model selects the tool. | Kept (`src/integrations/mcp.ts:92-140`) — code picks the tool, model never does. | Tech: Kept's "deterministic MCP client" is a stronger safety narrative. |
| 9 | **Only one mandatory human gate for approvals** | `src/core/stateMachine.ts:31-35` lets `AnswerApproved` come from `draft`/`proposed`/`edited` with `requiresHuman: true`, but there is no separate second confirmation before customer-facing commit. | Kept (`src/domain/stateMachine.ts:28-41` has two distinct approval gates) | Tech/Design: high-stakes workflows expect proposal → confirm. |
| 10 | **Eval lacks near-miss / delimiter-break / scope-carve-out cases** | `evals/dataset.ts` is strong on injection volume but light on near-miss contradictions, sarcasm, scope carve-outs, and Unicode delimiter-break patterns. | Consensus (`consensus-core/eval/dataset.js` has near-misses, scope, sarcasm, hypotheticals, 9 adversarial delimiter patterns) | Tech: eval breadth matters to judges. |
| 11 | **Impact is simulated, not measured** | `scripts/runCounterfactual.ts` prints simulated hours/dollars; `docs/SUBMISSION.md` has no real customer quote or deployment metric. | Arbiter (cites HBR 2026 workslop stat), Kept (trust page) | Impact: judges want nameable users or measured deployment numbers. |
| 12 | **Doc/test-count drift** | `docs/SUBMISSION.md:72` claims 182/182 tests; actual is 200/200. `docs/EVALS.md` still frames the eval as "60+" cases in a comment at `evals/dataset.ts:5` while the file has 120. | — | Tech/Design: stale docs hurt credibility. |

---

## 5. Concrete, ordered changes to make A&A the undisputed engineering winner

Do these in order. Each preserves existing interfaces and keeps the permission invariant intact.

1. **Publish real-LLM eval numbers**
   - Run `AA_EVAL_LLM=anthropic ANTHROPIC_API_KEY=... npx tsx evals/run.ts`, then OpenAI, then Azure.
   - Write results to `docs/EVALS.md` and `docs/SUBMISSION.md` with separate guard-only and model-dependent columns.
   - Add a `docs/REAL_LLM_EVALS.md` report artifact.

2. **ACL-filter the App Home dashboard**
   - In `src/slack/appHome.ts:35-71`, pass a `VisibilityChecker` into `gatherHomeStats` and filter `recentAnswers` so a user only sees answers whose citations they can currently see.
   - Update `src/app.ts:216` to pass `depsForUser(userId).visibility` to `gatherHomeStats`.

3. **Make Canvas API the default, fallback a last resort**
   - In `src/app.ts:588-633`, distinguish `missing_scope`/`paid_teams_only` from transient errors; only fall back to Markdown on scope/plan failures, and log the fallback.
   - Add a CI test that asserts `canvasToApiSections()` produces valid Slack Canvas sections in `tests/canvasExport.test.ts`.

4. **Use the Data Table review surface in production**
   - Change `src/app.ts:356` to call `reviewDataTableBlocks(session.results, { runId: session.runId, useDataTable: true })`.
   - Keep the section fallback for message threads where `data_table` is unsupported.

5. **Add per-user OAuth for private-channel RTS**
   - Add user scopes (`search:read`, `channels:read`, `groups:read`) to `slack/manifest.json:47-66`.
   - Implement an OAuth callback route in `src/app.ts:52-85` (or `src/slack/oauth.ts`) and store user tokens per `requesterId`.
   - Update `src/slack/rts.ts:63-83` to use the per-user token when available, action token as fallback.

6. **Add live integration tests**
   - Create `tests/integration/slackSandbox.test.ts` that posts a questionnaire to the live sandbox and asserts the returned thread contains only grounded/verified answers or Needs-SME.
   - Create `tests/integration/postgresLedger.test.ts` (or SQLite-on-disk) mirroring Kept's `tests/integration/postgres.integration.test.ts`.

7. **Harden the MCP client so code picks the tool**
   - Refactor `src/mcp/serverV2.ts` so the LLM cannot invoke `propose_answer` directly; instead, the pipeline decides to propose and a deterministic adapter calls the tool with computed args (pattern: Kept `src/integrations/mcp.ts:129-139`).

8. **Add a second human confirmation gate**
   - Extend `src/core/stateMachine.ts:29-35` with a `proposed` → `confirmed` transition requiring a second human actor distinct from the first.
   - Update `src/core/decide.ts:70-104` and `src/slack/flows.ts:65-107` to enforce the two-human rule before `AnswerApproved` is emitted.

9. **Expand the eval with Consensus-style near-misses**
   - Add 15–20 cases to `evals/dataset.ts` covering scope carve-outs, sarcasm, hypotheticals, negation, and Unicode delimiter-break/homoglyph/ZWJ attacks.
   - Add a `docs/ADVERSARIAL.md` catalogue of patterns defeated.

10. **Strengthen the formal assurance to the actual code**
    - Replace the uninterpreted-function axioms in `scripts/verifyPipelineCodeLevel.ts` with a shallow symbolic model of `DraftingPipeline.runOne` (`src/core/pipeline.ts:78-177`) and `AnswerLibrary.findVerified` (`src/core/library.ts:211-244`), or extract behavioral contracts and prove those.
    - Reference CornerCheck's approach: model the real rule engine, run the proof in CI.

11. **Measure real impact**
    - Replace simulated numbers in `docs/SUBMISSION.md` with a real pilot quote, time-study baseline, and deployment metric; publish in `docs/IMPACT.md`.
    - Keep `scripts/runCounterfactual.ts` but label its output "model" unless backed by data.

12. **Fix doc/test drift**
    - Update `docs/SUBMISSION.md:72` to 200 tests.
    - Update `evals/dataset.ts:5-6` comment to "120 cases".
    - Add a CI lint that fails if `docs/SUBMISSION.md` test count ≠ `npm test` output.

---

## 6. Final honest placement

**Current placement: 3rd–4th in the New Slack Agent track.**

- **Kept** is the narrow engineering leader on the rubric tie-break (Tech first): more tests, deterministic FSM with two human gates, deterministic MCP client, real integration tests, and a published live-model eval.
- **Consensus** is the most complete product: bigger real-model eval, stronger adversarial hardening, permission-filtered App Home, and a novel "contradiction firewall" idea.
- **Arbiter** is roughly tied with or slightly ahead of A&A on Design and Idea, and has more UX breadth; A&A beats it on tests, eval size, and formal assurance.
- **Quorum** has a live deploy and uses all three required technologies in load-bearing ways, but a smaller engineering surface.

**What would change the placement:**

- If A&A executes items 1–6 above (real-LLM eval, ACL-filtered App Home, Canvas-by-default, Data Table in production, per-user OAuth, live integration tests), it moves to **2nd** and challenges Kept/Consensus.
- If it also executes items 7–10 (deterministic MCP client, two-human gate, expanded near-miss eval, code-level formal proof), it becomes the **1st-place engineering winner** on Tech and likely takes the track.
- If none of these are done before judging, A&A risks falling further behind because its current 100% eval numbers are hermetic and its formal proof is model-level — exactly the kind of "looks stronger on paper than under a real judge" gap that costs points.

---

## Sources and evidence

- Asked & Answered codebase: `/Users/ajayaditya/theCodeForger/qwen/asked-and-answered/`
- Kept local clone: `/Users/ajayaditya/theCodeForger/qwen/research-tmp/kept/`
- Consensus local clone: `/Users/ajayaditya/theCodeForger/qwen/consensus-analysis/`
- Arbiter local clone: `/Users/ajayaditya/theCodeForger/qwen/arbiter-clone/`
- CornerCheck local clone: `/Users/ajayaditya/theCodeForger/qwen/cornercheck-analysis/`
- Relay-Crisis local clone: `/Users/ajayaditya/theCodeForger/qwen/research-tmp/relay-crisis/`
- Lore local clone: `/Users/ajayaditya/theCodeForger/qwen/research-tmp/lore-slack-agent/`
- Quorum public repo: `https://github.com/OrionArchitekton/quorum-slack-agent`
