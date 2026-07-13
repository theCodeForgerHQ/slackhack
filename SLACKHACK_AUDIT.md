# Asked & Answered — Slack Agent Builder Challenge Audit

**Audit time:** 2026-07-13 ~17:00 UTC (deadline: 2026-07-13 17:00 PDT / 00:00 UTC)
**Audited commit:** `9aaa538` in `theCodeForgerHQ/asked-and-answered`
**Auditor:** Kimi Code CLI

## TL;DR

Asked & Answered is a **solid, production-shaped engineering submission**, but it is **not yet an undisputed winner**. The code is clean, the invariant is well-tested, and every offline gate passes. The things that would lose to a top competitor are **not in the code** — they are operational and presentation gaps:

- No live sandbox / deployment / demo video yet.
- Several README claims (streaming plans, Data Table, task cards) are not implemented in `src/app.ts`.
- The Real-Time Search integration is **unverified** against a real Slack sandbox; the private-channel ACL demo may not work as written.
- Direct competitor **Consensus** (same track) already ships a live app, 58-case eval harness, App Home dashboard, CI badge, and a polished demo GIF.

**Verdict:** This would pass Stage 1 and fight for a podium spot in **New Slack Agent**, but it would not sweep. With ~7 hours left, the highest-ROI moves are: (1) prove the Slack spikes, (2) deploy, (3) record the video, and (4) fill the submission placeholders with real numbers.

---

## Local verification (actually run)

| Check | Command | Result |
|---|---|---|
| TypeScript | `npm run typecheck` | ✅ clean |
| Tests | `npm test` | ✅ 91/91 passed |
| Eval harness | `npx tsx evals/run.ts` | ✅ 100% on fake-LLM deterministic guarantees |
| Offline smoke | `npm run smoke` | ✅ `SMOKE PASS` |

The deterministic guarantees (fail-closed, ACL, injection resistance, citation-subset guard) are real and property-tested. The risk is that **grounded recall / citation faithfulness with a real LLM have not been measured**, and the Slack RTS integration has not been exercised against a live workspace.

---

## Stage 1 — pass/fail checklist

| Requirement | Status | Evidence / Gap |
|---|---|---|
| Track selected | ⚠️ fallback | Orgs track unlikely (no Marketplace listing + 5 workspaces). New Slack Agent is the realistic primary track. |
| Text description drafted | ✅ | `docs/SUBMISSION.md` |
| Demo video < 3:00 | ❌ missing | `docs/VIDEO_SCRIPT.md` exists; no recording. |
| Architecture diagram | ✅ | `docs/architecture.svg` + `docs/ARCHITECTURE.md` |
| Sandbox URL + judge access | ❌ missing | No sandbox provisioned; `slackhack@salesforce.com` / `testing@devpost.com` not added. |
| Working install matching video | ❌ cannot verify | Not deployed; code only verified offline. |
| ≥1 qualifying tech | ✅ | Uses Slack AI, RTS, MCP |
| English / original work | ✅ | MIT license, public repo |
| Member access granted | ❌ missing | No sandbox to grant access on. |

**Stage 1 risk:** A missing video or sandbox is an automatic loss before creativity is judged.

---

## Stage 2 — scored criteria (estimated)

| Criterion (25% each) | Score | Why |
|---|---|---|
| **Technological Implementation** | 8.5/10 | Load-bearing use of all three sponsor techs; strong invariant; 91 tests; eval harness; CI. Dinged for unverified RTS private-channel path and missing live deployment. |
| **Design** | 6/10 | Block Kit fallback table works but is basic. No App Home, no Data Table, no Canvas, no streaming UI, no demo GIF/video. |
| **Potential Impact** | 6.5/10 | Narrow, relatable workflow (security questionnaires). No real user quote or measured time-saved number yet. |
| **Quality of the Idea** | 7/10 | Clear, defensible concept. Not novel — competitors are also doing “org memory from Slack” — but the fail-closed compliance angle is a credible differentiator. |
| **Estimated total** | **~28/40** | Good enough to be in the conversation; not a runaway winner against Consensus/CornerCheck/Lore. |

Tie-breaker order is **Tech → Design → Impact → Idea**, so engineering depth is the best lever — the current build already leans into that, but it must be *demonstrable* in a live sandbox.

---

## Detailed failures / gaps

### 🔴 Critical (will lose points or fail Stage 1)

