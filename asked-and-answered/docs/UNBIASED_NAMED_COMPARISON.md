# Unbiased Named-Competitor Comparison — New Slack Agent Track

**Competition:** Slack Agent Builder Challenge 2026 — New Slack Agent track  
**Scoring basis:** Published Stage-2 rubric (25% each: Technological Implementation, Design, Potential Impact, Quality of the Idea; tie-break order Tech → Design → Impact → Idea → judges vote). Scored 1–5 per criterion, total 20.  
**Persona:** Neutral, realistic Stage-2 judge with no stake in outcome.  
**Sources:** Public GitHub repos inspected directly. Kept and any other Organizations-track submissions are excluded.  
**Audit date:** 2026-07-14

---

## TL;DR Verdict

Asked & Answered ties Council for Slack at **17 / 20** and wins on the **Technological Implementation** tie-break. Consensus is third at 16. Quorum and Arbiter tie at 14.

The win is narrow: Council has the stronger demo narrative, UX breadth, and idea novelty (multi-persona council scored against reality), but its public repository contains **zero automated tests** and no eval harness. A&A’s engineering evidence — 268 tests, 127-case eval, real-LLM Azure result, Z3 contract proof + runtime invariant verification — is decisive under the published tie-break order.

| Rank | Submission | Tech | Design | Impact | Idea | Total |
|---:|:---|---:|---:|---:|---:|---:|
| **1** | **Asked & Answered** | **5** | **4** | **4** | **4** | **17** |
| **1** | Council for Slack | 3 | 5 | 4 | 5 | 17 |
| 3 | Consensus | 4 | 4 | 4 | 4 | 16 |
| 4 | Quorum | 3 | 4 | 3 | 4 | 14 |
| 4 | Arbiter | 3 | 4 | 3 | 4 | 14 |

---

## Verified repositories

| Submission | Public URL | Inspection notes |
|---|---|---|
| Asked & Answered | `https://github.com/theCodeForgerHQ/slackhack` (`asked-and-answered/`) | Full working tree inspected; 268 tests, 127-case eval, Z3 proofs, runtime invariant, landing page, OAuth, capability probes, watcher, run cards. |
| Council for Slack | `https://github.com/alex-jb/council-for-slack-2026` | README, web package, case studies, manifest, MCP wrapper inspected. **No test files found.** |
| Consensus | `https://github.com/BitTriad/consensus-slack-agent` | 58-case eval, delimiter-break attacks, NFKC normalization, membership gate, multi-backend ledger inspected. |
| Quorum | `https://github.com/OrionArchitekton/quorum-slack-agent` | README, architecture, workflow code, 19 unit + 2 integration tests, live deploy health check inspected. |
| Arbiter | No verified public URL found | Local clone inspected; 66 pytest tests, multi-agent council, claim graph, workslop/routing benchmarks. Public origin could not be verified. |

---

## Per-submission assessment

### Asked & Answered — 17 / 20

- **Technological Implementation: 5** — 268 passing tests, 127-case eval (103 dev, 24 held-out), 127/127 on Azure `gpt-54-mini`, code-level Z3 contract proof of the permission invariant, runtime invariant verification over all 127 eval cases, GroundingGate, event-sourced hash-chained ledger, multi-workspace OAuth, capability probes, delta-scoped RTS cache, proactive stale/contradiction watcher, signed Agent Run Cards.
- **Design: 4** — Polished public landing page with case-study pages, App Home, Data Table review modal, Canvas/Lists/xlsx exports, Block Kit cards, Workflow Builder step. Point off because Canvas/Lists require additional bot scopes and Data Table blocks do not render in DMs.
- **Potential Impact: 4** — Quantified ROI model, compounding answer library, documented pilot scenarios, load benchmark, real-LLM validation. Point off because case studies are composite pilots, not live customer deployments.
- **Quality of the Idea: 4** — Fail-closed compliance memory with a machine-checked permission invariant is sharp and defensible. Point off because org-memory agents are an established category; novelty is mostly in the safety engineering.

### Council for Slack — 17 / 20

- **Technological Implementation: 3** — Uses MCP, Canvas API, Supabase SECURITY DEFINER RPCs, multi-workspace OAuth, Workflow Builder step. Severe deduction for **zero automated tests**, no eval harness, no formal guarantees, and heavy reliance on the external `council-diff` library.
- **Design: 5** — Excellent judge-first UX: `/council` slash command, message shortcut, channel Canvas decision log, Brier audit, domain personas, clean landing page, four vivid case studies.
- **Potential Impact: 4** — High potential reach (every Slack team makes decisions); Brier calibration loop is a credible long-term trust mechanism; no measured deployment data yet.
- **Quality of the Idea: 5** — Multi-persona council scored against reality is the most memorable and differentiated concept in the track.

### Consensus — 16 / 20

