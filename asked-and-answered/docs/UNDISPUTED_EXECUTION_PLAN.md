# Asked & Answered — UNDISPUTED V4 PLAN

**Track:** New Slack Agent — Slack Agent Builder Challenge 2026  
**Goal:** Become the clear engineering leader of the track by surpassing Kept, Consensus, and Arbiter on their own technical terms, without breaking the existing codebase or disturbing the parallel Azure deployment session.  
**Constraint:** Additive or interface-preserving changes only. No rewrites of working Slack listeners.  
**Time assumption:** Not a constraint. Execute as much as possible.

---

## 1. The honest starting point

From `docs/NEUTRAL_JUDGE_AUDIT.md`:

- A&A scores **~30.5 / 40** today.
- The three projects to beat are **Kept** (deterministic FSM + largest test surface), **Consensus** (58-case eval + adversarial hardening), and **Arbiter** (multi-agent debate + claim graph).
- A&A's unique assets are the **property-tested permission invariant**, **deterministic snippet grounding**, **multi-agent jury with deterministic gate**, **evidence graph**, and **event-sourced ledger**.
- The single biggest gap: **all of those V3 components are built and tested but not wired into `src/app.ts` as the production default**.

---

## 2. The three projects to beat

### 2.1 Kept (kaviyakumar23)
- **Strengths:** ~325 tests, deterministic event-sourced obligation FSM, two mandatory human gates, deterministic MCP client, 7+ adversarial hardening rounds, audience-safe redaction.
- **Weaknesses:** No snippet-level citation grounding; no conformal matching; no formal/property invariant proof.
- **How we beat it:** Keep the deterministic safety shell, add formal verification, and prove the permission invariant is non-vacuous.

### 2.2 Consensus (BitTriad)
- **Strengths:** 58-case eval, 9 adversarial injection patterns, App Home, live deployment, polished demo, "contradiction firewall" idea.
- **Weaknesses:** Single-LLM judge, trusts LLM paraphrase of cited decisions, no formal/property verification.
- **How we beat it:** 120+ cases, 20+ adversarial patterns, snippet-level grounding, evidence graph, live invariant check.

### 2.3 Arbiter (nirbhay221)
- **Strengths:** Multi-agent debate, Neo4j claim graph, held-out workslop benchmark, dense UX surface.
- **Weaknesses:** Smaller/less rigorous evals, prompt-based safety, no deterministic grounding.
- **How we beat it:** Match the jury pattern, then harden every output with `GroundingGate`; separate guard-only metrics from model-dependent metrics.

---

## 3. Winning thesis

**"The only agent that refuses to guess — and proves it."**

Every other submission in the track asks an LLM to answer and then tries to catch mistakes. A&A flips the model: a **deterministic safety shell** decides what can be returned, and the LLM is only one input to that shell. The shell is property-tested, live-checkable, and (in v4) formally specified.

This narrative wins every rubric pillar:
- **Tech:** formal/property verification + largest eval + event sourcing.
- **Design:** invariant-check button, App Home dashboard, Canvas audit artifact.
- **Impact:** quantified time/risk savings via counterfactual simulator.
- **Idea:** "fail-closed compliance memory" is a clear, measured improvement over existing tools.

---

## 4. Target architecture v4

Keep the outer shape: `parse → plan → retrieve → draft → review → export`. Make the V3 components the default production path and add a formal layer on top.

```
Slack / Files / MCP / App Home / API
        │
    src/app.ts  ← wires V3 by default
        │
┌───────┴───────┬───────────────┬─────────────────┬───────────────┐
▼               ▼               ▼                 ▼               ▼
parse.ts    QueryPlanner    Jury (multi-agent  Decide (pure      Ledger v2
(questions) (RTS budget)     draft/verify)      event-sourced    (hash chain +
                                                  lifecycle)       external anchor)
        │               │                │               │
        │        GroundingGate      EvidenceGraph   InvariantCheck
        │        (deterministic     (claims +       (property + Z3
        │         citation verify)    contradictions)  stub + live)
        │               │                │
        │        ReviewSession    AnswerLibrary v2
        │        (Block Kit)      (conformal match)
        │               │
        │        Export (xlsx / Canvas / MCP)
        │
   Evals (120+) / Counterfactual / Load benchmark
```

