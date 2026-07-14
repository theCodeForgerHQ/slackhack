# Competitor Swarm Findings — Slack Agent Builder Challenge 2026

**Date:** 2026-07-14  
**Track:** New Slack Agent (with cross-track threats noted)  
**Baseline:** Asked & Answered (`asked-and-answered/`)  
**Sources:** GitHub code search, `gh` CLI inspection, raw README/package/manifest review, and public web search across the Devpost/Slack hackathon ecosystem.  
**Method:** Seven parallel explore agents searched distinct angles; this doc synthesizes the verified results.

---

## 1. Executive Summary

The Agent Swarm found **~71 public repositories** mentioning the Slack Agent Builder Challenge 2026. Of those, **~25 are substantive submissions** with readable READMEs, runnable code, and real engineering evidence. The rest are scaffolds, empty placeholders, or thin single-feature demos.

**Asked & Answered remains the engineering-rigor leader of the New Slack Agent track.** No competitor matches the combination of:
- 268 automated tests
- 127-case labeled eval with 24 held-out cases
- 127/127 pass on Azure `gpt-54-mini`
- Code-level Z3 contract proof + runtime invariant verification
- Deterministic snippet-level `GroundingGate`
- Hash-chained event-sourced ledger

However, the margin is narrow and the field is broader than the five named competitors in the existing docs. The most dangerous rivals beat A&A on **Design, Idea novelty, adversarial hardening, formal verification, or social-impact narrative** — not on total feature count.

### Highest-leverage threats

| Rank | Submission | Track | Why it threatens A&A | Primary rubric edge |
|---|---|---|---|---|
| 1 | **Council for Slack** | New | Zero tests, but best demo/UX/idea novelty and Brier calibration loop | Design, Idea |
| 2 | **Consensus** | New | 58-case eval + 9 adversarial injection patterns + ambient UX | Tech (eval/hardening), Design |
| 3 | **Kept** | New | 140+ tests, deterministic FSM, deterministic MCP client, 7 adversarial rounds | Tech (lifecycle), Design |
| 4 | **CornerCheck** | Agent for Good | Z3 safety proof + conformal prediction + 252 tests + live dashboard | Tech (formal methods), Impact |
| 5 | **Gavel** | Agent for Good | 927 tests, live Fly.io deploy, real civic data, bilingual output | Tech (tests/deploy), Impact |
| 6 | **Lore** | Agent for Good | Multi-hop KG, 191 tests, cited Canvas research reports | Idea, Design |
| 7 | **Quorum** | New | Vercel DurableAgent for 7-day approval hooks, clean decision provenance | Design, Idea |
| 8 | **Arbiter** | New | Multi-agent debate council, claim graph, workslop scoring | Idea, Design |
| 9 | **Aegis** | New | N-of-M approvals, policy engine, TTL escalation | Design, Tech |
| 10 | **Déjà** | New | 83-query adversarial governance benchmark, ambient contradiction | Tech (eval), Idea |

---

## 2. New Slack Agent Track — Verified Competitors

### 2.1 Council for Slack
- **Repo:** https://github.com/alex-jb/council-for-slack-2026
- **Thesis:** Multi-persona "second-opinion ritual" — 5 domain-typed voices deliberate, an Oracle adjudicates, and Brier scores audit calibration when reality resolves.
- **Stack:** Next.js 16 + Bolt JS on Vercel, Supabase SECURITY DEFINER RPCs, Anthropic Sonnet 4.6, `council-diff` npm package, MCP server.
- **Surfaces:** `/council` slash command, message shortcut, channel Canvas decision log, Workflow Builder custom step, multi-workspace OAuth, Brier audit.
- **Better than A&A:**
  - Most memorable and differentiated idea in the track.
  - Polished landing page + multi-workspace OAuth + case studies.
  - Brier calibration loop is a credible long-term trust mechanism.
- **Absorbable into A&A (no regressions):**
  - Add Brier/calibration scoring for SME approvals.
  - Add a Canvas decision/approval log for security-control approvals.
  - Use multi-persona review for contested questionnaire answers.
  - Mirror approved answers into a channel Canvas decision log.