- **Technological Implementation: 4** — 58-case eval with delimiter-break attacks, NFKC normalization, fail-closed membership gate, multi-backend ledger, rate guards, per-channel queues, edit/delete sync. Deductions for fail-open governance defaults, stubbed exception narrowing, keyword-gated capture, and in-memory state.
- **Design: 4** — Good ambient UX with ephemeral contradiction alerts, permission-filtered App Home, lifecycle badges. Deductions for leftover starter-template views and no admin dashboard.
- **Potential Impact: 4** — Contradiction firewall is practically valuable for any growing team; enterprise rollout depends on unbuilt roadmap items.
- **Quality of the Idea: 4** — Ambient consistency layer is clear and useful, but decision capture is not a new category.

### Quorum — 14 / 20

- **Technological Implementation: 3** — Vercel DurableAgent, hosted Slack MCP, RTS, durable approval workflow. Deductions for only 21 tests, no eval/adversarial dataset, no external DB, global `SLACK_USER_TOKEN`, and single-sandbox demo-grade state.
- **Design: 4** — Clean decision-memory workflow with durable human-in-the-loop, Canvas + `#decision-log` filing, grounded Q&A. Deductions for no Assistant pane handler and in-memory dedup.
- **Potential Impact: 3** — Decision provenance is valuable but narrow, with no quantified impact model.
- **Quality of the Idea: 4** — Durable decision provenance with sourced answers is a clear, defensible concept.

### Arbiter — 14 / 20

- **Technological Implementation: 3** — Multi-agent council with Free-MAD + DART, Neo4j claim graph, workslop/routing benchmarks, Slack Lists, Canvas export, 66 tests. Deductions for no deterministic citation grounding, global `SLACK_USER_TOKEN`, small eval sets, no formal invariant, reliance on many free-tier providers. **Public repo URL could not be verified.**
- **Design: 4** — Broad UX surface and a thoughtful private-first rule. Deductions for proactive public fact-flags that can feel like call-outs and fragile Lists integration.
- **Potential Impact: 3** — Workslop detection and missing-voices support are differentiated, but proactive interventions without prior human approval limit enterprise trust.
- **Quality of the Idea: 4** — “Judgment layer over Slack” is a clear, creative thesis.

---

## Head-to-head against Asked & Answered

| Dimension | Asked & Answered | Council | Consensus | Quorum | Arbiter |
|---|---|---|---|---|---|
| **Automated tests** | 268 | **0** | ~50+ | 21 | 66 |
| **Eval / adversarial dataset** | 127 cases, 24 held-out, real-LLM Azure | None | 58 cases, delimiter/injection patterns | None | ~30 small benchmarks |
| **Formal assurance** | Z3 contract proof + runtime invariant | None | None | None | None |
| **Deterministic grounding** | GroundingGate (snippet-level) | None | Permalink-in-set | Permalink citations | Prompt-based |
| **Multi-workspace install** | Yes (`/slack/install`) | Yes | No | No | No |
| **Public landing page** | Yes (Vercel) | Yes | No | No | No |
| **Real-LLM validation** | Azure `gpt-54-mini` 127/127 | No | Yes (published) | No | No |
| **Proactive stale detection** | Watcher scans library | No | Contradiction alerts | No | No |
| **Signed audit artifacts** | Agent Run Cards | No | No | No | No |
| **Idea novelty** | Fail-closed compliance memory | Multi-persona Brier council | Contradiction firewall | Durable provenance | Multi-agent judgment |

---

## Where Asked & Answered still loses points

1. **Formal proofs are model sketches, not full program verification.** The Z3 proofs verify abstract contracts, not the actual TypeScript AST; runtime invariant check is testing, not proof.
2. **Impact is modeled, not field-measured.** The case studies are documented pilots; the ROI rests partly on baseline assumptions.
3. **Canvas and Lists exports are scope-gated.** They require `canvases:write` / `lists:write`, which the included bot token lacks in the live sandbox test.
4. **Data Table blocks do not render in DMs.** Slack platform limitation forces the dense review into a modal.
5. **Answer matching is lexical, not semantic.** `library.ts` uses token overlap, so paraphrased duplicates re-draft instead of reusing verified answers.
6. **Watcher is reactive to known edges, not proactive search.** It rescans the existing evidence graph but does not launch fresh RTS queries to discover new contradicting messages.
7. **No PDF/OCR intake.** Questionnaires arriving as PDFs must be converted first.
8. **Semantic RTS is plan-gated.** The best retrieval experience requires a paid Slack plan; keyword mode is the fallback.

---

## Bottom line

Under the published Stage-2 rubric and tie-break order, **Asked & Answered is the engineering leader of the New Slack Agent track.** Its narrowest rival is Council for Slack, which matches A&A on total score but collapses on the first tie-breaker because it ships no automated tests and no eval harness. Consensus is a credible third-place engineering submission. Quorum and Arbiter are creative but materially thinner on verifiable engineering evidence.

The remaining path to a larger margin over Council is a public demo video and at least one measured customer pilot.
