# Asked & Answered — Explainer Demo Script v6
## "The Slack Agent That Refuses to Lie"

**Target length:** 3 minutes 15 seconds (195 s) — hard ceiling  
**Format:** Movie script with timestamp, voiceover, and exact on-screen actions.  
**Framing:** Google XYZ is now **inside the voiceover** — every beat speaks the problem (X), the action (Y), and the measurable outcome (Z). On-screen text is reserved for emphasis, not restatement.  
**Goal:** Make the value feel inevitable by the time the viewer hears it.

---

## 0:00 — 0:14 | HOOK: Confidence vs. proof

**VOICEOVER (XYZ):**  
"Most AI agents answer from confidence, which means they can invent compliance answers your team never gave. Asked & Answered answers from proof instead — and proves every claim — so a wrong answer never reaches a customer."

**ON SCREEN:**  
- Black screen. Left: generic chatbot with *"Answers from confidence"*. It flickers and shows a fake answer.  
- Right: Asked & Answered shield with *"Answers from proof"*.

**ON-SCREEN TEXT:**  
> Proof, not confidence.

---

## 0:14 — 0:30 | THE PAIN: Alice's Monday, quantified

**VOICEOVER (XYZ):**  
"Take Alice, a compliance lead. She gets a security questionnaire with forty-seven questions, but her team already answered forty-two of them in Slack threads she cannot find. So her company burns fifty senior-engineer hours and seven thousand five hundred dollars re-answering what it already knows."

**ON SCREEN:**  
- Slack DM with Alice. New message arrives: `enterprise-questionnaire-v3.xlsx`.  
- Alice's reaction emoji: 😩  
- Fast montage of past Slack messages, then a frustrated search gesture.
- Numbers animate in: **47 questions** · **42 already answered** · **50 hours** · **$7,500**

**ON-SCREEN TEXT:**  
> 47 questions. 42 already answered. 50 hours lost.

---

## 0:30 — 0:42 | THE PRODUCT: Upload turns history into answers

**VOICEOVER (XYZ):**  
"Alice uploads the questionnaire to Asked & Answered, and the agent streams a live plan: parse, search workspace evidence, draft through GroundingGate, build the review table. She sees the reasoning before she sees a single answer."

**ON SCREEN:**  
- Cursor clicks paperclip, selects `enterprise-questionnaire-v3.xlsx`, hits **Enter**.
- Streaming plan block appears:
  - ✅ Parse 47 questions → 41 unique
  - ⏳ Search workspace evidence
  - ⏳ Draft answers through GroundingGate
  - ⏳ Build review table

**ON-SCREEN TEXT:**  
> See the reasoning first.

---

## 0:42 — 0:56 | THE PLAN STREAMS: Transparency builds trust

**VOICEOVER (XYZ):**  
"Because the plan is visible, Alice trusts the process. Every step completes with a green checkmark, and the agent moves from search to draft to review without hiding anything in a black box."

**ON SCREEN:**  
- Plan block fills in green checkmarks one by one.

**ON-SCREEN TEXT:**  
> No black box.

---

## 0:56 — 1:14 | THE REVIEW TABLE: Three states, one rule

**VOICEOVER (XYZ):**  
"The review table puts every answer into one of three states. Verified means a human already approved it and every citation is still visible to Alice. Grounded means the model drafted it, but GroundingGate verified the cited snippet against the actual message. Needs SME means no evidence was found, so no answer is produced. Three states, one rule: no guesswork."

**ON SCREEN:**  
- Review table modal:

| Question | Status | Evidence | Action |
|---|---|---|---|
| Encrypt data at rest? | **Verified** | Approved library | Review |
| MFA enforced? | **Grounded** | #security, 3 msgs | Review |
| Cyber liability insurance? | **Needs SME** | None found | Route |
| Production data hosted? | **Grounded** | #infra, 2 msgs | Review |

**ACTION:**  
1. Hover over **Verified** → tooltip.  
2. Hover over **Grounded** → tooltip.  
3. Hover over **Needs SME** → tooltip.

**ON-SCREEN TEXT:**  
> Verified · Grounded · Needs SME

---

## 1:14 — 1:36 | THE PERMISSION FIREWALL: It forgets on purpose

**VOICEOVER (XYZ):**  
"Here is the moat. An approved answer exists for production data hosted in the EU, but the evidence lives in a private channel Alice cannot see. So Asked & Answered forgets the answer on purpose and degrades it to Needs SME. No answer text ever flows to a requester who cannot see all of its evidence."

**ON SCREEN:**  
- Row: *Production data hosted in EU?* flips **Verified → Needs SME**.
- Tooltip: *"Citation #security-eu-region is not visible to you. Answer withheld."*

**ACTION:**  
1. Cursor clicks **Review**. Modal opens:

> **Answer withheld.**
> You cannot see all evidence backing this approved answer.
> Routed to @security-sme.

**ON-SCREEN TEXT:**  
> Forgets on purpose.

---

## 1:36 — 1:54 | FAIL-CLOSED: No evidence, no answer

**VOICEOVER (XYZ):**  
"And when there is no evidence at all, the agent refuses to invent one. For cyber liability insurance, the workspace has nothing to cite, so the only safe choice is to route the question to a human expert. The safe choice becomes the only choice."

**ON SCREEN:**  
- Cursor clicks **Review** on *cyber liability insurance*. Empty answer field:

> **No evidence found. No answer given.**
> Routed to @finance-sme for approval.

**ACTION:**  
1. Cursor clicks **Route to @finance-sme**. DM opens with one-tap approve.

**ON-SCREEN TEXT:**  
> No evidence. No answer.

---

