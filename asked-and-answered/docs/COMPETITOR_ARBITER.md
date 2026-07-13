# Forensic Review: Arbiter

## 1. Core engineering thesis

Arbiter is a multi-verdict “judgment layer” that routes Slack messages through a cheap coordinator into specialized pipelines—heterogeneous-agent fact-checking, arithmetic anti-workslop scoring, and quote-first decision support—persisted in a Neo4j claim graph and surfaced through Slack UI, MCP reactions, Canvas exports, and native Lists.

---

## 2. Most impressive technical implementations

### Multi-agent debate council
- `arbiter-clone/council.py:1-129` — full Lymerorium-style council: convergence early-stop, Free-MAD anti-conformity round, and DART dispute search.
- `arbiter-clone/council.py:77` — `run_council()` orchestrates round-1 parallel debate, split detection, and optional round 2.
- `arbiter-clone/council.py:33` — `_free_mad_suffix()` forces each panelist to critique every other position and explicitly disallows majority opinion as evidence.
- `arbiter-clone/council.py:52` — `_dart_search()` fires a targeted web search on the most opposed pair when the panel splits.
- `arbiter-clone/llm.py:341` — `_debate()` runs Skeptic first, then Advocate + Analyst in parallel with prior verdict visible, reducing groupthink.
- `arbiter-clone/llm.py:497-576` — synthesizer node runs 3× self-consistency when the panel splits and anonymizes panel identities to prevent sycophancy.

### Claim / contradiction / credit graph
- `arbiter-clone/knowledge_graph.py:6-11` — schema: `(:Claim)` linked to `(:Source)` via `[:CITES]`, with `[:CONTRADICTS]` and `[:SUPPORTS]` claim-to-claim edges.
- `arbiter-clone/knowledge_graph.py:59-99` — `save_claim()` persists verdicts, sources, authors, permalinks, and auto-links contradictory claims from the last 30 days.
- `arbiter-clone/knowledge_graph.py:102-128` — `find_earlier()` powers the credit ledger with keyword-regex matching across prior claims.
- `arbiter-clone/knowledge_graph.py:131-156` — `find_related()` injects related verified claims into the synthesizer context.
- `arbiter-clone/ledger.py:38-48` — formats credit as a gift line (`“Maya raised this first on Jun 2”`).
- `arbiter-clone/ledger.py:54-88` — prediction detection + logging to the graph and Slack List.

### Workslop benchmark
- `arbiter-clone/substance.py:34-52` — strict concreteness extraction: units must name a person, number, date, or named artifact.
- `arbiter-clone/substance.py:88-94` — density score: 3+ substantive units per 100 words = 100.
- `arbiter-clone/substance.py:172-198` — final formula `0.6*density + 0.2*grounded + 0.2*novelty - 0.25*fluff`, guaranteeing zero-unit content cannot pass.
- `arbiter-clone/eval.py:46-152` — dev set: 10 hollow vs 10 dense messages, including cliché-free “polite vagueness” hard negatives.
- `arbiter-clone/eval.py:160-212` — held-out set written after the formula was frozen, plus borderline cases reported but not scored.
- `arbiter-clone/eval.py:245-272` — `eval_substance()` prints per-component breakdown and separation gap.
- `arbiter-clone/eval.py:223-242` — `eval_holdout()` runs the frozen formula once.

### Routing benchmark
- `arbiter-clone/judgment.py:106-147` — `classify()` uses cheap heuristics + a fast-model classifier to route to claim / decision / substance / none.
- `arbiter-clone/judgment.py:94-103` — `_heuristics()` gates ~90% of traffic before any LLM call.
- `arbiter-clone/judgment.py:32-69` — decision-phrase and filler-phrase wordlists that feed the heuristic gate.
- `arbiter-clone/eval.py:500-552` — `eval_router()` reports full confusion matrix, per-mode precision/recall/F1, and macro-F1 over 150 labeled cases.
- `arbiter-clone/eval.py:562-636` — `HELDOUT_CASES` tests messy, never-tuned phrasings (`“ship it 🚀”`, `“alright greenlit”`, etc.).