- **Rubric edges:** Design 5/5, Idea 5/5. **Critical weakness:** public repo contains **zero automated tests** and no eval harness — decisive under Tech tie-break.

### 2.2 Consensus
- **Repo:** https://github.com/BitTriad/consensus-slack-agent
- **Thesis:** Ambient "contradiction firewall" — captures decisions from normal conversation and privately alerts authors before they contradict a standing decision.
- **Stack:** TypeScript, Bolt JS, MongoDB/SQLite, Cerebras GLM-4.7 + Gemini fallback, Slack MCP server, RTS.
- **Surfaces:** Ambient capture (no slash command), live contradiction alerts, permission-filtered App Home, edit/delete sync, consistency audit.
- **Evidence:** 58-case eval, 9 adversarial injection patterns (fullwidth, RTL, ZWJ, HTML entities), published P/R: 1.000 / 0.964.
- **Better than A&A:**
  - Fully ambient UX (no upload step).
  - Explicit contradiction detection as first-class feature.
  - Published adversarial eval with delimiter-break cases.
  - NFKC normalization + delimiter wrapping for injection hardening.
  - Fail-closed membership gate for private-channel redaction.
- **Absorbable into A&A (no regressions):**
  - Expand `evals/dataset.ts` with near-misses and Unicode delimiter-break cases.
  - Adopt NFKC normalization and escape opening *and* closing untrusted tags in `src/core/sanitize.ts`.
  - Add persistent per-user dismissal memory for false-positive answers.
  - Build a two-stage audit scanner for contradictions in the approved-answer library.
- **Rubric edges:** Tech (eval + hardening), Design (ambient UX).

### 2.3 Kept
- **Repo:** https://github.com/kaviyakumar23/kept
- **Thesis:** Human-verified, event-sourced obligation ledger for shared customer channels — LLM only proposes commands; a deterministic engine decides every transition behind two mandatory human gates.
- **Stack:** TypeScript, Bolt JS, PostgreSQL event store, Redis/BullMQ, MCP deterministic client, Zod, Vitest.
- **Surfaces:** App Home dashboard, edit modals, roadmap-contradiction warning, Linear/Jira/webhook adapters.
- **Evidence:** 140 hermetic tests + live integration tests, `npm run demo` end-to-end lifecycle, 7-round adversarial hardening.
- **Better than A&A:**
  - Explicit guarded FSM for obligation lifecycle.
  - Deterministic MCP client (model never picks the tool).
  - Idempotency keys, optimistic concurrency, audience-safe leak scanner.
  - Strong adversarial regression discipline.
- **Absorbable into A&A (no regressions):**
  - Add explicit guarded FSM for questionnaire row states.
  - Make the MCP write path deterministic/code-selected.
  - Add idempotency keys and optimistic concurrency to the approval ledger.
  - Adopt the "adversarial regression round" discipline.
- **Rubric edges:** Design (lifecycle UX), Tech (event-sourced engine).

### 2.4 Quorum (OrionArchitekton)
- **Repo:** https://github.com/OrionArchitekton/quorum-slack-agent
- **Thesis:** Decision-memory agent that detects thread-level decisions, drafts a structured record, and routes approval through a durable Vercel Workflow.
- **Stack:** pnpm monorepo, Next.js 15, Vercel Workflow DurableAgent, Bolt, Vercel AI SDK, Slack MCP server, RTS.
- **Surfaces:** Message shortcut, durable Approve/Edit/Discard workflow, proactive nudge, `@Quorum` Q&A, live `/api/health`.
- **Evidence:** 19 unit + 2 integration tests.
- **Better than A&A:**
  - Durable multi-day human approval hook (no in-process polling).
  - Clean curated-record + broad-workspace search split.
- **Absorbable into A&A (no regressions):**
  - Durable approval hooks for SME review deadlines.
  - Decision-record schema and Canvas/channel filing.
  - Proactive nudge for stale questionnaire rows.
- **Rubric edges:** Design (durable workflow), Idea.

