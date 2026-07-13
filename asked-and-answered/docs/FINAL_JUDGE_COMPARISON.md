# Final Judge Comparison — Asked & Answered vs. New Slack Agent Track

**Competition:** Slack Agent Builder Challenge 2026 — New Slack Agent track  
**Persona:** Neutral, realistic Stage-2 judge, no stake in outcome  
**Commit audited:** `21ad1d8` plus uncommitted working changes from the current build session  
**Date:** 2026-07-13

---

## TL;DR Verdict

Asked & Answered is a **strong, principled engineering submission** with several genuinely unique assets: a permission invariant enforced by deterministic guards, a 127-case eval with held-out set, a code-level Z3 proof sketch, event-sourced/hash-chained ledger, conformal question matching, and a recently added two-human-gate lifecycle with distinct-actor enforcement. It has closed many of the gaps identified in earlier audits.

However, it is **not the undisputed winner**. On an honest application of the published Stage-2 rubric, it currently places **4th** in the New Slack Agent track:

1. **Consensus** — most complete product + real-model eval + novel “contradiction firewall” idea.
2. **Kept** — narrow engineering rival with more tests, deterministic command engine, real Postgres/Redis integration suite, and published live-model eval.
3. **Arbiter** — broader multi-agent UX breadth and research narrative; A&A beats it on tests/eval/formal assurance but trails on design breadth.
4. **Asked & Answered** — credible engineering contender, slightly ahead of Quorum on raw rubric total.
5. **Quorum** — live deploy and load-bearing use of all three required technologies, but smaller engineering surface.

**Honest rubric total:** **32.5 / 40**  
**Honest track placement:** **4th**; could move to **1st–2nd** if it publishes real-LLM eval numbers and adds live integration tests.

---

## 1. Verified Outputs (re-run for this comparison)

All commands run from `/Users/ajayaditya/theCodeForger/qwen/asked-and-answered` on commit `21ad1d8` with the current working-tree changes.

| Command | Result |
|---|---|
| `npm run typecheck` | clean |
| `npm test` | 33 test files, **214/214 passed** |
| `npm run smoke` | **SMOKE PASS** |
| `npx tsx evals/run.ts` | **127 cases** (103 dev, 24 held-out); 100% on grounded recall, fail-closed, injection resistance, citation faithfulness, stale-evidence detection; guard-only 75/75; model-dependent 52/52 |
| `npx tsx scripts/verifyPipelineCodeLevel.ts` | **PROVED (unsat)** |
| `npx tsx scripts/verifyInvariantZ3.ts` | **PROVED (unsat)** |
| `npx tsx scripts/runCounterfactual.ts` | 37.5 SME hours / $5,625 saved per 100 questions (explicitly simulated) |
| `npx tsx scripts/runLoadBenchmark.ts` | ~37,400 questions/sec (local, hermetic) |

---

## 2. Per-Pillar Rubric Scorecard

Scoring basis: published Stage-2 rubric (25% each: Technological Implementation, Design, Potential Impact, Quality of the Idea; tie-break order Tech → Design → Impact → Idea). Demo video, CI badges, live sandbox availability, and Home UI polish are ignored for the engineering scorecard but noted separately.

| Pillar | Asked & Answered | Kept | Consensus | Arbiter | Quorum |
|---|---:|---:|---:|---:|---:|
| **Technological Implementation** | **9.0** | **9.5** | **8.5** | **8.5** | **7.5** |
| **Design** | **8.0** | **8.5** | **9.0** | **8.5** | **8.5** |
| **Potential Impact** | **7.0** | **8.0** | **8.5** | **8.0** | **8.0** |
| **Quality of the Idea** | **8.5** | **8.5** | **9.0** | **8.5** | **8.0** |
| **Rubric total (out of 40)** | **32.5** | **34.5** | **35.0** | **33.5** | **32.0** |

### Asked & Answered — justification by pillar

