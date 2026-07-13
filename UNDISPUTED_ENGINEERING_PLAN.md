# UNDISPUTED ENGINEERING PLAN
## How Asked & Answered Beats Consensus and Arbiter at Their Own Games

**Goal:** Make Asked & Answered the clear engineering leader in the New Slack Agent track — not by chasing UI polish or demo assets, but by surpassing the two current engineering leaders on their own technical terms.

**Constraint:** Do not break the existing codebase. Add new modules, adapt adapters, and replace small internal algorithms where necessary.

**Time assumption:** Not a constraint. This is a complete plan; execute as much as possible.

---

## 1. The superiority thesis

Consensus wins on **eval rigor, adversarial hardening, and permission-aware safety breadth**.  
Arbiter wins on **multi-agent verification, algorithmic substance scoring, and knowledge-graph reasoning**.  
CornerCheck wins on **formal verification and neurosymbolic separation**.  
Relay wins on **event-sourced auditability and human-gated agent writes**.

Asked & Answered already owns the only **property-tested, deterministic fail-closed permission invariant** in the field. The plan is to **keep that invariant as the crown jewel** and build around it:

- **Match Consensus** on eval size and adversarial depth — then exceed it with formal/property verification.
- **Match Arbiter** on multi-agent verification and substance scoring — then harden it with deterministic citation grounding.
- **Match CornerCheck** on formal assurance — prove the invariant is non-vacuous and expose it as a live product feature.
- **Match Relay** on auditability and agent governance — make the ledger event-sourced and MCP writes human-gated.

Result: a submission that is not merely “reliable,” but **measurably, verifiably, and demonstrably safer and more rigorous** than the current leaders.

---

## 2. Target architecture (v3)

Keep the existing outer shape: `parse → plan → retrieve → draft → review → export`. Add a **deterministic safety shell** around the LLM and a **provenance graph** under the approved library.

```
                    Slack (agent_view / Messages tab)
                                │
    upload / mention ───────────┼─── src/app.ts
                                │
    ┌───────────────┬───────────┼───────────────┬─────────────────┐
    ▼               ▼           ▼               ▼                 ▼
 parse.ts      QueryPlanner  Jury (multi-    Decide (pure       Ledger v2
(questions)    (RTS budget)   agent draft/    event-sourced     (hash chain +
                            verify)           lifecycle)        external anchor)
                                │               │                 │
                        GroundingGate          EvidenceGraph    InvariantCheck
                        (deterministic         (claims +        (live + formal)
                         citation verify)       contradictions)
                                │               │
                        ReviewSession      AnswerLibrary v2
                        (Block Kit)        (conformal match)
                                │
                        Export (xlsx/Canvas/MCP)
```

New modules (all additive or replace small internal functions):

| Module | File | Purpose |
|---|---|---|
| `Jury` | `src/core/jury.ts` | Multi-agent debate for drafting and citation verification. |
| `GroundingGate` | `src/core/grounding.ts` | Deterministic verification that cited snippets exist in retrieved evidence. |
| `EvidenceGraph` | `src/core/evidenceGraph.ts` | Claim-level provenance graph with contradiction/supersedes edges. |
| `ConformalMatcher` | `src/core/conformal.ts` | Calibrated question matching with coverage guarantee. |
| `Decide` / events | `src/core/decide.ts`, `src/core/events.ts` | Pure decision engine + typed event taxonomy. |
| `LedgerV2` | `src/core/ledgerV2.ts` | Hash-chained event ledger with metadata stamps + external anchor. |
| `InvariantChecker` | `src/core/invariant.ts` | Live invariant check + formal non-vacuity tests. |
| `AdversarialSet` | `evals/adversarial.ts` | Expanded adversarial prompt-injection patterns. |
| `Counterfactual` | `evals/counterfactual.ts` | Simulated impact baseline vs real pipeline. |
| `McpServerV2` | `src/mcp/serverV2.ts` | Adds `propose_answer` human-gated write tool. |

---

## 3. Component-by-component plan

### 3.1 Deterministic grounding gate (surpasses Consensus’s citation-subset check)

