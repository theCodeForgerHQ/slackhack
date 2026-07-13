# Project Design — "Asked & Answered"

> **v2 NOTICE (2026-07-11):** This v1 text was reviewed by a four-judge no-context panel (see `judge-simulation.md`). Eleven findings were accepted; where this document conflicts with the **V2 Hardened Decisions** section at the bottom, **v2 wins**.

## One-liner
**Asked & Answered** turns your team's Slack history into completed security questionnaires, RFPs, and vendor forms — every answer evidence-cited, SME-approved, and tamper-evidently logged. It never invents a compliance answer: no evidence, no answer.

*(Name is human-voiced legalese — "asked and answered" is the courtroom objection to re-asking a settled question. Avoids the "fourth SlackSage in the gallery" trap. Alternates if collision found: "Second Ask", "On File".)*

## The pain (nameable user, quantified)
Every B2B deal ships a security questionnaire / RFP / vendor-onboarding form: 50–300 rows, 90% asking what the team has already answered somewhere — in #security threads, in last quarter's spreadsheet, in the SOC 2 doc. Industry surveys put the cost at **20–40 person-hours per questionnaire**, and it lands on the same two SMEs every time, blocking live deals for days. The nameable user: *the AE who pings #security every quarter with the same 200-row spreadsheet, and the security engineer who answers it — again.*
Existing tools (Conveyor, Loopio, Vanta Questionnaire Automation) live *outside* Slack and require maintaining a separate knowledge base. **The improvement (rubric's own escape hatch — "how much does the project improve on it?"): the evidence already lives in Slack; the SMEs already live in Slack; the approval already happens in Slack. A&A makes Slack itself the answer library — zero-copy, citation-first, approval-gated.**

## End-to-end workflow (the single demo journey)
1. **Intake** — user opens A&A in the Messages tab (agent_view) and uploads a questionnaire (xlsx/csv, or pastes questions). Suggested prompts onboard first-time users.
2. **Plan** — agent streams a visible plan (`chat.startStream`, plan block + task cards): "Parsed 47 questions → deduped to 41 → searching workspace evidence → drafting → routing gaps."
3. **Evidence retrieval (RTS, load-bearing)** — the **Query Planner** consolidates 41 questions into ~9 batched `assistant.search.context` calls (OR-clauses, filter reuse, per-user 10 req/min budget enforced, keyword-mode first-class since sandbox lacks semantic search), then drills into hits with bounded `conversations.replies` context. *Remove RTS and the product is dead — it IS the evidence engine.*
4. **Fail-closed drafting** — each question gets one of three states:
   - **Verified** — matches an SME-approved answer in the library → reused with provenance;
   - **Grounded** — new draft, every sentence cited to Slack permalinks/files that the *requesting user can see* (RTS permission model does the ACL work);
   - **Needs SME** — insufficient evidence → **the agent refuses to draft** and routes instead. A compliance answer is never hallucinated, by construction.
5. **Review surface (Block Kit, native)** — a **Data Table** of questions × state × confidence × owner; each row opens a **Card**: draft, citations, `feedback_buttons` (Approve / Edit / Reject). Needs-SME rows are DM'd to the suggested owner (chosen via RTS user/channel-activity signals) with `context_actions`.
6. **Approval ledger** — every approve/edit/reject appends to a **hash-chained audit ledger** (actor, timestamp, answer hash, evidence hashes). `/aa verify` recomputes the chain live — tamper-evidence demoed, not claimed.
7. **Artifact out** — completed questionnaire exported as a **Canvas** (via Slack MCP server, user-consented) + downloadable xlsx, every answer footnoted with permalinks + approval record. *Tangible artifact ends the demo.*
8. **The compounding payoff** — approved answers become the library. **Questionnaire #1: 41 questions, ~3.5h wall clock incl. SME turnaround. Questionnaire #2: 68% auto-Verified, 22 minutes.** That before/after is the demo's closing number.

## Qualifying-tech map (all three, load-bearing — passes the update-44783 "tell" test)
| Tech | Use | Would it work without? |
|---|---|---|
| **Slack AI capabilities** | `agent_view` Messages-tab surface; `chat.startStream/append/stop` streaming; `assistant.threads.setStatus/setTitle/setSuggestedPrompts`; plan block, task cards, markdown block, **Data Tables**, Cards, `feedback_buttons`, `context_actions` (the June-2026 Block Kit push, by name) | No — the review surface and agent UX are the product's frontend |
| **RTS API** | `assistant.search.context` (messages+files, filters, OR-clauses, `include_context_messages`), `assistant.search.info` capability probe, action_token plumbing abstracted into a clean module, **rate-limit-aware Query Planner with graceful keyword fallback** | No — sole evidence engine; also solves the platform's #1 documented pain point (10 req/min) visibly |
| **MCP** | (a) consumes the **Slack MCP server** (`mcp.slack.com/mcp`, user-token OAuth) for Canvas creation + SME DMs on the user's behalf; (b) ships **`asked-answered-mcp`** — our own MCP server exposing `search_answers`, `get_answer_provenance`, `export_questionnaire` (readOnlyHint set) so the approved library is reachable from Claude/Cursor and registrable with the Slackbot MCP client where rolled out | No — actions and external reach die; the own-server direction also demos the newest platform surface |

## Depth artifacts (absorbed from the current field's best, then extended)
- **Eval harness with published numbers** (à la Consensus/Relay/DecisionOps): seeded sandbox with planted ground-truth evidence + ~70 labeled questions → report **retrieval recall/precision, citation faithfulness (does the permalink actually support the sentence — judged + spot-checked), fail-closed correctness (refusal rate on the 15 deliberately unanswerable questions = must be 15/15), prompt-injection resistance (N adversarial docs planted in the workspace trying to poison drafts; target N/N defeated, citing Slack's own prompt-injection guidance)**. Numbers go in the README and the video.
- **Hash-chained approval ledger + live verify** (à la CornerCheck/flightrec) — but ours guards a *universal* workflow, not a niche one.
- **Human-gated writes** (à la Relay): nothing becomes Verified, and nothing leaves the workspace, without an SME click.
- **Zero-copy compliance by design**: the library stores only app-authored approved answers + permalink pointers — never copied Slack content. This is a Marketplace review requirement turned into a headline feature.
- **Hygiene**: 150+ offline hermetic tests (mocked Slack transport), GitHub Actions CI, typed codebase, ARCHITECTURE.md + diagram showing exactly where AI/MCP/RTS sit (update-44560 requirement), LIMITATIONS.md with honest negative results (e.g., "PDF parsing cut for scope; semantic search unavailable in sandbox so keyword mode is primary; auto-approval rejected on principle").
- **Live 24/7 deployment** (Fly.io/Railway) + judge sandbox pre-seeded with a realistic company workspace (channels, threads, files) so judges can run the full journey in <5 minutes; judge-access checklist done on day 1, not last.

## Rubric self-score targets
- **Technological Implementation**: all 3 techs load-bearing + eval numbers + tests/CI + the Query Planner as a named engineering contribution → target 5.
- **Design**: Data-Table review surface + Cards + streaming plan + Canvas artifact = balanced frontend/backend by construction → target 5.
- **Potential Impact**: every B2B org in Slack; 20–40h → minutes, compounding; beyond Slack: vendors/procurement broadly → target 4.5.
- **Quality of Idea**: exists outside Slack; improvement argument is native evidence + native SMEs + zero-copy + fail-closed → target 4.
- Tie-break order (Tech → Design → Impact → Idea) favors this profile by construction.

## Scope discipline (60h, solo + AI pair)
- **In:** xlsx/csv + pasted-text intake; the 8-step journey above; eval harness; ledger; Canvas + xlsx export; own MCP server (read-only tools); Marketplace bureaucracy track (parallel).
- **Out (stated in LIMITATIONS):** PDF OCR intake, semantic-search reliance, auto-approval, Slack Connect flows, multi-language.
- **Cut order if behind:** own-MCP-server garnish → xlsx export (keep Canvas) → owner-suggestion heuristics (keep manual routing). The 8-step demo journey is never cut.

## Demo video (target 2:40, scripted)
0:00–0:20 the pain (real 200-row spreadsheet, "#security answered this in March"); 0:20–0:50 upload → streaming plan; 0:50–1:50 Data Table review: one Grounded approval with citations, one **fail-closed refusal**, one SME routing; 1:50–2:15 Canvas export + `/aa verify` ledger check; 2:15–2:40 questionnaire #2 auto-verifies 68% in 22 min + eval-numbers card. Product footage only; no slides.

## Submission text skeleton (mirrors rubric; human-voiced)
Problem → What it does → **Why it needs RTS / Why it needs MCP / Why it's a Slack agent** (pre-answering the tell test) → How we built it (component-by-component + diagram) → Evals & numbers → What we deliberately didn't build → What's next. Keyword-complete for the AI-analysis pass ("MCP server integration", "Real-Time Search API", "Slack AI").

---

# V2 HARDENED DECISIONS (post judge panel — these override v1 above)

## Architecture changes
1. **Two App IDs, same codebase.** App A = internal sandbox app: judging, full rate tiers, Slack MCP access, "functions as depicted." App B = distributed app: Marketplace submission only. Never demo on App B.
2. **Verified-answer ACL revalidation.** On every Verified reuse: re-check each citation's visibility for the current requester (RTS probe); any failure → degrade to Needs SME. Shipped as a labeled eval case ("private-evidence answer must not reach unauthorized requester").
3. **Retrieval strategy inverted.** Per-question RTS queries are PRIMARY (41 questions ≈ 5 min at the 10/min budget — honest and demoable); OR-batched consolidation is the DEGRADED mode; eval publishes numbers per strategy. `include_context_messages` is the primary context source; `conversations.replies` is a cached last resort on App A only.
4. **MCP leg = our own MCP server** (`asked-answered-mcp`: `search_answers`, `get_answer_provenance`, both readOnlyHint) — protected core, never cut. Canvas-via-Slack-MCP is CUT first; artifact export = `files.upload` xlsx (+ Canvas via plain Web API only if hours remain).
5. **Demo journey = 5 subsystems, 100% bot-token:** upload → streamed plan → RTS retrieval → Data Table review (one approval, one fail-closed refusal, one SME route) → `/aa verify` ledger check → xlsx export. Questionnaire #2 compounding appears ONLY if measured working by T-36h; otherwise the eval card closes the video.

## Honesty rules
6. **No number exists until measured.** 68% / 22 min / 3.5h are deleted everywhere. Eval descoped to ~30–40 labeled questions, 3 metric families (retrieval recall; fail-closed refusal correctness incl. the 15 unanswerables; injection resistance on 5 planted adversarial docs), harness config published in README. Measured values only, rounded honestly, methodology asterisk on-screen.
7. **Tests: 60 meaningful, hermetic, CI-run.** Not "150+".
8. **Repro trio:** public repo, MIT license in root, README quickstart with one-command run + judge access instructions.

## Track discipline (Orgs-primary survives only under ALL THREE)
9. Gate probed and observably counting within first 12h (App B distribution on, 5 defensibly-real workspaces created + used, pre-submission checklist watched).
10. Total Marketplace spend time-boxed to **6h hard stop** (landing/support/privacy pages generated, listing assets, AI disclosures).
11. Decision gate at **T-48h** (≈ Jul 12, 05:00 PT): checks not green → New Slack Agent, pre-written submission text swapped in. One-line disclosure in Orgs text: installs bootstrapped across own workspaces per Devpost's workspace guidance.

## Day-1 spikes (first 4 hours, before any feature code)
S1. `slack create agent` scaffold (agent_view, post-June-30) → verify `app_home_opened`/`app_context_changed`/`message.im` fire in sandbox. Do NOT build on legacy assistant-template (4 known Bolt bugs; irreversible manifest switch).
S2. action_token spike: one file-upload `message.im` event → harvest token → 9 spaced `assistant.search.context` calls → log. If single-use/short-lived: per-batch token refresh via exchange, or user-token path — decided day 1.
S3. Data Table render spike in sandbox; fallback (paginated sections + overflow menus) designed behind the same component interface; paginate at 20 rows regardless.
S4. Marketplace gate probe (see 9).

## Video v2 (target ≤2:40, product on screen by 0:20)
- 0:00–0:15 real human: recorded quote/screenshot from an actual security engineer or AE (interview scheduled day 1), their real hour-count. Fully synthetic questionnaire on screen.
- 0:15–0:50 upload → streamed plan (product visible by 0:20).
- 0:50–1:25 review surface ~35s: one Grounded approval with citations.
- 1:25–1:50 **the peak: the refusal.** "No evidence → no answer. It would rather ask a human than invent a compliance answer." + SME route landing as a DM.
- 1:50–2:05 ledger as theater: tamper out-of-band → `/aa verify` → red flag on the exact row.
- 2:05–2:40 xlsx artifact with footnoted citations → measured-numbers card with methodology asterisk (+ questionnaire #2 clip only if T-36h gate passed).
- Compliance: no competitor names on screen (text description only), no third-party marks/music, no real data.
- Tagline pattern: lead with the reframe ("Your Slack already answered this — proven, cited, approved"), not the category.

## Timeline anchors
- Deploy publicly by ~hour 20; judge sandbox seeded + access granted by hour 24.
- Video recorded Jul 12 (day), uploaded Jul 12 (night PT); **Devpost submission complete Jul 12 night — a full day early**; Jul 13 = bugfix + resubmit-refinement margin only.

## V2.1 addenda (readiness audit, Jul 11 ~10:00 IST)
- **Idea framing corrected:** Conveyor HAS a Slack app (bot-mention bridge to their external library). Our delta, stated honestly: workspace-as-the-library (RTS, zero-copy, nothing to maintain), per-requester ACL-revalidated answers (no incumbent has this), fail-closed refusals, native agent_view. Conveyor named in text description only — never in the video (trademark clause).
- **Citations are answer-level** (1–3 permalinks + snippets per answer), not per-sentence.
- **ACL invariant elevated to headline engineering contribution:** property-based test suite over the ledger/library state machine enforcing "no answer text flows to a requester who cannot see all of its evidence" + live demo (lower-privilege user sees Verified degrade to Needs-SME). The Best-Technological-Implementation play.
- **Durability:** non-sleeping host + uptime monitor through Aug 11; sandbox (6-month lifespan) kept active through judging.
- **Judge-README written first** — it is the acceptance spec for the never-cut journey.