- **Technological Implementation: 9.0**  
  Strengths verified in code: 214 passing tests across 33 files; 127-case eval with dev/held-out split and deterministic guard-only metrics; `GroundingGate` (`src/core/grounding.ts`) for snippet-level citation verification; event-sourced `LedgerV2` with hash-chain verification (`src/core/ledgerV2.ts`); conformal matcher (`src/core/conformal.ts`); multi-agent jury (`src/core/jury.ts`); two mandatory human gates with **distinct-actor enforcement** (`src/core/decide.ts:95-96`, `src/core/stateMachine.ts:33-34`); per-user OAuth scaffolding with callback route and SQLite token store (`src/slack/oauth.ts`, `src/app.ts:86-140`, `slack/manifest.json:69-73`); ACL-filtered App Home (`src/slack/appHome.ts:60-90`, `tests/appHome.test.ts:66-91`); NFKC/delimiter hardening (`src/core/sanitize.ts`); code-level Z3 proof script (`scripts/verifyPipelineCodeLevel.ts`).  
  Deductions: the Z3 proof still uses uninterpreted functions representing pipeline components rather than verifying the actual TypeScript implementation; no published real-LLM eval numbers (eval defaults to a faithful fake LLM); no live Postgres/Slack integration test suite; Data Table review surface is used in App Home but not in DM review threads.

- **Design: 8.0**  
  Strengths: App Home dashboard with ACL-filtered recent answers and Data Table of runs; Canvas export with API-first attempt plus Markdown fallback; Block Kit review cards with Confirm/Approve two-gate UX; Workflow Builder custom step; MCP server exposing the approved library.  
  Deductions: Canvas export falls back to Markdown file upload on any API error (`src/app.ts:603-629`); Data Table builder exists but is not used in the production DM review path; no native Slack Lists integration.

- **Potential Impact: 7.0**  
  Strengths: clear security-questionnaire workflow; explicit counterfactual impact simulator with documented baseline rules (`docs/BASELINE-RULES.md`, `evals/counterfactual.ts`); local load benchmark.  
  Deductions: impact is explicitly simulated, not measured; no real customer quote, pilot metric, or deployment time-study.

- **Quality of the Idea: 8.5**  
  Strengths: “fail-closed compliance memory” is a sharp, defensible framing; the permission invariant is a genuine differentiator; the agent compounds approved answers into a reusable, permission-aware library.  
  Deduction: org-memory agents are not a wholly new category, so the novelty is in the execution (guards + invariant + governance) rather than the category itself.

---

## 3. Head-to-Head Engineering Comparison

| Dimension | Asked & Answered | Kept | Consensus | Arbiter | Quorum |
|---|---|---|---|---|---|
| **Tests** | 214 | ~325 | 132 | 66 | 19 + 2 int |
| **Eval size** | 127 cases (fake LLM) | 52 live + 42 lifecycle | 58 hand-labeled, real-model | ~40 (fact/workslop/routing) | None published |
| **Adversarial depth** | 30+ poison docs; homoglyph, ZWJ, RTL, delimiter-break, JSON smuggling, fake-system tags | 7+ hardening rounds | 9 delimiter/injection patterns; near-miss/scope/sarcasm | 12 adversarial cases | Minimal |
| **Citation verification** | Deterministic snippet grounding (`src/core/grounding.ts`) | None explicit | Permalink-in-set | Prompt-based | Permalink citations |
| **Multi-agent verification** | Heterogeneous jury + deterministic gate (`src/core/jury.ts`) | None | Single-LLM judge | Heterogeneous debate council (Free-MAD + DART) | DurableAgent + MCP tools |
| **State machine / governance** | Event-sourced + pure `decide()` + guarded FSM | Deterministic FSM (`src/domain/stateMachine.ts`) | Flat ledger + governance stub | Audit log | Durable workflow step |
| **Agent write safety** | State-machine-gated; model can propose but not approve | Two mandatory human gates; code-picked MCP tool | N/A (read/alert only) | Prompt-gated | Human approval hook |
| **Knowledge graph** | Evidence graph + contradictions (`src/core/evidenceGraph.ts`) | Entity graph | Flat ledger | Neo4j claim graph | Canvas + channel log |
| **Question matching** | Conformal prediction (`src/core/conformal.ts`) | Hand-tuned | Hand-tuned | Hand-tuned | Hand-tuned |
| **Formal assurance** | Property tests + Z3 proof sketch (`scripts/verifyPipelineCodeLevel.ts`) | Tests only | None | None | None |
| **Design surfaces** | App Home + Data Table + Canvas export + Block Kit + Workflow step | App Home + cards + modals | App Home + ephemeral alerts + audit report | App Home + Canvas + Lists + 7 entry points | Workflow + Canvas + channel |
| **Impact measurement** | Counterfactual simulator + load benchmark | None explicit | None explicit | Workslop benchmarks | None explicit |
| **Per-user OAuth / private-channel RTS** | Scaffolding + callback + SQLite store | Not highlighted | Membership gate | Global `SLACK_USER_TOKEN` | `SLACK_USER_TOKEN` required |
| **Two distinct human gates** | Yes (`src/core/decide.ts:95-96`) | Yes (`src/domain/stateMachine.ts`) | N/A | No | Approval hook |