### 2.5 Arbiter
- **Repo:** https://github.com/nirbhay221/arbiter
- **Thesis:** Multi-verdict judgment layer over Slack — fact-checks claims, scores "workslop," finds missing decision voices, delegates for absent teammates.
- **Stack:** Python, Bolt, Neo4j claim graph, LangGraph, 7-provider model router, Tavily/web search, Slack MCP server.
- **Surfaces:** Mentions, slash, shortcuts, reactions, assistant pane, watched channels, Slack Lists, Canvas audit export.
- **Evidence:** 66 tests; fact-check/workslop/routing benchmarks.
- **Better than A&A:**
  - Multi-model debate council improves fact-check accuracy.
  - Claim graph models contradictions, credit, and predictions.
  - Arithmetic substance scoring immune to verbosity bias.
  - Broadest UX surface.
- **Absorbable into A&A (no regressions):**
  - Use a small council to review low-confidence drafts.
  - Build a claim/contradiction graph over evidence and approved answers.
  - Add substance/density scoring to draft quality checks.
  - Export the audit trail to Canvas.
- **Rubric edges:** Idea, Design, Potential Impact.

### 2.6 Déjà
- **Repo:** https://github.com/bogacsmz/deja
- **Thesis:** Decision-governance layer — ambiently watches Slack and brakes only when a new proposal conflicts with a standing, sourced decision.
- **Stack:** Python, Bolt, Claude Max subscription, RTS (`assistant.search.context`), MCP (`recall_memory`, `check_decision`).
- **Evidence:** 83-query adversarial benchmark, 0 confident-wrong, 96% recall, 0 false-CONFLICTS governance benchmark.
- **Better than A&A:**
  - Excellent benchmark transparency (publishes the numbers that hurt).
  - Ambient governance without opt-in.
  - MCP as agent-to-agent brake.
- **Absorbable into A&A (no regressions):**
  - Adopt adversarial benchmark structure.
  - Add MCP governance tool for answer-library checks.
  - Document honest limits like Déjà.
- **Rubric edges:** Tech (adversarial eval), Idea.

### 2.7 Loop Closer
- **Repo:** https://github.com/varunbhandarii/Loop-Closer
- **Thesis:** Finds dropped balls (unanswered questions, unkept commitments) in Slack and closes them.
- **Stack:** TypeScript, Bolt, Postgres, Claude, MCP server, RTS.
- **Evidence:** 340+ tests, streamed plan with sources, verify-before-nudge.
- **Better than A&A:**
  - Largest test count found in New Agent track.
  - Strong privacy model (no message content stored).
  - Loop-detection UX.
- **Absorbable into A&A (no regressions):**
  - Loop-detection for stale questions.
  - Streamed plan display.
  - Redaction/paraphrase storage policy.
- **Rubric edges:** Tech (test count), Design, Privacy narrative.

### 2.8 Lore
- **Repo:** https://github.com/drMurlly/lore-slack-agent
- **Thesis:** Multi-hop cited research over workspace history with an ephemeral knowledge graph and Canvas reports.
- **Stack:** Python, Bolt, local LLM via Ollama, FastMCP glossary server, RTS with interchangeable backends.
- **Evidence:** 191 offline tests; YouTube demo.
- **Better than A&A:**
  - Multi-hop retrieval and knowledge graph.
  - Deterministic timeline-drift resolution.
  - MCP glossary for domain jargon.
- **Absorbable into A&A (no regressions):**
  - Multi-hop retrieval for complex multi-control questionnaires.
  - Knowledge graph of controls/decisions/contradictions.
  - MCP glossary server for security/regulatory acronyms.
  - Canvas research reports.
- **Rubric edges:** Idea, Design, Potential Impact.

### 2.9 Aegis
- **Repo:** https://github.com/yama3133/aegis-slack-app
- **Thesis:** MCP-based human-approval control plane — any agent pauses before risky actions and waits for Slack approval.
- **Stack:** TypeScript, Bolt, MCP, Amazon Bedrock.
- **Surfaces:** MCP tools `request_approval`, `check_approval`, `wait_for_approval`; Block Kit cards with Approve / Deny / Edit & Approve / Request Info.
- **Better than A&A:**
  - Generalizable approval infrastructure with policy engine.
  - Edit & Approve flow and N-of-M approvals.
