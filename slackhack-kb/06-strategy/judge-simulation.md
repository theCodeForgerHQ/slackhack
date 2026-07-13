# No-Context Judge Panel — Consolidated Verdicts (2026-07-11)

Four independent judges, no build context, given only the official rubric, the v1 design doc, the field intel, and (red team only) the platform-constraint files.

## Verdicts
| Judge | Verdict | Scores (Tech/Design/Impact/Idea) |
|---|---|---|
| Product generalist (ex-Salesforce evangelist type) | **WIN** (Orgs), conditional on execution | 5 / 4 / 4 / 3.5 (~4.1 weighted) |
| Winner-pattern meta-analyst | **First-place profile** — 22/24 on the 12-factor playbook | n/a (factor-based) |
| Slack platform engineer | **CONTENDER** — ceiling is track win + run at CornerCheck tier, IF day-one fixes | 4 / 4 / 4 / 4 |
| Adversarial red team | **Conditionally sound**; unsound as-written; most likely failure = attrition, not DQ | risk-based |

## Consensus strengths (all four agreed)
- Most rubric-literate plan in the field; fail-closed drafting is a genuine product insight and anti-wrapper moat; Query Planner is a real named engineering contribution; track choice is correct in principle; beats the visible Orgs field "without hesitation, and it isn't close."

## Consolidated findings → v2 changes (all accepted)
1. **[CRITICAL — platform judge] Verified-answer ACL leak.** Verified reuse bypasses RTS permissions; answer text derived from private evidence could reach users who can't see it. → **Re-validate every citation against the current requester on reuse; degrade Verified→Needs SME on any failure; ship it as a labeled eval case.**
2. **[FATAL-if-unmanaged — red team] Single App ID poisons the demo.** Activating distribution for Marketplace makes the app "unlisted distributed" → prohibited from Slack MCP server + Tier-1 throttle on `conversations.replies`. → **Two App IDs: App A internal (judging sandbox, full tiers), App B distributed (Marketplace submission). Same codebase.**
3. **[FATAL-if-unmanaged — red team] Marketplace gate probed too late.** → **Probe in first 12h** (activate App B distribution, create workspaces, watch the pre-submission counter). **Decision gate moves T-24h → T-48h. Marketplace spend time-boxed to 6h hard stop.** Workspaces must be defensibly real + one-line disclosure in submission text. Miss any condition → New Slack Agent, pre-written text ready. Honest odds: valid+clean Orgs submission ~40–50%; entry survives stage 1 in some track ~90%+.
4. **[MAJOR — platform judge] Retrieval engine vs real rate limits.** OR-batching corrupts question↔evidence attribution; replies drill-down stalls on distributed tier. → **Per-question RTS queries primary (41 q ≈ 5 min at 10/min — honest), OR-batching as degraded mode with per-strategy eval numbers; `include_context_messages` is the primary context source; `conversations.replies` = cached last resort (App A internal tier).**
5. **[MAJOR — platform judge + red team] MCP story was half-decorative and cut-ordered backwards.** Canvas/DM work with bot token; the honest MCP leg is our OWN server. → **Own MCP server (2 read-only tools: `search_answers`, `get_answer_provenance`) is protected core; Canvas-via-Slack-MCP cut first; export via `files.upload` xlsx.**
6. **[MAJOR — red team + meta-analyst] Scripted-before-measured numbers.** 68%/22min/3.5h appear in drafts for an unbuilt system — fabrication signature + "functions as depicted" liability. → **All numbers deleted from drafts; only measured values enter video/README. Eval descoped to what 8h buys: ~30–40 labeled questions, 3 metric families (retrieval recall, fail-closed refusals, injection resistance on 5 planted docs), config published.**
7. **[MAJOR — red team] Demo journey had 6 failable live subsystems + a second pass.** → **Shrunk to 5 subsystems, 100% bot-token completable: upload → plan stream → RTS retrieval → Data Table review (one approval, one fail-closed refusal, one SME route) → ledger verify → xlsx export. Questionnaire #2 compounding shown only if working by T-36h; else the eval card closes the video.**
8. **[MAJOR — red team] Day-1 spikes required** (each ≤1h, before feature code): (a) agent_view events fire from current `slack create agent` scaffold (NOT legacy assistant-template — 4 known Bolt bugs, irreversible manifest switch); (b) action_token freshness/reuse semantics with a file-upload event funding ~9 spaced RTS calls; (c) Data Table block renders in sandbox — fallback = paginated sections behind the same component interface, paginate at 20 rows regardless; (d) Marketplace gate probe.
9. **[Disqualifier exposure — meta-analyst] Repro trio missing.** → **Public repo + MIT license in root + README quickstart + judge credentials. ~1h.**
10. **[Video — product judge] Fixes:** real human in first 5s (interview an actual security engineer/AE; their hour-count, their quote); the **fail-closed refusal is the emotional center** ("It would rather ask a human than invent a compliance answer"); compress table tour to ~35s; ledger = 10s tamper-attack theater, not cryptography narration; methodology asterisk on-screen for any number; fully synthetic spreadsheet; competitor names in text only (trademark clause); product on screen by 0:20; tagline leads with the reframe, not the category.
11. **[Timing — meta-analyst + red team] Deploy publicly by ~hour 20; video uploaded and Devpost submitted 24h early (Jul 12 night PT); tests target 60 meaningful, not 150+.**

## The one sentence to build by (red team)
The modal loss is **attrition**: shipping an ambitious 75%-polished app whose video shows things the judge's sandbox doesn't reproduce — losing Technological Implementation, its own tie-break weapon, to someone who did one smaller thing flawlessly. The sponsor already published the antidote: *"Do one thing really well. Cut scope, don't ship broken breadth."*
