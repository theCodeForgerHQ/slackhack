# Decisions log (ADR-lite)

One entry per spike verdict, frozen contract, or platform fact. Newest first within each stage.

## Whole-repo audit (post-build hardening)

### 2026-06-10 - Audit PR-C: docs and tests catch up to the code

- HANDLER-LEVEL TESTS (the suite audit's top gap): the Slack glue layer (assistant
  dispatch, all Block Kit action handlers, App Home views) was the only code a judge's
  clicks execute that CI never executed; its blanket fail-closed excepts meant a
  regression would first surface MID-DEMO. tests/unit/test_handlers.py now pins the
  composition with recorders: verdict card on CLEAR, picker on ambiguity, board on a
  card, fail-closed replies on crashes, thread-targeted action replies, valid home
  blocks including the DENIED rendering, honest fallback view.
- PROD GUARD on clean_ledger: the fixture TRUNCATEs whatever DATABASE_URL points at;
  one local run against the Render DB would have destroyed the production audit ledger.
  Non-local hosts now refuse unless CI or CORNERCHECK_ALLOW_TEST_TRUNCATE is set.
- Weak assertions tightened: the CLEAR-card test passed even with the labels swapped
  ("CLEAR" is a substring of "DO NOT CLEAR"); the identical-twins typo test accepted
  the crowding bug it exists to catch; the dashboard chain assert admitted every value.
- Comment truth pass (every item verified against code): the conformal docstrings
  claimed inf-quantile = "certifies nothing" when an inf gate would certify EVERYTHING
  (load_gate validation is the real guard; docstrings now say so); prove_identity_gate
  relabeled as the contract AXIOM check it is (consistency, not code-derived proof),
  in the demo script output too; canvas export, monitor cadence, schemas field name,
  parse comments, audit_table date, seed_demo rate comment, judge-canvas wording.
- Consolidation: er/names.py is the single name-normalization vocabulary (norm for
  scoring, fold for seed keying, semantics unchanged and documented); app/context.py
  unifies the two divergent action-token extractors; dead code removed
  (project_suspension, today(), today_iso()).
- Docs: architecture.md rewritten to the shipped system (corroboration node, conformal
  gate, monitor, ledger _meta, live proof; it contradicted the README diagram);
  README layout now lists all 11 packages and the documented triplet matches CI
  exactly (ruff format --check included); counts true everywhere (251); the
  "live-marked tests excluded" claim dropped (no test carries the marker); pyproject
  gains urls/classifiers/authors.
- DESIGN NOTE made explicit (wiring audit DISC-3): the freeform agent can never pass
  the ledger gate because only the deterministic pipeline confirms fighters into the
  session. Intentional: the agent reads everything, only the pipeline writes.


### 2026-06-10 - Audit PR-B: every product surface hardened

- Injury scan is now a TRI-STATE: an attempted-but-failed scan (API error or response
  shape drift) returns ok=False and the verdict card says "Workspace injury scan
  unavailable" instead of rendering identically to "no chatter found". No-token
  surfaces are expected, not failures. The freeform brain prompt carries the same note
  so the model never narrates "no injury chatter" over a dead scan.
- Ledger tamper-evidence now covers METADATA: append_entry stamps _meta (actor, action,
  app-time) INSIDE the hashed payload ("_meta" is reserved; producers using it are
  refused loudly); verify cross-checks the columns against the stamp, including a
  backdated/postdated ts (120s skew tolerance), and reports how many rows were
  meta-checked. The daily ops digest carries the chain head (seq + hash) as an EXTERNAL
  truncation anchor in Slack history; dedup compares anchorless text so the advancing
  head cannot kill duplicate suppression (the suite caught exactly that regression).
  Scope documented honestly in the verify tool description, including its conditions.
- Brain client poisons on ANY abnormal mid-stream exit (BaseException), not just
  timeout: an abandoned response tail can never serve as the next thread's answer. The
  status callback swallows its own Slack errors. CORNERCHECK_MODEL_FALLBACK is now
  actually wired (ClaudeAgentOptions.fallback_model).
- @CornerCheck channel mentions get the deterministic pipeline (verdict card / board /
  pointer, fail-closed), ending the mention-silence gap; the card board gained the same
  audit/proof buttons as the verdict card; App Home renders denials as :no_entry:
  DENIED (a refused CLEAR no longer wears green) and publishes an honest fallback view
  when the ledger is unreachable; manifest suggested prompts now name real seeded
  fighters (the fictional spike-era "Dragan Petrovic" is gone).
- Smalls: pool self-heals severed connections; migrations name the failing file;
  proof-card coverage phrase reads the live calibration artifact (logged fallback);
  dashboard tryline/conformal copy fixed + inline favicon (console now clean).

### 2026-06-10 - Eight-brain repo audit: three safety BLOCKERs found and fixed

- A seven-reviewer parallel audit (Gemini whole-repo, silent-failure hunter, mock/hardcode
  hunter, wiring tracer, test-suite analyzer, comment auditor, organization reviewer; the
  Codex eighth honestly reported unavailability) plus a Playwright browser pass over the
  live dashboard. Three genuine safety BLOCKERs that 219 green tests never touched:
  1. GHOST FIGHTER = CLEAR (live-reproduced): a valid-but-absent fighter id returned zero
     suspensions and evaluated to CLEAR with "no-active-suspension". Fixed: every
     evaluation/write path now refuses when the fighter row is absent (LookupError into
     the fail-closed surface; the MCP write tool ledgers the refusal).
  2. RULES YAML FAILED OPEN: a typo'd key in the sparring overlay silently became a 0-day
     no-contact window after a KO, still printing a sourced-looking rule id. Fixed:
     load_rules validates every Outcome has a positive int in every table (refuses to
     LOAD), and the lookup is [outcome], never .get(outcome, 0).
  3. LOCK 1 / LOCK 2 DEADLOCK: the in-tool re-check validated the RAW engine verdict
     while the hook validated the corroboration-TIGHTENED one, so tightened cases had no
     writable decision (failed closed, with spurious denials). Fixed: lock 1 now applies
     the same tighten() composition and compares against the composed verdict; the write
     payload carries the corroboration evidence like every pipeline write.