- **Absorbable into A&A (no regressions):**
  - Policy engine for low-risk auto-approval.
  - N-of-M approvals for high-sensitivity questionnaires.
  - Edit & Approve flow for SME corrections.
- **Rubric edges:** Design, Potential Impact.

### 2.10 Threadwork
- **Repo:** https://github.com/ShreyanshVaibhaw/threadwork
- **Thesis:** Turns any Slack thread into a Canvas work post, task list, cited related history, and a supervised Agent Run Card.
- **Stack:** JavaScript/Bolt, MCP, RTS, Canvas, Slack Lists, OpenRouter.
- **Better than A&A:**
  - Structured work artifacts with human-signed agent runs.
  - Clean graceful-degradation matrix for restricted scopes.
- **Absorbable into A&A (no regressions):**
  - Agent Run Card pattern for questionnaire approval steps.
  - Human signature/attestation per approved row.
  - Capability probes at startup.
- **Rubric edges:** Design, Idea.

### 2.11 flightrec-slack
- **Repo:** https://github.com/kitfunso/flightrec-slack
- **Thesis:** Privileged-action Slack agent whose every run is recorded in an append-only, hash-chained audit store.
- **Stack:** TypeScript, Bolt, SQLite (append-only hash chain), MCP.
- **Surfaces:** `/grant` form, `/audit` report, `/audit tamper` demo mode.
- **Evidence:** 26 tests.
- **Better than A&A:**
  - Tamper-evident audit chain with integrity attestation.
  - Parameter-level deterministic gate.
- **Absorbable into A&A (no regressions):**
  - Hash-chained audit ledger for approvals/rejections.
  - MCP audit server for approved answers.
  - Structured modal approvals for sensitive actions.
- **Rubric edges:** Tech (audit integrity), Design.

### 2.12 Meridian
- **Repo:** https://github.com/Tasfia-17/meridian-slack-agent
- **Thesis:** Decision and commitment intelligence — auto-detects decisions/commitments from conversation, logs them as Canvas docs, exposes via MCP.
- **Stack:** Python, Bolt, FastMCP, Claude Haiku, SQLite/MemoryStore, Canvas API, RTS.
- **Evidence:** 45 offline tests.
- **Better than A&A:**
  - Strong Canvas-native artifact design.
  - Commitment nudges.
  - Deterministic confidence scoring.
- **Absorbable into A&A (no regressions):**
  - Canvas-first audit artifacts.
  - Commitment tracking for questionnaire deadlines.
  - Deterministic confidence scoring display.
- **Rubric edges:** Design (Canvas integration).

### 2.13 Slack Compass
- **Repo:** https://github.com/nag-gude/slack-compass
- **Thesis:** Detects missing stakeholders, forgotten decisions, and contradictions before they become launch failures.
- **Stack:** TypeScript/Bolt, Claude, evidence graph, RTS.
- **Surfaces:** `/compass ghost`, `/compass resurrect`, `/compass contradict`, proactive `#ship-it` monitoring, App Home dashboard.
- **Better than A&A:**
  - Proactive detection of missing stakeholders and contradictions.
  - Watch engine with alert/resolve lifecycle.
- **Absorbable into A&A (no regressions):**
  - Ghost-stakeholder detector for SME routing.
  - Watch engine for stale/contradicting approved answers.
- **Rubric edges:** Idea, Design.

### 2.14 Priors
- **Repo:** https://github.com/sneg55/priors
- **Thesis:** Proactively flags when a forming decision contradicts the team's own prior decisions.
- **Stack:** TypeScript, `@slack/bolt`, Anthropic SDK, Zod, Result types.
- **Evidence:** 50 tests.
- **Better than A&A:**
  - Focused, minimal UX.
  - Precision-over-recall design.
- **Absorbable into A&A (no regressions):**
  - Staged pipeline language for contradiction detection.
  - Precision-bias UX.
- **Rubric edges:** Simplicity, focus.