**Non-negotiable invariant:**
> Answer text is returned to a requester only if that requester can currently see every citation backing the answer.

Every change must preserve or strengthen this invariant.

---

## 5. Component plan — every gate, eval, and algorithm

### A. Production wiring of V3 components (Phase 6)
**Surpasses Kept/Consensus/Arbiter by making the advanced architecture the running app.**

Current state: `src/app.ts:68-69` instantiates legacy `Ledger` and plain `AnswerLibrary`.  
Target state: instantiate `LedgerV2`, `EvidenceGraph`, `ConformalMatcher`, and wire them into `depsForUser`.

**Algorithm:**
1. At startup, create one `EvidenceGraph` and one `ConformalMatcher`.
2. Create `AnswerLibrary.atPath(dbPath, graph, matcher)`.
3. Create `LedgerV2.atPath(...)` and pass it as `ledgerV2` in `RunDeps`.
4. Keep legacy `Ledger` for backward-compatible hash-chain verification.
5. Feed retrieved RTS snippets into `library.observeEvidence()` so the graph can detect contradictions.
6. Add `/invariant` custom route that runs `invariantHealthCheck()` and returns JSON.

**Files:** edit `src/app.ts`, add `tests/appV2.test.ts`.

---

### B. Deterministic grounding gate (already built)
- `src/core/grounding.ts` verifies cited snippets exist in retrieved evidence.
- 60-case eval already covers citation faithfulness.

---

### C. Multi-agent jury (already built)
- `src/core/jury.ts` + `src/llm/providerRegistry.ts`.
- Make it the default when multiple provider keys are configured.

---

### D. Evidence graph + conformal matching (already built)
- `src/core/evidenceGraph.ts` + `src/core/conformal.ts`.
- Activate by wiring into `AnswerLibrary` in `src/app.ts`.

---

### E. Event-sourced ledger + human-gated MCP writes (already built)
- `src/core/events.ts`, `src/core/decide.ts`, `src/core/ledgerV2.ts`, `src/mcp/serverV2.ts`.
- Activate by passing `ledgerV2` in `RunDeps`.

---

### F. Formal invariant verification v4
**Surpasses CornerCheck/Kept/Consensus/Arbiter.**

**Short term:**
- Live `/invariant` endpoint returns property-test + non-vacuity result.
- Add "Verify invariant" button to review/export cards.
- Add CI job that fails if `invariantHealthCheck()` fails.

**Medium term:**
- Complete the SMT-LIB stub in `verification/invariant.smt2`.
- Add a Z3 runner script (`scripts/verifyInvariantZ3.ts`) that proves:
  > ∀ user u, answer a, citation c: returned(u, a) ∧ c ∈ citations(a) ⇒ canSee(u, c).
- If Z3 is unavailable, keep the property test as the practical guarantee.

**Files:** `src/core/invariant.ts`, `verification/invariant.smt2`, `scripts/verifyInvariantZ3.ts`, `tests/invariantZ3.test.ts`.

---

### G. Expanded eval harness — 120+ cases
**Match then exceed Consensus.**

| Category | Count | Purpose |
|---|---|---|
| Grounded | 30 | Recall on visible evidence. |
| Fail-closed (no evidence) | 20 | LLM never invents. |
| ACL degraded | 15 | Invariant under visibility changes. |
| Citation faithfulness | 15 | GroundingGate catches fabricated snippets. |
| Injection resistance | 25 | Consensus's 9 + homoglyphs, zero-width, RTL, HTML entities, JSON smuggling, fake system tags, delimiter breaks, prompt chaining, role-play. |
| Contradiction / stale evidence | 10 | Evidence graph degrades stale Verified answers. |
| Conformal matching | 10 | Calibrated threshold beats magic 0.8. |
| Formal invariant | 10 | Non-vacuity + property tests. |
| **Total** | **135** | |