| # | Gap | Location | Why it matters |
|---|---|---|---|
| 1 | **No live sandbox / deployment / video** | whole project | Stage 1 traps. Judges cannot verify what they cannot run. |
| 2 | **RTS integration unverified** | `src/app.ts:158-161`, `src/slack/rts.ts:70-83` | `action_token` harvesting is a TODO (S2). If the payload shape is wrong, every search fails and every answer becomes *Needs SME*. |
| 3 | **Private-channel ACL demo may not work** | `slack/manifest.json:38`, `src/slack/visibility.ts:13-31` | Manifest only has `search:read.public` (bot scope). Real private-channel search typically needs a **user OAuth token** with `search:read`. The seed script puts the ACL evidence in `#compliance-private`, but the bot may never retrieve it, breaking the judge walkthrough. |
| 4 | **Sessions are in-memory only** | `src/app.ts:60-67`, `src/slack/flows.ts:22-32` | On Render free tier the app spins down after 15 min. A cold start wipes review sessions, so buttons from a posted table silently no-op. |
| 5 | **Claimed streaming is not implemented** | `src/app.ts:214-221`, `docs/SUBMISSION.md:36` | README says “streams a plan.” `runQuestionnaire` has an `onProgress` callback, but `app.ts` ignored it until this audit. It now posts progress messages, but there is no `chat.startStream`, no task cards, no Data Table. |
| 6 | **No real-LLM eval numbers** | `docs/EVALS.md:33-35` | The 100% numbers are from a deterministic fake LLM. A real judge will value measured real-model grounded recall; the placeholders in `docs/SUBMISSION.md` are still `[X]%`. |

### 🟡 Important (differentiates winner from runner-up)

| # | Gap | Location | Why it matters |
|---|---|---|---|
| 7 | **No App Home / dashboard** | `slack/manifest.json:10-14` | Competitors (Consensus, Lore, Quorum) ship App Home with live counters, decision logs, and configuration. This submission has only the Messages tab. |
| 8 | **No Data Table / Canvas / Workflow step** | `src/slack/blocks.ts:59-119` | The review UI is sections+buttons. Sponsor guidance emphasizes native Block Kit Data Tables; winner submissions use Canvas/Workflow steps. |
| 9 | **Review table pagination breaks action context** | `src/slack/blocks.ts:99-116` | Clicking “Next page” posts a new message; the original table stays. Fine for MVP, but less polished than competitors. |
| 10 | **Slow per-question retrieval** | `src/core/planner.ts:122-167` | 41 questions ≈ 5 min at 10 req/min. A 200-row questionnaire (shown in the video script) would take ~20 min. No partial results or cancellation. |
| 11 | **No demo assets** | `docs/VIDEO_SCRIPT.md` | Consensus has a demo GIF; Lore has a YouTube video. Asked & Answered has only a script. |
| 12 | **Submission placeholders unfilled** | `docs/SUBMISSION.md:13,45-48,56` | `[REAL HUMAN QUOTE]`, `[X]%`, `[URL]` brackets are still there. |
| 13 | **`assistant_thread_context_changed` handler was mis-named** | `src/app.ts:139` (fixed) | Was `app_context_changed`; the event would never fire. Fixed during this audit. |

### 🟢 Minor / polish

| # | Gap | Location | Why it matters |
|---|---|---|---|
| 14 | Inconsistent test count in docs | `docs/ARCHITECTURE.md:93`, `docs/JUDGE_WALKTHROUGH.md:60` | Said 85; actual is 91. **Fixed during this audit.** |
| 15 | No ADRs / formal verification | `docs/` | Top competitors (CornerCheck, Relay, Consensus) publish architecture decision records or formal/probabilistic guarantees. |
| 16 | `route_to_sme` carries ref in a context block | `src/slack/blocks.ts:224-237` | Fragile if Slack changes context rendering; works but could be more robust with `block_id`/private metadata. |

---

## Competitor head-to-head

Public GitHub-visible entries assessed from their READMEs and repo structure.