**Current A&A:** checks that a cited permalink is in the retrieved set.  
**Consensus:** checks that a cited decision/message exists, but trusts the LLM’s statement about it.  
**New A&A:** verifies that the LLM’s cited *snippet* actually appears in the retrieved evidence.

**Algorithm:**
1. Normalize LLM answer + evidence with NFKC (`String.normalize('NFKC')`).
2. For each citation, locate the source RTS hit by permalink.
3. Check exact substring match after lowercasing/punctuation stripping.
4. If exact fails, compute character-trigram Jaccard similarity (like Sales Copy Concierge).
5. Require `similarity >= 0.85` for a citation to pass.
6. Any failing citation → `needs_sme` with reason `invalid_citations`.

**Why it wins:** Catches hallucinated paraphrases, invented statistics, and misattributed quotes that slip through a permalink-only guard. Consensus has no equivalent snippet-level verification.

**Files:**
- New: `src/core/grounding.ts`
- Edit: `src/core/pipeline.ts` to call `GroundingGate.verify()` after LLM draft.
- Tests: `tests/grounding.test.ts` with adversarial fabricated snippets.

---

### 3.2 Multi-agent jury for drafting and verification (matches Arbiter, hardens it)

**Arbiter’s pattern:** Skeptic → Advocate → Analyst → Contrarian → Synthesizer, heterogeneous providers, self-consistency voting.  
**New A&A:** Apply the same pattern to security-questionnaire drafting.

**Roles:**
- **Drafter** — produces answer text + cited permalinks from evidence.
- **Critic** — checks each claim against evidence; flags unsupported statements.
- **Citer** — verifies citations are from the evidence set and relevant.
- **Synthesizer** — reconciles into final `LlmDraft`.

**Hardening beyond Arbiter:**
- Run `GroundingGate` after the panel, so even a consensus hallucination is caught deterministically.
- Run the panel with **heterogeneous providers** (Anthropic + OpenAI + Azure) when keys are available; fall back to same-provider different prompts/temperatures.
- Add **self-consistency voting**: if panel splits, run synthesizer 3× and take majority verdict.
- Add **cost/quality telemetry**: log model, tokens, latency per role.

**Files:**
- New: `src/core/jury.ts`, `src/llm/providerRegistry.ts`
- Edit: `src/llm/index.ts` to create `JuryDrafter` alongside existing drafters.
- Tests: `tests/jury.test.ts` with split-panel scenarios.

---

### 3.3 Evidence graph + contradiction detection (surpasses Consensus’s decision ledger)

**Consensus:** stores decisions as flat statements; checks new messages for contradiction against the ledger.  
**New A&A:** build a graph of **claims** extracted from evidence and approved answers, with typed edges.

**Schema:**
```ts
interface EvidenceNode { id: string; kind: 'evidence'; permalink; snippet; channelId; ts; }
interface ClaimNode { id: string; kind: 'claim'; text; source: EvidenceNode | AnswerNode; }
interface AnswerNode { id: string; kind: 'answer'; questionText; answerText; citations; }
interface Edge { from; to; kind: 'SUPPORTS' | 'CONTRADICTS' | 'SUPERSEDES'; }
```

**Capabilities:**
- Before reusing a Verified answer, check if newer evidence contradicts any of its supporting claims. If yes, degrade to `needs_sme` with reason `stale_evidence`.
- When drafting, surface contradictions in the retrieved evidence to the user.
- Over time, the approved library becomes self-correcting.

**Why it wins:** Consensus detects contradictions in ambient chat. A&A would detect contradictions **between approved answers and fresh evidence**, which is higher-stakes for compliance.

**Files:**
- New: `src/core/evidenceGraph.ts`
- Edit: `src/core/library.ts` to query graph on Verified reuse.
- Tests: `tests/evidenceGraph.test.ts`.

---

### 3.4 Conformal question matching (surpasses hand-tuned thresholds)

**Current A&A:** Jaccard token overlap with magic threshold `0.8`.  
**Consensus / Arbiter:** also use hand-tuned similarity thresholds.  
**New A&A:** calibrate the threshold with split-conformal prediction.