### Canvas export (audit trail)
- `arbiter-clone/audit.py:102-115` — `publish_canvas()` exports the last 100 interventions as a Markdown table via MCP.
- `arbiter-clone/audit.py:22-46` — every intervention is logged with mode, trigger, confidence, action, and summary to Neo4j or JSON fallback.
- `arbiter-clone/mcp_client.py:88-89` — `create_canvas()` Slack MCP tool wrapper.
- `arbiter-clone/mcp_client.py:59-73` — reusable MCP session with JSON-RPC framing and stale-session reset.

### Slack Lists
- `arbiter-clone/lists_sync.py:1-198` — native Slack Lists mirror with automatic list creation and per-workspace state isolation.
- `arbiter-clone/lists_sync.py:72-127` — `_ensure_list()` creates Prediction Ledger and Decision Register schemas, disabling itself permanently on hard scope/plan failures.
- `arbiter-clone/lists_sync.py:138-161` / `184-197` — `add_prediction()` and `add_decision()` write rows via `slackLists.items.create`.
- `arbiter-clone/lists_sync.py:164-181` — `mark_prediction()` flips status to hit/miss when predictions resolve.

### Bonus: proactive cascade & private-first delivery
- `arbiter-clone/app.py:1112-1197` — `on_message()` runs the full proactive cascade in watched channels: away delegate, missing-voices, private substance receipts, public claim flags.
- `arbiter-clone/app.py:1149-1162` — substance receipts are delivered ephemerally to the author only.
- `arbiter-clone/app.py:282-304` — missing-voices cards use the new `task_card` block and register the decision in the native Slack List.

---

## 3. Patterns Asked & Answered should absorb

| Arbiter pattern | Why it wins | Suggested A&A file |
|---|---|---|
| Heterogeneous-agent council with Free-MAD + DART (`council.py`) | Improves fact-check accuracy and surfaces genuine disagreement; A&A’s `JuryDrafter` currently uses deterministic majority vote only. | Extend `src/core/jury.ts` or add `src/core/council.ts` implementing `DraftingLlm` with role prompts, split detection, and a dispute-recruitment search. |
| Claim graph with contradiction / credit / prediction edges (`knowledge_graph.py`) | Builds workspace memory: “who said it first,” stale-evidence detection, and prediction calibration. | Extend `src/core/evidenceGraph.ts` with `Claim`/`Prediction` nodes, `CONTRADICTS` edges, and `findEarliest()`; or add `src/core/claimGraph.ts`. |
| Arithmetic, decomposed anti-hallucination scoring (`substance.py`) | Immune to verbosity bias; every point is traceable to countable units. | Add `src/core/scoring.ts` with density/fluff/grounded/novelty metrics; use it to score drafts and surface low-confidence rows. |
| Judgment router / coordinator (`judgment.py`) | One-intervention rule keeps the bot from spamming multiple verdicts on one message. | Add `src/core/coordinator.ts` that classifies DMs/mentions into questionnaire vs fact-check vs substance vs decision modes and dispatches accordingly. |
| Slack Lists for prediction/decision registers (`lists_sync.py`) | Native persistence visible to the whole workspace, not just bot state. | Add `src/slack/listsSync.ts` mirroring approved answers or open SME routes into Lists. |
| Canvas audit export (`audit.py` + `mcp_client.py`) | Compliance-shaped artifact; judges love transparency. | Extend `src/slack/canvasExport.ts` with an audit-trail variant, or add `src/core/audit.ts` logging approvals/rejections and exporting via Canvas API. |
| Proactive channel watch + reaction trigger (`app.py`) | More surface area than “upload a questionnaire.” | Add channel-watch state in `src/slack/sessionStore.ts` and an `app.event('message')` handler in `src/app.ts` for lightweight proactive help. |
| Quote-first delegate / roundtable (`delegate.py`, `roundtable.py`) | Novel human-in-the-loop affordance; never speaks for someone without record. | Add `src/core/delegate.ts` / `src/core/roundtable.ts` using `SlackRtsClient` per user and A&A’s existing grounding gate. |