### 2.15 Paper Trail
- **Repo:** https://github.com/jacklachan/paper-trial
- **Thesis:** "Your team's decisions, with receipts" — log decisions from any thread, browse a ledger in App Home, ask sourced questions.
- **Stack:** Python 3.11+, Bolt for Python, SQLite, FastMCP, Gemini/Groq/heuristic fallback.
- **Better than A&A:**
  - Simpler decision-capture UX.
  - Bidirectional MCP (read + propose with approval).
  - AI-free fallback.
- **Absorbable into A&A (no regressions):**
  - Message shortcut for logging approved answers.
  - MCP `propose_answer` UX patterns.
- **Rubric edges:** Ease of capture.

### 2.16 Tribal Knowledge Agent
- **Repo:** https://github.com/divergent99/tribal-knowledge-agent
- **Thesis:** Synthesized workspace-history answers with citations, conflict detection, staleness flags, honest "no answer found."
- **Stack:** Node.js/Bolt, Claude, RTS, Block Kit.
- **Better than A&A:**
  - Query expansion fallback for keyword-only RTS.
  - Explicit conflict/stale flags and humility.
- **Absorbable into A&A (no regressions):**
  - Query expansion for low-coverage RTS.
  - Conflict/staleness badges on answers.
- **Rubric edges:** Design (clarity).

### 2.17 Devil's Advocate
- **Repo:** https://github.com/run58669-maker/devils-advocate
- **Thesis:** Red-team bot that detects premature consensus in a thread and posts structured, evidence-backed dissent.
- **Stack:** Python/Bolt, Gemini 2.5 Flash, MCP DuckDuckGo web search.
- **Better than A&A:**
  - Active red-teaming of decisions with external evidence.
  - Confidence-gated, non-spammy interventions.
- **Absorbable into A&A (no regressions):**
  - Red-team review for newly approved answers.
  - External web evidence for security-control claims.
- **Rubric edges:** Idea, Potential Impact.

---

## 3. Agent for Good Track — Cross-Track Threats

These entries compete in a different track but illustrate what high-impact / high-formal-verification judging can look like.

### 3.1 CornerCheck
- **Repo:** https://github.com/StephenSook/cornercheck
- **Thesis:** Fail-closed fighter-clearance agent across jurisdictions, with formally verified safety proof.
- **Stack:** Python, `slack-bolt`, FastMCP, Z3-solver, Pydantic, Postgres, `jellyfish`, `portion`.
- **Evidence:** 252 passing tests + Z3 safety proof that "active suspension means never CLEAR".
- **Better than A&A:**
  - Full Z3 formal verification of a concrete safety invariant.
  - Conformal prediction for identity matching (95.1% holdout coverage).
  - Public live dashboard.
  - Three independent fail-closed locks.
- **Absorbable into A&A (no regressions):**
  - Use Z3 to prove date/interval invariants for evidence freshness windows.
  - Apply conformal calibration to answer-matching thresholds.
  - Add a public dashboard showing audit-chain verification.
  - Add a live "verify ledger" button.
- **Rubric edges:** Tech (formal methods), Impact, Idea.

### 3.2 Gavel
- **Repo:** https://github.com/tmoody1973/gavel-slack-agent
- **Thesis:** Proactive Slack agent for Milwaukee civic transparency — watches city agendas, warns neighborhoods before votes, bilingual English/Spanish.
- **Stack:** JS/TS, Bolt, Claude Agent SDK, Convex vector DB, custom Milwaukee Civic MCP server, RTS, Deepgram, Fly.io.
- **Evidence:** 927 tests, live deployed.
- **Better than A&A:**
  - Largest test count found across all tracks.
  - Real-world deployment with live civic data.
  - Three-memory retrieval architecture.
- **Absorbable into A&A (no regressions):**
  - Proactive alert scheduling for stale/questionnaire deadlines.
  - Bilingual Canvas/export support.
  - Custom MCP server for external compliance data.
- **Rubric edges:** Impact, Tech (tests/deploy), Design.