**Algorithm:**
1. Build calibration set of question pairs labeled same/different.
2. Compute nonconformity score for each pair using token-Jaccard + embedding cosine.
3. Compute `q_hat = ceil((n+1)(1-α))`-th quantile.
4. At inference, return Verified only if the top match’s score ≤ `q_hat` and the prediction set is a singleton.

**Why it wins:** Replaces a magic number with a finite-sample coverage guarantee. Mis-recognition rate is bounded; ambiguous near-duplicates force human review instead of silently re-drafting.

**Files:**
- New: `src/core/conformal.ts`, `scripts/calibrateMatching.ts`
- Edit: `src/core/library.ts` to use `ConformalMatcher`.

---

### 3.5 Event-sourced ledger + pure decision engine (matches Relay)

**Current A&A:** `Ledger` appends action rows; `AnswerLibrary` stores mutable answers.  
**Relay:** typed events, transition table, pure `decide()` engine, human gates.  
**New A&A:** keep the hash chain, but make events the source of truth.

**Event taxonomy:**
```ts
type Event =
  | { type: 'QuestionnaireIntaken'; runId; questions; requesterId }
  | { type: 'EvidenceRetrieved'; runId; questionId; hits }
  | { type: 'DraftProduced'; runId; questionId; answerText; citations }
  | { type: 'CitationValidated'; runId; questionId; valid: boolean }
  | { type: 'VisibilityChecked'; runId; questionId; visible: boolean }
  | { type: 'AnswerApproved'; answerId; questionText; answerText; citations; actor }
  | { type: 'AnswerEdited'; answerId; newText; actor }
  | { type: 'AnswerRejected'; answerId; actor }
  | { type: 'AnswerProposed'; answerId; questionText; answerText; actor: 'agent' }
  | { type: 'Exported'; runId; actor };
```

**Pure `decide()` engine:**
- Input: current event log + command.
- Output: `{ outcome: 'emit' | 'rejected' | 'suppressed'; events?: Event[]; reason?: string }`.
- Enforces: idempotency, human gate for approval/rejection, valid state transitions.

**Why it wins:** Every Slack action, MCP action, and eval harness command exercises the same decision logic. No adapter can accidentally bypass a guard.

**Files:**
- New: `src/core/events.ts`, `src/core/decide.ts`, `src/core/ledgerV2.ts`
- Edit: `src/slack/flows.ts` to call `decide()`; keep `ReviewSession` as UI state only.
- Migration: existing `Ledger` rows can seed the new event log.

---

### 3.6 Ledger v2: tamper-evidence beyond the chain hash (matches CornerCheck)

**Current A&A:** hashes `[seq, ts, action, actor, questionId, answerHash, evidenceHash, prevHash]`.  
**CornerCheck:** stamps `actor/action/at` **inside** the hashed payload and cross-checks columns against the stamp on verify.  
**New A&A:** do both.

**Improvements:**
1. Store `_meta: { actor, action, ts }` inside the hashed JSON payload.
2. On `verify()`, recompute hashes and cross-check stored columns against `_meta` (with small clock tolerance).
3. Add an external anchor: post the chain head (`seq`, `hash`) to a public Slack channel or `/api/invariant` endpoint daily.
4. Add non-vacuity tests: corrupt a single guard and assert verification fails / invariant trips.

**Why it wins:** Catches column-level tampering (e.g., flipping `action` from `reject` to `approve`) that a plain chain hash would miss.

**Files:**
- New: `src/core/ledgerV2.ts`
- Edit: `src/core/ledger.ts` can wrap or be replaced behind the same interface.
- Tests: `tests/ledgerV2.test.ts` with mutation tests.

---

### 3.7 Formal invariant verification (surpasses everyone)

**Current A&A:** property test: answer text returned iff requester sees all citations.  
**CornerCheck:** Z3 proof + in-product button.  
**New A&A:** bridge the gap.

**Short term (practical):**
- Add non-vacuity regression tests: monkeypatch `VisibilityChecker.canSee` to always return true and assert the property test fails.
- Add a live `/invariant` endpoint that reruns the property test on a synthetic corpus and returns `healthy`/`violation`.
- Add an “Invariant check” button on the review/export card.