---

## 4. Remaining Gaps That Prevent A&A From Being the Undisputed Winner

| # | Gap | Evidence | Why it costs rubric points |
|---|---|---|---|
| 1 | **No published real-LLM eval numbers** | `evals/run.ts` defaults to fake LLM; `docs/EVALS.md` says sandbox numbers are reported in submission but none are checked in | Tech/Impact: a judge cannot verify model-dependent recall or citation faithfulness with a real model. Consensus and Kept publish real-model reports. |
| 2 | **Z3 proof is a model sketch, not code verification** | `scripts/verifyPipelineCodeLevel.ts` uses uninterpreted functions (`grounded`, `aclFreshDraftPassed`, etc.) and asserts their behavior; it does not prove the actual TypeScript pipeline implements those axioms | Tech: a real judge distinguishes “proof of a model” from “proof the running code satisfies the invariant.” CornerCheck ties Z3 to the real rule engine. |
| 3 | **No live integration tests** | `tests/integration.test.ts` is hermetic (5 tests); no real Postgres/Slack sandbox suite | Tech: judges reward proven production wiring, not just hermetic unit tests. Kept and Relay run real integration suites. |
| 4 | **Canvas export falls back to Markdown file upload** | `src/app.ts:603-629` tries `canvases.create`, catches any error, and uploads a Markdown file | Design: the audit artifact is not guaranteed to be a native Canvas. Consensus, Arbiter, and Quorum write native Canvas. |
| 5 | **Data Table review surface not used in DM threads** | `src/slack/dataTable.ts` exists, but `src/app.ts:356` calls `reviewTableBlocks` (section fallback) | Design: the advanced surface is dead code in the main review flow. |
| 6 | **Impact is simulated, not measured** | `scripts/runCounterfactual.ts` prints simulated hours/dollars; output is explicitly labeled “SIMULATED” | Impact: judges want nameable users or measured deployment numbers. |
| 7 | **No native Slack Lists integration** | A&A surfaces data in App Home/Canvas; no `slackLists.items.create` equivalent | Design: Arbiter and Quorum use native Lists as durable workspace-visible storage. |

---

## 5. What A&A Must Prove to Take First Place

1. **Publish real-LLM eval numbers.** Run the 127-case dataset with Anthropic, OpenAI, and Azure; report guard-only metrics separately from model-dependent metrics. This single change closes the largest gap vs. Consensus and Kept.
2. **Add live integration tests.** A real SQLite/Postgres ledger test and a live Slack sandbox test (post questionnaire → assert grounded/Needs-SME thread) would move A&A ahead of Kept on proven production wiring.
3. **Strengthen the formal assurance to the actual code.** Replace uninterpreted-function axioms with a shallow symbolic model of `DraftingPipeline.runOne` and `AnswerLibrary.findVerified`, or extract behavioral contracts and prove those in CI.
4. **Make Canvas the default audit artifact.** Distinguish scope/plan failures from transient errors and only fall back to Markdown when the Canvas API is truly unavailable.
5. **Use the Data Table in production review threads.** Wire `reviewDataTableBlocks(..., { useDataTable: true })` into the main DM flow.
6. **Measure real impact.** Replace the simulated counterfactual with a pilot quote, time-study baseline, or deployment metric; keep the simulator but label it clearly as a model.

If A&A executes items 1–3, it becomes a **credible 1st–2nd place engineering contender**; if it also executes 4–6, it is the **track leader on technological implementation** and likely wins the tie-break.

---

## 6. Operational Notes (Not Scored, but Worth Mentioning)

- **Live app / sandbox:** `docs/SUBMISSION.md` lists a Render deployment and sandbox access; these are Stage-1 operational gates and are not factored into the engineering scorecard above.
- **Doc/test drift:** `docs/SUBMISSION.md` now correctly claims 214 tests and 127 eval cases; earlier drift has been fixed in the current working tree.
- **Code health:** `npm run typecheck` is clean; the CI workflow runs typecheck, tests, smoke, eval, both Z3 proofs, counterfactual, and load benchmark.