- Also in this pass: the MCP subprocess gained logging (its failures were invisible to
  operators), er_fighter_details aligned to the ERROR envelope shape, and a test
  assertion that was missing "in md" (always-true) repaired.
- Remaining audit fixes are staged as PR-B (product surface: manifest prompt placeholder
  "Dragan Petrovic", app_mention handler, card-board buttons, dashboard copy + favicon,
  brain poison asymmetry, injury-scan tri-state, ledger metadata coverage) and PR-C
  (docs/test hygiene): full plan in project memory.

## Galaxy tier 2

### 2026-06-09 - Workflow Builder custom step: the verdict as a building block

- app/workflow_step.py + manifest `functions.check_fighter_clearance` (inputs fighter_name
  required + jurisdiction optional; outputs status/detail/fighter) + settings
  function_runtime=remote. Any workflow can branch on the SAME deterministic verdict the
  assistant gives; every check ledgered by the same pipeline.
- FROZEN CONTRACT for automation: the step NEVER auto-clears and never resolves ambiguity
  itself. NEEDS_PICK/NOT_FOUND return as explicit statuses with "NOT cleared" detail, and
  any internal error calls fail(), which HALTS the workflow: a halted workflow cannot book
  a fighter. Pure outputs mapping unit-tested per status.
- Manifest batch (ONE reinstall covers everything): functions block + function_runtime +
  pins:write (lets judge_canvas.py pin the tour). HUMAN STEP 4f: re-apply
  slack/manifest.json, Save, Reinstall to workspace; the step then appears in Workflow
  Builder under the CornerCheck app.

### 2026-06-09 - WAVE B docs: demo script v2.1 + Devpost v2, judge-panel fact-checked

- Both judge-facing docs rewritten around the full 9-feature reality, then run through an
  adversarial judge-lens fact-check that verified EVERY number against the repo (207 tests,
  54 cases, 4203/95% conformal, Z3 scope) and caught real issues, all fixed:
  (1) BLOCKER: the script's beat math ended at exactly 3:00 against a strictly-under rule
  with VO densities up to 256 wpm; retimed to 2:53 with ~145 wpm word budgets per beat.
  (2) DATA BUG: "14 jurisdictions" was string-variant inflation (10 actual commissions);
  fixed at the ROOT with migration 008 (normalizes existing rows, incl. prod at next boot)
  + normalized JSON (top-up proven to add 0 after, no dupes) so the dashboard now says 10
  honestly. (3) "4,203 real query/fighter pairs" overclaimed: they are query VARIANTS built
  from the real fighter table; reworded to match what calibration.json itself says.
  (4) Three pausable-frame contradictions in the script (cached-vs-live wording, "posted
  days earlier" vs same-day seeding, the conformal footnote pointed at a human-pick card
  that shows a different note). (5) The demo card paired a bantamweight with a heavyweight;
  now division-plausible (dos Santos vs Blaydes, Silva vs Tavares) and still hits all three
  bands. (6) Devpost gained an explicit Design paragraph (the under-represented criterion).
- Judge canvas script (scripts/judge_canvas.py): creates + shares + posts the five-minute
  tour Canvas in a #start-here channel (Stephen runs once; pin needs pins:write, batched
  into the next manifest reinstall). 4th suggested prompt: the Jon Jones famous case.

### 2026-06-09 - The deployed URL becomes a live public dashboard

- app/static/dashboard.html (committed, self-contained; Barlow Condensed + IBM Plex Mono,
  bout-sheet aesthetic) + app/dashboard.py + rewired web.py routes: `/` dashboard,
  `/api/stats` (live DB counts + chain verified + conformal gate + last monitor run),
  `/api/proof` (runs the REAL Z3 equivalence proof + non-vacuity control per request,
  ~5ms, healthy ONLY on the exact PROVEN+COUNTEREXAMPLE pair), `/healthz` unchanged.
  The judge's first click now lands on a living, self-verifying system.
- FAIL-SOFT per section: DB down -> page renders with unavailable markers, stats return
  partial JSON, never 500; handler crashes return fixed JSON, never a stack trace.
- Adversarial gate caught pre-merge (all fixed + pinned): (1) the chain-status fail-soft
  path echoed RAW EXCEPTION TEXT (DB host:port class) to the public JSON; (2) uncached
  /api/stats was a DoS lever against the SHARED clearance pool (count(*) scans + full
  chain re-verification per request, abandoned check-threads parking on the pool's 30s
  queue) -> 30s in-process result cache + 2s pool timeout for dashboard reads; (3) the
  default Server header fingerprinted the exact Python version; (4) a transient page-read
  failure permanently poisoned the lru_cache with the fallback; (5) HEAD returned 501 to
  uptime monitors; unknown paths returned false 200s.
- boxing cache TTL 7 -> 21 days (career records change only when a fighter fights; keeps
  the demo period warm on one live call per boxer).

### 2026-06-09 - Cited cases 15 -> 54, coverage-honesty panel, prod case top-up