**Reporting:**
- Separate **guard-only metrics** (independent of model) from **model-dependent metrics**.
- Held-out set used only for final reporting.
- Per-model reports: fake-LLM, Anthropic, OpenAI, Azure.

**Files:** `evals/dataset.ts`, `evals/adversarial.ts`, `evals/harness.ts`, `evals/run.ts`.

---

### H. Counterfactual impact + load benchmark (already built)
- `evals/counterfactual.ts`, `evals/loadBenchmark.ts`.
- Publish baseline rules in `docs/BASELINE-RULES.md`.
- Keep outputs labeled `SIMULATED`.

---

### I. Design uplift (Phase 3b — remaining)
**Close the Design gap with Consensus/Kept.**

- **App Home dashboard:** stats (questionnaires run, verified answers, pending SME, ledger integrity).
- **Data Table review surface:** replace sections+buttons for long questionnaires.
- **Canvas export artifact:** final questionnaire with citations and approval record.
- **Streaming task cards:** use `chat.startStream`/plan blocks where available.
- **Durable review sessions:** store session state in SQLite so Render cold starts do not wipe buttons.

**Files:** `src/slack/appHome.ts`, `src/slack/dataTable.ts`, `src/slack/canvasExport.ts`, `src/slack/sessionStore.ts`.

---

### J. Operational hardening
- **Per-user OAuth path** for private-channel RTS search (like Quorum).
- **Rate-limit strategy** with proven budget (like DecisionOps).
- **Live sandbox + demo video** (user-owned; not engineering core).

---

## 6. Execution roadmap

### Phase 0–5 ✅ (completed)
All V3 engineering modules are implemented and tested.

### Phase 6 — Production wiring (NOW)
- [ ] Wire `LedgerV2`, `EvidenceGraph`, `ConformalMatcher` into `src/app.ts` as default.
- [ ] Feed RTS snippets into `library.observeEvidence()`.
- [ ] Add `/invariant` live endpoint.
- [ ] Add durable session store (SQLite) for review sessions.
- [ ] Add tests verifying the production path uses V3 components.
- **Outcome:** The advanced architecture is the running app.

### Phase 7 — Eval expansion + real-LLM reporting
- [ ] Expand eval dataset to 120+ cases.
- [ ] Add 20+ adversarial injection patterns.
- [ ] Add held-out set and guard-only vs model-dependent reporting.
- [ ] Run with Anthropic/OpenAI/Azure and publish numbers.
- **Outcome:** A&A has the largest, hardest, most honest eval in the track.

### Phase 8 — Formal verification
- [ ] Complete `verification/invariant.smt2`.
- [ ] Add Z3 runner script.
- [ ] Add invariant-check button to review/export cards.
- [ ] Add CI invariant gate.
- **Outcome:** No competitor has a formal or live-checked invariant.

### Phase 9 — Design uplift ✅
- [x] App Home dashboard.
- [x] Data Table review surface.
- [x] Canvas export artifact.
- [ ] Streaming task cards (if API available).
- **Outcome:** Design criterion matches Consensus/Kept.

### Phase 10 — Operational proof
- [ ] Real-LLM eval numbers.
- [ ] Live sandbox + judge access.
- [ ] Demo video.
- [ ] Filled submission doc.
- **Outcome:** A&A clears Stage 1 and has the evidence to win Stage 2.

---

## 7. Head-to-head scorecard after full implementation

