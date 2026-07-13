# Asked & Answered — UNDISPUTED WINNER Findings & Engineering Plan

**Competition:** Slack Agent Builder Challenge 2026  
**Track:** New Slack Agent  
**Audited project:** `theCodeForgerHQ/asked-and-answered`  
**Research date:** 2026-07-13  
**Research scope:** Every findable public GitHub submission in the New Slack Agent track, plus cross-track engineering leaders.

---

## 1. Executive summary — the honest verdict

Asked & Answered is **not** currently the undisputed winner of the New Slack Agent track. It is a **strong podium contender** with one genuinely unique asset: a property-tested, deterministic fail-closed permission invariant. The two projects most likely to beat it are **Consensus** and **Arbiter**, and they win on a combination of **eval rigor, architectural ambition, and demo completeness** — not merely reliability.

The good news: every gap is closable without breaking the existing codebase. The bad news: closing them all is a multi-day engineering sprint, not a 6-hour polish pass.

**This document contains:**
- The exact official rubric and prize structure.
- A validated pass/fail audit of the current codebase.
- A head-to-head review of **every findable New Slack Agent submission**.
- Concrete reasons Consensus and Arbiter score higher.
- A modular engineering plan to surpass both at their own games.

---

## 2. Official rubric and prize reality

Source: [Slack Agent Builder Challenge Official Rules](https://slackhack.devpost.com/rules) and [Devpost prize updates](https://slackhack.devpost.com/updates).

### 2.1 Stage 1 — pass/fail gate

Before any creative scoring, a submission must:

| Requirement | Consequence if missing |
|---|---|
| Select a track | Disqualification |
| Working demo video < 3 min, publicly hosted | Stage 1 loss |
| Architecture diagram | Stage 1 loss |
| Slack sandbox URL with `slackhack@salesforce.com` and `testing@devpost.com` as members | Stage 1 loss |
| App installed and functioning consistently with the video | Stage 1 loss |
| Use at least one of: Slack AI capabilities, MCP server integration, Real-Time Search API | Disqualification |

### 2.2 Stage 2 — scored rubric (equally weighted)

| Criterion (25% each) | What it really rewards |
|---|---|
| **Technological Implementation** | Quality software development; load-bearing use of required techs; tests; error handling; architecture legibility; reproducibility. |
| **Design** | Slack-native UX; balanced frontend/backend; Block Kit interactivity; App Home; loading/empty states. |
| **Potential Impact** | Quantified, nameable-user story; Slack-community first, beyond-Slack second. |
| **Quality of the Idea** | Creative **or** a clear, measured improvement on an existing concept. The rubric explicitly rewards improvement, not just novelty. |

**Tie-break order:** **Tech → Design → Impact → Idea.** Engineering depth is the first tie-breaker.

### 2.3 Prizes — there is NO third-place cash prize

| Prize | New Slack Agent Track | Cash |
|---|---|---|
| **1st Place** | 1 winner | **$8,000 USD** + Slack cert voucher + Dreamforce 2026 pass + swag + features |
| **2nd Place** | 1 winner | **$4,000 USD** + features |
| **Achievement Prizes** | 3 winners across all tracks | **$2,000 USD** each for Best UX, Best Technological Implementation, Most Innovative Slack Agent |

**Critical point:** There is no "3rd place" ranking prize. If A&A does not win 1st or 2nd, the only remaining cash path is an Achievement Prize ($2,000). A submission that places "third" by score but is not selected for an Achievement Prize wins **$0 cash**.

**Can you be "sure" you come third?** No. The public field is large, judging is discretionary, and many submissions (Consensus, Arbiter, Kept, Compass, Council, DecisionOps, ThreadWork, etc.) have strong claims. You can hope for a high placement, but "sure third" is not a meaningful guarantee.

**Can you go down?** Yes. If the live sandbox, video, or eval numbers are missing or broken, Stage 1 failure is possible, which puts you below every submission that clears Stage 1 regardless of code quality.

---

## 3. Current Asked & Answered — validation and gaps

### 3.1 What passes right now (verified by actual runs)

| Check | Command | Result |
|---|---|---|
| TypeScript | `npm run typecheck` | ✅ clean |
| Unit tests | `npm test` | ✅ **91/91 passed** |
| Eval harness (fake LLM) | `npx tsx evals/run.ts` | ✅ 100% on deterministic guarantees |
| Offline smoke | `npm run smoke` | ✅ `SMOKE PASS` |

### 3.2 The crown jewel: a real invariant

A&A enforces and property-tests this invariant:

> **Answer text is returned to a requester only if that requester can currently see every citation backing the answer.**

This is enforced in `src/core/library.ts` (ACL revalidation), `src/core/pipeline.ts` (citation-subset guard + re-check), and `tests/flows.test.ts` / property tests. **No competitor has a property-tested permission invariant of this kind.** It is a legitimate engineering differentiator.

### 3.3 Where it fails against a real judge

| Gap | Location | Why it loses points |
|---|---|---|
| **No live sandbox / deployment / video** | whole project | Stage 1 trap. Judges cannot score what they cannot run. |
| **RTS integration unverified live** | `src/app.ts`, `src/slack/rts.ts` | `action_token` harvesting and private-channel search may not work as written. |
| **Sessions are in-memory only** | `src/app.ts` | Render free-tier spin-down wipes review sessions; buttons silently no-op after cold start. |
| **No App Home / Data Table / Canvas** | `slack/manifest.json`, `src/slack/blocks.ts` | Design criterion is weak compared to competitors. |
| **No real-LLM eval numbers** | `docs/EVALS.md`, `docs/SUBMISSION.md` | 100% is from a fake LLM. Judges value measured real-model performance. |
| **Small eval set** | `evals/dataset.ts` | 15 cases vs. Consensus's 58. |
| **Question matching uses magic threshold** | `src/core/library.ts:53` | `TOKEN_OVERLAP_THRESHOLD = 0.8` is uncalibrated. |
| **No snippet-level citation grounding** | `src/core/pipeline.ts:119-124` | Checks permalink subset, not whether the LLM's cited snippet actually exists in evidence. |
| **MCP server is read-only** | `src/mcp/server.ts` | Less impressive than human-gated write tools. |
| **No counterfactual impact measurement** | — | "Saves SME time" is unquantified. |
| **Submission placeholders unfilled** | `docs/SUBMISSION.md` | `[X]%`, `[URL]`, `[REAL HUMAN QUOTE]` brackets remain. |

### 3.4 Rubric self-score as it stands today

| Criterion | Score | Why |
|---|---|---|
| **Technological Implementation** | 8/10 | Load-bearing use of all three sponsor techs; strong invariant; 91 tests; eval harness; CI. Dinged for unverified live Slack path and small eval. |
| **Design** | 6/10 | Block Kit fallback table works but is basic. No App Home, Data Table, Canvas, or streaming task cards. |
| **Potential Impact** | 6/10 | Narrow, relatable workflow. No real user quote or measured time-saved number. |
| **Quality of Idea** | 7/10 | Clear concept. Not novel — competitors also do "org memory from Slack" — but the fail-closed compliance angle is a credible differentiator. |
| **Estimated total** | **~27/40** | Good enough to be in the conversation; not a runaway winner. |

---

## 4. Every findable New Slack Agent submission — reviewed

The following table summarizes the **publicly discoverable** GitHub submissions that self-identify as New Slack Agent track entries. The analysis is based on raw repo inspection, READMEs, source trees, test files, and eval harnesses.

| Project | Track | Tests | Eval | Required Slack techs live | Engineering thesis | Verdict vs. A&A |
|---|---|---|---|---|---|---|
| **[Consensus](https://github.com/BitTriad/consensus-slack-agent)** | New Slack Agent | ~153 | **58 cases**, P 1.000 / R 0.964, 9/9 adversarial | AI ✅ MCP ✅ RTS ✅ | Decision ledger + contradiction firewall; permission-aware surfacing; App Home dashboard | **Direct rival.** More eval cases, live app, App Home, polished demo. Weaker deterministic verification and single-LLM judge. |
| **[Arbiter](https://github.com/nirbhay221/arbiter)** | New Slack Agent | 66 | Fact-check 10/10, workslop 20/20 + 9/10 held-out, routing 91% | AI ✅ MCP ✅ RTS ✅ | Multi-agent debate across heterogeneous providers; Neo4j claim graph; substance scoring; prediction ledger | **Direct rival.** More algorithmically ambitious; broader verdict surface. Smaller, less rigorous evals; contradictory metric claims. |
| **[Kept](https://github.com/kaviyakumar23/kept)** | Organizations (not your track, but learn from) | **317** | 42 lifecycle/safety checks, classification 96% live | AI ✅ MCP ✅ RTS ✅ | Event-sourced obligation ledger; Proof-of-Done reconciliation; deterministic MCP client; human-gated FSM | **Engineering ceiling in the whole competition.** Pure decision core, tenant isolation, concurrency control. A&A should absorb its event-sourcing and human-gating patterns. |
| **[Slack Compass](https://github.com/nag-gude/slack-compass)** | New Slack Agent | 35 | None | AI ✅ RTS ✅ MCP ❌ | Autonomous org-intelligence: missing stakeholders, stale decisions, contradictions; App Home; Compass Cards | Strong UX and proactive monitoring. No MCP, no eval, in-memory graph. A&A beats it on tests and invariant. |
| **[Council for Slack](https://github.com/alex-jb/council-for-slack-2026)** | New Slack Agent | **0** | 4 manual case studies | MCP ✅ AI ❌ RTS ❌ | 5-persona LLM council + Brier calibration audit; Canvas log; Workflow Builder step | Strong design/idea narrative. Zero automated tests, no RTS. A&A is far ahead on engineering evidence. |
| **[DecisionOps](https://github.com/rdxsai/decisionops)** | New Slack Agent | 66 | 5 logic-layer checks (no retrieval quality metrics) | RTS ✅ AI ❌ MCP ❌ | Incremental Slack-native memory; delta-scoped RTS; metadata-as-DB; Canvas briefs | Tight memory thesis but no MCP and no eval metrics. A&A has more complete required-tech surface. |
| **[Flightrec](https://github.com/kitfunso/flightrec-slack)** | New Slack Agent | 26 | None | MCP ✅ AI ❌ RTS ❌ | Privileged-action agent with tamper-evident black-box audit log | Strong security architecture, but only 1/3 required Slack techs and no eval. |
| **[Sales Copy Concierge](https://github.com/takumimorimoto-yakumo/slack-agent-builder-challenge)** | New Slack Agent | 54 | None | MCP ✅ AI ❌ RTS ❌ | Human-in-the-loop sales copy approval with verbatim + trigram citation grounding | Excellent deterministic grounding gate that A&A should absorb. Missing AI/RTS. |
| **[ThreadWork](https://github.com/ShreyanshVaibhaw/threadwork)** | New Slack Agent | unknown | unknown | unknown | Thread-to-work-post extraction with supervised agent run | Not deep-analyzed; likely mid-field. |
| **[Devil's Advocate](https://github.com/run58669-maker/devils-advocate)** | New Slack Agent | unknown | unknown | unknown | MCP-sourced red-teaming of premature consensus | Not deep-analyzed; idea play. |
| **[Tribal Knowledge Agent](https://github.com/divergent99/tribal-knowledge-agent)** | New Slack Agent | unknown | unknown | unknown | Workspace search + cited answers + conflict detection | Similar space to A&A; not deep-analyzed. |
| **[Spyglass](https://github.com/abhaysingh1122/spyglass)** | New Slack Agent | unknown | unknown | unknown | Competitor-intelligence agent | Not deep-analyzed. |
| **[Gateway](https://github.com/subheeksh5599/gateway)** | New Slack Agent | unknown | unknown | unknown | MCP-powered tool bridge + Next.js dashboard | Not deep-analyzed. |
| **[Pulse (tarunagarwal1981)](https://github.com/tarunagarwal1981/pulse-slack-agent)** | New Slack Agent | unknown | unknown | unknown | Cited market-intelligence briefings via MCP | Not deep-analyzed. |
| **[Prospector](https://github.com/Deepak-Sangle/prospector)** | New Slack Agent | unknown | unknown | unknown | Social listening / lead gen agent | Not deep-analyzed. |
| **[TelecomAI](https://github.com/Steven3-art/telecomai-slack-agent)** | New Slack Agent | unknown | unknown | unknown | Telecom FTTH diagnostics | Not deep-analyzed. |
| **[HireHive](https://github.com/sanskriti45-tech/hirehive-slack-agent)** | New Slack Agent | unknown | unknown | unknown | Recruitment agent | Not deep-analyzed. |
| **[SlackOps Agent](https://github.com/AppZ3/slackops-agent)** | New Slack Agent | unknown | unknown | unknown | DevOps incident response | Not deep-analyzed. |
| **[Slack-Ops (maniginam)](https://github.com/maniginam/slack-ops-agent)** | New Slack Agent | unknown | unknown | unknown | Portfolio / crypto ops agent | Not deep-analyzed. |

### Cross-track engineering leaders (worth absorbing from)

| Project | Track | Tests | Why it matters |
|---|---|---|---|
| **[CornerCheck](https://github.com/StephenSook/cornercheck)** | Agent for Good | **256** (+ Z3 proof) | The engineering ceiling: formal verification, conformal prediction, Data Table, Canvas, Workflow step. |
| **[Relay-Crisis](https://github.com/indrapranesh/relay-crisis)** | Agent for Good | Vitest suite | Event-sourced ledger, human-gated MCP writes, counterfactual impact simulator, load benchmark. |
| **[Lore (drMurlly)](https://github.com/drMurlly/lore-slack-agent)** | Agent for Good | 191 | Knowledge graph, Canvas reports, MCP glossary. |

---

## 5. Why Consensus and Arbiter score higher — not just reliability

### 5.1 Consensus

| Rubric pillar | Why it scores higher than A&A |
|---|---|
| **Tech Implementation** | 58-case eval including 9 adversarial injection patterns; three-backend ledger (Mongo/SQLite/JSON); rate/queue/abuse controls; membership cache; dual-model stack. |
| **Design** | Ambient capture → ephemeral contradiction alert → App Home dashboard → audit report. Feels like a complete product. |
| **Potential Impact** | "Decision memory" is a universal team pain; quantified consistency and policy drift. |
| **Quality of Idea** | The "contradiction firewall" framing is novel and instantly legible. |

**Key insight:** Consensus wins on **Idea novelty** and **eval/safety breadth**, not just uptime. A&A's "security questionnaire filler" is a clearer workflow but a less surprising idea.

### 5.2 Arbiter

| Rubric pillar | Why it scores higher than A&A |
|---|---|
| **Tech Implementation** | Multi-agent debate across heterogeneous LLM families; held-out workslop benchmark; router F1 metric; Neo4j claim graph; prediction ledger. |
| **Design** | Seven entry points (`@Arbiter`, `/verdict`, Assistant pane, message shortcut, watched channels, multimodal). Dense but coherent. |
| **Potential Impact** | Anchored to measurable wastes: 40% of workers receive polished-but-hollow AI content, ~2 hours wasted per incident. |
| **Quality of Idea** | "Judgment layer" / "workslop detector" / "missing voices" are fresh framings. |

**Key insight:** Arbiter wins on **algorithmic sophistication** and **architectural ambition**. It looks like research engineering.

### 5.3 Where Asked & Answered still beats both

- **Property-tested invariant** (200-run fast-check): neither Consensus nor Arbiter has this.
- **Deterministic fail-closed pipeline** with citation-subset guard: stronger than their heuristic/prompt-based safety.
- **Strict TypeScript + clean architecture**: easier to defend as quality software development.
- **Hash-chained tamper-evident ledger**: a concrete demo theater piece.

**Your gap is not reliability. It is perceived novelty, eval size, and architectural ambition.**

---

## 6. Can A&A get a better architecture now that everything is built?

Yes. The existing architecture is already clean enough to extend modularly. The key is to keep the **permission invariant as the crown jewel** and build around it with four superior layers:

1. **Deterministic grounding** (surpass Consensus on citation safety).
2. **Multi-agent verification** (match Arbiter, then harden with deterministic gate).
3. **Evidence graph + conformal matching** (match CornerCheck's rigor where it fits A&A).
4. **Event-sourced governance** (match Relay / Kept on auditability and human-gated writes).

None of these require rewriting `app.ts`, breaking the Slack listeners, or changing the core `parse → plan → retrieve → draft → review → export` shape.

---

## 7. The plan: how Asked & Answered beats Consensus and Arbiter at their own games

### 7.1 Superiority thesis

- **Match Consensus** on eval size and adversarial depth — then exceed it with formal/property verification.
- **Match Arbiter** on multi-agent verification and substance scoring — then harden it with deterministic citation grounding.
- **Match CornerCheck** on formal assurance — prove the invariant is non-vacuous and expose it as a live product feature.
- **Match Relay / Kept** on auditability and agent governance — make the ledger event-sourced and MCP writes human-gated.

Result: a submission that is **measurably, verifiably, and demonstrably safer and more rigorous** than the current leaders.

### 7.2 Target architecture v3

Keep the existing outer shape. Add a **deterministic safety shell** around the LLM and a **provenance graph** under the approved library.

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

### 7.3 Component plan

#### A. Deterministic grounding gate (surpass Consensus)

**Current A&A:** checks that a cited permalink is in the retrieved set.  
**Consensus:** checks that a cited decision/message exists, but trusts the LLM's statement about it.  
**New A&A:** verifies that the LLM's cited *snippet* actually appears in the retrieved evidence.

**Algorithm:**
1. Normalize LLM answer + evidence with NFKC.
2. For each citation, locate the source RTS hit by permalink.
3. Check exact substring match after lowercasing/punctuation stripping.
4. If exact fails, compute character-trigram Jaccard similarity.
5. Require `similarity >= 0.85` for a citation to pass.
6. Any failing citation → `needs_sme` with reason `invalid_citations`.

**Files:**
- New: `src/core/grounding.ts`
- Edit: `src/core/pipeline.ts` to call `GroundingGate.verify()` after LLM draft.
- Tests: `tests/grounding.test.ts` with adversarial fabricated snippets.

#### B. Multi-agent jury for drafting and verification (match + harden Arbiter)

**Arbiter's pattern:** Skeptic → Advocate → Analyst → Contrarian → Synthesizer.  
**New A&A:** Apply the same pattern to security-questionnaire drafting.

**Roles:**
- **Drafter** — produces answer text + cited permalinks from evidence.
- **Critic** — checks each claim against evidence; flags unsupported statements.
- **Citer** — verifies citations are from the evidence set and relevant.
- **Synthesizer** — reconciles into final `LlmDraft`.

**Hardening beyond Arbiter:**
- Run `GroundingGate` after the panel, so even a consensus hallucination is caught deterministically.
- Run the panel with heterogeneous providers (Anthropic + OpenAI + Azure) when keys are available.
- Add self-consistency voting: if panel splits, run synthesizer 3× and take majority verdict.
- Add cost/quality telemetry.

**Files:**
- New: `src/core/jury.ts`, `src/llm/providerRegistry.ts`
- Edit: `src/llm/index.ts` to create `JuryDrafter`.
- Tests: `tests/jury.test.ts`.

#### C. Evidence graph + contradiction detection (surpass Consensus)

**Consensus:** flat decision ledger; checks new messages for contradiction.  
**New A&A:** build a graph of **claims** extracted from evidence and approved answers, with typed edges.

**Schema:**
```ts
interface EvidenceNode { id: string; kind: 'evidence'; permalink; snippet; channelId; ts; }
interface ClaimNode { id: string; kind: 'claim'; text; source: EvidenceNode | AnswerNode; }
interface AnswerNode { id: string; kind: 'answer'; questionText; answerText; citations; }
interface Edge { from; to; kind: 'SUPPORTS' | 'CONTRADICTS' | 'SUPERSEDES'; }
```

**Capabilities:**
- Before reusing a Verified answer, check if newer evidence contradicts any supporting claim. If yes, degrade to `needs_sme` with reason `stale_evidence`.
- Surface contradictions in retrieved evidence to the user.

**Files:**
- New: `src/core/evidenceGraph.ts`
- Edit: `src/core/library.ts` to query graph on Verified reuse.
- Tests: `tests/evidenceGraph.test.ts`.

#### D. Conformal question matching (surpass hand-tuned thresholds)

**Current A&A:** Jaccard token overlap with magic threshold `0.8`.  
**New A&A:** calibrate the threshold with split-conformal prediction.

**Algorithm:**
1. Build calibration set of question pairs labeled same/different.
2. Compute nonconformity score using token-Jaccard + embedding cosine.
3. Compute `q_hat = ceil((n+1)(1-α))`-th quantile.
4. Return Verified only if top match score ≤ `q_hat` and prediction set is a singleton.

**Files:**
- New: `src/core/conformal.ts`, `scripts/calibrateMatching.ts`
- Edit: `src/core/library.ts` to use `ConformalMatcher` behind a flag.

#### E. Event-sourced ledger + pure decision engine (match Relay / Kept)

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

**Files:**
- New: `src/core/events.ts`, `src/core/decide.ts`, `src/core/ledgerV2.ts`
- Edit: `src/slack/flows.ts` to call `decide()`; keep `ReviewSession` as UI state only.

#### F. Ledger v2: tamper-evidence beyond chain hash (match CornerCheck)

**Improvements:**
1. Store `_meta: { actor, action, ts }` inside the hashed JSON payload.
2. On `verify()`, recompute hashes and cross-check stored columns against `_meta`.
3. Add external anchor: post chain head to a public Slack channel or `/api/invariant` endpoint daily.
4. Add non-vacuity tests: corrupt a single guard and assert verification fails.

**Files:**
- New: `src/core/ledgerV2.ts`
- Edit: `src/core/ledger.ts` can wrap or be replaced behind the same interface.
- Tests: `tests/ledgerV2.test.ts` with mutation tests.

#### G. Formal invariant verification (surpass everyone)

**Short term:**
- Add non-vacuity regression tests: monkeypatch `VisibilityChecker.canSee` to always return true and assert the property test fails.
- Add live `/invariant` endpoint that reruns the property test on a synthetic corpus.
- Add an "Invariant check" button on the review/export card.

**Long term:**
- Encode the invariant in Z3/SMT-LIB.
- Prove that the pipeline code refines the spec.
- Surface the proof in CI and product.

**Files:**
- New: `src/core/invariant.ts`, `tests/invariant.test.ts`
- Optional: `verification/invariant.smt2`

#### H. Expanded eval harness (match then exceed Consensus)

| Category | Count |
|---|---|
| Grounded | 30 |
| Fail-closed (no evidence) | 20 |
| ACL degraded | 15 |
| Citation faithfulness | 15 |
| Injection resistance | 20 (Consensus's 9 + role-play, JSON smuggling, fake system tags, delimiter breaks, prompt chaining) |
| Contradiction / stale evidence | 10 |
| Conformal matching | 10 |
| **Total** | **120+** |

**Reporting:**
- Report **guard-only metrics** separately from **model-dependent metrics**.
- Add held-out set used only for final reporting.
- Add local/hermetic load benchmark.

**Files:**
- New: `evals/adversarial.ts`, `evals/counterfactual.ts`, `evals/loadBenchmark.ts`
- Edit: `evals/dataset.ts`, `evals/harness.ts`, `evals/run.ts`

#### I. Human-gated MCP writes (match Relay / Kept)

**Design:**
- `propose_answer(questionText, answerText, citations?)` → files an `AnswerProposed` event with `actor: 'agent'`.
- The answer appears in Slack as a pending proposal card with **Approve / Edit / Reject**.
- `decide()` rejects any agent-originated `AnswerApproved` event unless it came through the human UI.
- Tool is disabled unless `AA_MCP_WRITES_ENABLED=1`.

**Files:**
- New: `src/mcp/serverV2.ts`
- Edit: `src/core/decide.ts` to enforce human gate.

#### J. Counterfactual impact simulator (match Relay)

**New A&A:**
1. Define baseline model: manual questionnaire process = ticket per question, SME response time, uncited answer probability, inconsistent-answer probability.
2. Run the same questionnaire corpus through A&A's hermetic pipeline.
3. Compute delta: SME hours saved, citation coverage, inconsistent answers avoided.
4. Label clearly as `SIMULATED`; publish baseline rules.

**Files:**
- New: `evals/counterfactual.ts`, `docs/BASELINE-RULES.md`

---

## 8. Implementation roadmap (modular, no breakage)

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
- **At this point A&A matches Relay / Kept on auditability and governance.**

### Phase 5 — Formal verification + counterfactual + load benchmark
- Add live invariant endpoint, optional Z3 proof.
- Add counterfactual simulator.
- Add load benchmark.
- **At this point A&A is the engineering benchmark of the track.**

---

## 9. Head-to-head scorecard after full implementation

| Dimension | Consensus | Arbiter | New A&A (after plan) |
|---|---|---|---|
| **Eval size** | 58 cases | ~40 cases across modes | **120+ cases** |
| **Adversarial depth** | 9 patterns | 12 cases | **20 patterns + non-vacuity tests** |
| **Citation verification** | Permalink-in-set | Prompt-based fact-check | **Deterministic snippet grounding** |
| **Multi-agent verification** | Single judge | Heterogeneous debate | **Heterogeneous debate + deterministic gate** |
| **Knowledge/claim graph** | Flat decision ledger | Neo4j claim graph | **Evidence graph with contradiction/supersedes edges** |
| **Question matching** | Hand-tuned | Hand-tuned | **Conformal prediction** |
| **Ledger auditability** | Hash-chain, edit-sync | Audit log | **Event-sourced + metadata-stamped + external anchor** |
| **Agent write safety** | N/A | Human-gated via prompts | **Human-gated via event-sourced state machine** |
| **Formal assurance** | None | None | **Property tests + live invariant + optional Z3** |
| **Impact measurement** | None explicit | Workslop benchmarks | **Counterfactual simulator + load benchmark** |

---

## 10. What to do before the deadline vs. after

If any time remains before 2026-07-13 5:00 PM PT:

1. **Submit something that clears Stage 1.** Video + sandbox + judge access are non-negotiable.
2. **Run real-LLM evals** and fill the numbers in `docs/SUBMISSION.md`.
3. **Record the demo** with the fail-closed refusal as the emotional peak.
4. **If you have 2+ hours left**, implement `GroundingGate` and add 10 adversarial eval cases. This is the single highest-ROI engineering upgrade.

After the deadline, execute Phases 0–5 of this plan to make Asked & Answered the undisputed engineering winner of the track, regardless of the current competition outcome.

---

## 11. Final honest take

Asked & Answered is one of the most **principled** engineering submissions in the field. Its permission invariant is real, its code is clean, and its fail-closed design is defensible. But principled engineering is not the same as **demonstrable, measured, polished** engineering.

To become undisputed:
- **Match Consensus on eval rigor and breadth.**
- **Match Arbiter on architectural ambition and multi-agent verification.**
- **Surpass everyone on deterministic safety, formal assurance, and auditability.**
- **Anchor Impact with a real human story and honest simulated numbers.**

The path is clear. The code is already good enough to support it. The only remaining question is execution.
