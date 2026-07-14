# Asked & Answered — Explainer Demo Script v2
## "The Slack Agent That Refuses to Lie"

**Target length:** 3 minutes (180 s) — hard cut  
**Format:** Movie script with timestamp, voiceover, and exact on-screen actions.  
**Framing:** Google XYZ — every beat states the problem (X), the action (Y), and the measurable outcome (Z).  
**Goal:** Win on Impact, Design, and Idea by telling a human story with engineering proof.

---

## 0:00 — 0:12 | HOOK: Alice's Monday

**VOICEOVER:**  
"It's Monday. Alice, the compliance lead, just got another security questionnaire. Forty-seven questions. Most of them, her team already answered."

**ON SCREEN:**  
- Slack DM with Alice. A new message arrives with an Excel attachment: `enterprise-questionnaire-v3.xlsx`.  
- Alice's reaction emoji: 😩  
- Cut to a fast montage of past Slack messages containing the same answers: encryption, MFA, hosting, incident response.

**XYZ FRAMING overlay:**  
> Compliance teams answer the same questions repeatedly (X), because approved answers are buried in Slack (Y), so deals stall and answers drift (Z).

---

## 0:12 — 0:24 | THE STAKES: The wrong answer is expensive

**VOICEOVER:**  
"One invented answer can cost two million dollars and an audit finding. The safe thing is not to answer faster. It's to answer only when you can prove it."

**ON SCREEN:**  
- Split screen. Left: a generic chatbot confidently typing *"Yes, we carry $5M cyber liability insurance."* Right: a red audit badge: **Control failure — no evidence**.  
- Text animates: **This is what a RAG bot does.**

**XYZ FRAMING overlay:**  
> Naive AI answers from confidence (X), which creates compliance fiction (Y), which kills deals and audits (Z).

---

## 0:24 — 0:40 | THE UPLOAD: Questions in, plan out

**VOICEOVER:**  
"Alice drags the questionnaire into Asked & Answered. It streams a plan she can read."

**ON SCREEN:**  
- Slack DM with Asked & Answered. Cursor clicks the paperclip icon, selects `enterprise-questionnaire-v3.xlsx`, hits **Enter**.

**ACTION:**  
1. Click paperclip in message composer.  
2. Select the questionnaire file.  
3. Press Enter to upload.

- The agent posts a streaming plan block:
  - ✅ Parse 47 questions → 41 unique
  - ⏳ Search workspace evidence with Real-Time Search
  - ⏳ Draft answers through GroundingGate
  - ⏳ Build review table

**XYZ FRAMING overlay:**  
> Upload a questionnaire (X); the agent surfaces its retrieval plan live (Y), so reviewers trust the process before they see the answers (Z).

---

## 0:40 — 1:05 | THE REVIEW TABLE: Three states, one rule

**VOICEOVER:**  
"Every row lands in one of three states. Verified. Grounded. Or Needs SME. There is no fourth state called 'guess.'"

**ON SCREEN:**  
- Block Kit Data Table appears:

| Question | Status | Evidence | Action |
|---|---|---|---|
| Encrypt data at rest? | **Verified** | Approved library | Review |
| MFA enforced? | **Grounded** | #security, 3 msgs | Review |
| Cyber liability insurance? | **Needs SME** | None found | Route |
| Production data hosted? | **Grounded** | #infra, 2 msgs | Review |

**ACTION:**  
1. Hover over **Verified** badge. Tooltip: *"Reused from approved library; visibility re-checked for you."*  
2. Hover over **Grounded** badge. Tooltip: *"Drafted from cited Slack messages; snippet verified by GroundingGate."*  
3. Hover over **Needs SME** badge. Tooltip: *"No evidence. No answer. Human routed."*

**XYZ FRAMING overlay:**  
> Every answer (X) is classified by evidence strength (Y), so hallucinated compliance claims are structurally impossible (Z).

---

## 1:05 — 1:25 | THE CONTRAST: What RAG does vs. what we do

**VOICEOVER:**  
"A RAG bot would have invented something for cyber liability insurance. Asked & Answered refuses."

**ON SCREEN:**  
- Cursor clicks **Review** on the *cyber liability insurance* row.  
- Modal opens. The answer field is empty. Large text:

> **No evidence found. No answer given.**
> Routed to @finance-sme for approval.

**ACTION:**  
1. Cursor clicks **Route to @finance-sme**.  
2. A DM to @finance-sme opens with the question and a one-tap **Approve** button.

**VOICEOVER:**  
"The safe default is human. Always."

**XYZ FRAMING overlay:**  
> When evidence is missing (X), the agent escalates instead of hallucinating (Y), eliminating compliance fiction at the source (Z).

---

## 1:25 — 1:45 | APPROVE ONCE, REUSE FOREVER: The compounding payoff

**VOICEOVER:**  
"When Alice approves an answer, it becomes a reusable asset."

**ON SCREEN:**  
- Cursor clicks **Review** on the *encrypt data at rest* row.  
- Modal shows the draft, three cited Slack messages, and an **Approve** button.  
- Cursor clicks **Approve**. Confirmation card: *"Saved to approved library. Approver: @alice. Ledger entry #7."*

