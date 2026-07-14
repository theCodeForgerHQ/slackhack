# Asked & Answered — Explainer Demo Script v1
## "The Slack Agent That Refuses to Lie"

**Target length:** 3 minutes 30 seconds (210 s)  
**Format:** Movie script with timestamp, voiceover, and exact on-screen actions.  
**Framing:** Google XYZ — every beat states the problem (X), the action (Y), and the measurable outcome (Z).  
**Goal:** Win on Impact, Design, and Idea scores by making the fail-closed compliance memory feel inevitable.

---

## 0:00 — 0:12 | HOOK: The question you already paid to answer

**VOICEOVER:**  
"Every security questionnaire asks something your team already answered. Somewhere. In Slack."

**ON SCREEN:**  
- Black screen. A single Slack message fades in: *"Yes, we encrypt all customer data at rest using AES-256."*  
- Cut to a security questionnaire Excel sheet. Cursor highlights the same question: *"Do you encrypt customer data at rest?"*  
- A red stamp appears: **UNANSWERED — SME NEEDED**.

**XYZ FRAMING overlay:**  
> Teams re-answer the same compliance question 20× per year (X), because no one can find the last approved answer (Y), so deals slow down and answers drift (Z).

---

## 0:12 — 0:28 | THE STAKES: One wrong answer costs more than one late answer

**VOICEOVER:**  
"Sales says yes. Legal finds out later. One invented answer can kill a two-million-dollar deal — or turn an audit into a finding."

**ON SCREEN:**  
- Split screen. Left: a Slack DM with Asked & Answered. Right: a mock audit report with a red **Control failure: answer not evidenced** badge.  
- Numbers animate in:
  - **40+ SME hours** per enterprise questionnaire
  - **$5,625** simulated cost per 100 questions
  - **0 tolerance** for hallucinated compliance claims

**XYZ FRAMING overlay:**  
> The cost of a wrong answer (X) is higher than the cost of a slow answer (Y), so the only safe default is to refuse to answer without evidence (Z).

---

## 0:28 — 0:45 | THE PRODUCT: Meet Asked & Answered

**VOICEOVER:**  
"Asked & Answered is a Slack-native agent that turns your workspace history into completed security questionnaires, RFPs, and vendor forms — every answer evidence-cited, SME-approved, and tamper-evidently logged."

**ON SCREEN:**  
- Full-screen view of the Asked & Answered app in Slack (Messages tab).  
- App says: *"Drag a questionnaire here, paste questions, or forward a thread."*

**ACTION (explicit):**  
1. Cursor clicks the paperclip icon in the Slack message composer.  
2. Selects `sample-questionnaire.xlsx` from the file picker.  
3. Hits **Enter** to upload.

**XYZ FRAMING overlay:**  
> Upload any questionnaire (X); the agent streams a plan and searches your workspace with Real-Time Search (Y); it returns every row as Verified, Grounded, or Needs SME (Z).

---

## 0:45 — 1:10 | THE PLAN STREAMS: You see it think

**VOICEOVER:**  
"You don't get a black box. You get a plan."

**ON SCREEN:**  
- In the DM, the agent posts a streaming plan block:
  - Step 1/4: Parse 4 questions → 3 unique
  - Step 2/4: Search workspace evidence with RTS
  - Step 3/4: Draft answers through GroundingGate
  - Step 4/4: Build review table

**ACTION:**  
1. Cursor scrolls up slightly to reveal the full plan block.  
2. Each step gets a green checkmark as it completes.

**VOICEOVER:**  
"It deduplicates, budgets Real-Time Search calls under the 10-per-minute limit, and routes each question to the right evidence."

**XYZ FRAMING overlay:**  
> Instead of hiding reasoning (X), the agent surfaces its retrieval plan (Y), so reviewers trust what happens next (Z).

---

## 1:10 — 1:45 | THE REVIEW TABLE: Three states, zero invented answers

**VOICEOVER:**  
"Now the review table. Three states. No answer text ever flows without evidence."

**ON SCREEN:**  
- A Block Kit Data Table appears in the DM with 4 rows:

| Question | Status | Source | Action |
|---|---|---|---|
| Encrypt data at rest? | **Verified** | Approved library | Review |
| MFA enforced? | **Grounded** | #security, 3 messages | Review |
| Cyber liability insurance? | **Needs SME** | No evidence found | Ask expert |
| Production data hosted? | **Needs SME** | Private channel | Ask expert |

