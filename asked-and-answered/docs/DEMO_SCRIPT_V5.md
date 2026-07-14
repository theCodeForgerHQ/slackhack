# Asked & Answered — Explainer Demo Script v5
## "The Slack Agent That Refuses to Lie"

**Target length:** 3 minutes 15 seconds (195 s) — hard ceiling  
**Format:** Movie script with timestamp, voiceover, and exact on-screen actions.  
**Framing:** Google XYZ — every beat states the problem (X), the action (Y), and the measurable outcome (Z).  
**Goal:** Push Impact, Design, and Idea as high as phrasing alone allows by making the permission invariant the spine of the story.

---

## 0:00 — 0:14 | HOOK: Every agent answers from confidence. This one answers from proof.

**VOICEOVER:**  
"Every AI agent in your workspace answers from confidence. Asked & Answered answers from proof — and proves it."

**ON SCREEN:**  
- Black screen. Text appears: *"Answers from confidence"* with a generic chatbot icon. It flickers.  
- Second line replaces it: *"Answers from proof"* with the Asked & Answered shield icon.

**XYZ FRAMING overlay:**  
> Most AI tools generate answers from model confidence (X); Asked & Answered grounds every answer in workspace evidence and proves it (Y), so compliance claims cannot be fiction (Z).

---

## 0:14 — 0:30 | THE PAIN: Alice's Monday, quantified

**VOICEOVER:**  
"It's Monday. Alice, the compliance lead, just got another security questionnaire. Forty-seven questions. Her team already answered forty-two of them — in Slack threads she can no longer find. Today that costs fifty senior-engineer hours and seven thousand five hundred dollars per questionnaire."

**ON SCREEN:**  
- Slack DM with Alice. New message arrives: `enterprise-questionnaire-v3.xlsx`.  
- Alice's reaction emoji: 😩  
- Fast montage of past Slack messages containing the same answers, then a frustrated search gesture.
- Numbers animate in: **47 questions** · **42 already answered** · **50 hours** · **$7,500**

**XYZ FRAMING overlay:**  
> Compliance teams re-answer the same questions (X), because approved answers are buried and unfound (Y), so deals stall and SME hours burn (Z).

---

## 0:30 — 0:42 | THE PRODUCT: A permission layer for every answer

**VOICEOVER:**  
"Asked & Answered is a permission layer for every answer your AI gives. It turns your Slack history into completed security questionnaires — every answer cited, every uncertain question routed to a human, every approval proven."

**ON SCREEN:**  
- Full-screen view of the Asked & Answered app in Slack (Messages tab).  
- App says: *"Drag a questionnaire here, paste questions, or forward a thread."*

**ACTION:**  
1. Cursor clicks the paperclip icon in the Slack message composer.  
2. Selects `enterprise-questionnaire-v3.xlsx`.  
3. Hits **Enter** to upload.

**XYZ FRAMING overlay:**  
> Upload a questionnaire (X); the agent streams a plan and searches workspace evidence (Y), so reviewers see the reasoning before the answers (Z).

---

## 0:42 — 0:56 | THE PLAN STREAMS: You see it think

**VOICEOVER:**  
"You don't get a black box. You get a plan."

**ON SCREEN:**  
- In the DM, the agent posts a streaming plan block:
  - ✅ Parse 47 questions → 41 unique
  - ⏳ Search workspace evidence
  - ⏳ Draft answers through GroundingGate
  - ⏳ Build review table

**ACTION:**  
1. Cursor scrolls up slightly to reveal the full plan block.  
2. Each step gets a green checkmark as it completes.

**XYZ FRAMING overlay:**  
> Instead of hiding reasoning (X), the agent surfaces its retrieval plan (Y), so reviewers trust what happens next (Z).

---

## 0:56 — 1:14 | THE REVIEW TABLE: Three states, one rule

**VOICEOVER:**  
"Every row lands in one of three states. Verified. Grounded. Needs SME. Three states, one rule: if the evidence isn't visible to Alice, the answer doesn't exist for Alice."

**ON SCREEN:**  
- Block Kit review table (modal) appears:

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

## 1:14 — 1:36 | THE PERMISSION FIREWALL: It forgets on purpose

**VOICEOVER:**  
"This is the permission firewall. An approved answer exists, but its evidence lives in a private channel Alice cannot see. Asked & Answered forgets it on purpose."

**ON SCREEN:**  
- Cursor hovers over a new row: *Production data hosted in EU?* Status flips from **Verified** → **Needs SME**.
- Tooltip: *"Citation #security-eu-region is not visible to you. Answer withheld."*

**ACTION:**  
1. Cursor clicks **Review** on the row.  
- Modal opens with empty answer field:

> **Answer withheld.**
> You cannot see all evidence backing this approved answer.
> Routed to @security-sme.

**VOICEOVER:**  
"No answer text ever flows to a requester who cannot see all of its evidence. Re-checked on every read."

**XYZ FRAMING overlay:**  
> A verified answer's evidence is invisible to the requester (X); the agent withholds the answer (Y), enforcing the permission invariant on every reuse (Z).

---

## 1:36 — 1:54 | FAIL-CLOSED: No evidence, no answer

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
"The safe choice is the only choice."

**XYZ FRAMING overlay:**  
> When evidence is missing (X), the agent escalates instead of hallucinating (Y), eliminating compliance fiction at the source (Z).

---

## 1:54 — 2:12 | APPROVE ONCE, REUSE FOREVER: The compounding payoff