**VOICEOVER:**  
"Next questionnaire, same question — Verified instantly."

**ON SCREEN:**  
- Alice pastes the same questions. The new table shows *Encrypt data at rest?* as **Verified** immediately.

**XYZ FRAMING overlay:**  
> One SME approval (X) becomes an instant, reusable compliance asset (Y), compounding across every future questionnaire (Z).

---

## 1:45 — 2:00 | THE PROOF: Signed, chained, public

**VOICEOVER:**  
"Every approval is signed and chained. Don't trust the host. Verify it."

**ON SCREEN:**  
- One cut: Alice clicks a **Verify ledger** link in the confirmation card.  
- Browser opens to `https://asked-and-answered-app.onrender.com/verify-ledger`.  
- Page shows: **Ledger integrity: VERIFIED** · 8 entries · chain hash intact · last entry #7.

**ACTION:**  
1. Cursor clicks **Verify ledger** link.  
2. Browser tab opens. Green **VERIFIED** badge fills the screen for one second.

**XYZ FRAMING overlay:**  
> Every approval event (X) is written to a public, tamper-evident ledger (Y), so auditors verify integrity without trusting the host (Z).

---

## 2:00 — 2:15 | EXPORT WITH RECEIPTS: Ready for the customer

**VOICEOVER:**  
"When Alice exports, the questionnaire carries its own proof."

**ON SCREEN:**  
- Cursor clicks **Export xlsx** under the review table.  
- File downloads. Cursor opens it. Columns:
  - Question
  - Answer
  - Status
  - Evidence links
  - Approved by
  - Ledger entry

**ACTION:**  
1. Cursor clicks an **Evidence link** cell → opens original Slack message.  
2. Cursor clicks a **Ledger entry** cell → opens public verifier.

**XYZ FRAMING overlay:**  
> The finished artifact (X) carries its own provenance (Y), so customers and auditors see where every answer came from (Z).

---

## 2:15 — 2:35 | THE CLIFFHANGER: Stale answer, caught early

**VOICEOVER:**  
"Three months later, new evidence contradicts an approved answer. Before the customer notices, the agent flags it."

**ON SCREEN:**  
- App Home KPI dashboard opens:
  - Auto-answer rate: 75%
  - SME hours saved this month: 37.5
  - **Stale approved answers: 1** ⚠️

**ACTION:**  
1. Cursor clicks the **Stale approved answers** card.  
- Modal: *"'Encrypt data at rest' may be contradicted by newer evidence in #security. Re-review suggested."*

**VOICEOVER:**  
"It doesn't just answer. It watches."

**XYZ FRAMING overlay:**  
> Approved answers decay (X); the agent surfaces staleness before it becomes a liability (Y), keeping the library trustworthy over time (Z).

---

## 2:35 — 2:50 | THE EVIDENCE: Reproducible engineering

**VOICEOVER:**  
"This isn't a demo-only prototype. Every safety claim is reproducible."

**ON SCREEN:**  
- Terminal window. Commands run:
  - `npm test` → **284 passing**
  - `npx tsx evals/run.ts` → **136/136 cases passed**
  - `npx tsx scripts/verifyInvariantZ3.ts` → **PROVED**
  - `npm run smoke` → **SMOKE PASS**

- Metrics overlay:
  - 28,712 questions/sec
  - 0 invariant violations across 136 eval cases

**XYZ FRAMING overlay:**  
> We ship evidence (X): 284 tests, 136-case eval, code-level Z3 proof, live public verifier (Y), so judges can reproduce the safety claim (Z).

---

## 2:50 — 3:00 | CLOSE: The agent that refuses to lie

**VOICEOVER:**  
"Asked & Answered. The Slack agent that refuses to lie."

**ON SCREEN:**  
- Final card:

> **Asked & Answered**
> *The Slack agent that refuses to lie.*
>
> Try it: asked-and-answered-app.onrender.com  
> Code: github.com/theCodeForgerHQ/asked-and-answered  
> **284 tests · 136/136 eval · Z3 proved · Live now.**

**ACTION:**  
1. Cursor clicks the live app link.  
2. Landing page loads with case studies.

**XYZ FRAMING overlay:**  
> We built the agent (X), proved it safe (Y), and shipped it live (Z).

---

## PRODUCTION NOTES

- **Hard 3:00 ceiling.** If any beat runs long, cut the terminal command list before cutting the human beats.
- **No motion graphics.** Every action is a real click, scroll, or keystroke.
- **1080p, 60fps, highlighted cursor.**
- **Voiceover pace:** ~150 words/minute; script is ~460 words.
- **Music:** tension under the RAG-bot contrast; resolve on "No evidence found. No answer given."

## RUBRIC SCORING MAP

| Rubric | How v2 scores it |
|---|---|
| **Impact** | Alice's emotional arc, quantified savings, compounding reuse, stale-answer catch, export with receipts. |
| **Design** | 3-state UX, fail-closed modal, streaming plan, one-cut verifier, App Home cliffhanger. |
| **Idea** | "The Slack agent that refuses to lie" — memorable, bounded, safety-first. |
| **Tech** | Terminal evidence + Z3 proof + live verifier shown, not just claimed. |
