# Kept — Forensic Review

Repo: https://github.com/kaviyakumar23/kept (cloned to `research-tmp/kept` for review).

## 1. Core engineering thesis

Kept is a Slack-native, event-sourced **obligation ledger** for shared customer channels: the LLM only *proposes* typed commands, while a pure, I/O-free `decide()` engine plus an explicit guarded finite-state machine enforce two mandatory human gates and proof-of-done reconciliation before any event is appended or any customer-facing message is sent.

## 2. Exact file paths and line numbers

### command → decide → event store
- **`src/app/orchestrator.ts:155-257`** — `ingestMessage()` turns a Slack message into a `DetectInput`, resolves RTS context, and dispatches through the engine seam.
- **`src/engine/obligationService.ts:155-182`** — `dispatch()` is the single seam: read log → `decide()` → compare-and-append → re-project, with optimistic-concurrency retry loop.
- **`src/engine/commandHandler.ts:78-142`** — `decide()` is the pure decision core: envelope validation → idempotency → evidence/leak consistency checks → zero-copy scan → reconciliation gate → `canApply()`.
- **`src/store/eventStore.ts:33-46`** — the `EventStore.append()` contract with `expectedVersion` and the zero-copy/append-only guarantees.
- **`src/domain/projection.ts:23-156`** — pure fold from event log to current `Obligation`, including derived flags (`is_overdue`, `is_at_risk`, `is_disputed`).

### Two human gates
- **`src/domain/stateMachine.ts:26-45`** — `TRANSITIONS` table encodes every event type with `from`, `to`, `requiresApproval`, `requiresEvidence`, `changesState`.
- **`src/domain/stateMachine.ts:70-113`** — `canApply()` rejects missing `approved_by` (`APPROVAL_REQUIRED`) and missing evidence (`INSUFFICIENT_EVIDENCE`).
- **`src/policy/actionTiers.ts:16-34`** — action-tier map mirrors the FSM so adapters know which commands require human confirmation.
- **`src/app/orchestrator.ts:307-340`** — Gate 1 (`confirmCommitment`): human approval is dispatched and persisted *before* any work-item create; the per-obligation lock serializes create+link.
- **`src/app/orchestrator.ts:515-532`** — Gate 2 (`verify()`): re-gathers proof at verify time, then dispatches `VERIFY_FULFILLMENT`.

### Deterministic MCP client
- **`src/integrations/mcp.ts:92-140`** — `McpWorkItemAdapter.createIssue()`: code resolves the tool name by heuristic over `listTools()` and calls it with computed args; the LLM never selects the tool.
- **`src/integrations/mcp.ts:171-202`** — `createSimulatedMcpWorkItems()` exercises a real in-process MCP client↔server round-trip in tests/demo.
- **`src/integrations/mcp.ts:220-264`** — `McpProofClient`: read-only deterministic MCP surface used for feature-flag / CI / issue-status proof reads.

### Adversarial hardening
- **`tests/hardening.test.ts:44-109`** — G2 forged/mislabeled evidence and G4 command-path leak rejection.
- **`tests/hardening.test.ts:203-249`** — second-round findings: Unicode-dash obfuscation, dotted/spaced PR references, zero-copy value-channel newline/oversized detection.
- **`tests/mcpHardening.test.ts:41-69`** — Round-6: retry self-heals after a transient MCP work-item failure; no orphaned confirmed obligation.
- **`tests/mcpHardening.test.ts:71-101`** — Round-6: length/depth caps on MCP result parsing prevent ReDoS and stack overflow.
- **`tests/round7.test.ts:26-58`** — Round-7: Assistant/analytics surfaces bounded (no `Math.max(...spread)` crash), escaped attacker-controlled fields, capped block lists.
- **`tests/concurrency.test.ts:27-91`** — optimistic concurrency: `ConcurrencyError`, dispatch retry, exactly-once same-key dispatch.
- **`tests/adversaryRound8.test.ts:9-15`** — `requireTeam` fails closed on malformed Slack payloads.

### Integration tests
- **`vitest.integration.config.ts:8`** — runs `tests/integration/**/*.test.ts` against real Postgres/Redis; each suite `skipIf(!env)` so `npm test` stays hermetic.
- **`tests/integration/postgres.integration.test.ts:11-92`** — full lifecycle persisted in Postgres, reconnect replay, race-safe compare-and-append, zero-copy rejection.
- **`tests/integration/bullmq.integration.test.ts:8-40`** — live Redis/BullMQ scheduling + idempotent re-schedule.
- **`tests/integration/oauthPlatform.integration.test.ts:11-91`** — real Postgres-backed installation store and scheduler.
- **`tests/integration/roadmapPostgres.integration.test.ts:8-30`** — live Postgres roadmap source.

### Eval harness / report
- **`src/eval/runner.ts:73-340`** — deterministic lifecycle/safety scenario battery: happy path, duplicate suppression, semantic dedupe, reopen, false-closure matrix, forged evidence, unauthorized actions, leakage, reminders, due-date supersession.
- **`src/eval/report.ts:124-130`** — generates `docs/eval-report.md` with per-class precision/recall/F1 and confusion matrix.
- **`docs/eval-report.md`** — published result: 96% signal accuracy, 0.97 macro-F1, 100% duplicate suppression, 0 false closures, 0% leakage, 0 unauthorized actions.

## 3. Patterns Asked & Answered should absorb