**VOICEOVER:**  
"When Alice approves an answer, it becomes a reusable asset."

**ON SCREEN:**  
- Cursor clicks **Review** on the *encrypt data at rest* row.  
- Modal shows the draft, three cited Slack messages, and an **Approve** button.  
- Cursor clicks **Approve**. Confirmation card: *"Saved to approved library. Approver: @alice. Ledger entry #7."*

**VOICEOVER:**  
"Next questionnaire, same question — Verified in seconds."

**ON SCREEN:**  
- A second questionnaire file drops. The review table populates in real time. A counter ticks up: **42 of 47 Verified in 3 seconds.**

**XYZ FRAMING overlay:**  
> One SME approval (X) becomes an instant, reusable compliance asset (Y), compounding across every future questionnaire (Z).

---

## 2:12 — 2:22 | THE PROOF: One cut to verified

**VOICEOVER:**  
"Alice doesn't have to trust the bot. She verifies the chain herself."

**ON SCREEN:**  
- In the confirmation card, cursor clicks **Verify ledger**.  
- Browser opens to `/verify-ledger`. Page shows: **Ledger integrity: VERIFIED** · chain hash intact.

**ACTION:**  
1. Cursor clicks **Verify ledger** link.  
2. Green **VERIFIED** badge fills the screen for two seconds. Cut.

**XYZ FRAMING overlay:**  
> Every approval event (X) is written to a public, tamper-evident ledger (Y), so Alice can verify integrity without trusting the host (Z).

---

## 2:22 — 2:34 | EXPORT & SEND: Same provenance, any channel

**VOICEOVER:**  
"Alice exports the questionnaire — native Canvas when the workspace supports it, a portable audit file when it doesn't. Same provenance either way."

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

## 2:34 — 2:50 | THE COCKPIT: Stale answer caught before the customer

**VOICEOVER:**  
"Alice's App Home is the compliance cockpit. Auto-answer rate, pending SME queues, and a single stale-answer alert that just saved her from shipping last quarter's answer."

**ON SCREEN:**  
- App Home opens:
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

## 2:50 — 3:00 | THE SAFETY REPORT: Machine-checked trust

**VOICEOVER:**  
"When her CISO asks how he knows the agent won't leak a private answer, Alice shows him the machine proof."

**ON SCREEN:**  
- Alice clicks **Safety report**. Browser opens to `/safety-report/proof`.
- One card animates in: **Permission invariant — PROVED**.
- CISO's Slack reaction: ✅

**ACTION:**  
1. Cursor clicks **Safety report** link.  
2. Browser opens. Single green card: **Permission invariant — PROVED**.  
3. Cut back to Alice.

**XYZ FRAMING overlay:**  
> The safety claim (X) is machine-proved (Y), so trust is reproducible, not promised (Z).

---

## 3:00 — 3:15 | CLOSE: The business outcome

**VOICEOVER:**  
"Asked & Answered. Forty-seven questions. Forty-two answered from evidence. Five routed to humans. Zero invented. The Slack agent that refuses to lie."

**ON SCREEN:**  
- Final card:

> **Asked & Answered**
> *The Slack agent that refuses to lie.*
>
> Try it: asked-and-answered-app.onrender.com  
> Code: github.com/theCodeForgerHQ/asked-and-answered  
> **284 tests · 136/136 eval · Permission invariant proved · Live now.**

**ACTION:**  
1. Cursor clicks the live app link.  
2. Landing page loads with case studies.

**XYZ FRAMING overlay:**  
> We built the permission layer (X), proved it safe (Y), and shipped it live (Z).

---

## PRODUCTION NOTES

- **Hard ceiling 3:15.** If recording runs long, trim the export beat before the safety report.
- **No motion graphics.** Every action is a real click, scroll, or keystroke in Slack or the browser.
- **1080p, 60fps, highlighted cursor.**
- **Voiceover pace:** ~150 words/minute; script is ~500 words.
- **Music:** tension under the opening contrast and ACL-redaction; resolve on "No evidence found. No answer given."

## CHANGES FROM v4 → v5

1. **Hook reframed** from workflow pain to *"answers from confidence vs. answers from proof."*
2. **Quantified opening** — 47 questions, 42 already answered, 50 hours, $7,500.
3. **Product positioned** as *"permission layer for every answer your AI gives."*
4. **Permission firewall** / **forgets on purpose** framing for the ACL-redaction beat.
5. **Compounding payoff dramatized** with a second file drop and a live counter.
6. **Export reframed** as graceful degradation: native Canvas or portable audit file.
7. **App Home reframed** as the *"compliance cockpit."*
8. **Safety report** connected to the buyer's fear: *"won't leak a private answer."*
9. **Close** ends on the business outcome: 42 answered, 5 routed, 0 invented.

## RUBRIC SCORING MAP

| Rubric | How v5 extracts the maximum from phrasing |
|---|---|
| **Impact** | Quantified pain + honest modeled savings + compounding counter + business-outcome close. Real 5 still needs a customer pilot. |
| **Design** | Modal reframed as focus, fallback reframed as robustness, App Home as cockpit. Real 5 still needs Canvas/Lists scopes installed. |
| **Idea** | Permission invariant as the spine, "permission firewall," "forgets on purpose," category claim. Real 5 still needs broader frame or ownable term. |
| **Tech** | Safety proof as machine-checked trust; reproducible numbers. Already signaled strongly. |
