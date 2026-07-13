# Forensic Review: Consensus (BitTriad)

Source: `https://github.com/BitTriad/consensus-slack-agent` (cloned to `consensus-analysis/`).

## 1. Core Engineering Thesis

Consensus is an ambient, LLM-driven organizational-memory layer that captures team decisions from ordinary Slack messages, stores them in a durable lifecycle-aware ledger, and uses a scope-aware contradiction judge hardened against prompt injection to warn authors before they contradict prior decisions, while enforcing channel-membership privacy fail-closed on every alert and dashboard view.

## 2. Most Impressive Technical Implementations

| Feature | File | Lines | Why it matters |
|---|---|---|---|
| **Eval dataset** | `consensus-core/eval/dataset.js` | 11–589 | 58 hand-labeled cases: clear contradictions, near-misses (scope, sarcasm, hypotheticals, negation), ambiguous-but-decidable cases, and 9 adversarial prompt-injection attempts including fullwidth/RTL/ZWJ/HTML-entity delimiter breaks. Used by `npm run eval`. |
| **NFKC normalization** | `consensus-core/judge.js` | 27–35 (esp. 31) | `wrapUntrusted` calls `.normalize('NFKC')` before escaping, folding fullwidth homoglyphs (e.g. `＜` → `<`) so ASCII-only delimiter escapes cannot be bypassed. Repeated in `consensus-core/audit.js` 105–113. |
| **Delimiter wrapping** | `consensus-core/judge.js` | 8–35 | `UNTRUSTED_GUARD` system instruction plus `wrapUntrusted` escapes both `</untrusted` and `<untrusted` sequences after NFKC, preventing breakout and forged nested wrappers. Used for every message, decision, and RTS context fed to the judge. |
| **Membership gate** | `consensus-core/permissions.js` | 39–95 | `getMembers` pages `conversations.members` up to 6,000 members, caches for 5 min, and **fails closed** (API error → empty set → redact). `canSeeDecision` short-circuits public channels; private-channel decisions are redacted per viewer. |
| **App Home** | `listeners/events/app-home-opened.js` | 20–56 | Fetches 50 decisions, filters via `canSeeDecision` *before* trimming to 15, then renders `homeView` from `consensus-core/blocks.js` 265–378 with live stats, audit CTA, and permission-filtered decision log. |
| **Contradiction firewall** | `consensus-core/pipeline.js` | 521–775 | `handleChannelMessage` → `runPipeline`: keyword-gated multi-decision capture, daily per-author cap, rate guard, per-channel queue, then contradiction judge against enforceable decisions from *other* threads, with ephemeral alert or redacted notice. |
| **Scope-aware judge** | `consensus-core/judge.js` | 242–332 | `judgeContradiction` system prompt explicitly trains scope discipline (same subject + incompatible position + overlapping scope), negation handling, superseded decisions, and reopens; JSON verdict is extracted defensively with one retry and a safe default on parse failure. |
| **Two-stage audit** | `consensus-core/audit.js` | 18–345 | Stage A: one LLM scan proposes latent conflict pairs from up to 60 decisions. Stage B: each pair is verified by the same measured `judgeContradiction` in both directions, confirming only if confidence ≥ 0.8. Dismissed pairs are remembered. |
| **Edit/delete sync** | `consensus-core/pipeline.js` | 777–1002 | `handleMessageEdited` re-classifies edited text and reconciles kept/retired/added decisions by normalized statement; `handleMessageDeleted` retires all decisions captured from a deleted message. |
| **Multi-backend ledger** | `consensus-core/ledger.js` | 154–895 | Identical interface over MongoDB (production), `node:sqlite` (CI/local), or JSON fallback; includes migrations, dedup indexes, per-user dismissal memory, and event log. |

## 3. Patterns Asked & Answered Should Absorb

A&A already credits Consensus in `src/core/sanitize.ts`. To beat Consensus, A&A should copy the *operational* patterns below, mapped to A&A filenames:

1. **Comprehensive hand-labeled eval with adversarial delimiter cases**
   - *Pattern:* Expand `evals/dataset.ts` beyond the current 120 cases to include near-misses, scope carve-outs, negation, and Unicode/HTML-entity/ZWJ delimiter-break attacks—exactly as Consensus does in `consensus-core/eval/dataset.js`.
   - *Target file:* `evals/dataset.ts`

2. **NFKC + bidirectional delimiter escaping**
   - *Pattern:* A&A’s `sanitizeEvidenceSnippet` only escapes `</evidence>`. Adopt Consensus’s pattern of escaping **both** opening and closing untrusted-tag sequences after NFKC normalization.
   - *Target file:* `src/core/sanitize.ts`

3. **Per-user dismissal / false-positive memory with durable normalization**
   - *Pattern:* When a user marks an answer as wrong, store the normalized question/answer text keyed by user + answer so the same user is not re-alerted. Consensus uses `normalize()` + `recordDismissal()` in `consensus-core/ledger.js` 127–134 and 392–402.
   - *Target file:* `src/core/library.ts` (add `recordDismissal`/`isKnownFalsePositive`) or new `src/core/dismissals.ts`

4. **Two-stage contradiction audit of the approved-answer library**
   - *Pattern:* A&A could scan approved answers for latent conflicts (e.g. two approved answers giving contradictory answers to the same control). Use Consensus’s Stage-A candidate generator + Stage-B measured verifier in `consensus-core/audit.js`.
   - *Target file:* new `src/core/audit.ts`