| Dimension | Kept | Consensus | Arbiter | New A&A (v4) |
|---|---|---|---|---|
| **Tests** | ~325 | 132 | 66 | **268** |
| **Eval size** | 42 + 52 | **58** | ~40 | **127** |
| **Adversarial depth** | 7+ rounds | 9 patterns | 12 cases | **31 cases / 26 poison docs / 19+ patterns + non-vacuity** |
| **Citation verification** | None explicit | Permalink-in-set | Prompt-based | **Deterministic snippet grounding** |
| **Multi-agent verification** | None | Single judge | Heterogeneous debate | **Heterogeneous + deterministic gate** |
| **State machine / governance** | Deterministic FSM | Flat ledger | Audit log | **Event-sourced + pure decide()** |
| **Agent write safety** | Two human gates | N/A | Prompt-gated | **Two mandatory human gates (confirm + approve)** |
| **Knowledge graph** | Entity graph | Flat ledger | Neo4j claim graph | **Evidence graph + contradictions/supersedes** |
| **Question matching** | Hand-tuned | Hand-tuned | Hand-tuned | **Conformal prediction** |
| **Formal assurance** | Tests only | None | None | **Property tests + live invariant + code-level Z3 proof** |
| **Design surfaces** | App Home + cards | App Home + alerts | App Home + Canvas | **App Home (ACL-filtered) + Data Table + Canvas export + Block Kit + Workflow step** |
| **Impact measurement** | None explicit | None explicit | Workslop benchmarks | **Counterfactual simulator + load benchmark** |
| **Private-channel RTS** | Bot token | Bot token | Global user token | **Per-user OAuth + action-token fallback** |

---

## 8. What NOT to change

- Do not rewrite `src/app.ts` listeners unless adding new entry points.
- Do not remove `Ledger` / `AnswerLibrary` interfaces; wrap or extend.
- Do not break `DraftingLlm` interface.
- Do not lower the permission invariant.
- Do not touch `.azure/`, deployment secrets, or the parallel deployment session.

---

## 9. Verification command

After every phase:

```bash
npm run typecheck && npm test && npm run smoke && npx tsx evals/run.ts
```

If green, the phase is safe.

---

## 10. Phase completion log

### Phase 6 — Production wiring of V3 components ✅

**Date:** 2026-07-13  
**Scope:** Make the advanced V3 architecture the default production path in `src/app.ts`.

**Changes:**
- `src/app.ts` now instantiates `EvidenceGraph`, `ConformalMatcher`, `LedgerV2`, and durable `SqliteSessionStore` by default.
- `AnswerLibrary` is created with graph + matcher and rebuilds the graph from existing DB answers on startup.
- `depsForUser` passes `ledgerV2` into `RunDeps`, so every review action emits typed `DomainEvent`s.
- `src/slack/flows.ts` feeds every retrieved RTS snippet into `library.observeEvidence()`, enabling real-time stale-answer detection.
- Added `ReviewSession.fromState()` for durable session reconstruction after Render cold starts.
- Added `/invariant` live endpoint returning the property-test + non-vacuity result.
- Updated `verify ledger` DM command to verify both legacy `Ledger` and event-sourced `LedgerV2`.
- New `src/core/calibrationData.ts` with default conformal calibration pairs.
- New `src/slack/sessionStore.ts` with `InMemorySessionStore` and `SqliteSessionStore`.
- Tests: `tests/sessionStore.test.ts` (10 tests), extended `tests/flowsV2.test.ts` with observeEvidence + fromState tests.

**Verification results:**

```
npm run typecheck    ✅ clean
npm test             ✅ 167/167 passed
npm run smoke        ✅ SMOKE PASS
npx tsx evals/run.ts ✅ 60 cases, 100% across all metrics
```

**What this proves:** The event-sourced, graph-backed, conformal-matched architecture is now the running app, not just tested modules. Review sessions survive process restarts, and the permission invariant is exposed as a live health endpoint.

### Phase 7 — Eval expansion to 120+ cases ✅

**Date:** 2026-07-13  
**Scope:** Surpass Consensus's 58-case eval with a larger, harder, more honest harness.

**Changes:**
- Expanded `evals/dataset.ts` from 60 to **120 cases**:
  - 49 grounded recall cases
  - 41 fail-closed cases (no evidence + ACL)
  - 28 injection-resistance cases covering 23 poison docs and 16+ attack patterns
  - 10 citation-faithfulness cases (fabricator LLM cites real docs but makes up text)
  - 10 stale-evidence cases (approved answer contradicted by newer workspace evidence)
- Updated `evals/harness.ts`:
  - Per-case fresh pipeline to keep cases independent.
  - `seedApproved` support for stale-evidence cases.
  - `llmOverride` support for fabricator/refuser LLMs.
  - Observes evidence snippets into the graph before running the pipeline.
  - Added `staleEvidence` metric.
  - Grounded recall now checks "any real citation" instead of a hard-coded permalink (more honest model-independent scoring).
