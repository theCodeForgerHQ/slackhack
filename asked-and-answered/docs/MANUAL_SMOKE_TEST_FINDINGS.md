# Manual Smoke Test Findings — Asked & Answered

**Date:** 2026-07-14  
**Tester:** Kimi Code CLI  
**Scope:** Every HTTP endpoint, Slack event/action surface, core component, MCP server, real-LLM eval, and production deployment path tested manually via curl, synthetic Slack payloads, live Slack API calls, and direct script execution.

---

## 1. What was tested

### 1.1 Public web layer (Vercel)
- `https://public-sigma-orpin.vercel.app` — landing page
- `/case-studies/` and all four case-study pages
- `/install-success.html`

**Result:** All return 200 with correct titles and content.

### 1.2 Live app HTTP routes (Render)
Tested against `https://asked-and-answered-app.onrender.com` after the fixes in this pass.

| Route | Status | Notes |
|---|---|---|
| `GET /` | 200 | Serves landing page |
| `GET /health` | 200 | Plain-text `ok` |
| `GET /invariant` | 200 | `{"status":"pass","casesRun":50}` |
| `GET /docs/SUBMISSION.md` | 200 | Markdown served |
| `POST /slack/actions` | 401 | Mounted; signature verification active |
| `GET /slack/install` | 500 | Missing `SLACK_CLIENT_ID` env var (see blockers) |

### 1.3 Slack API connectivity
- `auth.test` with the Test Sandbox bot token — valid, team `Test Sandbox 123`
- `conversations.list`, `users.list`, `conversations.open`, `chat.postMessage`, `files.upload` — exercised
- Confirmed the installed bot token lacks `search:read`/`search:read.public` in the current sandbox, so the live RTS evidence engine fails closed (expected with a stale token; fresh install from manifest grants the scope)

### 1.4 Synthetic Slack events to local app
Signed payloads sent to `http://localhost:3000/slack/events` and `…/slack/actions`.

| Event / Action | Result |
|---|---|
| `app_home_opened` | 200 |
| `assistant_thread_started` | 200 |
| `message.im` text questionnaire | Full pipeline ran; review table + canvas fallback posted |
| `message.im` `verify ledger` | Bot posted ledger-verification blocks |
| `open_answer_card` | Answer card posted |
| `route_to_sme` | SME picker posted |
| `approve_answer` / `reject_answer` / `confirm_answer` | Correct gate behavior (e.g., "no draft to approve" for needs-SME questions) |
| `export_xlsx` | XLSX file uploaded to Slack DM |
| `export_canvas` | Markdown fallback posted |
| App Home actions (`apphome_run_questionnaire`, `apphome_verify_ledger`, `apphome_check_invariant`, `run_z3_verify`, `apphome_return_home`) | 200 (views.publish fails on fake view id, as expected) |
| Modal submissions (`sme_answer_modal`, `edit_answer_modal`) | 200; after persistence fix, answers are saved and compound on re-run |

### 1.5 End-to-end compounding flow (local)
1. Send 3 questions → all routed to SME (no evidence in sandbox).
2. SME provides answer for q1, confirms, approves.
3. Re-run same 3 questions → **only q1 auto-verified**, q2/q3 correctly routed to SME.

This verified that the conformal matcher fix eliminated the false-positive cross-question reuse seen before the fix.

### 1.6 Core component scripts
- `npm run smoke` — PASS
- `npx tsx evals/run.ts` (deterministic) — 127/127 PASS
- `npx tsx evals/run.ts` with `AA_EVAL_LLM=azure` — 127/127 PASS (after self-grounding retry)
- `npx tsx scripts/verifyInvariantZ3.ts` — PROVED
- `npx tsx scripts/verifyPipelineCodeLevel.ts` — PROVED
- `npx tsx scripts/measureImpact.ts` — generated ROI numbers
- `npx tsx scripts/testAzure.ts` — Azure OpenAI drafter works
- MCP server over stdio — initialize, tools/list, search_answers all respond correctly

### 1.7 Full automated test suite
- `npm run typecheck` — clean
- `npm test` — 268/268 passed

---

## 2. Critical issues found and fixed

### 2.1 `/slack/actions` endpoint not mounted in production HTTP mode
**Finding:** Bolt's `HTTPReceiver` defaults to only `/slack/events`. Block Kit actions and modal submissions returned 404 on the deployed app.

**Fix:** `src/app.ts:107-112` now passes `endpoints: ['/slack/events', '/slack/actions']` when not in Socket Mode.

**Verified:** `POST /slack/actions` on Render returns 401 (signature required), meaning the endpoint is mounted.

### 2.2 SME modal answers not persisted
**Finding:** `sme_answer_modal` and `edit_answer_modal` view handlers updated the in-memory `ReviewSession` but never called `putSession()`, so SME-provided answers and edits were lost after modal close.