5. **Lifecycle governance with trusted-channel and authority-user env gates**
   - *Pattern:* Capture status depends on channel trust, and lifecycle transitions require authority. Consensus implements this in `consensus-core/governance.js` 37–116. A&A could mark SME-provided answers as `proposed` until an authority confirms.
   - *Target file:* new `src/core/governance.ts`, integrate in `src/slack/flows.ts`

6. **Per-channel serialization + rate guard for intake**
   - *Pattern:* Consensus queues one pipeline run per channel and drops bursts beyond a cap (`pipeline.js` 237–297, 106–157). A&A’s DM intake currently has no equivalent backpressure; add sliding-window rate limits per user and global.
   - *Target file:* `src/slack/flows.ts` or new `src/core/rateGuard.ts`

7. **Permission-filtered App Home rows**
   - *Pattern:* Consensus fetches a wide window and filters by `canSeeDecision` before rendering (`listeners/events/app-home-opened.js` 42–49). A&A’s `appHomeBlocks` shows the most recent answers without re-checking visibility; adopt the same fetch-wide-then-filter pattern.
   - *Target file:* `src/slack/appHome.ts`

8. **Edit/delete sync for source evidence**
   - *Pattern:* If a cited Slack message is edited or deleted, Consensus reconciles the ledger (`pipeline.js` 777–1002). A&A could detect stale citations and downgrade previously approved answers.
   - *Target file:* new `src/core/ledgerSync.ts`, integrate with `src/core/ledgerV2.ts`

## 4. Concrete Weaknesses A&A Can Exploit

1. **Governance defaults are wide open.** Unless `CONSENSUS_GOVERNANCE_STRICT=1` is set, every channel is trusted and every user can confirm decisions (`consensus-core/governance.js` 60–65, 77–96, 109–116). This is a dangerous production default. A&A should contrast its fail-closed invariant with Consensus’s demo-friendly fail-open defaults.

2. **Exception narrowing is a stub.** `narrowsScope()` always returns `false` (`consensus-core/governance.js` 188–193), meaning Consensus cannot honestly model legitimate carve-outs. A&A can highlight its own grounded, evidence-scoped answers as more precise.

3. **Capture is keyword-gated, hurting recall.** `isDecisionAdjacent()` only runs the LLM classifier if the stripped message contains one of ~50 decision keywords (`consensus-core/pipeline.js` 397–461, 542). Decisions stated without those keywords are silently missed. A&A can claim better recall on implicit answers.

4. **Ambient RTS is off by default and bot-token path is expected to fail.** `CONSENSUS_RTS=1` is required (`consensus-core/pipeline.js` 712–718), and the bot token lacks search scopes (`consensus-core/rts.js` 17–26). A&A already uses per-user action tokens for permission-aware RTS—use that as a differentiator.

5. **Dismissal memory is exact-prefix only.** `normalize()` strips punctuation and lowercases but does not understand paraphrase (`consensus-core/ledger.js` 127–134, 395–401). A user who rephrases a previously dismissed contradiction will be re-alerted. A&A can advertise semantic dismissal memory (embeddings).

6. **Alert suppression is in-memory only.** `alertedToday` and `recordAlerted` live in process memory (`consensus-core/pipeline.js` 188–235), so a restart loses daily suppression state. A&A should persist reviewer feedback in its SQLite library.

7. **Capture cap is trivially evaded.** `MAX_CAPTURES_PER_USER_PER_DAY` is per-author (`consensus-core/pipeline.js` 78–93); a small set of users can still flood the ledger. A&A can point to its hash-chained, tamper-evident approval ledger as abuse-resistant.

8. **Last audit summary is in-memory.** `lastAudit` is a module-level variable (`consensus-core/audit.js` 57–73), lost on restart. A&A’s `LedgerV2` already persists event-sourced state; an audit log would survive restarts.

9. **Local Claude path ignores temperature.** `claudeComplete` does not pass `temperature` (`consensus-core/llm.js` 80–98), making the audit scan non-deterministic on local dev. A&A’s provider registry can enforce deterministic sampling.

10. **Leftover starter-template code.** `listeners/views/app-home-builder.js` is the generic Bolt starter App Home, not the real Consensus view. It suggests the project still carries template scaffolding that a polished submission would remove.

## 5. Rubric Scores

| Dimension | Score | Justification |
|---|---|---|
| **Tech** | 8.5 / 10 | Excellent: measured eval (58 cases, 9 injections), multi-backend ledger, NFKC+delimiter prompt hardening, fail-closed membership gate, rate guards, per-channel queues, edit/delete sync, two-stage audit, multi-provider LLM. Deductions for wide-open governance defaults, exception-model stub, keyword-gated capture, in-memory alert state, and ignored temperature on local path. |
| **Design** | 8 / 10 | Strong UX: ephemeral contradiction alerts with reasoning/dismiss/supersede actions, permission-filtered App Home, lifecycle badges, audit report. Deductions for leftover starter-template files, no built admin dashboard, and defaults that favor demo over production safety. |
| **Impact** | 8 / 10 | High practical value for any organization tired of repeating decisions. The contradiction firewall is a genuinely useful ambient behavior. Deductions because real enterprise rollout still depends on roadmap items (one-click install, admin dashboard, member-tenure gating) that are documented but not built. |
| **Idea** | 7 / 10 | “Ambient consistency layer / contradiction firewall” is a clear, defensible concept, but decision capture and policy monitoring are not new. The novelty is in the Slack-native ambient implementation and the measured judge. |

**Overall:** Consensus is the most technically complete competitor in the track. A&A can beat it by matching its eval rigor and delimiter hardening, then contrasting A&A’s fail-closed defaults, persistent ledger, permission-aware RTS, and semantic dismissal memory against Consensus’s demo-friendly defaults and unimplemented governance stubs.