**ACTION:**  
1. Cursor hovers over the **Verified** badge on row 1. Tooltip: *"Reused from approved library; visibility re-checked for you."*  
2. Cursor hovers over the **Grounded** badge on row 2. Tooltip: *"Drafted from cited Slack messages; snippet verified by GroundingGate."*  
3. Cursor hovers over the **Needs SME** badge on row 3. Tooltip: *"No evidence found. A human gets asked instead."*

**VOICEOVER:**  
"Verified means a human already approved it, and every citation is still visible to you. Grounded means the model drafted it, but GroundingGate checked the cited snippet against the actual messages. Needs SME means we refuse to invent an answer."

**XYZ FRAMING overlay:**  
> Every compliance answer (X) is classified by evidence strength (Y), so hallucinations are structurally impossible (Z).

---

## 1:45 — 2:10 | FAIL-CLOSED BY DESIGN: The agent that says "I don't know"

**VOICEOVER:**  
"This is the product in one screen. No evidence, no answer, no apology."

**ON SCREEN:**  
- Cursor clicks **Review** on the *cyber liability insurance* row.  
- A modal opens. The answer field is empty. Text reads:

> **Asked & Answered would rather ask a human than invent a compliance answer.**
>
> Reason: No workspace evidence found for "cyber liability insurance."
> Routed to: @finance-sme

**ACTION:**  
1. Cursor clicks the **Ask @finance-sme** button.  
2. A direct message to `@finance-sme` opens with the question pre-filled and a one-tap approve link.

**VOICEOVER:**  
"It doesn't guess. It doesn't soften. It routes to the right human and waits."

**XYZ FRAMING overlay:**  
> When evidence is missing (X), the agent escalates instead of hallucinating (Y), eliminating compliance fiction at the source (Z).

---

## 2:10 — 2:35 | APPROVE ONCE, REUSE FOREVER: The compounding payoff

**VOICEOVER:**  
"When a human does answer, the agent learns it — permission-checked and signed."

**ON SCREEN:**  
- Cursor clicks **Review** on the *encrypt data at rest* row.  
- Modal shows the draft answer, three cited Slack messages with permalinks, and an **Approve** button.  
- Cursor clicks **Approve**.  
- A confirmation card appears: *"Saved to approved library. Approver: @alice. Ledger entry #7."*

**VOICEOVER:**  
"That answer is now in the approved library. Next time the same question is asked, it comes back Verified — instantly."

**ON SCREEN:**  
- Cursor pastes the same four questions into the DM.  
- The new review table shows:

| Question | Status |
|---|---|
| Encrypt data at rest? | **Verified** |
| MFA enforced? | **Grounded** |
| Cyber liability insurance? | **Needs SME** |
| Production data hosted? | **Needs SME** |

**ACTION:**  
1. Cursor hovers over the **Verified** badge on row 1. Tooltip: *"Reused from approved library entry #7. Visibility re-checked."*

**XYZ FRAMING overlay:**  
> One SME approval (X) becomes an instant, reusable compliance asset (Y), compounding across every future questionnaire (Z).

---

## 2:35 — 2:55 | PROVE IT: Tamper-evident ledger

**VOICEOVER:**  
"Every approval is append-only and hash-chained. Don't trust us. Verify it."

**ON SCREEN:**  
- Cursor types `verify ledger` in the DM and sends.  
- The agent replies with a verification card:

> **Ledger integrity: VERIFIED**
> Entries: 8  
> Chain hash: intact  
> Last entry: #7 — approve "Encrypt data at rest"  
> Signature: valid  
> [Open public verifier](https://asked-and-answered-app.onrender.com/verify-ledger)

**ACTION:**  
1. Cursor clicks the **Open public verifier** link.  
2. Browser opens to `/verify-ledger`. The page shows the same hash chain and a green **VERIFIED** badge.  
3. Cursor scrolls down to show the JSON event log.

**XYZ FRAMING overlay:**  
> Every approval event (X) is written to a public, tamper-evident ledger (Y), so auditors can verify integrity without trusting the host (Z).

---

## 2:55 — 3:15 | EXPORT WITH RECEIPTS: Ready for the customer

**VOICEOVER:**  
"When you're done, export the questionnaire — with citations, approvals, and a tamper check."

**ON SCREEN:**  
- Back in Slack, cursor clicks **Export xlsx** under the review table.  
- A file download notification appears.  
- Cursor opens the downloaded Excel file. Columns show:
  - Question
  - Answer
  - Status
  - Evidence links
  - Approved by
  - Ledger entry

**ACTION:**  
1. Cursor clicks a cell under **Evidence links**. It opens the original Slack message in a browser tab.  
2. Cursor clicks a cell under **Ledger entry**. It opens the public verifier at that entry.

**XYZ FRAMING overlay:**  
> The finished artifact (X) carries its own proof of provenance (Y), so customers and auditors see where every answer came from (Z).

---

## 3:15 — 3:30 | APP HOME KPI DASHBOARD: See the value

**VOICEOVER:**  
"And for the person who owns compliance, the App Home shows the value in real time."

**ON SCREEN:**  
- Cursor clicks the Asked & Answered app icon in the Slack left sidebar.  
- App Home opens with KPI cards:
  - **Auto-answer rate:** 75%
  - **Pending SME reviews:** 3
  - **Stale approved answers:** 1
  - **SME hours saved this month:** 37.5
  - **Questions processed:** 100

**ACTION:**  
1. Cursor clicks the **Stale approved answers** card.  
2. A modal opens showing one answer with a warning: *"Newer evidence in #security may contradict this answer. Re-review suggested."*

**VOICEOVER:**  
"It doesn't just answer. It watches. It tells you when approved answers go stale."

**XYZ FRAMING overlay:**  
> Approved answers decay (X); the dashboard surfaces staleness before it becomes a liability (Y), keeping the library trustworthy over time (Z).

---

## 3:30 — 3:50 | THE EVIDENCE: Engineering you can reproduce

**VOICEOVER:**  
"This isn't a prototype that works in the demo. It's reproducible engineering."

**ON SCREEN:**  
- Terminal window appears. Commands run one after another:
  - `npm test` → **284 passing**
  - `npx tsx evals/run.ts` → **136/136 cases passed**
  - `npx tsx scripts/verifyInvariantZ3.ts` → **PROVED**
  - `npm run smoke` → **SMOKE PASS**
- A final metrics card overlays:
  - 28,712 questions/sec
  - 75% auto-answer rate
  - $5,625 saved per 100 questions
  - 0 invariant violations across 136 eval cases

**ACTION:**  
1. Cursor highlights the `PROVED` output from Z3.  
2. Screen splits to show the public verifier and the live Render app side by side.

**XYZ FRAMING overlay:**  
> We ship evidence (X): 284 tests, 136-case eval, code-level Z3 proof, and a live public verifier (Y), so judges can reproduce the safety claim (Z).

---

## 3:50 — 4:05 | THE IDEA: Fail-closed compliance memory

**VOICEOVER:**  
"Asked & Answered is not a chatbot. It is a fail-closed compliance memory for every Slack workspace. It makes your team's past answers searchable, approvable, reusable — and provably honest."

**ON SCREEN:**  
- A visual diagram animates:
  - Slack history → Real-Time Search → GroundingGate → SME approval → LedgerV2 → Approved library → Next questionnaire
- Each arrow lights up in sequence.

**XYZ FRAMING overlay:**  
> The idea (X): every compliance answer must be grounded in evidence and approved by a human (Y), creating a self-auditing institutional memory that scales trust (Z).

---

## 4:05 — 4:20 | CLOSING: The question every judge should ask

**VOICEOVER:**  
"The real question isn't whether AI can answer questionnaires. It's whether you can trust the answer. Asked & Answered proves you can."

**ON SCREEN:**  
- Final card with logo, tagline, and CTA:

> **Asked & Answered**
> *The Slack agent that refuses to lie.*
>
> Try it: [asked-and-answered-app.onrender.com](https://asked-and-answered-app.onrender.com)  
> Code: github.com/theCodeForgerHQ/asked-and-answered  
> **284 tests. 136/136 eval. Z3 proved. Live now.**

**ACTION:**  
1. Cursor clicks the live app link.  
2. Landing page loads. Cursor scrolls through case studies.

**XYZ FRAMING overlay:**  
> We built the agent (X), proved it safe (Y), and shipped it live (Z).

---

## PRODUCTION NOTES

- **No motion graphics.** Every action is a real click, scroll, or keystroke in Slack or a browser.
- **Screen captures should be at 1080p, 60fps, with cursor highlighted.**
- **Voiceover pace:** ~145 words per minute; script is ~520 words.
- **Background music:** subtle, builds during plan stream, drops for the "refuses to lie" beat.
- **Evidence overlays:** appear as clean lower-thirds, not walls of text.

## WHAT THIS SCRIPT SELLS

| Rubric | How the script scores it |
|---|---|
| **Impact** | Quantified savings, compounding reuse, App Home KPIs, export with receipts, public verifier. |
| **Design** | Clear 3-state UX, streaming plan, fail-closed modal, App Home dashboard, tamper-evident audit. |
| **Idea** | Fail-closed compliance memory; the agent that refuses to lie; trust through evidence, not model confidence. |