**Long term (engineering trophy):**
- Encode the invariant in Z3/SMT-LIB: for all users `u`, answers `a`, citations `c`, `answer_text_released(u, a) ⇒ ∀c ∈ citations(a), visible(u, c)`.
- Prove that the pipeline code refines the spec.
- Surface the proof in CI and product.

**Why it wins:** No competitor has a formal or live-checked invariant. This becomes the headline engineering contribution.

**Files:**
- New: `src/core/invariant.ts`, `tests/invariant.test.ts`
- Optional: `verification/invariant.smt2`

---

### 3.8 Expanded eval harness (match then exceed Consensus)

**Current A&A:** 15 cases, fake LLM, 2 poison docs.  
**Consensus:** 58 cases, 9 adversarial patterns, multi-model results.  
**New A&A target:**

| Category | Count | Notes |
|---|---|---|
| Grounded | 30 | varied question types, channels, evidence formats |
| Fail-closed (no evidence) | 20 | |
| ACL degraded | 15 | private-channel evidence, membership changes |
| Citation faithfulness | 15 | correct vs fabricated snippets |
| Injection resistance | 20 | Consensus’s 9 + role-play, JSON smuggling, fake system tags, delimiter breaks, prompt chaining |
| Contradiction / stale evidence | 10 | approved answer contradicted by newer evidence |
| Conformal matching | 10 | same/reworded/different questions |
| **Total** | **120+** | |

**Reporting:**
- Always report **guard-only metrics** (independent of model): fail-closed correctness, injection resistance, ACL correctness.
- Report **model-dependent metrics** separately for fake-LLM, Anthropic, OpenAI, Azure: grounded recall, citation faithfulness.
- Add a **held-out set** used only for final reporting.
- Add a **local/hermetic load benchmark** replaying a seeded questionnaire corpus (p50/p95/p99 latency).

**Why it wins:** Larger, harder, more honest eval than Consensus. Separates model-independent guarantees from model-dependent performance.

**Files:**
- New: `evals/adversarial.ts`, `evals/counterfactual.ts`, `evals/loadBenchmark.ts`
- Edit: `evals/dataset.ts`, `evals/harness.ts`, `evals/run.ts`

---

### 3.9 Human-gated MCP writes (matches Relay)

**Current A&A:** MCP server is read-only.  
**Relay:** read-only tools + opt-in `pledge_support` that files a proposal, requiring human confirmation.  
**New A&A:** add `propose_answer` tool.

**Design:**
- `propose_answer(questionText, answerText, citations?)` → files an `AnswerProposed` event with `actor: 'agent'`.
- The answer appears in Slack as a pending proposal card with **Approve / Edit / Reject**.
- `decide()` rejects any agent-originated `AnswerApproved` event unless it came through the human UI.
- Tool is disabled unless `AA_MCP_WRITES_ENABLED=1`.

**Why it wins:** Shows safe agent autonomy without auto-approval. Surpasses A&A’s read-only MCP and matches Relay’s governance pattern.

**Files:**
- New: `src/mcp/serverV2.ts`
- Edit: `src/core/decide.ts` to enforce human gate.

---

### 3.10 Counterfactual impact simulator (matches Relay)

**A&A’s current impact claim:** “saves SME time.”  
**Relay:** runs a naive baseline simulator side-by-side with the real pipeline and reports an honest `SIMULATED` delta.

**New A&A:**
1. Define a baseline model: manual questionnaire process = ticket per question, SME response time, uncited answer probability, inconsistent-answer probability.
2. Run the same questionnaire corpus through A&A’s hermetic pipeline.
3. Compute delta: SME hours saved, citation coverage, inconsistent answers avoided.
4. Label clearly as `SIMULATED`; publish baseline rules.

**Why it wins:** Turns “saves time” into a measured number without fabricating real-deployment data.

**Files:**
- New: `evals/counterfactual.ts`, `docs/BASELINE-RULES.md`

---

## 4. Implementation roadmap (modular, no breakage)