- 39 new VERIFIED suspension cases merged into seeds/data/curated_suspensions.json. Sourcing
  pipeline: 5 parallel research agents (different source modalities), 58 raw -> 40 deduped ->
  39 survived adversarial re-fetch verification (every source_url re-fetched, quote checked,
  refute-by-default; 1 rejected). 5 cases then spot-verified BY HAND against their pages
  (incl. firecrawl for a bot-gated ESPN page). Spread: 28 MMA + 11 boxing, 9 jurisdictions,
  all four types, judge-recognizable names (Jones, McGregor, Khabib, Canelo, Wilder, Fury,
  Tyson) AND fresh 2025-2026 cases with active/recently-lapsed windows (Taira, Pimblett,
  Brady/Edwards) that feed the roster monitor demo. Mike Tyson 1997 kept: the data honestly
  says "license revoked"; modeled as indefinite administrative.
- COVERAGE-HONESTY PANEL on App Home: live counts (cases, jurisdictions, fighters) + the
  honesty line ("a CLEAR means no recorded suspension matched; commissions remain the source
  of truth; not an exhaustive registry"). Fail-soft if the query breaks.
- PROD CONVERGENCE: bootstrap now calls seed_db.top_up_cases() when the DB is already seeded:
  ADDITIVE-ONLY, idempotent (keyed by fighter+start_date+jurisdiction, backed by a unique
  index from migration 007 + ON CONFLICT DO NOTHING for concurrent-boot race safety),
  ledgered as cases_topped_up. SCOPE: additions only; corrections to an existing case
  (end_date, reason, sources) do NOT propagate and require a --force reseed.
- IDENTITY-SPLIT GUARD (adversarial gate BLOCKER, fixed): case spellings that differ from
  the roster ("T.J. Dillashaw" vs "TJ Dillashaw", "Julianna Peña" vs "Julianna Pena")
  silently minted SHADOW fighters carrying the suspension while the real fighter read
  clean: the human-pick path then steered to the real (clean) row, a false CLEAR one
  click away. Fixed: the seeder fold-normalizes names (punctuation + diacritics) and
  ATTACHES a spelling-variant case to the real roster row; ambiguous 2+ matches refuse
  loudly. Deliberately NOT fuzzy: a first JW>=0.94 guard false-flagged "Ryan Garcia" vs
  "Ryan Gracie" (different real people) and broke the seed; fold-equality has no such
  false positives.
- Conformal artifact recalibrated post-merge (case fighters join the population): n=4203,
  floor=0.9436, holdout 95.1%.
- JUDGE-QUESTION FRAMING (deliberate): an indefinite suspension with no RECORDED lifting
  blocks forever (Jon Jones 2017, Sean O'Malley 2024 read DO_NOT_CLEAR today even though
  both later fought). That is fail-closed semantics, not a data bug: the card cites the
  recorded action, says "INDEFINITE (until cleared)", and directs to commission
  verification. Ten false blocks beat one false clear; the lifting of a medical suspension
  rarely makes the news, and the commission remains the source of truth.

### 2026-06-09 - Audit trail exports to a Slack Canvas (chain-verified at export time)

- "Export to Canvas" button on the audit table (action export_audit_canvas). app/canvas.py
  builds deterministic markdown from the ledger (chain VERIFIED immediately before export;
  a broken chain renders "do not trust this export"), creates a standalone canvas
  (canvases.create), grants the channel read access, posts the permalink.
- FROZEN CONTRACT: a failed EXPORT must never read as a failed AUDIT. Every failure path
  (missing scope, plan gate, network, permalink lookup) returns an actionable note and the
  in-Slack table stays authoritative. Handler never raises into the listener.
- Manifest gained canvases:write + files:read. HUMAN STEP (board 4e): re-apply
  slack/manifest.json in the app config and reinstall to the workspace; until then the
  button replies with exactly that instruction (fail-soft, demoable either way).
- Also fixed: the pre-existing audit table builder crashed on a non-dict ledger payload
  (poison-row guard added, same pattern as the monitor's).

### 2026-06-09 - In-product live Z3 proof button: the proof becomes a clickable surface

- Every verdict card now carries "See the safety proof" (action view_safety_proof): the
  handler runs prove_engine_equivalent_to_spec LIVE (~4 ms) plus the non-vacuity control
  (loosened start boundary must yield a counterexample), and app/blocks/proof_card.py
  renders from ProofResult fields only.
- FROZEN CONTRACT: a failed proof must NEVER render as reassurance. healthy requires
  EXACTLY (positive PROVEN, control COUNTEREXAMPLE); every other combination renders the
  PROOF FAILED alarm ("treat every CLEAR as unsafe"). Probed exhaustively in review (13
  unhealthy combinations all alarm). Handler exception fails closed ("treat unproven").
- Scope honesty on the card: suspension-window logic by Z3; identity separately by
  conformal calibration; human makes the call.
- Review also fixed two pre-existing z3_safety.py 'unknown' branches (crash instead of
  UNKNOWN; control mislabeling unknown as PROVEN); both were already fail-closed at the
  card layer, now also honest at the source.

## Galaxy tier 1

### 2026-06-09 - Proactive roster monitor: deterministic daily digest, ledgered alerting

- src/cornercheck/monitor.py: daily in-process daemon thread (gate = the LEDGER's last
  monitor_run timestamp, so restarts never double-fire and never skip a due run) + CLI
  entrypoint (`python -m cornercheck.monitor`) for an external cron later.
- FROZEN CONTRACT (per the gimmicks-to-avoid list): every trigger DETERMINISTIC. Window
  arithmetic (end_date within [today, today+14] lapsing; [today-7, today-1] lapsed: the Tim
  Hague mode) + ledger diffs since the last run (DO_NOT_CLEAR decisions, corroboration
  DISAGREED, suspensions.created_at). No LLM decides, phrases, or filters an alert. Quiet
  days send NOTHING (format_alert returns None on empty findings; no synthetic cheer).
- Auditable alerting: every run writes a monitor_run ledger entry (findings + alerted +
  posted), so the alert history is itself hash-chained. "Since last run" reads the ledger,
  not mutable state.
- Push = Slack incoming webhook (OPS_WEBHOOK_URL), fail-quiet: unset/unreachable still
  ledgers and logs; monitoring can never crash the service. In-process over a Render cron:
  zero new infra and cost; the CLI entry keeps the cron option open.
- HUMAN STEP (board 4c): Stephen creates the #cornercheck-ops incoming webhook and sets
  OPS_WEBHOOK_URL in .env + Render. Until then the monitor runs and ledgers, push disabled.
- Adversarial gate caught pre-merge (all fixed + pinned): (1) BLOCKER, a wall-clock "since"
  watermark had a PERMANENT silent blind spot (anything committed during the gather-to-
  ledger-write window, including the webhook round-trip, was missed forever while coverage
  looked contiguous); fixed with a seq watermark captured in the gather snapshot (seq order
  is commit order under the chain's advisory lock, so `seq > prior` is exact). (2) A missing
  ledger HMAC key would have pushed an identical un-auditable digest EVERY HOUR; fixed with
  a preflight (alerting that cannot be ledgered must not fire) + a duplicate-digest memo.
  (3) A malformed webhook URL raised outside the try and leaked the secret URL into logs
  hourly; fixed (constructed inside try, error logged without echoing).
- Documented semantics: first run baselines the diff at 24h ago; indefinite (until cleared)
  suspensions have no window to lapse, are excluded from window scans (`AND NOT indefinite`),
  and surface as a standing count line whenever a digest fires anyway (never alone: quiet
  days stay quiet); "today" is the UTC date, which can only read a window as lapsed EARLY
  (the safe direction).

### 2026-06-09 - Conformal identity gate: the threshold stops being hand-tuned

- er/conformal.py (exact split-conformal quantile, ~60 lines, cited: Vovk; Angelopoulos &
  Bates 2023) + scripts/calibrate_er.py (deterministic seeded calibration against the REAL
  fighters table, split BY FIGHTER, holdout coverage recorded) + committed artifact
  er/calibration.json (alpha=0.05, n=4187, q_hat=0.0593, floor=0.9407, holdout 95.5%;
  ORDER BY COLLATE "C" pins cross-machine determinism of the seeded generation).
- DELIBERATE: no MAPIE/scikit-learn. The roadmap suggested MAPIE; split conformal on a 1D
  nonconformity score is a quantile, and writing it out keeps the guarantee auditable and the
  deps at zero (same discipline as the stdlib API client).
- FROZEN CONTRACT: tighten-only composition in band(). Legacy CONFIRMED additionally requires
  the conformal prediction set be a SINGLETON; 2+ plausible candidates demote to AMBIGUOUS
  (Chow's reject rule, calibrated). The gate never promotes. Non-finite q_hat or unusable
  artifact disables the gate WITH annotation (a single-candidate retrieval under an inf
  quantile would otherwise read as a meaningless "singleton certification": caught in design
  review, pinned by test).
- SCOPE, stated honestly (the Z3 lesson): the guarantee is MARGINAL (not per-query) and
  conditional on the true fighter being retrieved (retrieval is deliberately high-recall).
- Now BOTH halves of the fail-closed claim carry formal backing: Z3 proves the rules half,
  conformal coverage certifies the identity half.

### 2026-06-09 - Live boxing-data.com corroboration: a second source that can only tighten

- sources/boxing_data.py (stdlib urllib client, Postgres response cache, recorded-real demo
  fixtures) + sources/corroborate.py (deterministic comparison, no LLM) + tighten-only
  composition in brain/pipeline.py. CorroborationOut rides every verdict and is ledgered.
- FROZEN CONTRACT: corroboration TIGHTENS only. DISAGREED (live source shows MORE bouts than
  the record on file, when a record IS on file) withholds a CLEAR pending commission
  verification. UNAVAILABLE / UNMATCHED / NOT_APPLICABLE (MMA) annotate and never block:
  absence of evidence is not disagreement. Nothing the live source says can loosen a verdict.
- PLATFORM FACTS (live-probed 2026-06-09, key verified): host boxing-data-api.p.rapidapi.com,
  auth X-RapidAPI-Key; origin Cloudflare BANS default Python user agents (403 "error code:
  1010", and the failed call still burns RapidAPI quota), a product User-Agent passes; search
  is token-fuzzy (full-name query returns up to 25 partial matches; exact casefold match
  required); stats keys are OPTIONAL per fighter and total_bouts is inconsistent with w+l+d
  where present (sums computed on both sides instead); /v2/fights/?fighter_id= returned 0
  bouts for a headline fighter, so the bout-during-suspension check was CUT from V1 (will not
  build on an endpoint that returns empty); free tier 100 requests/month (7-day Postgres
  cache + one search call per uncached boxing fighter).
- DB FACT: all 4 seeded boxing fighters carry 0-0-0 records (record not on file). 0-0-0 means
  "not recorded", never "never fought": the live record FILLS the gap (CONFIRMED), it cannot
  disagree with an empty record. Hugo Alfredo Santillan is absent from the live source
  entirely: the honest UNMATCHED path, demoed with real data.
- Adversarial gates caught pre-merge: (1) BLOCKER, wrong-shape-but-valid-JSON upstream data
  crashed the whole verdict AND poisoned the cache for 7 days (fixed: shape guards + a
  never-raises UNAVAILABLE wrapper in corroborate_fighter); (2) bools/negatives pass
  isinstance(int) and could fabricate CONFIRMED or garbage-block via DISAGREED (fixed:
  type-is-int + non-negative checks); (3) failure-class-blind logging (fixed: exception type
  in every degradation log). Each pinned by a regression test.
- KNOWN GAP (documented, deliberate): the MCP rules_evaluate_clearance tool returns the
  un-tightened rule verdict (corroboration lives in the pipeline path that drives the cards
  and the ledger). Wire it into the MCP surface if/when the agent path needs it.

### 2026-06-09 - Whole-fight-card clearance: the matchmaker's real workflow, fail-closed per slot

- New surface: paste a card ("UFC 310: A vs B, C vs D") and every bout lands on one Block Kit
  board, each fighter banded CLEAR / DO NOT CLEAR / NEEDS PICK with blockers cited. parse_card
  (app/parse.py) extracts fighter slots; clear_card (brain/pipeline.py) fans each slot through
  the proven start_clearance pipeline under an isolated `{thread_key}#cardN` sub-thread (one
  fighter's disambiguation never clobbers another's) and ledgers the batch as `card_check`;
  build_card_board (app/blocks/card_board.py) renders from the deterministic verdicts only.
- FROZEN CONTRACT: parse_card does NO dedup. Two distinct fighters sharing a display name (two
  real Bruno Silvas on one card) must each get a row; each fails closed to NEEDS PICK. Dedup
  here is a fail-open: a never-checked fighter.
- Adversarial gate (silent-failure-hunter) caught 5 fail-open parser bugs pre-merge: same-name
  dedup dropping a fighter; mid-name keyword stripping ("California Kid" mangled); silent
  short-name drops ("AJ"); single-"vs" question misrouted onto a board; "and"-split fragmenting
  names ("Anderson Silva"). All fixed, each pinned by a regression test (tests/unit/test_card.py).
- Routing rule: a card needs 2+ "vs"/"versus" or an explicit card keyword AND 2+ parsed
  fighters; single-vs questions stay on the single-clearance path. Second gate (code-reviewer)
  verified signatures, fail-closed handler parity, and per-fighter ledgering independently: CLEAN.

## Demo + submission prep

### 2026-06-08 - Demo script + Devpost writeup, adversarial fact-check caught real errors

- docs/demo-script.md (10-beat video script: VO lines, camera on/off, recording guide) +
  docs/devpost-submission.md. Forced two parallel reviewers (copy/rubric + adversarial
  fact-check). Both high-value.
- FACT-CHECK CAUGHT (all fixed): (1) 15 U.S.C. 6306(b) is BOXING-ONLY (Muhammad Ali Boxing
  Reform Act); the engine emitted it on every cross-jurisdiction suspension incl. MMA fighters
  (dos Santos demo + 10/15 cases are MMA). A legal overreach a domain judge catches instantly.
  Fixed in CODE: sport-aware consultation note (boxing binding; MMA framed as the gap, which
  STRENGTHENS the thesis). (2) Tim Hague: the 2024 inquiry recommended a single REGISTRY, not
  a "cross-commission view"; his suspension had lapsed, he was a late replacement. Cross-
  jurisdiction is OUR US extension, not the inquiry's words. Corrected. (3) "Kautz Type 2" is
  the wrong cell (Type 2 = Symbolic[Neuro], we are LLM-outer); dropped the number, kept
  "neurosymbolic". (4) Z3 claim scoped to "the suspension-window logic; if a suspension is
  active, never CLEAR" (not the whole system). README + both docs + engine updated.
- DOMAIN FACT (reusable): 15 U.S.C. 6306(b) consult-first is professional BOXING only; MMA has
  no federal equivalent. Use the MMA gap as a strength, never cite 6306 as binding for MMA.
- AI-tone: zero em-dashes, no blocklist words across all judge-facing docs. 114 tests green.

## Stage 7

### 2026-06-08 - Frontier layer: Z3 verification SHIPPED, and it caught a real fail-open bug

- src/cornercheck/verification/z3_safety.py: Z3/SMT verification of the clearance engine.
  NOT a tautology (an adversarial review caught a first draft that was): the engine's
  interval-membership formula (mirrored from rules/engine.py suspension_interval) is proven
  EQUIVALENT to an INDEPENDENTLY written safety spec (_spec_must_block: "started AND not
  properly ended") over all integer dates/intervals. Two formulas, different reasoning, so
  Z3 must solve the logic; any divergence yields a counterexample.
- The proof FOUND A REAL FAIL-OPEN BUG: a suspension with end_date < start_date made
  P.closed(start,end) empty, so the fighter was never active and silently CLEARED. The worst
  direction for a fail-closed system. FIXED in engine.suspension_interval: malformed ranges
  now fail closed (treated as open-ended from start, blocking until a human corrects the row).
- Non-vacuity is itself tested: test_refinement_proof_is_NOT_vacuous monkeypatches a corrupted
  engine_active and asserts Z3 returns a COUNTEREXAMPLE (a green proof under corruption would
  be worthless). Plus teeth demos: the pre-fix malformed-range hole and a >=/> boundary mutation.
- Hypothesis bridge binds the REAL Python evaluate() to the spec on random inputs INCLUDING
  malformed ranges, so the all-inputs Z3 proof and the real code can't silently diverge.
- Identity gate proven (no clearance without a confirmed fighter). 114 tests green.
- Framing: neurosymbolic (Kautz Type 2) in README + submission. scripts/z3_proof_demo.py drives
  the "prove equivalence -> corrupt the engine -> Z3 hands you the broken input" demo beat.
- Adversarial review of the proof: codex-rescue was unavailable (ChatGPT account tier blocks
  the codex model), substituted an independent silent-failure-hunter agent with all tools; it
  ran a 184,500-case cross-check and found the vacuity + the end<start fail-open hole. Both fixed.

### Stage 7 stretch items - ASSESSED, DEFERRED (logged, not silent)

- Conformal prediction with reject option (MAPIE LAC + Chow's rule) on the ER banding:
  deferred. High effort (needs a labeled calibration set of name-match pairs we don't have
  cleanly), marginal value over the existing fail-closed banding (T_HIGH/T_LOW + identical-
  name-always-disambiguate) plus the Z3 proof. Revisit only if time before submission.
- Graph-ER connected components: deferred, same reasoning.

## Stage 1 spikes

### 2026-06-07 - Spike A: Bolt Assistant over Socket Mode = WORKS

- Evidence (live CornerCheck sandbox): `assistant_thread_started` fired on 4/4 pane opens,
  handler latencies 0.445-0.607s; `user_message` echo round-trip 1.043s including
  `set_status` + `say` + `set_title`. All far under the 3s ceiling. Suggested prompts rendered
  and prompt-click sends the prompt text as a user message.
- Fix discovered: `features.app_home.messages_tab_enabled: true` is REQUIRED or the agent
  pane shows "Sending messages to this app has been turned off". Manifest patched (b9cb1b0).
- Surface confirmed by introspection (rule: installed package = truth): slack_bolt 1.28.0
  exports `Assistant`, `Say`, `SayStream`, `SetStatus`, `SetSuggestedPrompts`, `SetTitle`;
  Assistant decorators: `thread_started`, `user_message`, `thread_context_changed`, `bot_message`.
- Observation: the manifest `assistant_view.suggested_prompts` render in the pane; per-thread
  `set_suggested_prompts` from the handler coexists. Revisit which wins during Stage 5.

### 2026-06-07 - Platform fact: no assistant.search.* wrapper in slack_sdk 3.42.0 (latest)

- `WebClient` has no `assistant_search_context` / `assistant_search_info` methods even on the
  newest SDK (3.42.0 == PyPI latest). The RTS endpoints must be called raw via
  `client.api_call("assistant.search.context", json={...})`.
- Consequence for Stage 5: `search/rts.py` wraps the raw call behind our own typed client.

### 2026-06-07 - Spike B: RTS keyword search = WORKS

- **action_token location (the build-critical unknown): `body.event.assistant_thread.action_token`**,
  present on BOTH `assistant user_message` and `app_mention` events; 62-char ephemeral string,
  fresh per event; `assistant_thread` object contains only the token on these events.
- `assistant.search.context` (raw `api_call`, json body: query/limit/content_types/action_token)
  returns `ok=true` + real hits with rich metadata (`author_name`, `author_user_id`, `team_id`,
  `channel_id`, `channel_name`, `message_ts`, `content`).
- **Indexing lag is real: ~1-3 minutes.** Searches fired <1s after posting found 0 hits; the same
  query minutes later found 4. NOT a bot-author filter: bot-posted seeds ARE returned.
  Consequence: `seed_demo.py` posts seeds well before demo time; runbook gets a >=5 min buffer.
- `assistant.search.info` on this sandbox: `{"ok": true, "is_ai_search_enabled": true}`.
  AI search is ON: semantic mode may be available here (upside vs research expectation of
  keyword-only). Test semantic explicitly during Stage 5; keyword remains the designed floor.
- Intermittent `invalid_action_token` observed once on a later app_mention despite a
  fresh-extracted token (suspect single-use/short TTL or event redelivery). Stage 5 `rts.py`
  must degrade gracefully on token rejection (cached/fallback result + retry guidance), never crash.
- Fallback (conversations.history lexicon scan) NOT needed; primary path adopted.

### 2026-06-07 - Spike C: Claude Agent SDK -> say_stream = WORKS

- Full brain pattern proven live in the sandbox: SDK session (claude-agent-sdk 0.2.93,
  model claude-opus-4-8) + in-process SDK-MCP tool + token streaming into the agent pane via
  `say_stream()` ChatStream (`append`/`stop`). Tool call rendered as a visible thinking line;
  final answer derived strictly from tool data.
- **The SDK ships a BUNDLED Claude Code CLI** (`claude_agent_sdk/_bundled/claude`): the Render
  worker needs NO separate CLI install. Deploy concern eliminated.
- Cost/latency on opus: $0.7298 for the query; 13.8s total, ~11s of it cold CLI boot.
  **Stage 4 design: persistent `ClaudeSDKClient` session per worker, never per-message
  `query()` cold boots.** Budget note: ~$0.73/verdict on opus is fine inside the
  $150-200 ceiling but smoke runs should count it.
- SDK defers MCP tools: the agent called ToolSearch to load `mcp__spike__lookup_fighter`
  before using it (one extra turn). Acceptable; revisit preloading in Stage 4.
- `say_stream` is injected via `context["say_stream"]` (AttachingConversationKwargs
  middleware); `ChatStream.stop(blocks=...)` can attach Block Kit at stream end - that is the
  verdict-card delivery mechanism for Stage 5.

### 2026-06-07 - Spike D: Data Table ("table") block = WORKS

- `chat.postMessage` with `type: "table"` block (rows of raw_text cells + column_settings)
  returned ok=true AND renders as a real table on desktop web AND iOS mobile
  (verified by Stephen, screenshots in session). Columns, alignment, wrapping all honored.
- Block schema per live docs: max 100 rows x 20 cells, raw_text/raw_number/rich_text cells,
  column align/is_wrapped. Adopted as the audit-ledger view for Stage 5;
  section-fields fallback not needed.

## Stage 5

### 2026-06-08 - Slack surface SHIPPED, all 4 beats verified live + adversarial-hardened

- Live in the CornerCheck sandbox, all four demo beats confirmed by screenshot:
  (1) Merab -> CLEAR card; (2) "Is Junior dos Santos cleared in Texas?" -> red DO NOT CLEAR
  card with cited CSAC suspension + 6306 consultation note; (3) "Is Bruno Silva cleared?"
  -> disambiguation card with 5 real candidates -> click Select -> inline verdict card
  logged to the ledger; (4) View audit trail button. Plus the agentic brain answering
  free-form with live source citation, and seeded ops conversations for the RTS beat.
- Architecture: deterministic clearance path (parse -> pipeline -> card) is the floor,
  no LLM dependency; the agentic brain is the flex for free-form/meta questions.
- TWO live bugs found + fixed during testing: (a) Select did nothing because the
  interactivity payload's thread_key doesn't share in-memory state -> confirm_candidate
  is now self-contained (re-resolves the button's query, requires the picked fighter to be
  a real candidate; still fail-closed); (b) action results posted as nested side-threads ->
  now chat_postMessage to the assistant thread root so verdicts render inline.
- Forced pre-merge adversarial review (code-reviewer + silent-failure-hunter, both verified
  against vendored Bolt source) -> all findings fixed with regression tests:
  - Bolt's default error handler only LOGS. A DB/ledger failure mid-clearance or mid-Select
    would strand the user. Both handlers now post an explicit FAIL-CLOSED non-clearance on
    any exception; a global app.error net catches the rest.
  - Routing used substring matching ("how" in "Howard" misrouted real clearance Qs to the
    brain). Now whole-word matching; "Is Howard/Scanlon/Whatley cleared?" routes to the card.
  - Spotlight envelope could be escaped by untrusted workspace text containing the literal
    closing tag. Now defanged (angle chars replaced); injection fence holds.
- 104 tests green.

## Stage 4

### 2026-06-07 - FROZEN CONTRACTS (Stage 5 builds against these; changes require a new entry)

MCP server: ONE FastMCP stdio server named `cornercheck`
(`python -m cornercheck.mcp_server.server`). Tool surface (7 of max 12):

| Tool | Args | Returns |
|---|---|---|
| er_resolve_fighter | query | {status: CONFIRMED/AMBIGUOUS/NOT_FOUND, note, candidates[{fighter_id, full_name, weight_class, record, sport, jurisdiction, score}]} |
| er_fighter_details | fighter_id | {fighter{...}, suspensions[{type,start,end,indefinite,jurisdiction,reason,source_url}]} |
| rules_evaluate_clearance | fighter_id, on_date?, target_jurisdiction? | {decision, on_date, active[], applied_rules[], consultation_note} |
| rules_outcome_window | outcome(TKO/KO/KO_LOC), cause?, sparring? | {days, applied_rules[]} |
| ledger_record_clearance | thread_key, fighter_id, decision, on_date?, target_jurisdiction?, actor | {recorded, seq?, hash?, refusal_reason?} |
| ledger_recent_entries | limit=10 | {entries[...]} |
| ledger_verify_chain | - | {ok, checked, first_bad_seq, detail} |

Search/RTS is NOT an MCP tool: the Bolt layer (Stage 5) runs the RTS scan itself and
injects results as spotlighted untrusted data in the prompt. Keeps the action_token out
of LLM-visible space and untrusted content out of the tool-result channel (report 17).

**Fail-closed = three independent locks:**
1. IN-TOOL: ledger_record_clearance re-runs the rule engine server-side; a decision that
   contradicts the engine is refused AND the denied attempt is itself ledgered
   (action=clearance_write_denied: the attack becomes audit evidence).
2. PRETOOLUSE HOOK: denies ledger_record_clearance unless the SessionStore shows the
   thread confirmed this exact fighter_id AND the engine verdict recorded for that thread
   matches the decision being written.
3. SCHEMA: brain output is a Pydantic ClearanceVerdict; the Slack card renders from the
   deterministic pipeline result, never from LLM prose.

Brain: ONE persistent ClaudeSDKClient (bundled CLI subprocess), per-Slack-thread
`session_id`, asyncio loop in a daemon thread with a sync `ask()` facade for Bolt.
Deterministic pipeline (er.resolve -> SessionStore -> rules.evaluate -> ledger.append)
drives the clearance card; the agent narrates and handles free-form Q&A via the tools.

### 2026-06-07 - Stage 4 SHIPPED: results + adversarial-review hardening

- Live smoke (twice, pre and post hardening): agent loads the real stdio MCP server,
  calls er_resolve + rules_evaluate live, narrates with verbatim source URL + 6306(b)
  note, and says "not my judgment, engine's". Adversarial override attempt REFUSED with
  a correct explanation of the guards. ~$0.9/turn opus; 26s cold, 6s warm.
- Forced adversarial review (code-reviewer + silent-failure-hunter, both verified
  findings against installed SDK source) converged on one critical: the SDK client's
  receive stream is a single shared queue with NO per-session demux, so concurrent or
  timed-out asks bleed responses across threads. FIXED: whole query+receive span
  serialized by an asyncio.Lock created on the loop thread; timeout cancels the
  coroutine and poisons the client (next ask rebuilds it).
- Also fixed from review: pipeline gate assert replaced with explicit fail-closed check
  (asserts vanish under -O); hook gate denies malformed payloads instead of passing;
  SessionStore.snapshot() so the gate never reads torn state; garbage fighter_id/date on
  the write tool returns a structured refusal that is ITSELF ledgered (probes leave a
  trace); denial-ledger failures surface as audit_warning instead of vanishing; every
  tool wrapped in a typed ERROR envelope that can never read as a clearance (system
  prompt rule 7 forbids inferring anything from ERROR).
- 74 tests green including regression tests pinning every review finding.

## Stage 3

### 2026-06-07 - Rule engine + entity resolution = SHIPPED, live-smoked on real data

- Rules are DATA: arp_base.yaml (ABC minimums TKO=30/KO=60; ARP KO_LOC=90) +
  state_overlays.yaml (ABC BSI head-shot overlay) + sparring overlay explicitly attributed
  to CornerCheck/ARP guidance, never to the ABC. Longest-rule-wins. A test proves a YAML
  override changes outcomes with zero Python edits.
- portion interval algebra for suspension windows (indefinite = right-open to infinity;
  overlaps union). Cross-jurisdiction active suspension attaches the 15 U.S.C. §6306(b)
  consultation note (enforce-the-law framing).
- ER: pg_trgm high-recall retrieve + Jaro-Winkler re-score + banding
  (T_HIGH=0.95, MARGIN=0.04, T_LOW=0.82; identical normalized names ALWAYS disambiguate;
  below T_LOW refuses). splink offline training deferred per plan slip clause; golden
  fixtures pin behavior; revisit in Stage 7.
- Live real-data smoke (2026-06-07): Bruno Silva -> AMBIGUOUS with BOTH real UFC Bruno
  Silvas at score 1.00; Dvalishvili -> CONFIRMED; dos Santos -> DO_NOT_CLEAR (indefinite
  CSAC, §6306 note vs Texas, source cited); Chavez Jr -> CLEAR today but DO_NOT_CLEAR
  back-dated to 2012-12-01 (time-travel demo beat); Diaz -> DO_NOT_CLEAR until 2026-11-12.
- 48 tests green: rule matrix, Hypothesis "CLEAR iff no active suspension" +
  "every blocking suspension is cited", ER banding goldens, live-Postgres ER fixtures
  (ZZ-Test throwaway fighters work on empty CI DB and seeded local DB alike).

## Stage 2

### 2026-06-07 - Seed data: dataset + 15 verified suspension cases

- **Fighters dataset: github.com/KgKevin0/UFC-Stats UFC_fighters.csv, MIT license (verified),
  4,107 real fighters.** Downloaded at seed time into gitignored seeds/data/downloads/, never
  committed. Backup option: fivethirtyeight undefeated-boxers (CC-BY-4.0). Skipped:
  Greco1899/scrape_ufc_stats (GPL-3.0; MIT alternative is cleaner for an Apache-2.0 repo).
- **15 suspension cases, every one source-cited and adversarially verified** (workflow
  wf_eb8d2099-8f9: 3 finder agents + per-case verifier agents fetching each source URL;
  1 case honestly rejected when its source supported the death narrative but not a formal
  suspension record). Manual spot-checks on the anchors: Santillan (BDB no-fight order until
  Jul 31, fought Jul 20 in Argentina) and Chavez Jr (NSAC 9 months, $900k) re-verified by hand.
- Coverage: 6 jurisdictions (CSAC, TDLR, NSAC, NYSAC, Maryland, German BDB), boxing + MMA,
  KO/TKO/medical/administrative. **Four suspensions genuinely active as of 2026-06-07**
  (dos Santos indefinite, Diaz to 2026-11-12, Brahimaj/Coria indefinite, Strickland indefinite):
  live real-data demo material, zero mocking.
- Demo scenario mapping asserted by seed_db.py on every run: CLEAR=Merab Dvalishvili;
  cross-jurisdiction=Julio Cesar Chavez Jr.; active suspension=Junior dos Santos;
  RTS chatter=Geoff Neal; disambiguation=Bruno Silva (TWO real UFC fighters share the name).

### 2026-06-07 - Ledger + environment facts

- Tamper-evidence demo verified end to end on real Postgres: INTACT -> forge seq 4 via
  session_replication_role=replica bypass -> verify reports BROKEN at exactly seq 4 -> reset.
- Local docker Postgres maps host port 5433 (system Postgres owns 5432 on this machine).
- psycopg3 runs param-less execute() over the simple protocol, so multi-statement migration
  files apply fine from the python runner; CI applies the same files via psql.
- **Local pytest leaves test-keyed ledger rows** (integration suite truncates/appends with the
  conftest test key). After running pytest locally: `verify_chain_demo.py reset` +
  `seed_db.py --force`. Future hardening: dedicated cornercheck_test database.
- Ledger payloads are floats-free JSON by design (jsonb round-trip determinism); enforced by
  UnsafePayloadError at append and covered by Hypothesis properties.

### STAGE 1 GATE: PASSED 2026-06-07

All four spikes WORKS on their primary paths; zero pre-chosen fallbacks adopted.
Completed in one evening vs the planned Jun 8-12 window. Stage 2 (data foundation +
hash-chain ledger) unblocked ~4 days ahead of schedule.