**Fix:** Added `putSession(resolved.session)` after `smeProvide` and `edit` in `src/app.ts:875,888`.

**Verified:** After providing an SME answer, confirming, and approving, the answer is saved to the SQLite library and reused on the next questionnaire run.

### 2.3 Conformal matcher false positives
**Finding:** The token-Jaccard matcher with `qHat = 0.9` incorrectly matched "Do you carry cyber liability insurance?" against the approved answer for "Do you encrypt customer data at rest?", causing wrong answers to be auto-verified.

**Fix:**
- Removed stopwords before computing Jaccard in `src/core/conformal.ts`.
- Added a hard safety cap (`MAX_NONCONFORMITY = 0.6`) so matches require at least 40% content-word overlap.
- Added hard negative calibration pairs and regenerated `src/core/calibration.json`.

**Verified:** Re-running the compounding test with one approved answer now verifies only the matching question, not unrelated ones.

### 2.4 Azure real-LLM eval flakiness on verbatim grounding
**Finding:** `gpt-54-mini` occasionally paraphrased evidence, causing `GroundingGate` to reject the citation (`ungrounded_citations`). This produced 126/127 instead of 127/127.

**Fix:** `src/llm/openai.ts` now runs a self-grounding retry: if the first draft fails the same `GroundingGate` check used by the pipeline, it retries once with a stricter prompt demanding a contiguous verbatim quote.

**Verified:** Multiple Azure eval runs now consistently return 127/127.

### 2.5 Production Docker build failed
**Finding:** Render builds failed because:
- `node:22-slim` lacks build tools for `better-sqlite3`
- The repo root had no `Dockerfile` (it lived inside `asked-and-answered/`), and the Render service rootDir is empty
- `z3-solver` was a devDependency but is required at runtime for the App Home "Run Z3 proof" action
- `scripts/` was not copied into the production image

**Fix:**
- Added root `Dockerfile` that delegates into `asked-and-answered/`
- Installed `python3 make g++` in both build and runtime stages
- Moved `z3-solver` to `dependencies` in `package.json`
- Copied `scripts/` into the production image

**Verified:** Render deploy `srv-d9aj6a6rnols73ep2020` is now **live**.

---

## 3. Remaining blockers (require user action)

### 3.1 Render env vars for Slack install/OAuth
The Render service is live but `/slack/install` returns 500 because `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET` are not configured.

**Action required:** In the Render dashboard for `asked-and-answered-app`, set:
- `SLACK_CLIENT_ID` — from api.slack.com/apps → A0BHW9UC23A → OAuth & Permissions
- `SLACK_CLIENT_SECRET` — same location
- `SLACK_SIGNING_SECRET` — already present (app starts), but confirm it matches A0BHW9UC23A
- `SLACK_BOT_TOKEN` — already present (app starts)
- `AA_LEDGER_KEY` — already present (app starts)
- `AA_PUBLIC_URL=https://asked-and-answered-app.onrender.com` — set via API during this pass

### 3.2 Slack search scope in current sandbox token
The installed bot token in `Test Sandbox 123` lacks `search:read.public`, so live Slack search returns `not_allowed_token_type`. A fresh install from `slack/manifest.json` grants this scope.

### 3.3 Azure app not deployed
The Azure App Service `asked-and-answered-app` in `rg-asked-and-answered` does not exist. The parallel session referenced by earlier context did not complete the Azure deployment. The Render app is the current live target.

---

## 4. Verification summary

| Check | Result |
|---|---|
| Vercel landing + case studies | PASS |
| Render app live and routes mounted | PASS (modulo env blockers) |
| Synthetic Slack events/actions | PASS |
| End-to-end compounding, no false positives | PASS |
| `npm run typecheck` | PASS |
| `npm test` (268) | PASS |
| `npm run smoke` | PASS |
| Deterministic eval 127/127 | PASS |
| Azure real-LLM eval 127/127 | PASS |
| Z3 invariant + code-level proofs | PASS |
| MCP server stdio | PASS |
| Render production deploy | PASS |

---

## 5. Commits pushed

- `4b1eafb` — Manual smoke-test fixes: `/slack/actions` endpoint, conformal matcher safety cap, self-grounding LLM retry, modal persistence
- `9d935e1` — Fix Render build: add native build tools for better-sqlite3
- `8a95a17` — Add root Dockerfile for Render (delegates to asked-and-answered/)
- `b4bc0d4` — Render Dockerfile: copy scripts/ for runtime Z3 proof action
- `69bf742` — Move z3-solver to dependencies for runtime Z3 proof action

Pushed to `https://github.com/theCodeForgerHQ/slackhack.git` and `https://github.com/theCodeForgerHQ/asked-and-answered.git`.
