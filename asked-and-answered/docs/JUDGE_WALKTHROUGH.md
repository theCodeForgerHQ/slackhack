# Judge walkthrough (≈5 minutes)

Everything below runs in the shared developer sandbox we granted you access to
(`slackhack@salesforce.com` and `testing@devpost.com` are members). No setup.

## 0. Where to start
Open the **Asked & Answered** app in the sandbox → its **Messages** tab. You'll
see a welcome message with three prompts.

## 1. Run a questionnaire (60s)
Drag the file **`sample-questionnaire.xlsx`** (pinned in the app DM) into the
message box, or paste these lines:

```
Do you encrypt customer data at rest?
Is MFA enforced for all employees?
Do you carry cyber liability insurance?
Where is production data hosted?
```

The agent streams a plan, searches the workspace, and posts a **review table**.
Expected: encryption + MFA come back **Grounded** (with citations), insurance
comes back **Needs SME** (no evidence), hosting comes back **Needs SME** if you
are testing as a user without access to the private security channel.

## 2. See the fail-closed refusal (30s) — the core idea
Click **Review** on the *cyber liability insurance* row. The card shows **no
draft** and the line: *"Asked & Answered would rather ask a human than invent a
compliance answer."* This is the product in one screen.

## 3. Approve a grounded answer (30s)
Click **Review** on the *encrypt data at rest* row → read the draft and its
citation → **Approve**. It's saved to the answer library and logged.

## 4. Prove the compounding payoff (30s)
Paste the same four questions again. The encryption question now returns
**Verified** instantly (reused from your approval), with the approver credited —
and re-checked against your permissions.

## 5. Prove tamper-evidence (30s)
In the DM, type `verify ledger`. You'll see the approval chain verified intact.
(Our repo's `npm run smoke` demonstrates detection when an entry is altered.)

## 6. Export (20s)
Click **Export xlsx** under the review table. You get the completed
questionnaire with every answer's citations and approval record.

## 7. The MCP angle (optional, 60s)
`asked-answered-mcp` exposes the approved-answer library as read-only tools
(`search_answers`, `get_answer_provenance`). See `docs/ARCHITECTURE.md` and
`src/mcp/server.ts`. It honors the same visibility invariant and fails closed:
unconfigured, it redacts every evidence-backed answer; disclosure is opt-in.

---

### What to look at in the code
- The invariant: `src/core/library.ts` (`findVerified`) + `src/core/pipeline.ts`.
- Rate-aware retrieval: `src/core/planner.ts` (`QueryPlanner`, `RateBudget`).
- Tamper-evident ledger: `src/core/ledger.ts`.
- Eval numbers: `docs/EVALS.md` (reproduce with `npx tsx evals/run.ts`).
- 91 hermetic tests: `npm test`. Full offline loop: `npm run smoke`.
