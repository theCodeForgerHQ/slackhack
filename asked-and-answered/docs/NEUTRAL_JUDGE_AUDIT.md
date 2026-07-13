# Asked & Answered — Neutral Judge Audit

**Competition:** Slack Agent Builder Challenge 2026  
**Track:** New Slack Agent  
**Audit date:** 2026-07-13  
**Auditor persona:** Realistic Stage 2 judge scoring by the published rubric, with no stake in the outcome.

---

## TL;DR

Asked & Answered is **not** the undisputed winner of the New Slack Agent track. It is a **strong podium contender** with one genuinely unique asset: a property-tested, deterministic fail-closed permission invariant. However, the track contains at least **three submissions that currently score higher on engineering rigor**, and several others that match or exceed it on specific rubric pillars. The gap is not reliability alone — it is **eval size, formal assurance, architectural ambition, and production wiring**.

**Current honest rubric score:** ~30.5 / 40  
**Current track placement:** Likely 2nd–4th in New Slack Agent; not guaranteed third, and Stage 1 operational gaps could push it lower.

---

## 1. Official rubric and prize reality

Source: [slackhack.devpost.com/rules](https://slackhack.devpost.com/rules)

### Stage 1 — pass/fail gates

| Requirement | Consequence if missing |
|---|---|
| Select a track | Disqualification |
| Working demo video < 3 min, publicly hosted | Stage 1 loss |
| Architecture diagram | Stage 1 loss |
| Slack sandbox URL with judge access | Stage 1 loss |
| App installed and functioning consistently with video | Stage 1 loss |
| Use ≥1 of Slack AI / MCP / RTS | Disqualification |

### Stage 2 — scored rubric (25% each)

| Criterion | What it really rewards |
|---|---|
| **Technological Implementation** | Quality code; load-bearing sponsor-tech use; tests; error handling; architecture legibility; reproducible evals. |
| **Design** | Slack-native UX; balanced frontend/backend; Block Kit interactivity; App Home; loading/empty/error states. |
| **Potential Impact** | Quantified, nameable-user story; Slack community first. |
| **Quality of the Idea** | Creative **or** a clear, measured improvement on an existing concept. |

**Tie-break order:** Tech → Design → Impact → Idea.

### Prizes

| Prize | Cash |
|---|---|
| 1st place per track | **$8,000 USD** + Slack cert + Dreamforce pass + features |
| 2nd place per track | **$4,000 USD** + features |
| Achievement prizes (3 across all tracks) | **$2,000 USD** each — Best UX, Best Tech, Most Innovative |
| **Third place** | **$0** — there is no third-place cash prize. |

A submission that scores "third" by points but is not selected for an Achievement Prize wins no cash.

---

## 2. Current Asked & Answered — verified state

All commands were run on commit `2ec2728`.

| Check | Command | Result |
|---|---|---|
| TypeScript | `npm run typecheck` | ✅ clean |
| Tests | `npm test` | ✅ **155 / 155 passed** |
| Smoke | `npm run smoke` | ✅ SMOKE PASS |
| Eval harness | `npx tsx evals/run.ts` | ✅ **60 cases, 100%** on all guard metrics |
| Counterfactual | `npx tsx scripts/runCounterfactual.ts` | ✅ 37.5 hrs / $5,625 saved *(simulated)* |
| Load benchmark | `npx tsx scripts/runLoadBenchmark.ts` | ✅ 500 q in 13.9 ms, **35,875 qps** |

### What is genuinely strong

- **Permission invariant:** property-tested with non-vacuity proof (`src/core/invariant.ts`). No competitor has this.
- **Deterministic citation grounding:** snippet-level verification via `GroundingGate` (`src/core/grounding.ts`).
- **Multi-agent jury:** heterogeneous panel behind the `DraftingLlm` interface (`src/core/jury.ts`).
- **Evidence graph + conformal matcher:** stale-answer detection and calibrated question matching.
- **Event-sourced ledger + pure `decide()` engine:** matches Relay/Kept on auditability.
- **Human-gated MCP writes:** `propose_answer` tool that cannot auto-approve.

### Critical weaknesses against a real judge

| # | Gap | Location | Why it loses points |
|---|---|---|---|
| 1 | **V2 components not wired into production path** | `src/app.ts:68-69` | `LedgerV2`, `EvidenceGraph`, and `ConformalMatcher` are implemented and tested but the main app uses legacy `Ledger` and plain `AnswerLibrary`. The advanced architecture is a skeleton, not the running app. |
| 2 | **No live sandbox / deployment / demo video** | whole repo | Stage 1 gates. A judge cannot run the submission from GitHub alone. |
| 3 | **Sessions are in-memory only** | `src/app.ts:79` | Render free-tier spin-down wipes review sessions; buttons silently no-op. |
| 4 | **No App Home / Data Table / Canvas** | `slack/manifest.json`, `src/slack/blocks.ts` | Design criterion is weak vs. Consensus, Kept, Arbiter. |
| 5 | **No real-LLM eval numbers** | `docs/EVALS.md`, `docs/SUBMISSION.md` | 100% numbers are from deterministic fakes. A real judge wants measured model-dependent performance. |
| 6 | **Submission placeholders unfilled** | `docs/SUBMISSION.md` | `[REAL HUMAN QUOTE]`, `[X]%`, `[URL]` remain. |
| 7 | **Private-channel RTS scope uncertain** | `slack/manifest.json:39` | Bot scope `search:read.public` may not support the private-channel ACL demo as written. |
| 8 | **Doc/test-count drift** | `README.md`, `docs/ARCHITECTURE.md` | Docs still cite 91 tests while the repo has 155. |

### Rubric self-score (honest)

| Criterion | Score | Why |
|---|---|---|
| **Technological Implementation** | 9/10 | Deep code; 155 tests; 60-case eval; deterministic grounding; event sourcing. Dinged for V2 not wired into production path and no real-LLM numbers. |
| **Design** | 6.5/10 | Block Kit table works; no App Home, Data Table, Canvas, durable sessions. |
| **Potential Impact** | 7/10 | Clear workflow; honest counterfactual simulator; no real human quote or measured deployment number. |
| **Quality of Idea** | 8/10 | Fail-closed compliance memory is sharp and defensible; not the first "org memory from Slack" idea. |
| **Total** | **30.5 / 40** | Strong, but not runaway winner. |

---

## 3. Every findable New Slack Agent submission — reviewed

Research was conducted via public GitHub repos, Devpost rules, and web search on 2026-07-13. Devpost gallery is not yet published, so repo evidence is the primary source.

| Project | Track | Tests | Eval | Live | Slack techs | Surfaces | Engineering thesis | Verdict vs. A&A |
|---|---|---|---|---|---|---|---|---|
| **[Kept](https://github.com/kaviyakumar23/kept)** | New Slack Agent | **~325** | 42 lifecycle/safety checks, classification 69% F1, 0% leakage | `fly.dev` URL in manifest (404 unconfirmed) | AI ✅ MCP ✅ RTS ✅ | App Home, Block Kit cards, modals, `/kept` | Deterministic event-sourced obligation FSM; **two mandatory human gates**; deterministic MCP client; 7+ adversarial hardening rounds; audience-safe redaction | **Stronger engineering.** More rigorous state-machine governance and larger test surface. A&A should absorb its command→decide→event-store pattern. |
| **[Consensus](https://github.com/BitTriad/consensus-slack-agent)** | New Slack Agent | 132 | **58 cases**, P 1.000 / R 0.964, 9/9 injection defeats | `render.yaml` present; no public URL | AI ✅ MCP ✅ RTS ✅ | App Home, ephemeral alerts, in-thread cards, @mention Q&A | Decision ledger + contradiction firewall; permission-aware membership gate; NFKC + delimiter injection hardening | **Comparable / slightly stronger in eval & permissions.** Bigger labeled eval and stronger adversarial hardening; lacks A&A’s conformal/ACL formalism. |
| **[Arbiter](https://github.com/nirbhay221/arbiter)** | New Slack Agent | 66 | Fact-check 10/10, workslop 20/20 + held-out 9/10, routing 91% F1, 12/12 adversarial | None | AI ✅ MCP ✅ RTS ✅ | App Home, Slack Lists, Canvas, slash commands, @mention, shortcuts, watched channels | Multi-model debate (Skeptic→Advocate→Analyst→Contrarian→Synthesizer), LangGraph, Neo4j claim graph, prediction ledger | **Comparable / stronger in multi-agent reasoning & KG.** A&A has more tests and ACL invariants; Arbiter has denser UX and research-grade narrative. |
| **Slack Compass** | New Slack Agent | 35 | None | None | AI ✅ RTS ✅ MCP ❌ | App Home, `/compass`, Compass Cards | Evidence graph + three detectors (stakeholders, stale decisions, contradictions) | **Weaker.** No MCP, no eval, lighter safety. |
| **Council for Slack** | New Slack Agent | 0 | 4 manual case studies | Vercel 200 OK | MCP ✅ Canvas ✅ Workflow step-ready | `/council`, shortcuts, Channel Canvas, MCP | 5-persona council, Brier calibration audit | **Weaker engineering.** Strong concept, but zero automated tests is a hard gap. |
| **DecisionOps** | New Slack Agent | 67 | 5 logic checks, no accuracy metrics | None | RTS ✅ Canvas ✅ AI ❌ MCP ❌ | Message shortcut, Canvas brief | Delta-scoped RTS, metadata-as-DB, ≤6-call budget | **Comparable test volume, narrower scope.** No MCP / AI eval. |
| **ThreadWork** | New Slack Agent | 0 | None | None | Claims all three; manifest lacks `agent_view` / MCP flag | @mention, Canvas, Slack List, Agent Run Card | Structured extraction + supervised agent run | **Weaker.** No tests or eval. |

### Cross-track engineering leaders (absorbable)

| Project | Track | Tests | Why it matters |
|---|---|---|---|
| **[CornerCheck](https://github.com/StephenSook/cornercheck)** | Agent for Good | 205 (+ Z3 proof) | Engineering ceiling: Z3-verified fail-closed invariant, conformal prediction 95.1% holdout, Data Table, Canvas, Workflow step, live dashboard. |
| **[Relay-Crisis](https://github.com/indrapranesh/relay-crisis)** | Agent for Good | ~555 | Event-sourced ledger, human-gated MCP writes, PII-free projections, counterfactual simulator, load benchmark. |
| **[Lore](https://github.com/drMurlly/lore-slack-agent)** | Agent for Good | 191 | Knowledge graph with contradiction/timeline resolution, Canvas reports, MCP glossary. |

---

## 4. Why Kept, Consensus, and Arbiter score higher — not just reliability

### Kept

| Rubric pillar | Why it scores higher |
|---|---|
| **Tech Implementation** | ~325 tests; deterministic guarded FSM; two mandatory human gates; deterministic MCP client (model never selects tool); multi-source reconciliation; concurrency control; optimistic concurrency on append. |
| **Design** | App Home ledger dashboard, Block Kit confirmation/verify/closure cards, edit modals, Assistant pane. |
| **Potential Impact** | Obligation lifecycle is a concrete, high-stakes workflow (commitments, SLAs, incidents). |
| **Quality of Idea** | "Deterministic guardrails for agent promises" is a fresh, defensible framing. |

**Key insight:** Kept wins because it is built around a **provably safe state machine**, not an LLM-controlled workflow. Its engineering is the most principled in the track.

### Consensus

| Rubric pillar | Why it scores higher |
|---|---|
| **Tech Implementation** | 58 hand-labeled cases, 9 adversarial injection patterns, multi-model reporting, permission-aware membership gate. |
| **Design** | Complete product loop: ambient capture → ephemeral contradiction alert → App Home → audit report. |
| **Potential Impact** | "Decision memory" is a universal team pain with quantified consistency drift. |
| **Quality of Idea** | "Contradiction firewall" is novel and instantly legible. |

**Key insight:** Consensus wins on **eval breadth and idea novelty**, not uptime.

### Arbiter

| Rubric pillar | Why it scores higher |
|---|---|
| **Tech Implementation** | Multi-agent debate across heterogeneous LLMs, held-out workslop benchmark, router F1 metric, Neo4j claim graph. |
| **Design** | Seven entry points; dense but coherent UX. |
| **Potential Impact** | Anchored to measurable wastes ("40% of workers receive polished-but-hollow AI content"). |
| **Quality of Idea** | "Judgment layer" / "workslop detector" / "missing voices" are fresh framings. |

**Key insight:** Arbiter wins on **algorithmic sophistication and architectural ambition**.

### Where Asked & Answered still beats all three

- **Property-tested permission invariant** with non-vacuity proof.
- **Deterministic snippet-level grounding gate** (Consensus checks only permalinks; Arbiter is prompt-based; Kept does not ground answers to RTS snippets in the same way).
- **Event-sourced ledger + human-gated MCP writes** — matches Kept/Relay.
- **Conformal question matching** — none of the three uses calibrated matching.

**A&A's gap is not safety. It is (a) production wiring, (b) eval size, and (c) making the advanced architecture the default running app.**

---

## 5. Specific user questions answered

### Is Consensus better only by eval or by engineering itself?

Both. Consensus has a **larger labeled eval** (58 vs. 60 now comparable) and **stronger adversarial hardening** (NFKC + delimiter wrapping). Its engineering is also more **product-integrated**: ambient capture, edit/delete sync, dismissal memory. A&A now matches or exceeds on eval size and citation safety, but Consensus's eval was measured against **real hosted models** (GLM-4.7, gemma, Claude) — A&A's 100% is still hermetic.

### Can I get better architecture now that everything is built?

Yes. The V3 architecture modules (`LedgerV2`, `EvidenceGraph`, `ConformalMatcher`, `JuryDrafter`, `GroundingGate`, `InvariantChecker`) are implemented and tested. The single highest-ROI move is to **wire them into `src/app.ts` as the default production path**. This does not require rewriting listeners or breaking existing interfaces.

### Is it sure I come third? Will I go down?

**Not sure.** There is no guaranteed third-place cash prize; "third by score" without an Achievement Prize = $0. You can also **go down** if Stage 1 gates (video, sandbox, judge access) are missing or broken. A&A is currently a strong podium contender, but placement is discretionary and the field is large.

### Is there prize money for third place?

**No.** Only 1st ($8k), 2nd ($4k), and three $2k achievement prizes.

### Are there better projects to learn from?

Yes. Beyond the track leaders, **CornerCheck** (Z3 proof + conformal prediction), **Relay** (human-gated MCP writes + counterfactual impact), and **Lore** (knowledge graph + Canvas reports) all contain absorbable patterns.

---

## 6. What to absorb from the leaders

| Pattern | Source | How A&A applies it |
|---|---|---|
| Command → pure `decide()` → event store | Kept, Relay | Make `ReviewSession` actions emit typed events through `decide()` by default. |
| Two mandatory human gates | Kept | Enforce that agent proposals and approvals require distinct human confirmations. |
| Deterministic MCP client | Kept | Keep MCP server read-only; any write path proposes a command, never auto-commits. |
| Z3 formal proof of fail-closed invariant | CornerCheck | Encode "no answer text without visible citation" in SMT-LIB and prove it. |
| Conformal calibration | CornerCheck | Already started; expose the calibration report and coverage guarantee. |
| NFKC + delimiter injection hardening | Consensus | Normalize untrusted evidence and wrap it in unambiguous delimiters. |
| Per-message membership gate | Consensus | Re-check channel membership before surfacing any private-channel citation. |
| Multi-model debate panel | Arbiter | Already implemented; make it the default when multiple provider keys are present. |
| Knowledge-graph supersession edges | Lore | Expand `EvidenceGraph` with deterministic timeline-drift resolution. |
| Counterfactual impact simulator | Relay | Already implemented; publish baseline rules clearly. |

---

## 7. Final honest verdict

Asked & Answered is one of the most **principled** engineering submissions in the New Slack Agent track. Its permission invariant, deterministic grounding, multi-agent jury, evidence graph, and event-sourced ledger are real and well-tested. **But principled code is not the same as a demonstrable, measured, polished winner.**

To become the undisputed engineering winner, A&A must:

1. **Wire the V3 architecture into `src/app.ts`** so the advanced components are the default, not opt-in.
2. **Expand the eval to 120+ cases** with real-LLM reporting and a held-out set.
3. **Add a Z3/SMT proof** or stronger formal verification of the permission invariant.
4. **Fix operational gaps**: live sandbox, durable sessions, App Home/Data Table/Canvas, real-LLM eval numbers, filled submission doc.

The path is clear and the codebase already supports it. Execution remains the only open question.
