# Execution Plan — Asked & Answered (anchored IST; written Sat Jul 11, 09:30 IST)

**Hard deadline:** Tue Jul 14, 05:30 IST (Jul 13, 5:00 PM PT). **Self-deadline (submission complete):** Mon Jul 13, ~11:00 IST (Jul 12 night PT). ≈ **50 working hours** in 3 blocks. Solo + Claude Code.

## Phase 0 — Spikes & gates (Sat 10:00–16:00 IST, ~6h) — NO feature code before these
- [ ] Join Slack Developer Program; provision sandbox. Create **App A** (internal).
- [ ] S1: `slack create agent` scaffold (agent_view) → verify `app_home_opened` / `app_context_changed` / `message.im` fire. (≤1.5h)
- [ ] S2: action_token spike — file-upload event → token → 9 spaced `assistant.search.context` calls → log semantics. (≤1.5h)
- [ ] S3: Data Table block render spike; commit to fallback interface (paginate at 20 rows). (≤1h)
- [ ] S4: Create **App B**, activate distribution, create 5 defensibly-real workspaces, install via OAuth, generate genuine usage; open Marketplace pre-submission checklist and watch the 5-workspace counter. (≤2h, then background)
- [ ] Repo public + MIT license + CI skeleton + README stub. (≤0.5h)
- [ ] Message a real security engineer / AE contact for the 30-min interview (async; needed by Sun).
- **Gate G0 (16:00 Sat):** any spike red → apply its pre-designed fallback now (per-batch token refresh / paginated sections / etc.).

## Phase 1 — Core engine (Sat 16:00 – Sun 02:00 IST, ~10h)
- [ ] xlsx/csv + pasted-text intake; question parser + dedupe (tests first on fixtures).
- [ ] RTS module: action_token plumbing, per-question query strategy, 10/min budgeter, `include_context_messages` context, keyword-mode default, `assistant.search.info` probe. OR-batch mode behind a flag.
- [ ] Drafting pipeline: per-sentence citation binding; three-state classifier (Verified / Grounded / Needs SME); **fail-closed default**.
- [ ] Answer library store (app-authored answers + permalink pointers only — zero-copy); **ACL revalidation on Verified reuse**.
- Milestone M1: CLI-level run: file in → states+drafts+citations out, hermetic tests green.

## Phase 2 — Slack surface (Sun 09:00–19:00 IST, ~10h)
- [ ] agent_view loop: streaming plan (`chat.startStream`/append/stop, plan + task cards), setStatus/setTitle/suggested prompts.
- [ ] Review surface: Data Table (or fallback) + row Cards + `feedback_buttons`; approve/edit/reject handlers.
- [ ] SME routing DM with `context_actions`; manual owner pick (heuristics only if time).
- [ ] Hash-chained ledger + `/aa verify`.
- [ ] xlsx export via `files.upload` with footnoted citations + approval record.
- Milestone M2 (~hour 20 target): **deployed publicly** (Fly.io/Railway); full journey works end-to-end in sandbox.

## Phase 3 — Judge-readiness + depth (Sun 19:00 – Mon 03:00 IST, ~8h)
- [ ] Seed judge sandbox: realistic company (channels, threads, planted files, 5 adversarial injection docs, 15 unanswerable questions' worth of gaps).
- [ ] Grant Member access: slackhack@salesforce.com + testing@devpost.com. Judge README (exact steps, ≤5-min journey).
- [ ] Own MCP server: `search_answers`, `get_answer_provenance` (readOnlyHint), manifest; demo from Claude Code.
- [ ] Eval harness: 30–40 labeled questions; 3 metric families; run → **record the real numbers**; publish config + results in README.
- [ ] Tests to ~60 meaningful; CI green. ARCHITECTURE.md + diagram (where AI/MCP/RTS sit). LIMITATIONS.md.
- **Gate G1 = T-48h check (Sun eve):** Marketplace pre-submission checklist green? → stay Orgs (finish listing within the 6h box: landing/support/privacy pages, assets, AI disclosures; submit; capture App ID). Not green → **lock New Slack Agent**, swap pre-written text.

## Phase 4 — Story & submission (Mon 09:00–23:00 IST, ~10h)
- [ ] Interview clip/quote from the real human; synthetic 200-row questionnaire prop.
- [ ] Record demo per v2 script (≤2:40; product by 0:20; refusal is the peak; ledger tamper theater; measured-numbers card with asterisk). Edit; upload to YouTube (public) early — processing lag is real.
- [ ] **Questionnaire #2 T-36h check (Mon ~17:00):** compounding run measured working? include clip; else eval card closes.
- [ ] Devpost form: track, human-voiced description (mirrors rubric; keyword-complete: "MCP server integration", "Real-Time Search API", "Slack AI"), architecture diagram, video link, sandbox URL, App ID (if Orgs), OSS disclosures.
- [ ] **SUBMIT — Mon Jul 13 by ~23:00 IST** (≈ Jul 13 10:30 AM PT, > 6h margin). Devpost allows edits until the deadline — refine after.
- Tue morning IST: final sandbox smoke-run as a fresh user; fix-and-resave margin until 05:30 IST hard stop.

## Standing rules
1. The 5-subsystem demo journey is never cut; everything else has a pre-agreed cut order: Canvas-anything → owner heuristics → questionnaire-#2 → eval breadth (never below refusal+injection subsets).
2. No unmeasured number in any artifact.
3. Every video moment must reproduce in the judges' sandbox on App A.
4. Marketplace work total ≤6h, hard stop.
5. Commit early, commit often — dated history is originality evidence.
