# Asked & Answered — Explainer Demo Script v4
## "The Slack Agent That Refuses to Lie"

**Target length:** 3 minutes 10 seconds (190 s) — hard ceiling  
**Format:** Movie script with timestamp, voiceover, and exact on-screen actions.  
**Framing:** Google XYZ — every beat states the problem (X), the action (Y), and the measurable outcome (Z).  
**Goal:** Undisputed win on Impact, Design, and Idea by dramatizing the permission invariant — the one thing competitors cannot copy.

---

## 0:00 — 0:12 | HOOK: Alice's Monday

**VOICEOVER:**  
"It's Monday. Alice, the compliance lead, just got another security questionnaire. Forty-seven questions. Most of them, her team already answered."

**ON SCREEN:**  
- Slack DM with Alice. A new message arrives with an Excel attachment: `enterprise-questionnaire-v3.xlsx`.  
- Alice's reaction emoji: 😩  
- Fast montage of past Slack messages containing the same answers: encryption, MFA, hosting, incident response.

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

## 0:24 — 0:38 | THE UPLOAD: Questions in, plan out

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
  - ⏳ Search workspace evidence
  - ⏳ Draft answers through GroundingGate
  - ⏳ Build review table

**XYZ FRAMING overlay:**  
> Upload a questionnaire (X); the agent surfaces its retrieval plan live (Y), so reviewers trust the process before they see the answers (Z).

---

## 0:38 — 1:02 | THE REVIEW TABLE: Three states, one rule

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

## 1:02 — 1:22 | THE PERMISSION INVARIANT: Alice can't see it, so she can't get it

**VOICEOVER:**  
"This is the moat. An approved answer exists, but its evidence lives in a private channel Alice cannot see. Asked & Answered degrades it to Needs SME."

**ON SCREEN:**  
- Cursor hovers over a new row: *Production data hosted in EU?* Status flips from **Verified** → **Needs SME**.
- Tooltip appears: *"Citation #security-eu-region is not visible to you. Answer withheld."*

**ACTION:**  
1. Cursor clicks **Review** on the row.  
- Modal opens with empty answer field and text:

> **Answer withheld.**
> You cannot see all evidence backing this approved answer.
> Routed to @security-sme.

**VOICEOVER:**  
"No answer text ever flows to a requester who cannot see all of its evidence. Re-checked on every read."

**XYZ FRAMING overlay:**  
> A verified answer's evidence is invisible to the requester (X); the agent withholds the answer (Y), enforcing the permission invariant on every reuse (Z).

---

## 1:22 — 1:42 | FAIL-CLOSED: No evidence, no answer

**VOICEOVER:**  
"And when there is no evidence at all, the agent refuses to invent one."

**ON SCREEN:**  
- Cursor clicks **Review** on the *cyber liability insurance* row.  
- Modal opens. Empty answer field. Large text:

> **No evidence found. No answer given.**
> Routed to @finance-sme for approval.

**ACTION:**  
1. Cursor clicks **Route to @finance-sme**.  
- A DM to @finance-sme opens with the question and a one-tap **Approve** button.

**VOICEOVER:**  
"The safe default is human. Always."

**XYZ FRAMING overlay:**  
> When evidence is missing (X), the agent escalates instead of hallucinating (Y), eliminating compliance fiction at the source (Z).

---

## 1:42 — 2:00 | APPROVE ONCE, REUSE FOREVER

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

## 2:00 — 2:10 | THE PROOF: One cut to verified

**VOICEOVER:**  
"Alice doesn't have to trust the bot. She verifies the chain herself."

**ON SCREEN:**  
- In the confirmation card, cursor clicks **Verify ledger**.  
- Browser opens to `https://asked-and-answered-app.onrender.com/verify-ledger`.  
- Page shows: **Ledger integrity: VERIFIED** · 8 entries · chain hash intact.

**ACTION:**  
1. Cursor clicks **Verify ledger** link.  
2. Green **VERIFIED** badge fills the screen for one second. Cut.

**XYZ FRAMING overlay:**  
> Every approval event (X) is written to a public, tamper-evident ledger (Y), so Alice can verify integrity without trusting the host (Z).

---

## 2:10 — 2:22 | EXPORT & SEND: Ready for the customer

**VOICEOVER:**  
"Alice exports the questionnaire — with citations and approvals — straight to the customer."

**ON SCREEN:**  
- Cursor clicks **Export & send** under the review table.  
- A Slack compose window opens with the exported `.xlsx` attached.  
- Cursor clicks **Send**.

**ACTION:**  
1. Cut to recipient opening the file.  
2. Cursor clicks an **Evidence link** cell → opens original Slack message.

**XYZ FRAMING overlay:**  
> The finished artifact (X) carries its own provenance (Y), so customers and auditors see where every answer came from (Z).

---

## 2:22 — 2:38 | THE CLIFFHANGER: Stale answer, caught early

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

## 2:38 — 2:48 | THE SAFETY REPORT: Five seconds of proof

**VOICEOVER:**  
"When her CISO asks how she knows it's safe, Alice shows him one number."

**ON SCREEN:**  
- Alice clicks **Safety report**. Browser opens to `/safety-report/proof`.
- One metric card animates in: **Z3 proof: PROVED**.
- CISO's Slack reaction: ✅

**ACTION:**  
1. Cursor clicks **Safety report** link.  
2. Browser opens. Single green card: **Permission invariant — PROVED**.  
3. Cut back to Alice.

**XYZ FRAMING overlay:**  
> The safety claim (X) is machine-proved (Y), so trust is reproducible, not promised (Z).

---

## 2:48 — 3:00 | CLOSE: The agent that refuses to lie

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

- **Hard ceiling 3:10.** If recording runs long, trim the export beat before the safety report.
- **No motion graphics.** Every action is a real click, scroll, or keystroke.
- **1080p, 60fps, highlighted cursor.**
- **Voiceover pace:** ~150 words/minute; script is ~485 words.
- **Music:** tension under RAG-bot contrast and ACL-redaction; resolve on "No evidence found. No answer given."

## RUBRIC SCORING MAP

| Rubric | How v4 scores it |
|---|---|
| **Impact** | Alice's arc, quantified savings, compounding reuse, stale-answer catch, export-to-customer payoff. |
| **Design** | 3-state UX, fail-closed modal, ACL-redaction beat, streaming plan, one-cut verifier, App Home cliffhanger. |
| **Idea** | "The Slack agent that refuses to lie" + permission invariant as the moat. |
| **Tech** | Safety report shows Z3 proof; ACL-redaction dramatizes the machine-checked invariant. |

## CHANGES FROM v3

1. **Added permission-invariant beat (1:02–1:22).** Shows an approved answer being withheld because the requester cannot see the evidence — the single most defensible advantage over Consensus and Arbiter.
2. **Shortened safety report (2:38–2:48).** One card, one proof, one reaction. No scrolling through metrics.
3. **Tightened export beat (2:10–2:22).** Export & send in one action, then cut to recipient.