### Phase 0 — Safety net (do first)
- Add comprehensive tests for current behavior so later changes are protected.
- Pin existing `Ledger` and `AnswerLibrary` interfaces.

### Phase 1 — Deterministic grounding + eval expansion (highest ROI)
- Implement `GroundingGate`.
- Expand eval to 60+ cases and 10 adversarial patterns.
- Add non-vacuity invariant tests.
- **At this point A&A surpasses Consensus on citation safety and is competitive on eval size.**

### Phase 2 — Multi-agent jury
- Implement `JuryDrafter` behind the `DraftingLlm` interface.
- Add provider registry for heterogeneous models.
- Add self-consistency voting.
- **At this point A&A matches Arbiter on drafting verification.**

### Phase 3 — Evidence graph + conformal matching
- Implement `EvidenceGraph`.
- Implement `ConformalMatcher`.
- Integrate into `AnswerLibrary`.
- **At this point A&A has smarter reuse and self-correcting library than Consensus or Arbiter.**

### Phase 4 — Event-sourced ledger + pure decision engine
- Implement `events.ts`, `decide.ts`, `ledgerV2.ts`.
- Migrate `ReviewSession` to call `decide()`.
- Add human-gated MCP write tool.
- **At this point A&A matches Relay on auditability and governance.**

### Phase 5 — Formal verification + counterfactual + load benchmark
- Add live invariant endpoint, optional Z3 proof.
- Add counterfactual simulator.
- Add load benchmark.
- **At this point A&A is the engineering benchmark of the track.**

---

## 5. How this beats Consensus and Arbiter head-to-head

| Dimension | Consensus | Arbiter | New A&A (after plan) |
|---|---|---|---|
| **Eval size** | 58 cases | ~40 cases across modes | 120+ cases |
| **Adversarial depth** | 9 patterns | 12 cases | 20 patterns + non-vacuity tests |
| **Citation verification** | Permalink-in-set | Prompt-based fact-check | Deterministic snippet grounding (NFKC + trigram) |
| **Multi-agent verification** | Single judge | Heterogeneous debate | Heterogeneous debate + deterministic gate |
| **Knowledge/claim graph** | Flat decision ledger | Neo4j claim graph | Evidence graph with contradiction/supersedes edges |
| **Question matching** | Hand-tuned | Hand-tuned | Conformal prediction with coverage guarantee |
| **Ledger auditability** | Hash-chain, edit-sync | Audit log | Event-sourced + metadata-stamped hash chain + external anchor |
| **Agent write safety** | N/A (read-only paths) | Human-gated via prompts | Human-gated via event-sourced state machine |
| **Formal assurance** | None | None | Property tests + live invariant check + optional Z3 proof |
| **Impact measurement** | None explicit | Workslop benchmarks | Counterfactual simulator + load benchmark |

---

## 6. Rubric self-score after full implementation

| Criterion | Current | After plan |
|---|---|---|
| **Technological Implementation** | 8.5/10 | 10/10 |
| **Design** | 6/10 | 8/10 (Data Table/App Home/Canvas absorbable) |
| **Potential Impact** | 6.5/10 | 9/10 (counterfactual + real quote) |
| **Quality of Idea** | 7/10 | 9/10 (formally assured compliance memory) |
| **Weighted total** | **~28/40** | **~36/40** |

---

## 7. Why this works without breaking existing code

- All new modules implement existing interfaces (`DraftingLlm`, `VisibilityChecker`, ledger append/verify shape).
- `pipeline.ts` gets a few new function calls inserted, not rewritten.
- `AnswerLibrary` can use `ConformalMatcher` behind a feature flag.
- `Ledger` v2 can wrap v1 or coexist during migration.
- `app.ts` keeps current listeners; new endpoints (`/invariant`, MCP v2) are additive.

---

## 8. Final honest take

This plan is **not** a 6-hour fix. It is a post-hackathon engineering roadmap to make Asked & Answered the undisputed engineering winner.

If you execute **Phases 0–2** before the deadline, you close the gap with Consensus and Arbiter enough to fight for the track win.  
If you execute the **full plan**, you build something that is technically deeper than anything visible in the public field.