### 3.3 Vigie
- **Repo:** https://github.com/Vitalcheffe/vigie
- **Thesis:** Elder watch during heatwaves — crosses Météo-France alerts with beneficiary registry.
- **Stack:** Python, `slack_bolt`, MCP, OpenAI, Redis, Pydantic.
- **Evidence:** 159 tests, live Railway sandbox, App Home KPI dashboard.
- **Better than A&A:**
  - Strong social-impact story.
  - Live KPI dashboard.
- **Absorbable into A&A (no regressions):**
  - KPI dashboard in App Home (auto-answer rate, pending reviews, stale answers).
  - Scenario-based demo scripts.
- **Rubric edges:** Impact, Design.

### 3.4 Clarion
- **Repo:** https://github.com/knarayanareddy/clarion
- **Thesis:** Accessibility agent for deaf/HoH, low-vision, dyslexic, ESL, neurodivergent workers.
- **Stack:** TypeScript, Bolt JS v4, GPT-4o, better-sqlite3, MCP stdio server.
- **Better than A&A:**
  - Accessibility profiles.
  - Dignity-by-default UX.
- **Absorbable into A&A (no regressions):**
  - Accessibility profiles for requesters.
  - Private image-description flow.
- **Rubric edges:** Impact, Design.

---

## 4. Head-to-Head Engineering Matrix

| Dimension | Asked & Answered | Council | Consensus | Kept | Quorum | Arbiter | CornerCheck | Gavel | Lore |
|---|---|---|---|---|---|---|---|---|---|
| **Tests** | 268 | 0 | ~50+ | 140+ | 21 | 66 | 252 | 927 | 191 |
| **Eval / adversarial** | 127 cases, 24 held-out, real-LLM 127/127 | None | 58 cases, 9 injection patterns | 52+ lifecycle | None | ~30 small benchmarks | Z3 + conformal | Unknown | Offline harness |
| **Formal assurance** | Z3 contract + runtime invariant | None | None | FSM invariant tests | None | None | Z3 safety proof | None | None |
| **Citation grounding** | Snippet-level GroundingGate | None | Permalink-in-set | None | Permalink | Prompt-based | Rule engine | Structured + news + RTS | Multi-hop KG |
| **App Home** | ✅ ACL-filtered dashboard | ❌ | ✅ dashboard | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ |
| **Workflow Builder** | ✅ custom step | ✅ (scaffold) | ❌ | ❌ | ✅ durable | ❌ | ✅ step | ❌ | ❌ |
| **Canvas/Lists** | ✅ Canvas + Lists | ✅ Canvas | ❌ | ❌ | ✅ Canvas + channel | ✅ Lists + Canvas | ❌ | ❌ | ✅ Canvas |
| **MCP** | ✅ read-only server | ✅ wrapper | ✅ Slack MCP | ✅ deterministic client | ✅ Slack MCP | ✅ Slack MCP | ✅ FastMCP | ✅ 3 servers | ✅ FastMCP |
| **RTS** | ✅ per-user | ❌ | ✅ | ❌ | ✅ per-user | ✅ | ✅ | ✅ | ✅ |
| **Live deploy** | ✅ Render | ❌ | ❌ | ❌ | ✅ Vercel | ❌ | ✅ Render | ✅ Fly.io | ❌ |
| **Idea novelty** | Fail-closed compliance memory | Brier council | Contradiction firewall | Obligation lifecycle | Durable provenance | Judgment layer | Fighter safety | Civic transparency | Research KG |

---

## 5. Absorbable Improvements — Prioritized

All of these are additive or interface-preserving. None require rewriting the existing Slack listeners.

### Tier 1 — Do before final judging (highest rubric ROI)

1. **Adversarial eval expansion vs. Consensus**
   - Add 25+ adversarial cases: homoglyph, ZWJ, RTL, HTML entities, JSON smuggling, fake system tags, delimiter breaks, prompt chaining, role-play.
   - Adopt NFKC normalization + delimiter wrapping in `src/core/sanitize.ts`.
   - Publish guard-only vs. model-dependent metrics.

2. **N-of-M approvals + policy engine vs. Aegis/Kept**
   - Add a lightweight policy engine: auto-approve low-risk, N-of-M for high-sensitivity questionnaires, TTL escalation.
   - Keep the existing two-gate model as the default; make N-of-M opt-in per questionnaire.