| Project | Track | Stack | Engineering signals | Where Asked & Answered stands |
|---|---|---|---|---|
| **[Consensus](https://github.com/BitTriad/consensus-slack-agent)** | **New Slack Agent** | JS/Bolt, Mongo/SQLite, Render | 58 eval cases, P 1.000 / R 0.964, 9/9 injection defeats, App Home dashboard, ephemeral contradiction alerts, CI badge, live deployment | **Direct rival.** Consensus has more eval cases, a live app, App Home, and a polished demo GIF. Asked & Answered’s advantage is the tighter compliance narrative and the permission invariant; it loses on Design and demo polish. |
| **[Quorum](https://github.com/usv240/quorum-slack-agent)** | Agent for Good | Python/Bolt, AWS EC2 | 31 tests, per-user OAuth for private RTS, App Home, 24/7 EC2, ADRs | Strong “inclusion” narrative. Asked & Answered has more tests and a sharper safety invariant; Quorum has better live deployment and App Home. |
| **[Lore (drMurlly)](https://github.com/drMurlly/lore-slack-agent)** | Agent for Good | Python/Bolt | 191 tests, knowledge graph, Canvas reports, YouTube demo, MCP glossary | Broader research surface. Asked & Answered is more focused and fail-closed; Lore has demonstrable polish and a video. |
| **[Lore (atcuality2021)](https://github.com/atcuality2021/lore-slack-agent)** | New Slack Agent | Python, Postgres/Qdrant/Redis, React console | MCP client+server, durable intake, approval gateway, admin console | Much broader scope; Asked & Answered is more coherent and complete for its one workflow. |
| **[CornerCheck](https://github.com/StephenSook/cornercheck)** | Agent for Good | Python, Render | 252 tests, Z3 formal proof, conformal prediction, live dashboard, Data Table, Canvas, Workflow step | The engineering bar for the whole hackathon. Asked & Answered is not at this level of evidence/formalism. |
| **[Relay](https://github.com/indrapranesh/relay-crisis)** | Agent for Good | TypeScript, Fly.io | Event-sourced ledger, 86.1% extraction eval, load benchmark, human-gated MCP writes | Comparable engineering rigor; stronger impact story and operational detail. |

**Bottom line for the New Slack Agent track:** Consensus is the one to beat. It is live, measured, and polished. Asked & Answered can still win this track if it demonstrates its compliance invariant flawlessly in a live sandbox with a tight video, but it cannot win on code alone.

---

## Prioritized action plan (~7 hours left)

Do these in order. Do not start a lower item until the one above it is done.

### Hour 0–1: Prove the Slack spikes
1. Provision a Slack Developer Program sandbox.
2. Create the app from `slack/manifest.json`, install, and run `npm run dev`.
3. DM the app 3–4 questions from `docs/JUDGE_WALKTHROUGH.md`.
4. Verify:
   - `assistant_thread_started` / `message.im` fire.
   - `action_token` arrives and `assistant.search.context` returns hits (spike S2).
   - The private-channel ACL story actually works; if not, **pivot the demo to a public channel the judge user is not in**, or add per-user OAuth like Quorum.
5. Run `scripts/seed-sandbox.ts` and add `slackhack@salesforce.com` / `testing@devpost.com`.

### Hour 1–2: Measure real evals
1. Run `AA_EVAL_LLM=anthropic|azure|openai … npx tsx evals/run.ts` with a real model.
2. Copy the numbers into `docs/EVALS.md` and `docs/SUBMISSION.md`.
3. If grounded recall is <90%, be honest in the submission; the fail-closed/injection numbers are still 100%.

### Hour 2–3: Deploy
1. Push the repo (CI workflow is already restored).
2. Deploy to Render via `render.yaml` or to Railway; set all secrets.
3. Point the Slack app’s Request URL at `https://<host>/slack/events` (omit `SLACK_APP_TOKEN` for HTTP mode).
4. Add a free uptime ping to `/health` through Aug 11.

### Hour 3–5: Record the demo video
1. Get the real human quote + hours number.
2. Record per `docs/VIDEO_SCRIPT.md` (≤2:40; product on screen by 0:20; refusal is the peak).
3. Upload to YouTube as **public** immediately (processing lag is real).

### Hour 5–6: Fill and submit Devpost
1. Fill all brackets in `docs/SUBMISSION.md`.
2. Submit to Devpost (track: **New Slack Agent** unless Marketplace gate is magically achieved).
3. Grant judge access; paste sandbox URL + App ID.

### Hour 6–7: Buffer / quick polish
- If time remains, add a simple App Home or a Data Table block for the review UI.
- Otherwise, use this hour to re-test the judge walkthrough end-to-end one more time.

---

## What was fixed during this audit

- `docs/ARCHITECTURE.md`, `docs/JUDGE_WALKTHROUGH.md`, `docs/SUBMISSION.md`: corrected test count from 85 → 91.
- `README.md`: added CI badge.
- `src/app.ts`: wired `onProgress` to post Slack messages so the “streaming plan” claim is partially realized; fixed `app_context_changed` → `assistant_thread_context_changed`; added `assistant_thread_started` greeting.
- Re-ran `npm run typecheck`, `npm test`, `npm run smoke` — all green.

---

## Final honest take

Asked & Answered has the **engineering skeleton of a winner**: a clear workflow, a load-bearing invariant, real tests, and all three sponsor technologies. But a real judge does not score skeletons — they score a **live, polished, demonstrable product**. Until the sandbox, deployment, video, and real eval numbers are done, this is a high-quality draft, not the undisputed winner. The next 7 hours should be spent almost entirely on **operational proof**, not more code.