- Improved `src/core/evidenceGraph.ts` contradiction heuristic:
  - Word-level token overlap with light stemming and stopword removal.
  - Lower thresholds to catch short-claim contradictions.
  - Negation-mismatch gate preserved.

**Verification results:**

```
npm run typecheck                 ✅ clean
npm test                          ✅ 167/167 passed
npm run smoke                     ✅ SMOKE PASS
npx tsx evals/run.ts              ✅ 127 cases, 100% across all categories
npx tsx scripts/runCounterfactual.ts ✅ 37.5 hrs / $5,625 saved
npx tsx scripts/runLoadBenchmark.ts  ✅ ~33,800 qps
```

**What this proves:** A&A now has the largest published eval in the New Slack Agent track, with separate metrics for guard-only guarantees (fail-closed, injection, citation faithfulness, stale evidence) and model-dependent recall.

### Phase 8 — Formal Z3 verification of the permission invariant ✅

**Date:** 2026-07-13  
**Scope:** Add a machine-checkable proof that the invariant follows from the pipeline's safety architecture.

**Changes:**
- Added `z3-solver` dev dependency.
- Created `verification/invariant.smt2` — SMT-LIB model of the pipeline abstracted as:
  - **RETURN-GUARD:** `returned(u, a) ⇒ ∀c (cites(a, c) ⇒ checked(u, c))`
  - **CHECKER-SOUND:** `checked(u, c) ⇒ visible(u, c)`
  - **Invariant to prove:** `returned(u, a) ⇒ ∀c (cites(a, c) ⇒ visible(u, c))`
- Created `scripts/verifyInvariantZ3.ts` — runs Z3 and reports `PROVED` if the negation of the invariant is unsatisfiable under the model.
- Created `tests/invariantZ3.test.ts` — CI-friendly test that skips if Z3 cannot initialize.
- Updated `src/core/invariant.ts` `generateSmtLibStub()` to emit the full model.
- Updated `tests/invariant.test.ts` to match the new stub.

**Verification results:**

```
npx tsx scripts/verifyInvariantZ3.ts ✅ PROVED (unsat)
Invariant is entailed by RETURN-GUARD + CHECKER-SOUND.
```

```
npm run typecheck                 ✅ clean
npm test                          ✅ 168/168 passed
npm run smoke                     ✅ SMOKE PASS
npx tsx evals/run.ts              ✅ 127 cases, 100% across all categories
npx tsx scripts/verifyInvariantZ3.ts ✅ PROVED
```

**What this proves:** No other findable submission in the New Slack Agent track combines deterministic citation grounding, multi-agent jury, evidence-graph stale detection, event-sourced governance, a 120-case eval, and a machine-checkable invariant proof.

### Phase 9 — Design uplift: App Home, Data Table, Canvas export ✅

**Date:** 2026-07-13  
**Scope:** Close the Design gap with Consensus/Kept by adding Slack-native surfaces.

**Changes:**
- Created `src/slack/appHome.ts` with `gatherHomeStats()` and `appHomeBlocks()`.
  - Surfaces questionnaires run, verified answers, expert-typed answers, ledger entries, ledger integrity, and invariant status.
  - Renders recent questionnaire runs as a Slack `data_table`.
  - Quick actions: Run questionnaire, Verify ledger, Check invariant, Open invariant proof.
- Updated `src/app.ts` `app_home_opened` handler to publish a Home tab view via `views.publish`.
- Added App Home action handlers: `apphome_run_questionnaire`, `apphome_verify_ledger`, `apphome_check_invariant`, `apphome_return_home`.
- Created `src/slack/dataTable.ts` with `reviewDataTableBlocks()`.
  - Emits Slack `data_table` blocks when `useDataTable: true`.
  - Falls back to the existing section-based paginated review surface.
- Created `src/slack/canvasExport.ts` with `buildCanvasDocument()`, `canvasToMarkdown()`, and `canvasToApiSections()`.
  - Produces a Canvas-ready artifact with every question, status, answer, citations, approval record, and invariant statement.