3. **KPI App Home dashboard vs. Vigie/Bridge/GrantHawk**
   - Add stats: questionnaires run, verified answer rate, pending SME reviews, stale answers, ledger integrity.
   - This directly addresses the "Design" and "Impact" scoring concerns.

4. **Public ledger verifier / "See the safety proof" button vs. CornerCheck**
   - Expose a public `/verify-ledger` endpoint or Slack button that re-runs the Z3 proof + hash-chain verification.
   - Makes the formal assurance tangible to judges.

5. **Canvas-first approval decision log vs. Council/Meridian**
   - Mirror every approved answer to a channel Canvas decision log with citations and approver names.
   - Strengthens the audit artifact and Design score.

### Tier 2 — Strong differentiators if time allows

6. **Multi-hop evidence retrieval + lightweight KG vs. Lore/Arbiter**
   - For complex multi-control questionnaires, follow citation chains across messages.
   - Build a knowledge graph of controls, decisions, and contradictions.

7. **Brier/calibration scoring for SMEs vs. Council**
   - Track SME approval accuracy over time; surface calibration in App Home.
   - Use it to weight approver votes in N-of-M mode.

8. **Durable approval hooks vs. Quorum**
   - Replace in-process button timeouts with persistent deadline tracking for SME review.
   - Send proactive nudges for stale questionnaire rows.

9. **Proactive contradiction watcher (ambient) vs. Consensus/Déjà**
   - Listen to channel messages and offer to capture SME decisions / flag contradictions.
   - Make this opt-in per channel to avoid spam.

10. **MCP governance tool vs. Déjà/Paper Trail**
    - Expose `check_answer` / `propose_answer` MCP tools that external agents can call.
    - All writes still go through human approval.

### Tier 3 — Nice-to-have polish

11. **Human signature/attestation per row vs. Threadwork**
12. **Query expansion for keyword-only RTS vs. Tribal Knowledge Agent**
13. **Conflict/staleness badges on answers vs. Tribal Knowledge Agent**
14. **Red-team pre-approval check vs. Devil's Advocate**
15. **Bilingual export support vs. Gavel**
16. **Custom MCP server for external compliance data vs. Gavel**
17. **Accessibility profiles vs. Clarion**
18. **Audio/image accessibility export vs. VoiceDigest**
19. **Diagram intake (PDF/OCR + Mermaid) vs. PathFinder**
20. **Public dashboard for audit-chain status vs. CornerCheck**

---

## 6. Strategic Bottom Line

**Asked & Answered is currently the engineering leader of the New Slack Agent track.** The combination of 268 tests, a 127-case real-LLM eval, code-level Z3 contract proof, runtime invariant verification, and deterministic snippet grounding is unmatched.

**The three ways to lose are:**
1. **Council for Slack** wins on Design/Idea if judges overweight demo polish and novelty.
2. **Consensus** wins on adversarial hardening if its 58-case eval + injection suite is perceived as more rigorous.
3. **CornerCheck/Gavel** from Agent for Good set a high bar for formal verification and measured impact that can spill over into judge expectations.

**The fastest path to an undisputed win:**
- Keep the engineering-rigor lead (do not let test/eval/proof slip).
- Close the adversarial-hardening gap vs. Consensus.
- Add a KPI dashboard and Canvas decision log to close the Design gap vs. Council.
- Add a public "verify ledger" button to make the formal proof tangible.
- Add N-of-M approvals + policy engine to surpass Kept/Aegis on governance.

All of the above are additive and preserve the existing permission invariant.

---

## 7. Sources

- Slack Agent Builder Challenge Devpost: https://slackhack.devpost.com/
- Asked & Answered baseline: https://github.com/theCodeForgerHQ/asked-and-answered
- Competitor URLs listed inline throughout this document.
- Local comparison docs: `docs/UNBIASED_NAMED_COMPARISON.md`, `docs/FINAL_JUDGE_COMPARISON.md`, `docs/UNDISPUTED_EXECUTION_PLAN.md`.