| Kept pattern | Why it matters | Suggested A&A file |
|---|---|---|
| **Explicit guarded FSM table** (`TRANSITIONS` + `canApply`) | Every state change is auditable and impossible to bypass with a prompt. | `src/core/stateMachine.ts` |
| **Pure `decide(events, command)`** | No I/O means exhaustive, replayable unit tests for every guard. | Extend `src/core/decide.ts` |
| **Event-sourced projection** | Current state is a derived fold; audit history is free. | `src/core/projection.ts` + `src/store/eventStore.ts` |
| **Multi-source reconciliation with sufficiency lanes** | Explicit rules for when evidence is enough, not LLM vibe. | `src/core/reconciliation.ts` |
| **Deterministic MCP client (code picks tool)** | Satisfies MCP requirement without giving the model controls. | `src/integrations/mcpClient.ts` |
| **Idempotency keys everywhere** | Duplicate Slack events/webhooks are no-ops, not double side effects. | `src/core/idempotency.ts` |
| **Audience-safe output + leak scanner** | Customer-facing text is checked before it leaves. | `src/core/audience.ts` |
| **Zero-copy persistence guard** | No raw Slack bodies / prompts / model outputs hit the durable log. | `src/core/zeroCopy.ts` |
| **Optimistic concurrency / per-entity locks** | Racing button clicks or retries mint exactly one side effect. | `src/store/concurrency.ts` |
| **Adversarial regression rounds** | Findings become permanent tests; safety improves over time. | `tests/adversarialRounds.test.ts` |
| **Independent eval harness** | Reproducible metrics separate from the test suite. | `evals/runner.ts` + `evals/report.ts` |

## 4. Concrete weaknesses A&A can exploit

- **Small classification corpus and modest offline baseline.** `docs/eval-report.md` reports live OpenAI numbers (96% accuracy on 52 messages), but `npm run eval` with the offline heuristic shows only **64% commitment-class accuracy** and **0.69 macro-F1** (`src/eval/runner.ts:421-448`). A&A’s `evals/run.ts` already runs 120 cases with 100% deterministic fail-closed/injection/citation/stale metrics.
- **No formal invariant proof.** Kept’s safety is tested, not verified. A&A ships `scripts/verifyInvariantZ3.ts` and a property-test suite that intentionally fails when the visibility guard is disabled (`src/core/invariant.ts`).
- **Shallow entity resolution.** `src/engine/entityGraph.ts:27-52` matches exact cross-system refs or (`customer` + `subject_canonical`). It has no embedding/semantic similarity, so vague or paraphrased obligations create duplicates or miss matches.
- **Regex-based leak detector is knowingly bypassable.** `src/policy/audience.ts:30-44` and the comment at lines 15-18 admit a determined insider can spell a ref in prose; the backstop is human approval. A&A’s permission-first model (no answer text unless *every* citation is currently visible to the requester) is structurally stronger.
- **High human-friction ceiling.** Every commitment and every closure requires a human click. That is the thesis, but it caps throughput. A&A can stress auto-verified reuse (already-approved answers returned without human gate) as a scale advantage.
- **No stale-evidence contradiction graph.** Kept reconciles positive/negative signals but has nothing like A&A’s `EvidenceGraph` (`src/core/evidenceGraph.ts`) that downgrades an approved answer when newer evidence contradicts it.
- **No compound answer reuse library.** Kept’s ledger is per-obligation. A&A’s `AnswerLibrary` + `ConformalMatcher` compound across questionnaires; Kept cannot reuse prior prose automatically.
- **Integration tests are env-gated and unbenchmarked.** The integration suite `skipIf(!DATABASE_URL)` (`tests/integration/postgres.integration.test.ts:11`); there is no load test or counterfactual impact script, while A&A has `scripts/runLoadBenchmark.ts` and `scripts/runCounterfactual.ts`.
- **MCP result parsing is heuristic.** `src/integrations/mcp.ts:47-90` uses bounded regex and depth-capped `pickString`; schema drift from hosted Linear/Atlassian/Jira MCP servers could break issue linking in production.
- **No prompt-injection hardening in the classifier path.** Kept relies on forced tool-use + Zod (`src/llm/anthropic.ts`) but does not appear to test jailbreak/homoglyph/delimiter-break attacks against `proposeFromMessage`. A&A’s `src/core/sanitize.ts` and eval dataset explicitly plant these attacks.

## 5. Rubric scores

| Dimension | Score | Justification |
|---|---|---|
| **Tech** | 9/10 | Deterministic event-sourced engine, pure `decide()`, guarded FSM, deterministic MCP client, real in-process MCP round-trips, 317 hermetic tests + live Postgres/Redis integration suite, optimistic concurrency, zero-copy guard. Deduction: no formal invariant, heuristic MCP parsing, small classification corpus, no load/scale benchmarks. |
| **Design** | 9/10 | Clean 4-layer architecture with a strict LLM-proposes/code-decides seam; tenant isolation as a first-class invariant; audience policy and leak detection; Gate-before-side-effect ordering. Deduction: regex leak scanner is admitted defense-in-depth, and the classification path is not hardened against prompt injection. |
| **Impact** | 7/10 | Solves a real and painful failure mode (false "done" in customer channels), with a polished Slack-native UX and a trust page. The surface is compelling for CS/AM workflows, but the scope is narrow: only shared customer-channel obligations, every closure needs a human, and adoption depends on connecting several external systems to shine. |
| **Idea** | 7/10 | Bidirectional promise tracking and proof-of-done reconciliation are a clear improvement over inbound-only ticketing (Pylon/Thena), but the core concept exists and the innovation is mostly in the *execution* (deterministic engine + adversarial hardening) rather than a wholly new problem formulation. |

**Overall:** Kept is the strongest engineering execution in the customer-obligation space — the architecture is principled and the adversarial regression test discipline is exactly what judges reward. A&A beats it on *scope of reuse*, *formal permission invariant*, and *scale through verified automation*; Kept beats A&A on *tight lifecycle control* and *polished Slack-native closure UX*.