---

## 4. Concrete weaknesses A&A can exploit

1. **No deterministic citation grounding.** Arbiter resolves citations from model-chosen source numbers (`llm.py:400-414`); if the model omits numbers, it falls back to the first three evidence URLs. There is no check that the cited snippet actually supports the reasoning. A&A’s `GroundingGate` (`src/core/grounding.ts`) is a genuine moat—advertise it.

2. **Public proactive fact-flags can be call-outs.** In watched channels, Arbiter posts false/misleading verdict cards in-thread without prior human approval (`app.py:1185-1197`). A&A’s per-answer approval workflow is more enterprise-safe.

3. **No per-requester permission scoping.** Arbiter uses a global `SLACK_USER_TOKEN` for RTS (`tools.py:17-18`) and does not re-check whether the requester can see cited channels. A&A binds `SlackRtsClient` to the requesting user and re-validates every citation (`src/core/pipeline.ts:150-158`, `src/slack/visibility.ts`).

4. **Delegate fidelity is itself an LLM judgment.** `_fidelity_check()` (`delegate.py:38-51`) asks another model whether the answer is supported; it is neither deterministic nor property-tested. A&A can claim a deterministic grounding gate + human opt-in for persona inference.

5. **Adaptive debate skip is model-gated.** The “fast path” bypasses the council when a single LLM reports confidence ≥92 (`llm.py:600-603`). That is another LLM judgment, not a verified signal. A&A’s deterministic gates are cheaper and more reliable.

6. **Slack Lists integration is brittle.** On the first hard failure (`missing_scope`, `paid_teams_only`, etc.) the module disables itself for the session (`lists_sync.py:66-69`, `107-108`). There is no retry/queue/fallback workflow.

7. **Canvas export is a plain Markdown table.** `publish_canvas()` (`audit.py:102-115`) pipes a Markdown table through MCP. A&A already has structured Canvas sections (`src/slack/canvasExport.ts:123-147`); use that richness for a more polished audit artifact.

8. **Reliance on many free-tier providers.** `_PROVIDERS` supports seven providers (`llm.py:43-51`) and the default panel uses three NVIDIA-hosted models. Free-tier flakiness, rate limits, and key sprawl are real operational risks. A&A’s simpler provider stack is easier to run and judge.

9. **Small benchmark sets with optimistic reporting.** The routing benchmark is only ~150 cases (in-sample + held-out combined) and the fact-check benchmark is 10 cases. A&A’s 120-case eval with deterministic guarantees (`docs/EVALS.md`) is more robust and harder to dismiss.

10. **No formal invariant or property tests.** Arbiter has 66 unit tests covering deterministic helpers; A&A has 187 hermetic tests including a fast-check property suite on the permission invariant. Lean on that engineering rigor.

---

## 5. Rubric scores

| Dimension | Score | Justification |
|---|---|---|
| **Tech** | 8/10 | Strong multi-agent architecture, provider registry, claim graph, caching, and deterministic helper tests. Loses points for non-deterministic citation resolution, no per-requester ACL, and a global user token for RTS. |
| **Design** | 7/10 | Excellent UX breadth (mentions, slash commands, shortcuts, reactions, assistant pane, watched channels, App Home) and a thoughtful private-first rule. Proactive public call-outs and fragile Lists integration drag it down. |
| **Impact** | 7/10 | Workslop detection and missing-voices decision support are genuinely useful and differentiated. But lack of human approval before proactive interventions limits enterprise trust. |
| **Idea** | 8/10 | A “judgment layer” over Slack is a clear, memorable thesis. Multi-verdict routing, credit/calibration ledgers, and quote-first delegation are creative extensions of the core idea. |