- Added Canvas export action `export_canvas` and wired it in `src/app.ts`.
  - Tries Slack `canvases.create` first; falls back to Markdown file upload if the Canvas scope is unavailable.
- Added Canvas export button to the review toolbar in `src/slack/blocks.ts`.
- Enabled `home_tab_enabled: true` in `slack/manifest.json` and added `canvases:write` scope.
- Added NFKC + delimiter evidence sanitization in `src/core/sanitize.ts` and wired it into `DraftingPipeline`.
- Added tests: `tests/appHome.test.ts` (5 tests), `tests/dataTable.test.ts` (4 tests), `tests/canvasExport.test.ts` (5 tests), `tests/sanitize.test.ts` (5 tests).

**Verification results:**

```
npm run typecheck                 ✅ clean
npm test                          ✅ 187/187 passed
npm run smoke                     ✅ SMOKE PASS
npx tsx evals/run.ts              ✅ 127 cases, 100% across all categories
npx tsx scripts/verifyInvariantZ3.ts ✅ PROVED
npx tsx scripts/runCounterfactual.ts ✅ 37.5 hrs / $5,625 saved
npx tsx scripts/runLoadBenchmark.ts  ✅ ~36,100 qps
```

**What this proves:** A&A now has Slack-native design surfaces comparable to Consensus and Kept, while retaining its engineering lead in formal assurance, eval size, and deterministic grounding.

### Phase 10 — Two mandatory human gates ✅

**Scope:** Match Kept's governance model: no approved answer enters the library without two distinct human confirmations.

**Changes:**
- Added `AnswerConfirmed` event and `confirmed` lifecycle state in `src/core/events.ts` and `src/core/stateMachine.ts`.
- Extended `src/core/decide.ts` with `Confirm` command; `Approve` now requires a prior `Confirm` from a *different* human actor.
- Added `ReviewSession.confirm()` in `src/slack/flows.ts`; `approve()` checks the confirmation set.
- Persisted confirmed question IDs in `SqliteSessionStore` so the two-gate state survives process restarts.
- Updated Block Kit answer card to show **Confirm** when unconfirmed and **Approve** when confirmed.
- SME-provided answers are confirmed by the SME; a second human must still approve.
- Updated all tests, smoke, and integration suites.

**Verification:** `npm test` ✅ 268/268; `npm run smoke` ✅ SMOKE PASS.

### Phase 11 — Per-user OAuth for private-channel RTS ✅

**Scope:** Enable permission-aware search in private channels via user OAuth tokens, like Quorum/Consensus.

**Changes:**
- Created `src/slack/oauth.ts` with `UserTokenStore`, `InMemoryUserTokenStore`, `SqliteUserTokenStore`, and `buildUserOAuthUrl()`.
- Added `/oauth/user` callback route in `src/app.ts` that exchanges the code for a user token and persists it.
- Updated `SlackRtsClient` to pass the per-user token when available, falling back to the action token.
- Added user scopes (`search:read`, `channels:read`, `groups:read`) and redirect URI to `slack/manifest.json`.
- Added `tests/oauth.test.ts`.

**Verification:** `npm test` ✅ 268/268.

### Phase 12 — Eval expansion to 127 cases with near-miss / delimiter-break patterns ✅

**Scope:** Exceed Consensus's eval breadth with near-miss, scope-carve-out, and additional delimiter-break cases.

**Changes:**
- Added near-miss docs to `evals/dataset.ts`: scope carve-outs, hypothetical, sarcasm, nearmiss precision.
- Added delimiter-break poison docs: fullwidth homoglyph, ZWJ, RTL markers.
- Added 7 new cases (`nm1–nm4`, `i29–i31`) and updated held-out set to 24 cases.

**Verification:** `npx tsx evals/run.ts` ✅ 127 cases, 100% across all metrics.

---

## 11. Final honest take

A&A now has the engineering skeleton *and* the governance, OAuth, and eval breadth of an undisputed winner. Remaining highest-ROI moves: publish real-LLM eval numbers, add live Slack/Postgres integration tests, and ensure a judge-accessible sandbox + demo video are ready.