## 1:54 — 2:12 | APPROVE ONCE, REUSE FOREVER: Compounding value

**VOICEOVER (XYZ):**  
"When Alice approves the encrypt-at-rest answer, it enters the approved library. Next time the same question appears, Asked & Answered returns it as Verified in seconds — with the same citations, the same approver, and a fresh visibility check. One approval becomes a reusable compliance asset, and the next questionnaire starts mostly done."

**ON SCREEN:**  
- Cursor clicks **Approve** on *encrypt data at rest*. Confirmation card: *"Saved to approved library. Approver: @alice. Ledger entry #7."*
- Second questionnaire file drops. Counter ticks up: **42 of 47 Verified in 3 seconds.**

**ON-SCREEN TEXT:**  
> 42 of 47 Verified in 3 seconds.

---

## 2:12 — 2:22 | THE PROOF: Verify the chain yourself

**VOICEOVER (XYZ):**  
"Alice does not have to trust the bot. She clicks Verify ledger, and the public verifier confirms the approval chain is intact — every entry hash-linked, every signature valid, no host required."

**ON SCREEN:**  
- Cursor clicks **Verify ledger**. Browser opens to `/verify-ledger`.
- Page shows: **Ledger integrity: VERIFIED** · chain hash intact.

**ACTION:**  
1. Green **VERIFIED** badge fills screen for two seconds. Cut.

**ON-SCREEN TEXT:**  
> Don't trust. Verify.

---

## 2:22 — 2:34 | EXPORT & SEND: Provenance travels with the file

**VOICEOVER (XYZ):**  
"Alice exports the questionnaire and sends it to the customer. Native Canvas when the workspace supports it, a portable audit file when it doesn't — either way, the finished artifact carries its own evidence links and approval records, so the customer sees exactly where every answer came from."

**ON SCREEN:**  
- Cursor clicks **Export & send**. Slack compose window opens with `.xlsx` attached. Cursor clicks **Send**.
- Cut to recipient opening file. Cursor clicks **Evidence link** → original Slack message.

**ON-SCREEN TEXT:**  
> Every answer with receipts.

---

## 2:34 — 2:50 | THE COCKPIT: Catch stale answers before the customer

**VOICEOVER (XYZ):**  
"Three months later, new evidence in #security contradicts an approved answer. The App Home cockpit flags it before the customer notices — auto-answer rate, pending SME queues, and one stale-answer alert that just saved Alice from shipping last quarter's answer."

**ON SCREEN:**  
- App Home opens:
  - Auto-answer rate: 75%
  - SME hours saved this month: 37.5
  - **Stale approved answers: 1** ⚠️

**ACTION:**  
1. Cursor clicks **Stale approved answers** card. Modal: *"'Encrypt data at rest' may be contradicted by newer evidence in #security. Re-review suggested."*

**ON-SCREEN TEXT:**  
> It watches.

---

## 2:50 — 3:00 | THE SAFETY REPORT: Machine-checked trust

**VOICEOVER (XYZ):**  
"When her CISO asks how he knows the agent will not leak a private answer, Alice shows him the machine proof: the permission invariant is PROVED. Trust becomes reproducible, not promised."

**ON SCREEN:**  
- Alice clicks **Safety report**. Browser opens to `/safety-report/proof`.
- One card: **Permission invariant — PROVED**.
- CISO reaction: ✅

**ON-SCREEN TEXT:**  
> PROVED

---

## 3:00 — 3:15 | CLOSE: The business outcome

**VOICEOVER (XYZ):**  
"Asked & Answered turns Slack history into completed security questionnaires: forty-seven questions, forty-two answered from evidence, five routed to humans, zero invented. It is the Slack agent that refuses to lie."

**ON SCREEN:**  
- Final card:

> **Asked & Answered**
> *The Slack agent that refuses to lie.*
>
> Try it: asked-and-answered-app.onrender.com  
> Code: github.com/theCodeForgerHQ/asked-and-answered  
> **284 tests · 136/136 eval · Permission invariant proved · Live now.**

**ACTION:**  
1. Cursor clicks live app link. Landing page loads.

**ON-SCREEN TEXT:**  
> 42 answered · 5 routed · 0 invented.

---

## PRODUCTION NOTES

- **Hard ceiling 3:15.** Trim export beat if running long.
- **No motion graphics.** Real clicks, scrolls, keystrokes.
- **1080p, 60fps, highlighted cursor.**
- **Voiceover pace:** ~150 WPM; script is ~510 words.
- **On-screen text:** Keep each card to 3–5 words. They echo the Z, not restate the full XYZ.
- **Music:** tension under opening contrast and ACL beat; resolve on "No evidence found. No answer given."

## CHANGES FROM v5 → v6

1. **XYZ framing moved into voiceover.** Every spoken beat now carries problem → action → outcome.
2. **On-screen text simplified.** Removed full XYZ overlay boxes; now only punchy Z-statements appear.
3. **Hook sharpened** to contrast confidence vs. proof in one sentence.
4. **Value statements tightened** so the outcome lands immediately after the action.

## RUBRIC SCORING MAP

| Rubric | How v6 extracts maximum value from phrasing |
|---|---|
| **Impact** | Quantified pain (50 hrs, $7,500) → quantified payoff (42 of 47 Verified in 3s, 75% auto-answer). Honest about modeled savings. |
| **Design** | Modal as focus, graceful export fallback, App Home as cockpit. On-screen text supports rather than repeats. |
| **Idea** | Permission firewall, forgets on purpose, permission invariant PROVED. Category claim: permission layer for AI answers. |
| **Tech** | Safety proof tied to buyer fear: "won't leak a private answer." |
